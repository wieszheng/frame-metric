#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: frame_extractor
@Author  : shwezheng
@Time    : 2025/11/29 21:47
@Software: PyCharm
"""
import cv2
import numpy as np
import logging
from typing import List, Tuple, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class FrameExtractor:
    """帧提取器"""

    def __init__(self, sampling_rate: int = 2):
        """
        初始化

        Args:
        sampling_rate: 采样率，1
        表示提取所有帧，2
        表示每2帧提取1帧

        """
        self.sampling_rate = sampling_rate

    def extract_all_frames(
            self,
            video_path: str,
            output_callback=None
    ) -> List[Dict]:
        """
        提取视频所有帧

        Args:
        video_path: 视频路径
        output_callback: 回调函数，参数为(frame_data, frame_info)


        Returns:
        List[Dict]: 帧信息列表
        """
        cap = cv2.VideoCapture(video_path)
        frames_info = []

        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_number = 0
            extracted_count = 0

            logger.info(
                f"开始提取帧: total={total_frames}, sampling_rate={self.sampling_rate}")

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_number % self.sampling_rate != 0:
                    frame_number += 1
                    continue

                # 获取当前帧的时间戳（毫秒）
                timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))

                # 编码为JPEG
                success, buffer = cv2.imencode('.jpg', frame,
                                               [cv2.IMWRITE_JPEG_QUALITY,
                                                85])
                if not success:
                    logger.warning(f"Frame {frame_number} encoding failed")
                    frame_number += 1
                    continue

                frame_data = buffer.tobytes()

                # 计算帧特征
                features = self._calculate_frame_features(frame)

                frame_info = {
                    'frame_number': frame_number,
                    'timestamp': timestamp_ms,
                    'data': frame_data,
                    'size': len(frame_data),
                    **features
                }

                frames_info.append(frame_info)

                # 回调
                if output_callback:
                    output_callback(frame_data, frame_info)

                extracted_count += 1
                if (frame_number + 1) % 100 == 0 or frame_number == 0:
                    progress = (frame_number + 1) / total_frames * 100
                    logger.info(
                        f"  进度: {frame_number + 1}/{total_frames} ({progress:.1f}%)")



                frame_number += 1

            logger.info(
                f"帧提取完成: extracted={extracted_count}, total={total_frames}")

            return frames_info

        finally:
            cap.release()

    def _calculate_frame_features(self, frame: np.ndarray) -> Dict:
        """
        计算帧特征

        Args:
        frame: 帧图像


        Returns:
        Dict: 特征字典
        """
        # 转灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 亮度 (平均像素值)
        brightness = float(np.mean(gray))

        # 清晰度 (Laplacian方差)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness = float(laplacian_var)

        return {
            'brightness': brightness,
            'sharpness': sharpness
        }

    def calculate_scene_changes(self, frames_info: List[Dict]) -> List[float]:
        """
        计算场景变化分数

        Args:
        frames_info: 帧信息列表


        Returns:
        List[float]: 每帧的场景变化分数
        """
        if len(frames_info) < 2:
            return [0.0] * len(frames_info)

        scene_scores = [0.0]  # 第一帧场景变化为0

        for i in range(1, len(frames_info)):
            # 简化版：使用亮度差异作为场景变化指标
            prev_brightness = frames_info[i - 1]['brightness']
            curr_brightness = frames_info[i]['brightness']

            brightness_diff = abs(curr_brightness - prev_brightness)
            scene_score = min(brightness_diff / 50.0, 1.0)  # 归一化到0-1

            scene_scores.append(scene_score)

        return scene_scores
