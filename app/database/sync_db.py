#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: sync_db
@Author  : shwezheng
@Time    : 2025/11/26 23:30
@Software: PyCharm
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# 同步数据库引擎
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# 创建同步会话工厂
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)


# 同步依赖注入
def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
