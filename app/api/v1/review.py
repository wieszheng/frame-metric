# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/2 19:29
@Author   : wieszheng
@Software : PyCharm
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging
import uuid

from app.database import get_async_db
from app.models.video import Video, Frame, FrameAnnotation, VideoStatus, FrameType, MarkingMethod
from app.schemas.video import (
    VideoReviewResponse,
    FrameDetailResponse,
    FrameMarkingRequest,
    FrameMarkingResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{video_id}", response_model=VideoReviewResponse,
            summary="获取审核页面数据")
async def get_review_data(
        video_id: str,
        db: AsyncSession = Depends(get_async_db)
):
    """获取视频审核所需的所有数据 - SQLAlchemy 2.0语法"""

    # 查询视频
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    if video.status not in [VideoStatus.PENDING_REVIEW, VideoStatus.REVIEWED]:
        raise HTTPException(
            status_code=400,
            detail=f"视频状态为{video.status.value}，无法审核"
        )

    # 查询所有帧
    frames_stmt = select(Frame).where(Frame.video_id == video_id).order_by(
        Frame.frame_number)
    frames_result = await db.execute(frames_stmt)
    all_frames = frames_result.scalars().all()

    # 找出当前标记的首尾帧
    marked_first = next(
        (f for f in all_frames if f.frame_type == FrameType.FIRST), None)
    marked_last = next(
        (f for f in all_frames if f.frame_type == FrameType.LAST), None)

    # 找出候选帧
    first_candidates = [f for f in all_frames if f.is_first_candidate]
    last_candidates = [f for f in all_frames if f.is_last_candidate]

    return VideoReviewResponse(
        video_id=video.id,
        filename=video.original_filename,
        status=video.status.value,
        total_frames=video.total_frames,
        extracted_frames=video.extracted_frames,
        marking_method=video.marking_method.value if video.marking_method else None,
        ai_confidence=video.ai_confidence,
        marked_first_frame=FrameDetailResponse(
            id=marked_first.id,
            frame_number=marked_first.frame_number,
            timestamp=marked_first.timestamp,
            url=marked_first.minio_url,
            frame_type=marked_first.frame_type.value if marked_first.frame_type else None,
            confidence_score=marked_first.confidence_score,
            brightness=marked_first.brightness,
            sharpness=marked_first.sharpness,
            scene_change_score=marked_first.scene_change_score
        ) if marked_first else None,
        marked_last_frame=FrameDetailResponse(
            id=marked_last.id,
            frame_number=marked_last.frame_number,
            timestamp=marked_last.timestamp,
            url=marked_last.minio_url,
            frame_type=marked_last.frame_type.value if marked_last.frame_type else None,
            confidence_score=marked_last.confidence_score,
            brightness=marked_last.brightness,
            sharpness=marked_last.sharpness,
            scene_change_score=marked_last.scene_change_score
        ) if marked_last else None,
        first_candidates=[
            FrameDetailResponse(
                id=f.id,
                frame_number=f.frame_number,
                timestamp=f.timestamp,
                url=f.minio_url,
                is_first_candidate=f.is_first_candidate,
                confidence_score=f.confidence_score,
                brightness=f.brightness,
                sharpness=f.sharpness
            ) for f in first_candidates
        ],
        last_candidates=[
            FrameDetailResponse(
                id=f.id,
                frame_number=f.frame_number,
                timestamp=f.timestamp,
                url=f.minio_url,
                is_last_candidate=f.is_last_candidate,
                confidence_score=f.confidence_score,
                brightness=f.brightness,
                sharpness=f.sharpness
            ) for f in last_candidates
        ],
        all_frames=[
            FrameDetailResponse(
                id=f.id,
                frame_number=f.frame_number,
                timestamp=f.timestamp,
                url=f.minio_url,
                frame_type=f.frame_type.value if f.frame_type else None,
                brightness=f.brightness,
                sharpness=f.sharpness
            ) for f in all_frames
        ],
        needs_review=video.needs_review,
        reviewed_by=video.reviewed_by,
        reviewed_at=video.reviewed_at
    )


@router.post("/{video_id}/mark", response_model=FrameMarkingResponse,
             summary="提交帧标记")
async def submit_frame_marking(
        video_id: str,
        request: FrameMarkingRequest,
        db: AsyncSession = Depends(get_async_db)
):
    """提交人工标记的首尾帧 - SQLAlchemy 2.0语法"""

    # 查询视频
    video_stmt = select(Video).where(Video.id == video_id)
    video_result = await db.execute(video_stmt)
    video = video_result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # 查询首帧
    first_frame_stmt = select(Frame).where(Frame.id == request.first_frame_id)
    first_frame_result = await db.execute(first_frame_stmt)
    first_frame = first_frame_result.scalar_one_or_none()

    if not first_frame or first_frame.video_id != video_id:
        raise HTTPException(status_code=400, detail="首帧不存在或不属于该视频")

    # 查询尾帧
    last_frame_stmt = select(Frame).where(Frame.id == request.last_frame_id)
    last_frame_result = await db.execute(last_frame_stmt)
    last_frame = last_frame_result.scalar_one_or_none()

    if not last_frame or last_frame.video_id != video_id:
        raise HTTPException(status_code=400, detail="尾帧不存在或不属于该视频")

    # 验证首尾帧顺序
    if first_frame.frame_number >= last_frame.frame_number:
        raise HTTPException(status_code=400, detail="首帧必须在尾帧之前")

    try:
        # 清除之前的标记
        all_frames_stmt = select(Frame).where(Frame.video_id == video_id)
        all_frames_result = await db.execute(all_frames_stmt)
        all_frames = all_frames_result.scalars().all()

        for frame in all_frames:
            frame.frame_type = None

        # 设置新标记
        first_frame.frame_type = FrameType.FIRST
        last_frame.frame_type = FrameType.LAST

        # 创建标注记录
        first_annotation = FrameAnnotation(
            id=str(uuid.uuid4()),
            video_id=video_id,
            frame_id=first_frame.id,
            marked_as_first=True,
            marked_as_last=False,
            marking_method=MarkingMethod.MANUAL,
            confidence=1.0,
            reason="人工审核标记",
            annotator=request.reviewer,
            is_approved=True,
            reviewer=request.reviewer
        )

        last_annotation = FrameAnnotation(
            id=str(uuid.uuid4()),
            video_id=video_id,
            frame_id=last_frame.id,
            marked_as_first=False,
            marked_as_last=True,
            marking_method=MarkingMethod.MANUAL,
            confidence=1.0,
            reason="人工审核标记",
            annotator=request.reviewer,
            is_approved=True,
            reviewer=request.reviewer
        )

        db.add(first_annotation)
        db.add(last_annotation)

        # 更新视频状态
        video.status = VideoStatus.REVIEWED
        video.needs_review = False
        video.reviewed_by = request.reviewer
        video.reviewed_at = datetime.utcnow()
        video.review_notes = request.review_notes

        await db.commit()
        await db.refresh(first_frame)
        await db.refresh(last_frame)

        logger.info(
            f"视频 {video_id} 标记完成: first={first_frame.frame_number}, "
            f"last={last_frame.frame_number}, reviewer={request.reviewer}")

        return FrameMarkingResponse(
            video_id=video_id,
            status="success",
            message="标记成功",
            first_frame=FrameDetailResponse(
                id=first_frame.id,
                frame_number=first_frame.frame_number,
                timestamp=first_frame.timestamp,
                url=first_frame.minio_url,
                frame_type=first_frame.frame_type.value if first_frame.frame_type else None
            ),
            last_frame=FrameDetailResponse(
                id=last_frame.id,
                frame_number=last_frame.frame_number,
                timestamp=last_frame.timestamp,
                url=last_frame.minio_url,
                frame_type=last_frame.frame_type.value if last_frame.frame_type else None
            )
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"标记失败: {e}")
        raise HTTPException(status_code=500, detail=f"标记失败: {str(e)}")


@router.get("/list/pending", summary="获取待审核视频列表")
async def list_pending_reviews(
        skip: int = 0,
        limit: int = 20,
        db: AsyncSession = Depends(get_async_db)
):
    """获取所有待审核的视频 - SQLAlchemy 2.0语法"""

    stmt = (
        select(Video)
        .where(Video.status == VideoStatus.PENDING_REVIEW)
        .order_by(Video.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    videos = result.scalars().all()

    return {
        "total": len(videos),
        "videos": [
            {
                "video_id": v.id,
                "filename": v.original_filename,
                "status": v.status.value,
                "marking_method": v.marking_method.value if v.marking_method else None,
                "ai_confidence": v.ai_confidence,
                "created_at": v.created_at
            }
            for v in videos
        ]
    }