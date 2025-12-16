# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/2 19:23
@Author   : wieszheng
@Software : PyCharm
"""
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float,Enum as SQLEnum
from datetime import datetime
from typing import List, Optional
import enum

from app.models.video import Base


class TaskStatus(str, enum.Enum):
    """任务状态"""
    DRAFT = "draft"                    # 草稿
    PROCESSING = "processing"          # 处理中
    PENDING_REVIEW = "pending_review"  # 待审核
    COMPLETED = "completed"            # 已完成
    CANCELLED = "cancelled"            # 已取消


class Task(Base):
    """任务表 - 用户创建的测试任务"""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # 项目关联
    project_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("projects.id"), 
        nullable=True, 
        index=True
    )

    # 状态信息
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus),
        default=TaskStatus.DRAFT,
        index=True
    )

    # 统计信息
    total_videos: Mapped[int] = mapped_column(Integer, default=0)
    completed_videos: Mapped[int] = mapped_column(Integer, default=0)
    failed_videos: Mapped[int] = mapped_column(Integer, default=0)

    # 耗时统计（毫秒）
    total_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)  # 所有视频总耗时
    avg_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)  # 平均耗时
    min_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)  # 最小耗时
    max_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)  # 最大耗时

    # 用户信息
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255))

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # 关系
    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")
    task_videos: Mapped[List["TaskVideo"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name={self.name}, status={self.status})>"

class TaskVideo(Base):
    """任务-视频关联表"""
    __tablename__ = "task_videos"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False, index=True)

    # 顺序
    sequence: Mapped[int] = mapped_column(Integer, default=0)

    # 耗时计算（毫秒）
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # 首尾帧信息（冗余字段，方便查询）
    first_frame_id: Mapped[Optional[str]] = mapped_column(String(255))
    last_frame_id: Mapped[Optional[str]] = mapped_column(String(255))
    first_frame_timestamp: Mapped[Optional[float]] = mapped_column(Float)
    last_frame_timestamp: Mapped[Optional[float]] = mapped_column(Float)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # 时间戳
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    task: Mapped["Task"] = relationship(back_populates="task_videos")
    video: Mapped["Video"] = relationship()

    def calculate_duration(self) -> Optional[int]:
        """
        计算耗时（毫秒）

        Returns:
        耗时（毫秒）或None

        """
        if self.first_frame_timestamp is not None and self.last_frame_timestamp is not None:
            duration_seconds = self.last_frame_timestamp - self.first_frame_timestamp
            return int(duration_seconds * 1000)  # 转换为毫秒
        return None


def __repr__(self) -> str:
    return f"<TaskVideo(task_id={self.task_id}, video_id={self.video_id})>"