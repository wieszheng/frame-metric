#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: video
@Author  : shwezheng
@Time    : 2025/11/27 00:03
@Software: PyCharm
"""
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Enum as SQLEnum, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.enums.video import VideoStatus, FrameType


class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String)
    file_size = Column(Integer)
    duration = Column(Float)
    fps = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    minio_path = Column(String)
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.UPLOADING)
    task_id = Column(String)  # Celery任务ID
    error_message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    frames = relationship("Frame", back_populates="video", cascade="all, delete-orphan")


class Frame(Base):
    __tablename__ = "frames"

    id = Column(String, primary_key=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    frame_type = Column(SQLEnum(FrameType), nullable=False)
    minio_url = Column(String, nullable=False)
    timestamp = Column(Float, nullable=False)
    frame_number = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    video = relationship("Video", back_populates="frames")
