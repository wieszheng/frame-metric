# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/2 19:15
@Author   : wieszheng
@Software : PyCharm
"""
from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import DeclarativeBase
from pydantic import BaseModel

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    通用CRUD基类

    用法:

    class VideoCRUD(CRUDBase[Video, VideoCreate, VideoUpdate]):
        pass

    video_crud = VideoCRUD(Video)

    """

    def __init__(self, model: Type[ModelType]):
        """
        初始化CRUD对象

        Args:
        model: SQLAlchemy模型类

        """
        self.model = model

    async def get_video_id(
            self,
            db: AsyncSession,
            id: Any
    ) -> Optional[ModelType]:
        """
        根据视频ID查询单个对象

        Args:
        db: 异步数据库会话
        id: 主键ID

        Returns:
        对象实例或None
        """
        stmt = select(self.model).where(self.model.video_id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get(
            self,
            db: AsyncSession,
            id: Any
    ) -> Optional[ModelType]:
        """
        根据ID查询单个对象

        Args:
        db: 异步数据库会话
        id: 主键ID

        Returns:
        对象实例或None
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
            self,
            db: AsyncSession,
            *,
            skip: int = 0,
            limit: int = 100,
            filters: Optional[Dict[str, Any]] = None,
            order_by: Optional[Any] = None
    ) -> List[ModelType]:
        """
        查询多个对象

        Args:
        db: 异步数据库会话
        skip: 跳过记录数
        limit: 返回记录数
        filters: 过滤条件
        {"field": value}
        order_by: 排序字段


        Returns:
        对象列表
        """
        stmt = select(self.model)

        # 添加过滤条件
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        # 添加排序
        if order_by is not None:
            stmt = stmt.order_by(order_by)

        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(
            self,
            db: AsyncSession,
            *,
            obj_in: CreateSchemaType | Dict[str, Any]
    ) -> ModelType:
        """
        创建新对象

        Args:
        db: 异步数据库会话
        obj_in: Pydantic模型或字典


        Returns:
        创建的对象
        """

        if isinstance(obj_in, dict):
            obj_data = obj_in
        else:
            obj_data = obj_in.model_dump(exclude_unset=True)

        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)

        return db_obj

    async def update(
            self,
            db: AsyncSession,
            *,
            db_obj: ModelType,
            obj_in: UpdateSchemaType | Dict[str, Any]
    ) -> ModelType:
        """
        更新对象

        Args:
        db: 异步数据库会话
        db_obj: 要更新的对象
        obj_in: 更新数据


        Returns:
        更新后的对象
        """

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await db.flush()
        await db.refresh(db_obj)

        return db_obj

    async def update_by_id(
            self,
            db: AsyncSession,
            *,
            id: Any,
            obj_in: UpdateSchemaType | Dict[str, Any]
    ) -> Optional[ModelType]:
        """
        根据ID更新对象

        Args:
        db: 异步数据库会话
        id: 主键ID
        obj_in: 更新数据


        Returns:
        更新后的对象或None
        """

        db_obj = await self.get(db, id)
        if db_obj:
            return await self.update(db, db_obj=db_obj, obj_in=obj_in)
        return None

    async def delete(
            self,
            db: AsyncSession,
            *,
            id: Any
    ) -> Optional[ModelType]:
        """
        删除对象

        Args:
        db: 异步数据库会话
        id: 主键ID


        Returns:
        被删除的对象或None
        """

        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj

    async def count(
            self,
            db: AsyncSession,
            *,
            filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        统计记录数

        Args:
        db: 异步数据库会话
        filters: 过滤条件


        Returns:
        记录数
        """

        stmt = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        result = await db.execute(stmt)
        return result.scalar_one()

    async def exists(
            self,
            db: AsyncSession,
            *,
            id: Any
    ) -> bool:
        """
        检查对象是否存在

        Args:
        db: 异步数据库会话
        id: 主键ID


        Returns:
        是否存在
        """

        obj = await self.get(db, id)
        return obj is not None

    def get_sync(
            self,
            db: Session,
            id: Any
    ) -> Optional[ModelType]:
        """同步查询单个对象"""
        stmt = select(self.model).where(self.model.id == id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def get_multi_sync(
            self,
            db: Session,
            *,
            skip: int = 0,
            limit: int = 100,
            filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """同步查询多个对象"""
        stmt = select(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        stmt = stmt.offset(skip).limit(limit)
        result = db.execute(stmt)
        return result.scalars().all()

    def create_sync(
            self,
            db: Session,
            *,
            obj_in: CreateSchemaType | Dict[str, Any]
    ) -> ModelType:
        """同步创建对象"""
        if isinstance(obj_in, dict):
            obj_data = obj_in
        else:
            obj_data = obj_in.model_dump(exclude_unset=True)

        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)

        return db_obj

    def update_sync(
            self,
            db: Session,
            *,
            db_obj: ModelType,
            obj_in: UpdateSchemaType | Dict[str, Any]
    ) -> ModelType:
        """同步更新对象"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.flush()
        db.refresh(db_obj)

        return db_obj

    def delete_sync(
            self,
            db: Session,
            *,
            id: Any
    ) -> Optional[ModelType]:
        """同步删除对象"""
        obj = self.get_sync(db, id)
        if obj:
            db.delete(obj)
            db.flush()
        return obj
