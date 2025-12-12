#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: video_processor
@Author  : shwezheng
@Time    : 2025/11/29 21:48
@Software: PyCharm
"""
import cv2
import logging
from typing import Tuple, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoProcessor:
    """视频处理类"""

    @staticmethod
    def extract_video_info(video_path: str) -> Dict:
        """
        提取视频基本信息

        Args:
        video_path: 视频文件路径

        Returns:
        dict: 包含fps、frame_count、width、height、duration等信息

        """
        cap = cv2.VideoCapture(video_path)

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps)

            logger.info(
                f"Video info: {width}x{height}, {fps}fps, {duration:.2f}s")

            return {
                "fps": fps,
                "frame_count": frame_count,
                "width": width,
                "height": height,
                "duration": duration
            }
        except Exception as e:
            logger.error(f"Failed to extract video info: {e}")
            raise
        finally:
            cap.release()

    @staticmethod
    def extract_first_frame(video_path: str) -> Tuple[bytes, float, int]:
        """
        提取首帧

        Args:
        video_path: 视频文件路径


        Returns:
        tuple: (图片字节数据, 时间戳, 帧号)
        """
        cap = cv2.VideoCapture(video_path)

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)

            # 跳过可能的黑帧,读取0.5秒处的帧
            target_frame = int(fps * 0.5) if fps > 0 else 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            ret, frame = cap.read()

            if not ret:
                # 如果0.5秒处读取失败,读取第一帧
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                target_frame = 0

            if not ret or frame is None:
                raise ValueError("无法读取首帧")

            # 编码为JPEG
            success, buffer = cv2.imencode('.jpg', frame,
                                           [cv2.IMWRITE_JPEG_QUALITY, 90])

            if not success:
                raise ValueError("帧编码失败")

            timestamp = target_frame / fps if fps > 0 else 0

            logger.info(
                f"Extracted first frame: timestamp={timestamp:.2f}s, frame={target_frame}")

            return buffer.tobytes(), timestamp, target_frame

        except Exception as e:
            logger.error(f"Failed to extract first frame: {e}")
            raise
        finally:
            cap.release()

    @staticmethod
    def extract_last_frame(video_path: str) -> Tuple[bytes, float, int]:
        """
        提取尾帧

        Args:
        video_path: 视频文件路径


        Returns:
        tuple: (图片字节数据, 时间戳, 帧号)
        """
        cap = cv2.VideoCapture(video_path)

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # 尝试读取倒数第二秒的帧,避免黑帧
            target_frame = max(0, frame_count - int(
                fps * 2)) if fps > 0 else frame_count - 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            ret, frame = cap.read()

            if not ret:
                # 如果失败,读取最后一帧
                target_frame = max(0, frame_count - 1)
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, frame = cap.read()

            if not ret or frame is None:
                raise ValueError("无法读取尾帧")

            # 编码为JPEG
            success, buffer = cv2.imencode('.jpg', frame,
                                           [cv2.IMWRITE_JPEG_QUALITY, 90])

            if not success:
                raise ValueError("帧编码失败")

            timestamp = target_frame / fps if fps > 0 else 0

            logger.info(
                f"Extracted last frame: timestamp={timestamp:.2f}s, frame={target_frame}")

            return buffer.tobytes(), timestamp, target_frame

        except Exception as e:
            logger.error(f"Failed to extract last frame: {e}")
            raise
        finally:
            cap.release()

    @staticmethod
    def validate_video(video_path: str) -> bool:
        """
        验证视频文件是否有效

        Args:
        video_path: 视频文件路径


        Returns:
        bool: 是否有效
        """
        if not Path(video_path).exists():
            return False

        cap = cv2.VideoCapture(video_path)
        is_valid = cap.isOpened()
        cap.release()

        return is_valid
