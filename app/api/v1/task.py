# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/2 19:25
@Author   : wieszheng
@Software : PyCharm
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
import logging

from app.database import get_async_db
from app.crud.task import task_crud
from app.models.task import Task, TaskVideo, TaskStatus
from app.models.video import Video, Frame, FrameType, VideoStatus
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskDetailResponse,
    TaskVideoDetail,
    VideoAddToTask,
    TaskStatsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TaskResponse, summary="创建任务")
async def create_task(
        task_in: TaskCreate,
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建新任务

    - 用户创建一个空任务
    - 后续可以向任务中添加视频
    """
    task = Task(
        id=str(uuid.uuid4()),
        name=task_in.name,
        description=task_in.description,
        created_by=task_in.created_by,
        status=TaskStatus.DRAFT,
        total_videos=0,
        completed_videos=0,
        failed_videos=0
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"Task created: {task.id} by {task_in.created_by}")

    return TaskResponse.model_validate(task)


@router.get("/", response_model=List[TaskResponse], summary="获取任务列表")
async def list_tasks(
        user: str = None,
        skip: int = 0,
        limit: int = 20,
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取任务列表

    - 可选：按用户过滤
    - 支持分页
    """
    if user:
        tasks = await task_crud.get_by_user(db, user, skip=skip, limit=limit)
    else:
        tasks = await task_crud.get_multi(
            db,
            skip=skip,
            limit=limit,
            order_by=Task.created_at.desc()
        )

    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskDetailResponse,
            summary="获取任务详情")
async def get_task_detail(
        task_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取任务详情

    - 包含任务基本信息
    - 包含所有关联的视频列表
    - 包含每个视频的首尾帧信息
    """
    task = await task_crud.get_with_videos(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 构建视频详情列表
    video_details = []

    for tv in task.videos:
        video = tv.video

        # 查询首尾帧
        frames_stmt = select(Frame).where(
            Frame.video_id == video.id,
            Frame.frame_type.in_([FrameType.FIRST, FrameType.LAST])
        )
        frames_result = await db.execute(frames_stmt)
        frames = frames_result.scalars().all()

        first_frame = next(
            (f for f in frames if f.frame_type == FrameType.FIRST), None)
        last_frame = next((f for f in frames if f.frame_type == FrameType.LAST),
                          None)

        video_detail = TaskVideoDetail(
            id=tv.id,
            video_id=tv.video_id,
            order=tv.order,
            duration=tv.duration,
            first_frame_time=tv.first_frame_time,
            last_frame_time=tv.last_frame_time,
            notes=tv.notes,
            added_at=tv.added_at,
            video_filename=video.original_filename,
            video_status=video.status.value,
            video_width=video.width,
            video_height=video.height,
            first_frame_url=first_frame.minio_url if first_frame else None,
            last_frame_url=last_frame.minio_url if last_frame else None
        )
        video_details.append(video_detail)

    # 构建响应
    response = TaskDetailResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        status=task.status.value,
        total_videos=task.total_videos,
        completed_videos=task.completed_videos,
        failed_videos=task.failed_videos,
        total_duration=task.total_duration,
        avg_duration=task.avg_duration,
        min_duration=task.min_duration,
        max_duration=task.max_duration,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
        videos=video_details
    )

    return response


@router.put("/{task_id}", response_model=TaskResponse, summary="更新任务")
async def update_task(
        task_id: str,
        task_in: TaskUpdate,
        db: AsyncSession = Depends(get_async_db)
):
    """更新任务基本信息"""
    task = await task_crud.update_by_id(db, id=task_id, obj_in=task_in)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    await db.commit()

    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", summary="删除任务")
async def delete_task(
        task_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    删除任务

    - 级联删除所有关联的视频记录（不删除视频本身）
    """
    task = await task_crud.delete(db, id=task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    await db.commit()

    return {"message": "任务已删除", "task_id": task_id}


@router.post("/{task_id}/videos", summary="添加视频到任务")
async def add_videos_to_task(
        task_id: str,
        videos_in: VideoAddToTask,
        db: AsyncSession = Depends(get_async_db)
):
    """
    添加视频到任务

    - 支持批量添加
    - 视频必须已经上传并处理完成
    """
    task = await task_crud.get(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证视频是否存在
    for video_id in videos_in.video_ids:
        video = await db.get(Video, video_id)
        if not video:
            raise HTTPException(status_code=404,
                                detail=f"视频 {video_id} 不存在")

    # 添加视频到任务
    task_videos = await task_crud.add_videos_to_task(
        db,
        task_id=task_id,
        video_ids=videos_in.video_ids,
        notes=videos_in.notes
    )

    await db.commit()

    # 如果视频已处理完成，计算统计信息
    await task_crud.calculate_task_stats(db, task_id)
    await db.commit()

    return {
        "message": f"成功添加 {len(videos_in.video_ids)} 个视频",
        "task_id": task_id,
        "added_count": len(task_videos)
    }


@router.delete("/{task_id}/videos/{video_id}", summary="从任务中移除视频")
async def remove_video_from_task(
        task_id: str,
        video_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """从任务中移除指定视频"""
    success = await task_crud.remove_video_from_task(db, task_id, video_id)

    if not success:
        raise HTTPException(status_code=404, detail="视频不在该任务中")

    await db.commit()

    # 重新计算统计信息
    await task_crud.calculate_task_stats(db, task_id)
    await db.commit()

    return {"message": "视频已移除", "task_id": task_id, "video_id": video_id}


@router.post("/{task_id}/calculate", summary="计算任务统计")
async def calculate_task_statistics(
        task_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    计算任务统计信息

    - 计算所有视频的耗时（从首尾帧）
    - 更新任务的统计数据
    - 通常在视频处理完成后自动调用
    """
    task = await task_crud.get(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    await task_crud.calculate_task_stats(db, task_id)
    await db.commit()

    # 重新查询更新后的任务
    task = await task_crud.get(db, task_id)

    return {
        "message": "统计计算完成",
        "task_id": task_id,
        "total_duration": task.total_duration,
        "avg_duration": task.avg_duration,
        "completed_videos": task.completed_videos
    }


@router.get("/{task_id}/stats", response_model=TaskStatsResponse,
            summary="获取任务统计")
async def get_task_statistics(
        task_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取任务详细统计信息

    - 视频处理状态统计
    - 性能数据统计（耗时）
    - 帧数据统计
    """
    task = await task_crud.get_with_videos(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 统计视频状态
    processing_count = 0
    total_frames = 0

    for tv in task.videos:
        video = tv.video
        if video.status == VideoStatus.PROCESSING:
            processing_count += 1
        if video.extracted_frames:
            total_frames += video.extracted_frames

    avg_frames = total_frames / task.total_videos if task.total_videos > 0 else None

    return TaskStatsResponse(
        task_id=task.id,
        task_name=task.name,
        total_videos=task.total_videos,
        completed_videos=task.completed_videos,
        processing_videos=processing_count,
        failed_videos=task.failed_videos,
        total_duration=task.total_duration,
        avg_duration=task.avg_duration,
        min_duration=task.min_duration,
        max_duration=task.max_duration,
        total_frames=total_frames,
        avg_frames_per_video=avg_frames
    )