# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/2 19:25
@Author   : wieszheng
@Software : PyCharm
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, and_

from app.core.crud_base import CRUDBase
from app.models.task import Task, TaskVideo, TaskStatus
from app.models.video import Video, Frame, VideoStatus, FrameType
from pydantic import BaseModel


class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    created_by: str


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None


class TaskCRUD(CRUDBase[Task, TaskCreate, TaskUpdate]):
    """任务CRUD操作"""

    async def get_with_videos(
            self,
            db: AsyncSession,
            task_id: str
    ) -> Optional[Task]:
        """查询任务及其所有视频"""
        stmt = (
            select(Task)
            .where(Task.id == task_id)
            .options(selectinload(Task.task_videos))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_status(
            self,
            db: AsyncSession,
            status: TaskStatus,
            skip: int = 0,
            limit: int = 100
    ) -> List[Task]:
        """根据状态查询任务"""
        stmt = (
            select(Task)
            .where(Task.status == status)
            .order_by(Task.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_statistics(
            self,
            db: AsyncSession,
            task_id: str
    ):
        """更新任务统计信息"""
        # 查询任务的所有视频
        stmt = select(TaskVideo).where(TaskVideo.task_id == task_id)
        result = await db.execute(stmt)
        task_videos = result.scalars().all()

        # 查询任务
        task = await self.get(db, task_id)
        if not task:
            return

        # 统计
        total_videos = len(task_videos)
        completed_videos = 0
        failed_videos = 0
        durations = []

        for tv in task_videos:
            # 查询视频状态
            video_stmt = select(Video).where(Video.id == tv.video_id)
            video_result = await db.execute(video_stmt)
            video = video_result.scalar_one_or_none()

            if video:
                if video.status == VideoStatus.REVIEWED:
                    completed_videos += 1
                elif video.status == VideoStatus.FAILED:
                    failed_videos += 1

            # 收集耗时
            if tv.duration_ms:
                durations.append(tv.duration_ms)

        # 更新任务统计
        task.total_videos = total_videos
        task.completed_videos = completed_videos
        task.failed_videos = failed_videos

        if durations:
            task.total_duration_ms = sum(durations)
            task.avg_duration_ms = int(sum(durations) / len(durations))
            task.min_duration_ms = min(durations)
            task.max_duration_ms = max(durations)

        await db.flush()


class TaskVideoCRUD(CRUDBase[TaskVideo, BaseModel, BaseModel]):
    """任务视频CRUD操作"""

    async def get_by_task(
            self,
            db: AsyncSession,
            task_id: str
    ) -> List[TaskVideo]:
        """查询任务的所有视频"""
        stmt = (
            select(TaskVideo)
            .where(TaskVideo.task_id == task_id)
            .order_by(TaskVideo.sequence)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def add_video_to_task(
            self,
            db: AsyncSession,
            task_id: str,
            video_id: str,
            notes: Optional[str] = None
    ) -> TaskVideo:
        """添加视频到任务"""
        import uuid

        # 获取当前最大sequence
        stmt = select(func.max(TaskVideo.sequence)).where(TaskVideo.task_id == task_id)
        result = await db.execute(stmt)
        max_sequence = result.scalar_one_or_none() or 0

        # 创建关联
        task_video = TaskVideo(
            id=str(uuid.uuid4()),
            task_id=task_id,
            video_id=video_id,
            sequence=max_sequence + 1,
            notes=notes
        )

        db.add(task_video)
        await db.flush()

        return task_video

    async def update_duration(
            self,
            db: AsyncSession,
            task_video_id: str,
            first_frame_timestamp: float,
            last_frame_timestamp: float
    ):
        """更新耗时"""
        task_video = await self.get(db, task_video_id)
        if task_video:
            task_video.first_frame_timestamp = first_frame_timestamp
            task_video.last_frame_timestamp = last_frame_timestamp
            task_video.duration_ms = int((last_frame_timestamp - first_frame_timestamp) * 1000)
            await db.flush()

    async def get_video_id(
            self,
            db: AsyncSession,
            video_id: str
    ) -> Optional[TaskVideo]:
        """根据video_id查询任务视频"""
        stmt = select(TaskVideo).where(TaskVideo.video_id == video_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# 创建全局CRUD实例
task_crud = TaskCRUD(Task)
task_video_crud = TaskVideoCRUD(TaskVideo)
