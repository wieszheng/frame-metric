#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: config
@Author  : shwezheng
@Time    : 2025/11/26 23:29
@Software: PyCharm
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file(start_path: Optional[Path] = None) -> Path:
    """
    从当前目录开始向上查找 .env 文件
    """
    if start_path is None:
        start_path = Path(__file__).parent

    current_path = start_path.resolve()

    # 向上查找直到根目录
    while current_path != current_path.parent:

        env_file = current_path / ".env"
        if env_file.exists():
            return env_file
        current_path = current_path.parent

    # 如果没找到，返回项目根目录下的 .env（即使文件不存在）
    project_root = Path(__file__).parent.parent
    return project_root / ".env"


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    # 应用信息
    APP_NAME: str = "frame-metric"
    DEBUG: bool = False
    VERSION: str = "1.0.0"

    # 数据库配置
    DATABASE_URL: str = ""

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # MinIO配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minio"
    MINIO_SECRET_KEY: str = "minio123"
    MINIO_BUCKET: str = "video-frames"
    MINIO_SECURE: bool = False

    # 上传配置
    UPLOAD_DIR: str = "/tmp/video_uploads"
    MAX_VIDEO_SIZE: int = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS: str = ".mp4"

    # 并发配置
    MAX_CONCURRENT_UPLOADS: int = 5
    CELERY_WORKER_CONCURRENCY: int = 3

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """
        将异步数据库URL转换为同步URL(供Celery使用)
        """
        url = self.DATABASE_URL

        # PostgreSQL
        if "postgresql+asyncpg" in url:
            return url.replace("postgresql+asyncpg://",
                               "postgresql+psycopg2://")

        # MySQL
        if "mysql+aiomysql" in url:
            return url.replace("mysql+aiomysql://", "mysql+pymysql://")

        # SQLite
        if "sqlite+aiosqlite" in url:
            return url.replace("sqlite+aiosqlite:///", "sqlite:///")

        return url


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
