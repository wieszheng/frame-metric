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
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import select, func, and_

from app.core.crud_base import CRUDBase
from app.models.task import Task, TaskVideo, TaskStatus
from app.models.video import Video, Frame, FrameType, VideoStatus
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
            .options(
                selectinload(Task.videos).joinedload(TaskVideo.video)
            )
        )
        result = await db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def add_videos_to_task(
            self,
            db: AsyncSession,
            task_id: str,
            video_ids: List[str],
            notes: Optional[str] = None
    ) -> List[TaskVideo]:
        """添加视频到任务"""
        import uuid

        # 获取当前任务中的最大order
        max_order_stmt = (
            select(func.max(TaskVideo.order))
            .where(TaskVideo.task_id == task_id)
        )
        result = await db.execute(max_order_stmt)
        max_order = result.scalar() or 0

        # 创建关联记录
        task_videos = []
        for i, video_id in enumerate(video_ids):
            task_video = TaskVideo(
                id=str(uuid.uuid4()),
                task_id=task_id,
                video_id=video_id,
                order=max_order + i + 1,
                notes=notes
            )
            db.add(task_video)
            task_videos.append(task_video)

        await db.flush()

        # 更新任务的视频数量
        task = await self.get(db, task_id)
        if task:
            task.total_videos = task.total_videos + len(video_ids)

        return task_videos

    async def remove_video_from_task(
            self,
            db: AsyncSession,
            task_id: str,
            video_id: str
    ) -> bool:
        """从任务中移除视频"""
        stmt = select(TaskVideo).where(
            and_(
                TaskVideo.task_id == task_id,
                TaskVideo.video_id == video_id
            )
        )
        result = await db.execute(stmt)
        task_video = result.scalar_one_or_none()

        if task_video:
            await db.delete(task_video)

            # 更新任务的视频数量
            task = await self.get(db, task_id)
            if task:
                task.total_videos = max(0, task.total_videos - 1)

            return True

        return False

    async def calculate_task_stats(
            self,
            db: AsyncSession,
            task_id: str
    ) -> None:
        """计算任务统计信息（耗时等）"""
        # 查询任务的所有视频及其首尾帧
        stmt = (
            select(TaskVideo)
            .where(TaskVideo.task_id == task_id)
            .options(joinedload(TaskVideo.video))
        )
        result = await db.execute(stmt)
        task_videos = result.unique().scalars().all()

        durations = []
        completed_count = 0
        failed_count = 0

        for tv in task_videos:
            video = tv.video

            # 统计视频状态
            if video.status == VideoStatus.COMPLETED:
                completed_count += 1
            elif video.status == VideoStatus.FAILED:
                failed_count += 1

            # 计算耗时（从首尾帧）
            if video.status == VideoStatus.COMPLETED:
                # 查询首尾帧
                frames_stmt = select(Frame).where(
                    Frame.video_id == video.id,
                    Frame.frame_type.in_([FrameType.FIRST, FrameType.LAST])
                )
                frames_result = await db.execute(frames_stmt)
                frames = frames_result.scalars().all()

                first_frame = next(
                    (f for f in frames if f.frame_type == FrameType.FIRST),
                    None)
                last_frame = next(
                    (f for f in frames if f.frame_type == FrameType.LAST), None)

                if first_frame and last_frame:
                    duration = last_frame.timestamp - first_frame.timestamp

                    # 更新TaskVideo的耗时信息
                    tv.duration = duration
                    tv.first_frame_time = first_frame.timestamp
                    tv.last_frame_time = last_frame.timestamp

                    durations.append(duration)

        # 更新任务统计
        task = await self.get(db, task_id)
        if task:
            task.completed_videos = completed_count
            task.failed_videos = failed_count

            if durations:
                task.total_duration = sum(durations)
                task.avg_duration = sum(durations) / len(durations)
                task.min_duration = min(durations)
                task.max_duration = max(durations)

            # 更新任务状态
            if completed_count + failed_count == task.total_videos:
                task.status = TaskStatus.COMPLETED
            elif completed_count > 0 or failed_count > 0:
                task.status = TaskStatus.PROCESSING

        await db.flush()

    async def get_by_user(
            self,
            db: AsyncSession,
            user: str,
            skip: int = 0,
            limit: int = 20
    ) -> List[Task]:
        """查询用户的所有任务"""
        stmt = (
            select(Task)
            .where(Task.created_by == user)
            .order_by(Task.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


# 创建全局实例
task_crud = TaskCRUD(Task)