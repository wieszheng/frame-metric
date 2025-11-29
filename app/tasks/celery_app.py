#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: celery_app
@Author  : shwezheng
@Time    : 2025/11/29 21:49
@Software: PyCharm
"""
from celery import Celery
from app.config import settings

# 创建Celery应用
celery_app = Celery(
    "video_processor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery配置
celery_app.conf.update(
    # 序列化
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # 时区
    timezone='UTC',
    enable_utc=True,

    # 任务配置
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟硬超时
    task_soft_time_limit=25 * 60,  # 25分钟软超时

    # Worker配置
    worker_prefetch_multiplier=1,  # 每次只取一个任务
    worker_max_tasks_per_child=50,  # 每个worker处理50个任务后重启
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,

    # 结果后端
    result_expires=3600,  # 结果保留1小时

    # 任务路由
    task_routes={
        'app.tasks.video_tasks.*': {'queue': 'video_processing'}
    }
)

# 自动发现任务
celery_app.autodiscover_tasks(['app.tasks'])