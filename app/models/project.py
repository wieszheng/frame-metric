# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/16 19:40
@Author   : wieszheng
@Software : PyCharm
"""
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, Text, Enum as SQLEnum
from datetime import datetime
from typing import List, Optional
import enum

from app.models.base import Base


class ProjectStatus(str, enum.Enum):
    """项目状态"""
    ACTIVE = "active"  # 进行中
    ARCHIVED = "archived"  # 已归档
    COMPLETED = "completed"  # 已完成
    ON_HOLD = "on_hold"  # 暂停


class Project(Base):
    """项目表 - 用于组织和管理多个任务"""
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # 项目标签（可选，用于分类和筛选）
    tag: Mapped[Optional[str]] = mapped_column(String(100), index=True)

    # 项目代码/编号（可选，用于标识项目）
    code: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)

    # 状态信息
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus),
        default=ProjectStatus.ACTIVE,
        index=True
    )

    # 项目负责人
    owner: Mapped[str] = mapped_column(String(255), nullable=False)

    # 项目成员（JSON格式存储，或者可以创建单独的关联表）
    members: Mapped[Optional[str]] = mapped_column(String(100), index=True)

    # 用户信息
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255))

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # 关系 - 一个项目包含多个任务
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"
