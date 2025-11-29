#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: __init__.py
@Author  : shwezheng
@Time    : 2025/11/26 23:32
@Software: PyCharm
"""
from app.tasks.celery_app import celery_app
from app.tasks.video_tasks import process_video_frames

__all__ = ["celery_app", "process_video_frames"]