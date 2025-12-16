#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: __init__.py
@Author  : shwezheng
@Time    : 2025/11/29 21:53
@Software: PyCharm
"""
from fastapi import APIRouter
from app.api.v1 import video, task, review, project
from app.api.v1 import amazing_qr

api_router = APIRouter()

# 注册子路由
api_router.include_router(video.router, prefix="/video", tags=["video"])
api_router.include_router(amazing_qr.router, prefix="/qr", tags=["qr code"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(task.router, prefix="/task", tags=["task"])
api_router.include_router(project.router, prefix="/project", tags=["project"])  # 新增项目路由
