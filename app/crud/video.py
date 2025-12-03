# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/2 19:21
@Author   : wieszheng
@Software : PyCharm
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.crud_base import CRUDBase
from app.models.video import Video, Frame, FrameAnnotation, VideoStatus, \
    FrameType
from pydantic import BaseModel


# 创建简单的Schema用于CRUD
class VideoCreate(BaseModel):
    id: str
    filename: str
    original_filename: Optional[str] = None
    file_size: Optional[int] = None


class VideoUpdate(BaseModel):
    status: Optional[VideoStatus] = None
    progress: Optional[int] = None
    current_step: Optional[str] = None
    error_message: Optional[str] = None


class FrameCreate(BaseModel):
    id: str
    video_id: str
    frame_number: int
    timestamp: float
    minio_url: str


class FrameUpdate(BaseModel):
    frame_type: Optional[FrameType] = None
    confidence_score: Optional[float] = None


class FrameAnnotationCreate(BaseModel):
    id: str
    video_id: str
    frame_id: str
    marked_as_first: bool = False
    marked_as_last: bool = False


class VideoCRUD(CRUDBase[Video, VideoCreate, VideoUpdate]):
    """视频CRUD操作"""

    async def get_with_frames(
            self,
            db: AsyncSession,
            video_id: str
    ) -> Optional[Video]:
        """查询视频及其所有帧"""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Video)
            .where(Video.id == video_id)
            .options(selectinload(Video.frames))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_status(
            self,
            db: AsyncSession,
            status: VideoStatus,
            skip: int = 0,
            limit: int = 100
    ) -> List[Video]:
        """根据状态查询视频列表"""
        return await self.get_multi(
            db,
            skip=skip,
            limit=limit,
            filters={"status": status}
        )


class FrameCRUD(CRUDBase[Frame, FrameCreate, FrameUpdate]):
    """帧CRUD操作"""

    async def get_by_video(
            self,
            db: AsyncSession,
            video_id: str
    ) -> List[Frame]:
        """查询视频的所有帧"""
        stmt = (
            select(Frame)
            .where(Frame.video_id == video_id)
            .order_by(Frame.frame_number)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_candidates(
            self,
            db: AsyncSession,
            video_id: str,
            candidate_type: str = "first"
    ) -> List[Frame]:
        """获取候选帧"""
        if candidate_type == "first":
            stmt = select(Frame).where(
                Frame.video_id == video_id,
                Frame.is_first_candidate == True
            )
        else:
            stmt = select(Frame).where(
                Frame.video_id == video_id,
                Frame.is_last_candidate == True
            )

        result = await db.execute(stmt)
        return result.scalars().all()


class FrameAnnotationCRUD(
    CRUDBase[FrameAnnotation, FrameAnnotationCreate, BaseModel]):
    """帧标注CRUD操作"""

    async def get_by_video(
            self,
            db: AsyncSession,
            video_id: str
    ) -> List[FrameAnnotation]:
        """查询视频的所有标注"""
        stmt = select(FrameAnnotation).where(
            FrameAnnotation.video_id == video_id)
        result = await db.execute(stmt)
        return result.scalars().all()


# 创建全局CRUD实例
video_crud = VideoCRUD(Video)
frame_crud = FrameCRUD(Frame)
frame_annotation_crud = FrameAnnotationCRUD(FrameAnnotation)
