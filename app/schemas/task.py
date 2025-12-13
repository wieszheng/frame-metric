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
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(min_length=1, max_length=200, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    created_by: str = Field(description="创建人")


class TaskUpdate(BaseModel):
    """更新任务请求"""
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None


class TaskVideoAdd(BaseModel):
    """添加视频到任务"""
    model_config = ConfigDict(from_attributes=True)

    video_id: str = Field(description="视频ID")
    notes: Optional[str] = Field(None, description="备注")


class TaskVideoUpdate(BaseModel):
    """更新任务视频"""
    model_config = ConfigDict(from_attributes=True)

    first_frame_id: Optional[str] = None
    last_frame_id: Optional[str] = None
    notes: Optional[str] = None


class FrameMarkingUpdate(BaseModel):
    """更新首尾帧标记"""
    model_config = ConfigDict(from_attributes=True)

    first_frame_id: str = Field(description="首帧ID")
    last_frame_id: str = Field(description="尾帧ID")


class TaskVideoDetail(BaseModel):
    """任务视频详情"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    video_id: str
    sequence: int
    duration_ms: Optional[int]
    first_frame_id: Optional[str]
    last_frame_id: Optional[str]
    first_frame_timestamp: Optional[float]
    last_frame_timestamp: Optional[float]
    notes: Optional[str]
    added_at: datetime

    # 视频基本信息
    video_filename: Optional[str] = None
    video_status: Optional[str] = None

    # 首尾帧图片URL
    first_frame_url: Optional[str] = None
    last_frame_url: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """耗时（秒）"""
        if self.duration_ms:
            return self.duration_ms / 1000.0
        return None


class TaskStatistics(BaseModel):
    """任务统计信息"""
    model_config = ConfigDict(from_attributes=True)

    total_videos: int
    completed_videos: int
    failed_videos: int
    pending_videos: int

    # 耗时统计
    total_duration_ms: Optional[int]
    avg_duration_ms: Optional[int]
    min_duration_ms: Optional[int]
    max_duration_ms: Optional[int]

    @property
    def total_duration_seconds(self) -> Optional[float]:
        if self.total_duration_ms:
            return self.total_duration_ms / 1000.0
        return None

    @property
    def avg_duration_seconds(self) -> Optional[float]:
        if self.avg_duration_ms:
            return self.avg_duration_ms / 1000.0
        return None


class TaskResponse(BaseModel):
    """任务响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str]
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    # 统计信息
    statistics: TaskStatistics

    # 视频列表
    videos: List[TaskVideoDetail] = []


class TaskListResponse(BaseModel):
    """任务列表响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    total_videos: int
    completed_videos: int
    created_by: str
    created_at: datetime

    # 简化的统计
    avg_duration_ms: Optional[int]


class VideoFramesResponse(BaseModel):
    """视频帧列表响应"""
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    total_frames: int
    extracted_frames: int
    duration:float
    filename: str
    fps: int
    width: int
    height: int

    # 当前标记的首尾帧
    marked_first_frame_id: Optional[str]
    marked_last_frame_id: Optional[str]

    # 所有帧
    frames: List[dict]  # FrameDetailResponse列表