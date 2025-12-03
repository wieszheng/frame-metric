# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/2 19:24
@Author   : wieszheng
@Software : PyCharm
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class TaskCreate(BaseModel):
    """创建任务请求"""
    name: str = Field(..., min_length=1, max_length=200, description="任务名称")
    description: Optional[str] = Field(None, max_length=1000,
                                       description="任务描述")
    created_by: str = Field(..., description="创建者")


class TaskUpdate(BaseModel):
    """更新任务请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class VideoAddToTask(BaseModel):
    """添加视频到任务请求"""
    video_ids: List[str] = Field(..., min_items=1, description="视频ID列表")
    notes: Optional[str] = Field(None, description="备注")


class TaskVideoDetail(BaseModel):
    """任务中的视频详情"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    order: int
    duration: Optional[float] = None
    first_frame_time: Optional[float] = None
    last_frame_time: Optional[float] = None
    notes: Optional[str] = None
    added_at: datetime

    # 视频基本信息
    video_filename: Optional[str] = None
    video_status: Optional[str] = None
    video_width: Optional[int] = None
    video_height: Optional[int] = None

    # 首尾帧URL
    first_frame_url: Optional[str] = None
    last_frame_url: Optional[str] = None


class TaskResponse(BaseModel):
    """任务响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    status: str
    total_videos: int
    completed_videos: int
    failed_videos: int
    total_duration: Optional[float] = None
    avg_duration: Optional[float] = None
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class TaskDetailResponse(BaseModel):
    """任务详情响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    status: str
    total_videos: int
    completed_videos: int
    failed_videos: int
    total_duration: Optional[float] = None
    avg_duration: Optional[float] = None
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    # 视频列表
    videos: List[TaskVideoDetail] = []


class TaskStatsResponse(BaseModel):
    """任务统计响应"""
    task_id: str
    task_name: str

    # 视频统计
    total_videos: int
    completed_videos: int
    processing_videos: int
    failed_videos: int

    # 性能统计
    total_duration: Optional[float] = None
    avg_duration: Optional[float] = None
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None

    # 帧统计
    total_frames: int
    avg_frames_per_video: Optional[float] = None