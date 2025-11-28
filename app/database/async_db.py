#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: async_db
@Author  : shwezheng
@Time    : 2025/11/26 23:30
@Software: PyCharm
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


from app.core.config import settings

# 异步数据库引擎
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


# 异步依赖注入
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
