# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/16 19:50
@Author   : wieszheng
@Software : PyCharm
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func
from datetime import datetime

from app.core.crud_base import CRUDBase
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    code: Optional[str] = None
    owner: str
    members: Optional[str] = None
    created_by: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    status: Optional[ProjectStatus] = None
    owner: Optional[str] = None
    members: Optional[str] = None
    updated_by: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectCRUD(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    """项目CRUD操作"""

    async def get_with_tasks(
            self,
            db: AsyncSession,
            project_id: str
    ) -> Optional[Project]:
        """查询项目及其所有任务"""
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.tasks))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_status(
            self,
            db: AsyncSession,
            status: ProjectStatus,
            skip: int = 0,
            limit: int = 100
    ) -> List[Project]:
        """根据状态查询项目"""
        stmt = (
            select(Project)
            .where(Project.status == status)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_owner(
            self,
            db: AsyncSession,
            owner: str,
            skip: int = 0,
            limit: int = 100
    ) -> List[Project]:
        """根据负责人查询项目"""
        stmt = (
            select(Project)
            .where(Project.owner == owner)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_code(
            self,
            db: AsyncSession,
            code: str
    ) -> Optional[Project]:
        """根据项目代码查询项目"""
        stmt = select(Project).where(Project.code == code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def archive_project(
            self,
            db: AsyncSession,
            project_id: str
    ) -> Optional[Project]:
        """归档项目"""
        project = await self.get(db, project_id)
        if project:
            project.status = ProjectStatus.ARCHIVED
            project.archived_at = datetime.utcnow()
            await db.flush()
            await db.refresh(project)
        return project

    async def get_project_statistics(
            self,
            db: AsyncSession,
            project_id: str
    ) -> dict:
        """获取项目统计信息"""
        # 查询项目的所有任务
        stmt = select(Task).where(Task.project_id == project_id)
        result = await db.execute(stmt)
        tasks = result.scalars().all()

        total_tasks = len(tasks)
        active_tasks = sum(1 for t in tasks if t.status in [TaskStatus.DRAFT, TaskStatus.PROCESSING, TaskStatus.PENDING_REVIEW])
        completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        total_videos = sum(t.total_videos for t in tasks)

        return {
            "total_tasks": total_tasks,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "total_videos": total_videos
        }


# 创建全局CRUD实例
project_crud = ProjectCRUD(Project)
