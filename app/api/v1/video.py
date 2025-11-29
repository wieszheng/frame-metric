#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: video
@Author  : shwezheng
@Time    : 2025/11/29 21:53
@Software: PyCharm
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
import aiofiles
import os
from pathlib import Path

from app.database import get_async_db
from app.models.video import Video, Frame, VideoStatus, BatchUpload
from app.schemas.video import (
    VideoUploadResponse,
    BatchUploadResponse,
    VideoStatusResponse,
    BatchStatusResponse,
    TaskProgress,
    CancelTaskResponse,
    FrameResponse
)
from app.tasks.video_tasks import process_video_frames, \
    process_video_frames_full
from app.tasks.celery_app import celery_app
from app.services.minio_service import minio_service
from app.config import settings
from celery.result import AsyncResult
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=VideoUploadResponse,
             summary="上传单个视频")
async def upload_video(
        file: UploadFile = File(..., description="视频文件"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    上传单个视频文件

    - 验证文件格式和大小
    - 保存到临时目录
    - 触发后台任务处理
    - 立即返回task_id
    """

    # 1. 验证文件类型
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}. 支持的格式: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 2. 生成唯一ID
    video_id = str(uuid.uuid4())

    # 3. 保存文件
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    temp_filename = f"{video_id}{file_ext}"
    temp_path = os.path.join(settings.UPLOAD_DIR, temp_filename)

    try:
        # 流式保存文件
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            file_size = len(content)

            # 检查文件大小
            if file_size > settings.MAX_VIDEO_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"文件过大: {file_size / 1024 / 1024:.2f}MB, 最大允许: {settings.MAX_VIDEO_SIZE / 1024 / 1024:.0f}MB"
                )

            await f.write(content)

        # 4. 创建数据库记录
        video = Video(
            id=video_id,
            filename=temp_filename,
            original_filename=file.filename,
            file_size=file_size,
            status=VideoStatus.UPLOADING,
            progress=0,
            current_step="等待处理"
        )

        db.add(video)
        await db.commit()
        await db.refresh(video)

        # 5. 触发异步任务
        # task = process_video_frames.delay(video_id, temp_path)
        task = process_video_frames_full.delay(video_id, temp_path)
        # 6. 更新task_id
        video.task_id = task.id
        await db.commit()

        logger.info(f"Video uploaded: {video_id}, task: {task.id}")

        return VideoUploadResponse(
            video_id=video_id,
            task_id=task.id,
            status="processing",
            message="视频上传成功,正在后台处理"
        )

    except HTTPException:
        # 清理文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/batch-upload", response_model=BatchUploadResponse,
             summary="批量上传视频")
async def batch_upload_videos(
        files: List[UploadFile] = File(..., description="视频文件列表"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    批量上传视频文件

    - 支持同时上传多个视频(最多20个)
    - 每个视频独立处理
    - 返回批次ID用于统一查询
    """

    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")

    if len(files) > 20:
        raise HTTPException(status_code=400, detail="单次最多上传20个视频")

    # 创建批次
    batch_id = str(uuid.uuid4())
    batch = BatchUpload(
        id=batch_id,
        total_count=len(files)
    )
    db.add(batch)
    await db.commit()

    upload_results = []
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # 处理每个文件
    for file in files:
        try:
            # 验证文件
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in settings.ALLOWED_EXTENSIONS:
                upload_results.append(VideoUploadResponse(
                    video_id="",
                    task_id="",
                    status="failed",
                    message=f"{file.filename}: 不支持的格式"
                ))
                continue

            # 保存文件
            video_id = str(uuid.uuid4())
            temp_filename = f"{video_id}{file_ext}"
            temp_path = os.path.join(settings.UPLOAD_DIR, temp_filename)

            async with aiofiles.open(temp_path, 'wb') as f:
                content = await file.read()
                file_size = len(content)

                if file_size > settings.MAX_VIDEO_SIZE:
                    upload_results.append(VideoUploadResponse(
                        video_id="",
                        task_id="",
                        status="failed",
                        message=f"{file.filename}: 文件过大"
                    ))
                    continue

                await f.write(content)

            # 创建记录
            video = Video(
                id=video_id,
                batch_id=batch_id,
                filename=temp_filename,
                original_filename=file.filename,
                file_size=file_size,
                status=VideoStatus.UPLOADING
            )
            db.add(video)
            await db.commit()

            # 触发任务
            task = process_video_frames.delay(video_id, temp_path)
            video.task_id = task.id
            await db.commit()

            upload_results.append(VideoUploadResponse(
                video_id=video_id,
                task_id=task.id,
                status="processing",
                message=f"{file.filename} 上传成功"
            ))

        except Exception as e:
            logger.error(f"Batch upload error for {file.filename}: {e}")
            upload_results.append(VideoUploadResponse(
                video_id="",
                task_id="",
                status="failed",
                message=f"{file.filename}: {str(e)}"
            ))

    return BatchUploadResponse(
        batch_id=batch_id,
        total_count=len(files),
        videos=upload_results,
        message=f"批量上传完成,共{len(files)}个文件"
    )


@router.get("/status/{video_id}", response_model=VideoStatusResponse,
            summary="查询视频状态")
async def get_video_status(
        video_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """查询单个视频的处理状态和结果"""

    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # 获取帧信息
    frames_result = await db.execute(
        select(Frame).where(Frame.video_id == video_id)
    )
    frames = frames_result.scalars().all()

    return VideoStatusResponse(
        video_id=video.id,
        filename=video.original_filename,
        status=video.status.value,
        duration=video.duration,
        fps=video.fps,
        width=video.width,
        height=video.height,
        task_id=video.task_id,
        error_message=video.error_message,
        progress=video.progress,
        current_step=video.current_step,
        frames=[
            FrameResponse(
                id=f.id,
                type=f.id,
                url=f.minio_url,
                timestamp=f.timestamp,
                frame_number=f.frame_number
            ) for f in frames
        ],
        created_at=video.created_at
    )


@router.get("/progress/{video_id}", response_model=TaskProgress,
            summary="查询处理进度")
async def get_video_progress(
        video_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """实时查询视频处理进度"""

    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    return TaskProgress(
        video_id=video.id,
        task_id=video.task_id or "",
        status=video.status.value,
        progress=video.progress or 0,
        current_step=video.current_step or "等待处理",
        error_message=video.error_message
    )


@router.get("/batch-status/{batch_id}", response_model=BatchStatusResponse,
            summary="查询批次状态")
async def get_batch_status(
        batch_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """查询批次上传的整体状态"""

    # 查询批次中的所有视频
    result = await db.execute(
        select(Video).where(Video.batch_id == batch_id)
    )
    videos = result.scalars().all()

    if not videos:
        raise HTTPException(status_code=404, detail="批次不存在")

    # 统计状态
    completed_count = sum(
        1 for v in videos if v.status == VideoStatus.COMPLETED)
    failed_count = sum(1 for v in videos if v.status == VideoStatus.FAILED)
    processing_count = sum(
        1 for v in videos if v.status == VideoStatus.PENDING_REVIEW)

    # 获取每个视频的详细信息
    video_responses = []
    for video in videos:
        frames_result = await db.execute(
            select(Frame).where(Frame.video_id == video.id)
        )
        frames = frames_result.scalars().all()

        video_responses.append(VideoStatusResponse(
            video_id=video.id,
            filename=video.original_filename,
            status=video.status.value,
            duration=video.duration,
            fps=video.fps,
            width=video.width,
            height=video.height,
            task_id=video.task_id,
            error_message=video.error_message,
            progress=video.progress,
            current_step=video.current_step,
            frames=[
                FrameResponse(
                    id=f.id,
                    type=f.frame_type,
                    url=f.minio_url,
                    timestamp=f.timestamp,
                    frame_number=f.frame_number
                ) for f in frames
            ],
            created_at=video.created_at
        ))

    return BatchStatusResponse(
        batch_id=batch_id,
        total_count=len(videos),
        completed_count=completed_count,
        failed_count=failed_count,
        processing_count=processing_count,
        videos=video_responses
    )


@router.post("/cancel/{video_id}", response_model=CancelTaskResponse,
             summary="取消任务")
async def cancel_video_task(
        video_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """取消视频处理任务"""

    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    if video.status in [VideoStatus.COMPLETED, VideoStatus.FAILED,
                        VideoStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"无法取消已{video.status.value}的任务"
        )

    # 取消Celery任务
    if video.task_id:
        celery_app.control.revoke(video.task_id, terminate=True,
                                  signal='SIGKILL')
        logger.info(f"Cancelled task: {video.task_id}")

    # 更新数据库状态
    video.status = VideoStatus.CANCELLED
    video.error_message = "任务已被用户取消"
    video.progress = 0
    await db.commit()

    # 清理MinIO资源
    try:
        minio_service.delete_video_objects(video_id)
    except Exception as e:
        logger.error(f"Failed to clean up MinIO: {e}")

    return CancelTaskResponse(
        video_id=video_id,
        task_id=video.task_id or "",
        status="cancelled",
        message="任务已取消"
    )


@router.get("/task-info/{task_id}", summary="查询Celery任务信息")
async def get_task_info(task_id: str):
    """查询Celery任务的详细信息 (用于调试)"""

    try:
        result = AsyncResult(task_id, app=celery_app)

        return {
            "task_id": task_id,
            "state": result.state,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "failed": result.failed() if result.ready() else None,
            "result": str(result.result) if result.ready() else None,
            "traceback": str(result.traceback) if result.failed() else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", summary="列出所有视频")
async def list_videos(
        skip: int = 0,
        limit: int = 20,
        status: str = None,
        db: AsyncSession = Depends(get_async_db)
):
    """列出视频 (支持分页和状态过滤)"""

    query = select(Video)

    if status:
        try:
            status_enum = VideoStatus(status)
            query = query.where(Video.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")

    query = query.order_by(Video.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    videos = result.scalars().all()

    return {
        "total": len(videos),
        "videos": [
            {
                "video_id": v.id,
                "filename": v.original_filename,
                "status": v.status.value,
                "progress": v.progress,
                "created_at": v.created_at
            }
            for v in videos
        ]
    }
