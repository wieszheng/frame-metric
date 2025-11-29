#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: frame_analyzer
@Author  : shwezheng
@Time    : 2025/11/29 21:47
@Software: PyCharm
"""
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)


class FrameAnalyzer:
    """帧分析器 - 使用算法标记首尾帧"""

    def __init__(self):
        self.method = "algorithm"

    def analyze_first_last_frames(
            self,
            frames_info: List[Dict],
            scene_scores: List[float]
    ) -> Tuple[int, int, float]:
        """
        分析并标记首尾帧

        策略:
        - 首帧: 跳过开头的黑帧和低质量帧
        - 尾帧: 跳过结尾的黑帧和片尾字幕

        Args:
        frames_info: 帧信息列表
        scene_scores: 场景变化分数

            Returns:
            (first_frame_idx, last_frame_idx, confidence)

        """
        if not frames_info:
            raise ValueError("No frames to analyze")

        # 1. 寻找首帧
        first_idx = self._find_first_frame(frames_info, scene_scores)

        # 2. 寻找尾帧
        last_idx = self._find_last_frame(frames_info, scene_scores)

        # 3. 计算置信度
        confidence = self._calculate_confidence(frames_info, first_idx,
                                                last_idx)

        logger.info(
            f"首尾帧标记完成: first={first_idx}, last={last_idx}, confidence={confidence:.2f}")

        return first_idx, last_idx, confidence

    def _find_first_frame(self, frames_info: List[Dict],
                          scene_scores: List[float]) -> int:
        """
        寻找首帧

        策略:
        1.
        跳过开头的黑帧(亮度 < 30)
        2.
        寻找第一个清晰度较高的帧
        3.
        确保不在场景变化剧烈的位置
        """
        # 参数
        min_brightness = 30.0
        min_sharpness = 100.0
        search_range = min(len(frames_info), 150)  # 搜索前150帧

        for i in range(search_range):
            frame = frames_info[i]

            # 检查亮度
            if frame['brightness'] < min_brightness:
                continue

            # 检查清晰度
            if frame['sharpness'] < min_sharpness:
                continue

            # 检查场景稳定性 (避免在转场处)
            if i < len(scene_scores) and scene_scores[i] > 0.5:
                continue

            return i

        # 如果没找到合适的，返回第一个亮度足够的帧
        for i in range(search_range):
            if frames_info[i]['brightness'] >= min_brightness:
                return i

        return 0

    def _find_last_frame(self, frames_info: List[Dict],
                         scene_scores: List[float]) -> int:
        """
        寻找尾帧

        策略:
        1.
        从后往前搜索
        2.
        跳过黑帧和片尾字幕
        3.
        找到最后一个内容帧
        """
        min_brightness = 30.0
        min_sharpness = 100.0
        search_range = min(len(frames_info), 150)

        # 从后往前搜索
        for i in range(len(frames_info) - 1,
                       max(0, len(frames_info) - search_range - 1), -1):
            frame = frames_info[i]

            if frame['brightness'] < min_brightness:
                continue

            if frame['sharpness'] < min_sharpness:
                continue

            # 检查是否在场景变化处
            if i < len(scene_scores) and scene_scores[i] > 0.5:
                continue

            return i

        # 如果没找到，返回最后一个亮度足够的帧
        for i in range(len(frames_info) - 1,
                       max(0, len(frames_info) - search_range - 1), -1):
            if frames_info[i]['brightness'] >= min_brightness:
                return i

        return len(frames_info) - 1

    def _calculate_confidence(
            self,
            frames_info: List[Dict],
            first_idx: int,
            last_idx: int
    ) -> float:
        """计算置信度"""
        confidence = 0.5  # 基础置信度

        # 首帧质量加分
        if frames_info[first_idx]['sharpness'] > 200:
            confidence += 0.1
        if frames_info[first_idx]['brightness'] > 80:
            confidence += 0.1

        # 尾帧质量加分
        if frames_info[last_idx]['sharpness'] > 200:
            confidence += 0.1
        if frames_info[last_idx]['brightness'] > 80:
            confidence += 0.1

        # 位置合理性
        if first_idx < len(frames_info) * 0.1:  # 首帧在前10%
            confidence += 0.1
        if last_idx > len(frames_info) * 0.9:  # 尾帧在后10%
            confidence += 0.1

        return min(confidence, 1.0)

    def get_candidate_frames(
            self,
            frames_info: List[Dict],
            frame_type: str = 'first',
            top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        获取候选帧列表

        Args:
        frames_info: 帧信息
        frame_type: 'first'
        或
        'last'
        top_k: 返回前k个候选


        Returns:
        List[(frame_idx, score)]: 候选帧列表
        """

        scores = []

        search_range = min(len(frames_info), 150)

        if frame_type == 'first':
            indices = range(search_range)
        else:
            indices = range(len(frames_info) - 1,
                            max(0, len(frames_info) - search_range - 1), -1)

        for i in indices:
            frame = frames_info[i]

            # 计算分数: 亮度 + 清晰度
            score = (
                    frame['brightness'] / 255.0 * 0.4 +
                    min(frame['sharpness'] / 500.0, 1.0) * 0.6
            )

            scores.append((i, score))

        # 排序并返回top_k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
