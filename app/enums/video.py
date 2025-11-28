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
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FrameType(str, enum.Enum):
    FIRST = "first"
    LAST = "last"
