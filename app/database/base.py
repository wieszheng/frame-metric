#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: base
@Author  : shwezheng
@Time    : 2025/11/26 23:30
@Software: PyCharm
"""
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, DateTime, func
from typing import Any


class Base(DeclarativeBase):
    """基础模型类"""
    pass


class BaseModelMixin:
    """模型混入类，提供通用字段"""
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """将模型实例转换为字典"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}