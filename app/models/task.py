# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/2 19:23
@Author   : wieszheng
@Software : PyCharm
"""
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float
from datetime import datetime
from typing import List, Optional
import enum

from app.models.video import Base


class TaskStatus(str, enum.Enum):
    """任务状态"""
    DRAFT = "draft"  # 草稿
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class Task(Base):
    """任务表 - 用户创建的测试任务"""
    __tablename__ = "tasks"

    # 基本信息
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # 任务元数据
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.DRAFT)
    total_videos: Mapped[int] = mapped_column(Integer, default=0)
    completed_videos: Mapped[int] = mapped_column(Integer, default=0)
    failed_videos: Mapped[int] = mapped_column(Integer, default=0)

    # 统计信息
    total_duration: Mapped[Optional[float]] = mapped_column(Float)  # 总耗时（秒）
    avg_duration: Mapped[Optional[float]] = mapped_column(Float)  # 平均耗时（秒）
    min_duration: Mapped[Optional[float]] = mapped_column(Float)  # 最小耗时（秒）
    max_duration: Mapped[Optional[float]] = mapped_column(Float)  # 最大耗时（秒）

    # 创建者信息
    created_by: Mapped[str] = mapped_column(String(255))

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow,
                                                 index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow,
                                                 onupdate=datetime.utcnow)

    # 关系
    videos: Mapped[List["TaskVideo"]] = relationship(back_populates="task",
                                                     cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name={self.name}, status={self.status})>"


class TaskVideo(Base):
    """任务-视频关联表"""
    __tablename__ = "task_videos"

    # 基本信息
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False,
                                         index=True)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"),
                                          nullable=False, index=True)

    # 排序
    order: Mapped[int] = mapped_column(Integer, default=0)

    # 性能数据（从首尾帧计算）
    duration: Mapped[Optional[float]] = mapped_column(Float)  # 耗时（秒）
    first_frame_time: Mapped[Optional[float]] = mapped_column(Float)  # 首帧时间戳
    last_frame_time: Mapped[Optional[float]] = mapped_column(Float)  # 尾帧时间戳

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # 时间戳
    added_at: Mapped[datetime] = mapped_column(DateTime,
                                               default=datetime.utcnow)

    # 关系
    task: Mapped["Task"] = relationship(back_populates="videos")
    video: Mapped["Video"] = relationship()  # 从 app.models.video 导入

    def __repr__(self) -> str:
        return f"<TaskVideo(task_id={self.task_id}, video_id={self.video_id}, duration={self.duration})>"