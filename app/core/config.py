#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: config
@Author  : shwezheng
@Time    : 2025/11/26 23:29
@Software: PyCharm
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # MinIO配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "video-frames"
    MINIO_SECURE: bool = False

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # 数据库配置 - 异步
    ASYNC_DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/sparkles_async"
    # 数据库配置 - 同步
    SYNC_DATABASE_URL: str = "postgresql://user:password@localhost/sparkles_sync"

    # 应用配置
    UPLOAD_DIR: str = "/tmp/video_uploads"
    MAX_VIDEO_SIZE: int = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS: set = {".mp4", ".avi", ".mov", ".mkv"}

    # 并发配置
    MAX_CONCURRENT_UPLOADS: int = 5
    MAX_CONCURRENT_EXTRACTIONS: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
