# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/2 19:25
@Author   : wieszheng
@Software : PyCharm
"""
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
import logging

from app.database import get_async_db
from app.models.task import Task, TaskVideo, TaskStatus
from app.models.video import Video, Frame, VideoStatus, FrameType
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskVideoAdd,
    TaskVideoDetail,
    TaskStatistics,
    FrameMarkingUpdate,
    VideoFramesResponse
)
from app.crud.task import task_crud, task_video_crud
from app.crud.video import video_crud, frame_crud

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=TaskResponse, summary="创建任务")
async def create_task(
        task_in: TaskCreate,
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建新任务

    - name: 任务名称
    - description: 任务描述（可选）
    - created_by: 创建人
    """
    task_id = str(uuid.uuid4())

    task = Task(
        id=task_id,
        name=task_in.name,
        description=task_in.description,
        created_by=task_in.created_by,
        status=TaskStatus.DRAFT
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"任务创建成功: {task_id}, name={task_in.name}")

    return await _build_task_response(db, task)


@router.get("", response_model=List[TaskListResponse], summary="获取任务列表")
async def list_tasks(
        status: str = None,
        skip: int = 0,
        limit: int = 20,
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取任务列表

    - status: 筛选状态（可选）
    - skip: 跳过记录数
    - limit: 返回记录数
    """
    filters = {}
    if status:
        try:
            filters["status"] = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")

    tasks = await task_crud.get_multi(
        db,
        skip=skip,
        limit=limit,
        filters=filters,
        order_by=Task.created_at.desc()
    )

    return [
        TaskListResponse(
            id=t.id,
            name=t.name,
            status=t.status.value,
            total_videos=t.total_videos,
            completed_videos=t.completed_videos,
            failed_videos=t.failed_videos,
            pending_videos=t.total_videos - t.completed_videos - t.failed_videos,
            created_by=t.created_by,
            created_at=t.created_at,
            avg_duration_ms=t.avg_duration_ms
        )
        for t in tasks
    ]


@router.get("/{task_id}", response_model=TaskResponse, summary="获取任务详情")
async def get_task(
        task_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """获取任务详细信息，包含所有视频"""
    task = await task_crud.get_with_videos(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return await _build_task_response(db, task)


@router.put("/{task_id}", response_model=TaskResponse, summary="更新任务")
async def update_task(
        task_id: str,
        task_in: TaskUpdate,
        db: AsyncSession = Depends(get_async_db)
):
    """更新任务信息"""
    task = await task_crud.get(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_data = task_in.model_dump(exclude_unset=True)

    if "status" in update_data:
        update_data["status"] = TaskStatus(update_data["status"])

    task = await task_crud.update(db, db_obj=task, obj_in=update_data)
    await db.commit()

    return await _build_task_response(db, task)


@router.delete("/{task_id}", summary="删除任务")
async def delete_task(
        task_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """删除任务（及其所有关联视频）"""
    task = await task_crud.delete(db, id=task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    await db.commit()

    return {"message": "任务已删除", "task_id": task_id}


@router.post("/{task_id}/videos", response_model=TaskVideoDetail, summary="添加视频到任务")
async def add_video_to_task(
        task_id: str,
        video_in: TaskVideoAdd,
        db: AsyncSession = Depends(get_async_db)
):
    """
    添加已上传的视频到任务

    - video_id: 已上传的视频ID
    - notes: 备注（可选）
    """
    # 验证任务存在
    task = await task_crud.get(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证视频存在
    video = await video_crud.get(db, video_in.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # 检查是否已添加
    stmt = select(TaskVideo).where(
        TaskVideo.task_id == task_id,
        TaskVideo.video_id == video_in.video_id
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="视频已在任务中")

    # 添加视频
    task_video = await task_video_crud.add_video_to_task(
        db,
        task_id=task_id,
        video_id=video_in.video_id,
        notes=video_in.notes
    )

    # 更新任务统计
    await task_crud.update_statistics(db, task_id)

    await db.commit()
    await db.refresh(task_video)

    logger.info(f"视频添加到任务: task={task_id}, video={video_in.video_id}")

    return await _build_task_video_detail(db, task_video)


@router.delete("/{task_id}/videos/{task_video_id}", summary="从任务中移除视频")
async def remove_video_from_task(
        task_id: str,
        task_video_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """从任务中移除视频"""
    task_video = await task_video_crud.get(db, task_video_id)

    if not task_video or task_video.task_id != task_id:
        raise HTTPException(status_code=404, detail="任务视频不存在")

    await task_video_crud.delete(db, id=task_video_id)

    # 更新任务统计
    await task_crud.update_statistics(db, task_id)

    await db.commit()

    return {"message": "视频已从任务中移除"}


@router.get("/{task_id}/videos/{task_video_id}/frames", response_model=VideoFramesResponse, summary="获取视频所有帧")
async def get_video_frames(
        task_id: str,
        task_video_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取任务中某个视频的所有帧

    返回:
    - 所有帧的列表
    - 当前标记的首尾帧
    """
    # 查询任务视频
    task_video = await task_video_crud.get(db, task_video_id)
    if not task_video or task_video.task_id != task_id:
        raise HTTPException(status_code=404, detail="任务视频不存在")

    # 查询视频
    video = await video_crud.get(db, task_video.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # 查询所有帧
    frames = await frame_crud.get_by_video(db, video.id)

    # 找出标记的首尾帧
    marked_first = next((f for f in frames if f.frame_type == FrameType.FIRST), None)
    marked_last = next((f for f in frames if f.frame_type == FrameType.LAST), None)

    return VideoFramesResponse(
        video_id=video.id,
        total_frames=video.total_frames or 0,
        duration=video.duration or 0,
        filename= video.filename,
        fps=round(video.fps) or 0,
        width=video.width or 0,
        height=video.height or 0,
        extracted_frames=video.extracted_frames or 0,
        marked_first_frame_id=marked_first.id if marked_first else None,
        marked_last_frame_id=marked_last.id if marked_last else None,
        frames=[
            {
                "id": f.id,
                "frame_number": f.frame_number,
                "timestamp": f.timestamp,
                "url": f.minio_url,
                "frame_type": f.frame_type.value if f.frame_type else None,
                "is_first_candidate": f.is_first_candidate,
                "is_last_candidate": f.is_last_candidate,
                "brightness": f.brightness,
                "sharpness": f.sharpness
            }
            for f in frames
        ]
    )


@router.put("/{task_id}/videos/{video_id}/marking", response_model=TaskVideoDetail, summary="更新首尾帧标记")
async def update_frame_marking(
        task_id: str,
        video_id: str,
        marking: FrameMarkingUpdate,
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新视频的首尾帧标记

    - 更新帧类型
    - 重新计算耗时
    - 更新任务统计
    """
    # 查询任务视频

    task_video = await task_video_crud.get_video_id(db, video_id)

    if not task_video or task_video.task_id != task_id:
        raise HTTPException(status_code=404, detail="任务视频不存在")

    # 查询首帧
    first_frame = await frame_crud.get(db, marking.first_frame_id)
    if not first_frame or first_frame.video_id != task_video.video_id:
        raise HTTPException(status_code=400, detail="首帧不存在或不属于该视频")

    # 查询尾帧
    last_frame = await frame_crud.get(db, marking.last_frame_id)
    if not last_frame or last_frame.video_id != task_video.video_id:
        raise HTTPException(status_code=400, detail="尾帧不存在或不属于该视频")

    # 验证顺序
    if first_frame.frame_number >= last_frame.frame_number:
        raise HTTPException(status_code=400, detail="首帧必须在尾帧之前")

    # 清除旧标记
    all_frames_stmt = select(Frame).where(Frame.video_id == task_video.video_id, Frame.frame_type != None)
    all_frames_result = await db.execute(all_frames_stmt)
    all_frames = all_frames_result.scalars().all()

    for frame in all_frames:
        frame.frame_type = None

    # 设置新标记
    first_frame.frame_type = FrameType.FIRST
    last_frame.frame_type = FrameType.LAST

    # 更新Video信息状态
    video = await video_crud.get(db, task_video.video_id)
    if video:
        video.status = VideoStatus.REVIEWED
        video.current_step = "已审核"

    # 更新TaskVideo信息
    task_video.first_frame_id = first_frame.id
    task_video.last_frame_id = last_frame.id
    task_video.first_frame_timestamp = first_frame.timestamp
    task_video.last_frame_timestamp = last_frame.timestamp


    # 计算耗时
    duration_ms = last_frame.timestamp - first_frame.timestamp
    task_video.duration_ms = duration_ms

    # 更新任务统计
    await task_crud.update_statistics(db, task_id)

    await db.commit()
    await db.refresh(task_video)

    logger.info(
        f"首尾帧标记已更新: task_video={video_id}, "
        f"first={first_frame.frame_number}, last={last_frame.frame_number}, "
        f"duration={duration_ms}ms"
    )

    return await _build_task_video_detail(db, task_video)


@router.post("/{task_id}/complete", response_model=TaskResponse, summary="完成任务")
async def complete_task(
        task_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    标记任务为完成

    - 检查所有视频都已审核
    - 更新任务状态
    - 设置完成时间
    """
    task = await task_crud.get_with_videos(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查所有视频是否都已审核
    for tv in task.task_videos:
        video = await video_crud.get(db, tv.video_id)
        if video and video.status != VideoStatus.REVIEWED:
            raise HTTPException(
                status_code=400,
                detail=f"视频 {video.original_filename} 尚未审核完成"
            )

    # 更新任务状态
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(UTC)

    await db.commit()

    logger.info(f"任务已完成: {task_id}")

    return await _build_task_response(db, task)


# ============================================================
# 辅助函数
# ============================================================

async def _build_task_response(db: AsyncSession, task: Task) -> TaskResponse:
    """构建任务响应"""
    from datetime import datetime

    # 查询任务的所有视频
    task_videos = await task_video_crud.get_by_task(db, task.id)

    # 构建视频详情列表
    video_details = []
    for tv in task_videos:
        detail = await _build_task_video_detail(db, tv)
        video_details.append(detail)

    # 构建统计信息
    statistics = TaskStatistics(
        total_videos=task.total_videos,
        completed_videos=task.completed_videos,
        failed_videos=task.failed_videos,
        pending_videos=task.total_videos - task.completed_videos - task.failed_videos,
        total_duration_ms=task.total_duration_ms,
        avg_duration_ms=task.avg_duration_ms,
        min_duration_ms=task.min_duration_ms,
        max_duration_ms=task.max_duration_ms
    )

    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        status=task.status.value,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        statistics=statistics,
        videos=video_details
    )


async def _build_task_video_detail(db: AsyncSession, task_video: TaskVideo) -> TaskVideoDetail:
    """构建任务视频详情"""
    # 查询视频信息
    video = await video_crud.get(db, task_video.video_id)

    # 查询首尾帧URL
    first_frame_url = None
    last_frame_url = None

    if task_video.first_frame_id:
        first_frame = await frame_crud.get(db, task_video.first_frame_id)
        if first_frame:
            first_frame_url = first_frame.minio_url

    if task_video.last_frame_id:
        last_frame = await frame_crud.get(db, task_video.last_frame_id)
        if last_frame:
            last_frame_url = last_frame.minio_url

    return TaskVideoDetail(
        id=task_video.id,
        task_id=task_video.task_id,
        video_id=task_video.video_id,
        sequence=task_video.sequence,
        duration_ms=task_video.duration_ms,
        first_frame_id=task_video.first_frame_id,
        last_frame_id=task_video.last_frame_id,
        first_frame_timestamp=task_video.first_frame_timestamp,
        last_frame_timestamp=task_video.last_frame_timestamp,
        notes=task_video.notes,
        added_at=task_video.added_at,
        video_filename=video.original_filename if video else None,
        video_status=video.status.value if video else None,
        first_frame_url=first_frame_url,
        last_frame_url=last_frame_url
    )
