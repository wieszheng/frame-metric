#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: video
@Author  : shwezheng
@Time    : 2025/11/29 21:46
@Software: PyCharm
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FrameResponse(BaseModel):
    """帧响应模型"""
    id: str
    type: str
    url: str
    timestamp: float
    frame_number: Optional[int] = None

    class Config:
        from_attributes = True


class VideoUploadResponse(BaseModel):
    """单视频上传响应"""
    video_id: str
    task_id: str
    status: str
    message: str


class BatchUploadResponse(BaseModel):
    """批量上传响应"""
    batch_id: str
    total_count: int
    videos: List[VideoUploadResponse]
    message: str


class TaskProgress(BaseModel):
    """任务进度"""
    video_id: str
    task_id: str
    status: str
    progress: int = Field(ge=0, le=100, description="进度百分比")
    current_step: str
    error_message: Optional[str] = None


class VideoStatusResponse(BaseModel):
    """视频状态响应"""
    video_id: str
    filename: str
    status: str
    duration: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    task_id: Optional[str] = None
    error_message: Optional[str] = None
    frames: List[FrameResponse] = []
    progress: int = 0
    current_step: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BatchStatusResponse(BaseModel):
    """批次状态响应"""
    batch_id: str
    total_count: int
    completed_count: int
    failed_count: int
    processing_count: int
    videos: List[VideoStatusResponse]


class CancelTaskResponse(BaseModel):
    """取消任务响应"""
    video_id: str
    task_id: str
    status: str
    message: str
