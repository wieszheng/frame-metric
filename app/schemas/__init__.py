#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: __init__.py
@Author  : shwezheng
@Time    : 2025/11/26 23:31
@Software: PyCharm
"""
from app.schemas.video import (
    VideoUploadResponse,
    BatchUploadResponse,
    VideoStatusResponse,
    BatchStatusResponse,
    TaskProgress,
    CancelTaskResponse,
    FrameResponse,
    FrameDetailResponse,
    VideoReviewResponse,
    FrameMarkingRequest,
    FrameMarkingResponse
)
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectStatistics,
    TaskBriefInfo
)

__all__ = [
    "VideoUploadResponse",
    "BatchUploadResponse",
    "VideoStatusResponse",
    "BatchStatusResponse",
    "TaskProgress",
    "CancelTaskResponse",
    "FrameResponse",
    "FrameDetailResponse",
    "VideoReviewResponse",
    "FrameMarkingRequest",
    "FrameMarkingResponse",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListResponse",
    "ProjectStatistics",
    "TaskBriefInfo"
]
