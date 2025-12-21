#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: video
@Author  : shwezheng
@Time    : 2025/11/27 00:03
@Software: PyCharm
"""
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, \
    Enum as SQLEnum, Boolean, Text
from datetime import datetime
from typing import List, Optional

from app.enums import VideoStatus, MarkingMethod, FrameType
from app.models.base import Base


class Video(Base):
    """视频表"""
    __tablename__ = "videos"

    # 主键
    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # 基本信息
    batch_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)

    # 视频属性
    duration: Mapped[Optional[float]] = mapped_column(Float)
    fps: Mapped[Optional[float]] = mapped_column(Float)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    total_frames: Mapped[Optional[int]] = mapped_column(Integer)
    extracted_frames: Mapped[Optional[int]] = mapped_column(Integer)

    # 存储路径
    minio_path: Mapped[Optional[str]] = mapped_column(String(255))

    # 处理状态
    status: Mapped[VideoStatus] = mapped_column(
        SQLEnum(VideoStatus),
        default=VideoStatus.UPLOADING,
        index=True
    )
    task_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[Optional[str]] = mapped_column(String(255))
    error_message: Mapped[Optional[str]] = mapped_column(String(255))

    # 智能标记相关
    marking_method: Mapped[Optional[MarkingMethod]] = mapped_column(
        SQLEnum(MarkingMethod))
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=True)

    # 审核信息
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    review_notes: Mapped[Optional[str]] = mapped_column(Text)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # 关系
    frames: Mapped[List["Frame"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan"
    )
    annotations: Mapped[List["FrameAnnotation"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, filename={self.filename}, status={self.status})>"


class Frame(Base):
    """帧表"""
    __tablename__ = "frames"

    # 主键
    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # 外键
    video_id: Mapped[str] = mapped_column(
        ForeignKey("videos.id"),
        nullable=False,
        index=True
    )

    # 帧信息
    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    minio_url: Mapped[str] = mapped_column(String(255), nullable=False)

    # 标记信息
    frame_type: Mapped[Optional[FrameType]] = mapped_column(SQLEnum(FrameType))
    is_first_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    is_last_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)

    # 特征信息
    scene_change_score: Mapped[Optional[float]] = mapped_column(Float)
    brightness: Mapped[Optional[float]] = mapped_column(Float)
    sharpness: Mapped[Optional[float]] = mapped_column(Float)
    has_motion: Mapped[Optional[bool]] = mapped_column(Boolean)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)

    # 关系
    video: Mapped["Video"] = relationship(back_populates="frames")
    annotations: Mapped[List["FrameAnnotation"]] = relationship(
        back_populates="frame",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Frame(id={self.id}, frame_number={self.frame_number}, type={self.frame_type})>"


class FrameAnnotation(Base):
    """帧标注表 - 记录标注历史"""
    __tablename__ = "frame_annotations"

    # 主键
    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # 外键
    video_id: Mapped[str] = mapped_column(
        ForeignKey("videos.id"),
        nullable=False,
        index=True
    )
    frame_id: Mapped[str] = mapped_column(
        ForeignKey("frames.id"),
        nullable=False
    )

    # 标注信息
    marked_as_first: Mapped[bool] = mapped_column(Boolean, default=False)
    marked_as_last: Mapped[bool] = mapped_column(Boolean, default=False)
    marking_method: Mapped[MarkingMethod] = mapped_column(
        SQLEnum(MarkingMethod),
        nullable=False
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    reason: Mapped[Optional[str]] = mapped_column(Text)

    # 审核信息
    annotator: Mapped[Optional[str]] = mapped_column(String(255))
    is_approved: Mapped[Optional[bool]] = mapped_column(Boolean)
    reviewer: Mapped[Optional[str]] = mapped_column(String(255))
    review_comment: Mapped[Optional[str]] = mapped_column(Text)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)

    # 关系
    video: Mapped["Video"] = relationship(back_populates="annotations")
    frame: Mapped["Frame"] = relationship(back_populates="annotations")

    def __repr__(self) -> str:
        return f"<FrameAnnotation(id={self.id}, frame_id={self.frame_id}, method={self.marking_method})>"


class BatchUpload(Base):
    """批次上传表"""
    __tablename__ = "batch_uploads"

    # 主键
    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # 批次信息
    total_count: Mapped[int] = mapped_column(Integer)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<BatchUpload(id={self.id}, total={self.total_count})>"
