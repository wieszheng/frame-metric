#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: video
@Author  : shwezheng
@Time    : 2025/11/29 21:46
@Software: PyCharm
"""
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional, List
from datetime import datetime


class FrameResponse(BaseModel):
    """帧响应模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    frame_type: str
    timestamp: float
    is_first_candidate: bool
    is_last_candidate: bool
    frame_number: Optional[int] = None


class FrameDetailResponse(BaseModel):
    """帧详细信息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    frame_number: int
    timestamp: float
    url: str
    frame_type: Optional[str] = None
    is_first_candidate: bool = False
    is_last_candidate: bool = False
    confidence_score: Optional[float] = None
    brightness: Optional[float] = None
    sharpness: Optional[float] = None
    scene_change_score: Optional[float] = None


class VideoUploadResponse(BaseModel):
    """单视频上传响应"""
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    task_id: str
    status: str
    message: str


class BatchUploadResponse(BaseModel):
    """批量上传响应"""
    model_config = ConfigDict(from_attributes=True)

    batch_id: str
    total_count: int
    videos: List[VideoUploadResponse]
    message: str


class TaskProgress(BaseModel):
    """任务进度"""
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    task_id: str
    status: str
    progress: int = Field(ge=0, le=100, description="进度百分比")
    current_step: str
    error_message: Optional[str] = None


class VideoStatusResponse(BaseModel):
    """视频状态响应"""
    model_config = ConfigDict(from_attributes=True)

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

    @field_serializer('created_at')
    def format_datetime(self, value: datetime) -> str:
        """格式化时间为标准格式"""
        return value.strftime("%Y-%m-%d %H:%M:%S")


class BatchStatusResponse(BaseModel):
    """批次状态响应"""
    model_config = ConfigDict(from_attributes=True)

    batch_id: str
    total_count: int
    completed_count: int
    failed_count: int
    processing_count: int
    videos: List[VideoStatusResponse]


class CancelTaskResponse(BaseModel):
    """取消任务响应"""
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    task_id: str
    status: str
    message: str


class VideoReviewResponse(BaseModel):
    """视频审核响应"""
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    filename: str
    status: str
    total_frames: int
    extracted_frames: int
    marking_method: Optional[str] = None
    ai_confidence: Optional[float] = None
    marked_first_frame: Optional[FrameDetailResponse] = None
    marked_last_frame: Optional[FrameDetailResponse] = None
    first_candidates: List[FrameDetailResponse] = []
    last_candidates: List[FrameDetailResponse] = []
    all_frames: List[FrameDetailResponse] = []
    needs_review: bool = True
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    @field_serializer('reviewed_at')
    def format_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """格式化时间为标准格式"""
        if value is None:
            return None
        return value.strftime("%Y-%m-%d %H:%M:%S")


class FrameMarkingRequest(BaseModel):
    """帧标记请求"""
    model_config = ConfigDict(from_attributes=True)

    first_frame_id: str = Field(description="首帧ID")
    last_frame_id: str = Field(description="尾帧ID")
    reviewer: str = Field(description="审核人")
    review_notes: Optional[str] = Field(None, description="审核备注")


class FrameMarkingResponse(BaseModel):
    """帧标记响应"""
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    status: str
    message: str
    first_frame: FrameDetailResponse
    last_frame: FrameDetailResponse
