#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: main.py
@Author  : shwezheng
@Time    : 2025/11/26 23:29
@Software: PyCharm
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_async_db, close_async_db
from app.api.v1 import api_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting application...")
    await init_async_db()
    logger.info("Database initialized")

    yield

    # 关闭时
    logger.info("Shutting down application...")
    await close_async_db()
    logger.info("Database closed")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="视频帧提取标注系统 - 支持异步处理、批量上传、进度追踪",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/admin")
async def admin_page():
    """脚本模板管理页面"""
    admin_html_path = os.path.join(os.path.dirname(__file__), "static", "admin.html")
    if os.path.exists(admin_html_path):
        return FileResponse(admin_html_path)
    else:
        raise HTTPException(status_code=404, detail="Admin page not found")



# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["root"])
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.VERSION
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG
    )
