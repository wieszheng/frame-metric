#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: database
@Author  : shwezheng
@Time    : 2025/11/29 21:52
@Software: PyCharm
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, \
    async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import AsyncGenerator, Generator
from app.config import settings
from loguru import logger

# 异步数据库配置
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI依赖注入 - 获取异步数据库会话
    用法:
    @router.get("/videos")
    async def get_videos(db: AsyncSession = Depends(get_async_db)):
        result = await db.execute(select(Video))
        return result.scalars().all()

    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            await session.close()


# 同步数据库配置
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)


def get_sync_db() -> Generator[Session, None, None]:
    """
    获取同步数据库会话
    """

    db = SyncSessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


# 数据库初始化
async def init_async_db():
    """初始化数据库表 (异步方式)"""
    from app.models.video import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Async database initialized")


def init_sync_db():
    """初始化数据库表 (同步方式)"""
    from app.models.video import Base

    Base.metadata.create_all(bind=sync_engine)
    logger.info("Sync database initialized")


async def close_async_db():
    """关闭异步数据库连接"""
    await async_engine.dispose()
    logger.info("Async database closed")


def close_sync_db():
    """关闭同步数据库连接"""
    sync_engine.dispose()
    logger.info("Sync database closed")
