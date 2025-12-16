# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/16 19:50
@Author   : wieszheng
@Software : PyCharm
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class ProjectCreate(BaseModel):
    """创建项目请求"""
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(min_length=1, max_length=200, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    code: Optional[str] = Field(None, min_length=1, max_length=100, description="项目代码/编号")
    owner: str = Field(description="项目负责人")
    members: Optional[str] = Field(None, description="项目成员（JSON格式）")
    created_by: str = Field(description="创建人")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")


class ProjectUpdate(BaseModel):
    """更新项目请求"""
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    code: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[str] = None
    owner: Optional[str] = None
    members: Optional[str] = None
    updated_by: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectStatistics(BaseModel):
    """项目统计信息"""
    model_config = ConfigDict(from_attributes=True)

    total_tasks: int = Field(default=0, description="总任务数")
    active_tasks: int = Field(default=0, description="进行中的任务数")
    completed_tasks: int = Field(default=0, description="已完成的任务数")
    total_videos: int = Field(default=0, description="总视频数")


class TaskBriefInfo(BaseModel):
    """任务简要信息（用于项目详情）"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    total_videos: int
    completed_videos: int
    created_at: datetime


class ProjectResponse(BaseModel):
    """项目响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str]
    code: Optional[str]
    status: str
    owner: str
    members: Optional[str]
    created_by: str
    updated_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    archived_at: Optional[datetime]

    # 统计信息
    statistics: ProjectStatistics

    # 任务列表
    tasks: List[TaskBriefInfo] = []


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: Optional[str]
    status: str
    owner: str
    created_by: str
    created_at: datetime
    
    # 简化的统计
    total_tasks: int = 0
    completed_tasks: int = 0
    total_videos: int = 0
