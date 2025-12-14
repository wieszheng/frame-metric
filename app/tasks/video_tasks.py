#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: video_tasks
@Author  : shwezheng
@Time    : 2025/11/29 21:49
@Software: PyCharm
"""
from app.services.video_processor import VideoProcessor
from app.tasks.celery_app import celery_app
from app.services.frame_extractor import FrameExtractor
from app.services.frame_analyzer import FrameAnalyzer
from app.services.minio_service import minio_service
from app.models.video import (Video, Frame, FrameAnnotation, VideoStatus,
                              FrameType, MarkingMethod)
from app.database import SyncSessionLocal
from app.config import settings
from celery.exceptions import SoftTimeLimitExceeded
import uuid
import logging
import os
import asyncio

logger = logging.getLogger(__name__)


def update_video_progress(video_id: str, progress: int, step: str):
    """
    更新视频处理进度

    Args:
    video_id: 视频ID
    progress: 进度百分比(0 - 100)
    step: 当前步骤描述

    """
    db = SyncSessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.progress = progress
            video.current_step = step
            db.commit()
            logger.info(f"Progress updated: {video_id} - {progress}% - {step}")
    except Exception as e:
        logger.error(f"Failed to update progress: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3,
                 name='app.tasks.video_tasks.process_video_frames')
def process_video_frames(self, video_id: str, video_path: str):
    """
    处理视频帧提取任务

    Args:
    video_id: 视频ID
    video_path: 视频文件路径


    Returns:
    dict: 处理结果
    """
    db = SyncSessionLocal()

    try:
        logger.info(f"Starting video processing: {video_id}")
        update_video_progress(video_id, 5, "开始处理视频")

        # 获取视频记录
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")

        # 更新状态
        video.status = VideoStatus.EXTRACTING
        video.task_id = video_id
        db.commit()

        # 检查任务是否被取消
        # if self.is_aborted():
        #     raise Exception("Task cancelled by user")

        # 1. 提取视频信息
        update_video_progress(video_id, 20, "正在分析视频信息")
        video_info = VideoProcessor.extract_video_info(video_path)

        video.duration = video_info["duration"]
        video.fps = video_info["fps"]
        video.width = video_info["width"]
        video.height = video_info["height"]
        db.commit()

        logger.info(f"Video info extracted: {video_info}")

        # 2. 提取首帧
        # if self.is_aborted():
        #     raise Exception("Task cancelled by user")

        update_video_progress(video_id, 40, "正在提取首帧")
        first_frame_data, first_timestamp, first_frame_num = VideoProcessor.extract_first_frame(
            video_path)

        # 上传首帧
        update_video_progress(video_id, 50, "正在上传首帧到MinIO")
        first_frame_url = minio_service.upload_frame(
            video_id, first_frame_data, "first", first_timestamp
        )

        # 保存首帧记录
        first_frame = Frame(
            id=str(uuid.uuid4()),
            video_id=video_id,
            frame_type=FrameType.FIRST,
            minio_url=first_frame_url,
            timestamp=first_timestamp,
            frame_number=first_frame_num
        )
        db.add(first_frame)
        db.commit()

        logger.info(f"First frame uploaded: {first_frame_url}")

        # 3. 提取尾帧
        # if self.is_aborted():
        #     raise Exception("Task cancelled by user")

        update_video_progress(video_id, 70, "正在提取尾帧")
        last_frame_data, last_timestamp, last_frame_num = VideoProcessor.extract_last_frame(
            video_path)

        # 上传尾帧
        update_video_progress(video_id, 80, "正在上传尾帧到MinIO")
        last_frame_url = minio_service.upload_frame(
            video_id, last_frame_data, "last", last_timestamp
        )

        # 保存尾帧记录
        last_frame = Frame(
            id=str(uuid.uuid4()),
            video_id=video_id,
            frame_type=FrameType.LAST,
            minio_url=last_frame_url,
            timestamp=last_timestamp,
            frame_number=last_frame_num
        )
        db.add(last_frame)
        db.commit()

        logger.info(f"Last frame uploaded: {last_frame_url}")

        # 4. 上传原始视频 (可选)
        update_video_progress(video_id, 90, "正在上传原始视频")
        minio_path = minio_service.upload_video(
            video_id, video_path, video.filename
        )
        video.minio_path = minio_path

        # 5. 完成处理
        update_video_progress(video_id, 100, "处理完成")
        video.status = VideoStatus.COMPLETED
        db.commit()

        logger.info(f"Video processing completed: {video_id}")

        # 6. 清理临时文件
        if os.path.exists(video_path):
            os.remove(video_path)
            logger.info(f"Cleaned up temp file: {video_path}")

        return {
            "video_id": video_id,
            "status": "completed",
            "frames": [
                {
                    "type": "first",
                    "url": first_frame_url,
                    "timestamp": first_timestamp,
                    "frame_number": first_frame_num
                },
                {
                    "type": "last",
                    "url": last_frame_url,
                    "timestamp": last_timestamp,
                    "frame_number": last_frame_num
                }
            ]
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Task timeout: {video_id}")
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = VideoStatus.FAILED
            video.error_message = "处理超时"
            video.progress = 0
            db.commit()

        if os.path.exists(video_path):
            os.remove(video_path)
        raise

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Video processing failed: {video_id}, error: {error_msg}")

        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            if "cancelled" in error_msg.lower():
                video.status = VideoStatus.CANCELLED
                video.error_message = "任务已被用户取消"
            else:
                video.status = VideoStatus.FAILED
                video.error_message = error_msg
            video.progress = 0
            db.commit()

        if os.path.exists(video_path):
            os.remove(video_path)

        # 非取消错误才重试
        if "cancelled" not in error_msg.lower():
            raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, name='app.tasks.video_tasks.process_video_frames_full')
def process_video_frames_full(self, video_id: str, video_path: str):
    """
    完整的视频处理任务

    流程:
    1.
    提取所有帧(根据采样率)
    2.
    上传所有帧到MinIO
    3.
    计算帧特征和场景变化
    4.
    使用算法 / AI标记首尾帧
    5.
    生成候选帧列表
    6.
    设置状态为待审核
    """
    db = SyncSessionLocal()

    try:
        logger.info(f"开始处理视频: {video_id}")
        update_video_progress(video_id, 5, "开始处理")

        # 获取视频记录
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")

        video.status = VideoStatus.EXTRACTING
        video.task_id = self.request.id
        db.commit()

        # 1. 提取视频信息
        update_video_progress(video_id, 10, "分析视频信息")
        logger.info(f"视频路径: {video_path}")
        from app.services.video_processor import VideoProcessor

        video_info = VideoProcessor.extract_video_info(video_path)

        video.duration = video_info["duration"]
        video.fps = video_info["fps"]
        video.width = video_info["width"]
        video.height = video_info["height"]
        video.total_frames = video_info["frame_count"]
        db.commit()

        logger.info(f"视频信息: {video_info}")

        # 2. 提取所有帧
        update_video_progress(video_id, 20, "提取所有帧")
        extractor = FrameExtractor()

        frames_info = []
        extracted_count = 0

        def frame_callback(frame_data, frame_info):
            """帧提取回调 - 上传到MinIO并保存到数据库"""
            nonlocal extracted_count

            # 上传到MinIO
            frame_url = minio_service.upload_frame(
                video_id,
                frame_data,
                f"frame_{frame_info['frame_number']}",
                frame_info['timestamp']
            )

            # 保存到数据库
            frame = Frame(
                id=str(uuid.uuid4()),
                video_id=video_id,
                frame_number=frame_info['frame_number'],
                timestamp=frame_info['timestamp'],
                minio_url=frame_url,
                brightness=frame_info['brightness'],
                sharpness=frame_info['sharpness']
            )
            db.add(frame)

            extracted_count += 1

            # 每100帧提交一次
            if extracted_count % 100 == 0:
                db.commit()
                progress = 20 + int((extracted_count / video.total_frames) * 40)
                update_video_progress(video_id, progress,
                                      f"已提取 {extracted_count} 帧")

            frames_info.append(frame_info)

        # 执行提取
        extractor.extract_all_frames(video_path, frame_callback)
        db.commit()

        video.extracted_frames = extracted_count
        db.commit()

        logger.info(f"帧提取完成: {extracted_count} 帧")

        # 3. 计算场景变化
        update_video_progress(video_id, 65, "分析场景变化")
        scene_scores = extractor.calculate_scene_changes(frames_info)

        # 更新场景变化分数到数据库
        all_frames = db.query(Frame).filter(
            Frame.video_id == video_id).order_by(Frame.frame_number).all()
        for i, frame in enumerate(all_frames):
            if i < len(scene_scores):
                frame.scene_change_score = scene_scores[i]
        db.commit()

        # 4. 智能标记首尾帧
        update_video_progress(video_id, 75, "智能标记首尾帧")
        analyzer = FrameAnalyzer()

        first_idx, last_idx, confidence = analyzer.analyze_first_last_frames(
            frames_info,
            scene_scores
        )

        # 标记首尾帧
        first_frame = all_frames[first_idx]
        last_frame = all_frames[last_idx]

        first_frame.frame_type = FrameType.FIRST
        first_frame.confidence_score = confidence

        last_frame.frame_type = FrameType.LAST
        last_frame.confidence_score = confidence

        # 5. 生成候选帧
        update_video_progress(video_id, 85, "生成候选帧列表")

        first_candidates = analyzer.get_candidate_frames(frames_info, 'first',
                                                         top_k=5)
        last_candidates = analyzer.get_candidate_frames(frames_info, 'last',
                                                        top_k=5)

        # 标记候选帧
        for idx, score in first_candidates:
            all_frames[idx].is_first_candidate = True
            all_frames[idx].confidence_score = score

        for idx, score in last_candidates:
            all_frames[idx].is_last_candidate = True
            all_frames[idx].confidence_score = score

        db.commit()

        # 6. 创建标注记录
        first_annotation = FrameAnnotation(
            id=str(uuid.uuid4()),
            video_id=video_id,
            frame_id=first_frame.id,
            marked_as_first=True,
            marked_as_last=False,
            marking_method=MarkingMethod.ALGORITHM,
            confidence=confidence,
            reason="算法自动标记",
            annotator="system"
        )

        last_annotation = FrameAnnotation(
            id=str(uuid.uuid4()),
            video_id=video_id,
            frame_id=last_frame.id,
            marked_as_first=False,
            marked_as_last=True,
            marking_method=MarkingMethod.ALGORITHM,
            confidence=confidence,
            reason="算法自动标记",
            annotator="system"
        )

        db.add(first_annotation)
        db.add(last_annotation)

        # 7. 更新视频状态
        video.status = VideoStatus.PENDING_REVIEW
        video.marking_method = MarkingMethod.ALGORITHM
        video.ai_confidence = confidence
        video.needs_review = True
        video.progress = 100
        video.current_step = "等待人工审核"
        db.commit()

        # 8. 如果启用AI，触发AI分析
        if False and confidence < 0.8:
            logger.info(f"置信度较低({confidence})，触发AI分析")
            analyze_with_ai.delay(video_id)

        # 9. 清理临时文件
        if os.path.exists(video_path):
            os.remove(video_path)

        logger.info(f"视频处理完成: {video_id}")

        return {
            "video_id": video_id,
            "status": "pending_review",
            "extracted_frames": extracted_count,
            "first_frame": first_frame.frame_number,
            "last_frame": last_frame.frame_number,
            "confidence": confidence
        }

    except Exception as e:
        logger.error(f"视频处理失败: {video_id}, error: {e}")

        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = VideoStatus.FAILED
            video.error_message = str(e)
            video.progress = 0
            db.commit()

        if os.path.exists(video_path):
            os.remove(video_path)

        raise

    finally:
        db.close()


@celery_app.task(name='analyze_with_ai')
def analyze_with_ai(video_id: str):
    """
    使用AI分析视频帧(异步任务)
    """
    db = SyncSessionLocal()

    try:
        logger.info(f"开始AI分析: {video_id}")

        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")

        video.status = VideoStatus.ANALYZING
        video.current_step = "AI分析中"
        db.commit()

        # 获取候选帧
        first_candidates = db.query(Frame).filter(
            Frame.video_id == video_id,
            Frame.is_first_candidate == True
        ).order_by(Frame.confidence_score.desc()).limit(3).all()

        last_candidates = db.query(Frame).filter(
            Frame.video_id == video_id,
            Frame.is_last_candidate == True
        ).order_by(Frame.confidence_score.desc()).limit(3).all()

        # 准备候选数据
        candidates_data = {
            'first': [
                {
                    'frame_number': f.frame_number,
                    'timestamp': f.timestamp,
                    'data': _load_frame_data(f.minio_url)
                }
                for f in first_candidates
            ],
            'last': [
                {
                    'frame_number': f.frame_number,
                    'timestamp': f.timestamp,
                    'data': _load_frame_data(f.minio_url)
                }
                for f in last_candidates
            ]
        }

        video_context = {
            'filename': video.original_filename,
            'duration': video.duration,
            'total_frames': video.total_frames
        }

        # 调用AI分析 (需要在事件循环中运行)
        from app.services.ai_frame_analyzer import AIFrameAnalyzer
        analyzer = AIFrameAnalyzer()

        # 在新的事件循环中运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        first_frame_num, last_frame_num, confidence, reasoning = loop.run_until_complete(
            analyzer.analyze_frames_with_ai(candidates_data, video_context)
        )

        loop.close()

        logger.info(
            f"AI分析完成: first={first_frame_num}, last={last_frame_num}, "
            f"confidence={confidence}")

        # 更新标记
        all_frames = db.query(Frame).filter(Frame.video_id == video_id).all()

        # 清除旧标记
        for frame in all_frames:
            if frame.frame_type in [FrameType.FIRST, FrameType.LAST]:
                frame.frame_type = None

        # 设置新标记
        for frame in all_frames:
            if frame.frame_number == first_frame_num:
                frame.frame_type = FrameType.FIRST
                frame.confidence_score = confidence

                # 创建AI标注记录
                annotation = FrameAnnotation(
                    id=str(uuid.uuid4()),
                    video_id=video_id,
                    frame_id=frame.id,
                    marked_as_first=True,
                    marked_as_last=False,
                    marking_method=MarkingMethod.AI_MODEL,
                    confidence=confidence,
                    reason=reasoning,
                    annotator="claude-ai"
                )
                db.add(annotation)

            elif frame.frame_number == last_frame_num:
                frame.frame_type = FrameType.LAST
                frame.confidence_score = confidence

                annotation = FrameAnnotation(
                    id=str(uuid.uuid4()),
                    video_id=video_id,
                    frame_id=frame.id,
                    marked_as_first=False,
                    marked_as_last=True,
                    marking_method=MarkingMethod.AI_MODEL,
                    confidence=confidence,
                    reason=reasoning,
                    annotator="claude-ai"
                )
                db.add(annotation)

        # 更新视频
        video.status = VideoStatus.PENDING_REVIEW
        video.marking_method = MarkingMethod.AI_MODEL
        video.ai_confidence = confidence
        video.current_step = "AI分析完成，等待审核"
        db.commit()

        logger.info(f"AI标记已更新: {video_id}")

        return {
            "video_id": video_id,
            "first_frame": first_frame_num,
            "last_frame": last_frame_num,
            "confidence": confidence,
            "reasoning": reasoning
        }

    except Exception as e:
        logger.error(f"AI分析失败: {e}")

        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = VideoStatus.PENDING_REVIEW
            video.current_step = "AI分析失败，使用算法结果"
            db.commit()

        raise

    finally:
        db.close()


def _load_frame_data(minio_url: str) -> bytes:
    """从MinIO加载帧数据"""
    import requests
    response = requests.get(minio_url)
    return response.content


@celery_app.task(name='reanalyze_video_frames')
def reanalyze_video_frames(video_id: str, use_ai: bool = False):
    """重新分析视频帧"""
    db = SyncSessionLocal()

    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")

        # 获取所有帧
        frames = db.query(Frame).filter(
            Frame.video_id == video_id
        ).order_by(Frame.frame_number).all()

        frames_info = [
            {
                'frame_number': f.frame_number,
                'timestamp': f.timestamp,
                'brightness': f.brightness,
                'sharpness': f.sharpness,
                'data': _load_frame_data(f.minio_url)
            }
            for f in frames
        ]

        scene_scores = [f.scene_change_score or 0.0 for f in frames]

        if use_ai and settings.USE_AI_ANALYSIS:
            # 使用AI分析
            analyze_with_ai.delay(video_id)
        else:
            # 使用算法重新分析
            analyzer = FrameAnalyzer()
            first_idx, last_idx, confidence = analyzer.analyze_first_last_frames(
                frames_info,
                scene_scores
            )

            # 更新标记
            for frame in frames:
                frame.frame_type = None

            frames[first_idx].frame_type = FrameType.FIRST
            frames[last_idx].frame_type = FrameType.LAST

            video.marking_method = MarkingMethod.ALGORITHM
            video.ai_confidence = confidence

            db.commit()

        return {"status": "success"}

    finally:
        db.close()
