# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/16 19:50
@Author   : wieszheng
@Software : PyCharm
"""
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
import logging

from app.database import get_async_db
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectStatistics,
    TaskBriefInfo
)
from app.crud.project import project_crud

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=ProjectResponse, summary="创建项目")
async def create_project(
        project_in: ProjectCreate,
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建新项目

    - name: 项目名称
    - description: 项目描述（可选）
    - code: 项目代码/编号（可选，唯一）
    - owner: 项目负责人
    - members: 项目成员（可选，JSON格式）
    - created_by: 创建人
    - start_date: 开始日期（可选）
    - end_date: 结束日期（可选）
    """
    # 检查项目代码是否已存在
    if project_in.code:
        existing = await project_crud.get_by_code(db, project_in.code)
        if existing:
            raise HTTPException(status_code=400, detail=f"项目代码 '{project_in.code}' 已存在")

    project_id = str(uuid.uuid4())

    project = Project(
        id=project_id,
        name=project_in.name,
        description=project_in.description,
        code=project_in.code,
        owner=project_in.owner,
        members=project_in.members,
        created_by=project_in.created_by,
        start_date=project_in.start_date,
        end_date=project_in.end_date,
        status=ProjectStatus.ACTIVE
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    logger.info(f"项目创建成功: {project_id}, name={project_in.name}")

    return await _build_project_response(db, project)


@router.get("", response_model=List[ProjectListResponse], summary="获取项目列表")
async def list_projects(
        status: Optional[str] = Query(None, description="筛选状态"),
        owner: Optional[str] = Query(None, description="筛选负责人"),
        skip: int = Query(0, ge=0, description="跳过记录数"),
        limit: int = Query(20, ge=1, le=100, description="返回记录数"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取项目列表

    - status: 筛选状态（可选）：active, archived, completed, on_hold
    - owner: 筛选负责人（可选）
    - skip: 跳过记录数
    - limit: 返回记录数
    """
    # 根据条件查询
    if status and owner:
        # 同时筛选状态和负责人
        try:
            status_enum = ProjectStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
        
        stmt = (
            select(Project)
            .where(Project.status == status_enum, Project.owner == owner)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        projects = result.scalars().all()
    elif status:
        # 仅筛选状态
        try:
            status_enum = ProjectStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
        projects = await project_crud.get_by_status(db, status_enum, skip, limit)
    elif owner:
        # 仅筛选负责人
        projects = await project_crud.get_by_owner(db, owner, skip, limit)
    else:
        # 无筛选条件
        projects = await project_crud.get_multi(
            db,
            skip=skip,
            limit=limit,
            order_by=Project.created_at.desc()
        )

    # 构建响应
    response_list = []
    for p in projects:
        # 获取统计信息
        stats = await project_crud.get_project_statistics(db, p.id)
        
        response_list.append(
            ProjectListResponse(
                id=p.id,
                name=p.name,
                code=p.code,
                status=p.status.value,
                owner=p.owner,
                created_by=p.created_by,
                created_at=p.created_at,
                total_tasks=stats["total_tasks"],
                completed_tasks=stats["completed_tasks"],
                total_videos=stats["total_videos"]
            )
        )

    return response_list


@router.get("/{project_id}", response_model=ProjectResponse, summary="获取项目详情")
async def get_project(
        project_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """获取项目详细信息，包含所有任务"""
    project = await project_crud.get_with_tasks(db, project_id)

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return await _build_project_response(db, project)


@router.put("/{project_id}", response_model=ProjectResponse, summary="更新项目")
async def update_project(
        project_id: str,
        project_in: ProjectUpdate,
        db: AsyncSession = Depends(get_async_db)
):
    """更新项目信息"""
    project = await project_crud.get(db, project_id)

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    update_data = project_in.model_dump(exclude_unset=True)

    # 检查项目代码是否重复
    if "code" in update_data and update_data["code"]:
        existing = await project_crud.get_by_code(db, update_data["code"])
        if existing and existing.id != project_id:
            raise HTTPException(status_code=400, detail=f"项目代码 '{update_data['code']}' 已被其他项目使用")

    # 转换状态
    if "status" in update_data:
        try:
            update_data["status"] = ProjectStatus(update_data["status"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {update_data['status']}")

    project = await project_crud.update(db, db_obj=project, obj_in=update_data)
    await db.commit()

    logger.info(f"项目已更新: {project_id}")

    return await _build_project_response(db, project)


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(
        project_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    删除项目（及其所有关联任务）
    
    注意：这将级联删除项目下的所有任务和任务视频关联
    """
    project = await project_crud.delete(db, id=project_id)

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    await db.commit()

    logger.info(f"项目已删除: {project_id}")

    return {"message": "项目已删除", "project_id": project_id}


@router.post("/{project_id}/archive", response_model=ProjectResponse, summary="归档项目")
async def archive_project(
        project_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    归档项目
    
    - 将项目状态设置为 ARCHIVED
    - 记录归档时间
    """
    project = await project_crud.archive_project(db, project_id)

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    await db.commit()

    logger.info(f"项目已归档: {project_id}")

    return await _build_project_response(db, project)


@router.get("/{project_id}/statistics", response_model=ProjectStatistics, summary="获取项目统计信息")
async def get_project_statistics(
        project_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取项目统计信息
    
    返回：
    - 总任务数
    - 进行中的任务数
    - 已完成的任务数
    - 总视频数
    """
    project = await project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    stats = await project_crud.get_project_statistics(db, project_id)

    return ProjectStatistics(**stats)


@router.get("/{project_id}/tasks", response_model=List[TaskBriefInfo], summary="获取项目的所有任务")
async def get_project_tasks(
        project_id: str,
        status: Optional[str] = Query(None, description="筛选任务状态"),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取项目下的所有任务
    
    - status: 筛选任务状态（可选）
    - skip: 跳过记录数
    - limit: 返回记录数
    """
    project = await project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 构建查询
    stmt = select(Task).where(Task.project_id == project_id)

    if status:
        try:
            status_enum = TaskStatus(status)
            stmt = stmt.where(Task.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的任务状态: {status}")

    stmt = stmt.order_by(Task.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return [
        TaskBriefInfo(
            id=t.id,
            name=t.name,
            status=t.status.value,
            total_videos=t.total_videos,
            completed_videos=t.completed_videos,
            created_at=t.created_at
        )
        for t in tasks
    ]


# ============================================================
# 辅助函数
# ============================================================

async def _build_project_response(db: AsyncSession, project: Project) -> ProjectResponse:
    """构建项目响应"""
    # 获取统计信息
    stats = await project_crud.get_project_statistics(db, project.id)

    # 获取项目的任务列表
    stmt = (
        select(Task)
        .where(Task.project_id == project.id)
        .order_by(Task.created_at.desc())
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    # 构建任务简要信息列表
    task_briefs = [
        TaskBriefInfo(
            id=t.id,
            name=t.name,
            status=t.status.value,
            total_videos=t.total_videos,
            completed_videos=t.completed_videos,
            created_at=t.created_at
        )
        for t in tasks
    ]

    # 构建统计信息
    statistics = ProjectStatistics(**stats)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        code=project.code,
        status=project.status.value,
        owner=project.owner,
        members=project.members,
        created_by=project.created_by,
        updated_by=project.updated_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        start_date=project.start_date,
        end_date=project.end_date,
        archived_at=project.archived_at,
        statistics=statistics,
        tasks=task_briefs
    )
