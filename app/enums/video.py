#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: video
@Author  : shwezheng
@Time    : 2025/11/27 00:03
@Software: PyCharm
"""
import enum


class VideoStatus(str, enum.Enum):
    """视频处理状态"""
    UPLOADING = "uploading"
    EXTRACTING = "extracting"  # 提取所有帧中
    ANALYZING = "analyzing"  # AI分析中
    PENDING_REVIEW = "pending_review"  # 待人工审核
    REVIEWED = "reviewed"  # 已审核
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FrameType(str, enum.Enum):
    """帧类型"""
    FIRST = "first"  # 首帧
    LAST = "last"  # 尾帧
    MIDDLE = "middle"  # 中间帧
    KEY = "key"  # 关键帧


class MarkingMethod(str, enum.Enum):
    """标记方式"""
    ALGORITHM = "algorithm"  # 算法标记
    AI_MODEL = "ai_model"  # AI模型标记
    MANUAL = "manual"  # 人工标记

class TaskStatus(str, enum.Enum):
    """任务状态"""
    DRAFT = "draft"              # 草稿
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败