#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: template_matches
@Author  : shwezheng
@Time    : 2025/12/19 23:08
@Software: PyCharm
"""
import logging
import cv2
import numpy as np
import base64
import io
from PIL import Image

logger = logging.getLogger(__name__)


def base64_to_image(base64_str: str) -> np.ndarray:
    """
    将Base64字符串转换为OpenCV图像

    Args:
        base64_str: Base64编码的图像字符串（可包含或不包含data:image/png;base64,前缀）

    Returns:
        cv2格式的图像数据
    """
    try:
        # 移除data URI前缀（如果存在）
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        # 解码Base64
        img_bytes = base64.b64decode(base64_str)
        img = Image.open(io.BytesIO(img_bytes))

        # 转换为BGR格式（OpenCV使用BGR）
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.error(f"Base64转换失败: {str(e)}")
        raise ValueError(f"无效的Base64图像格式: {str(e)}")


def image_to_base64(img: np.ndarray, format: str = "png") -> str:
    """
    将OpenCV图像转换为Base64字符串

    Args:
        img: OpenCV图像
        format: 图像格式 (png, jpg等)

    Returns:
        Base64编码的字符串
    """
    _, buffer = cv2.imencode(f".{format}", img)
    return base64.b64encode(buffer).decode("utf-8")


def get_match_method(method_name: str):
    """获取OpenCV匹配方法"""
    methods = {
        "ccoeff": cv2.TM_CCOEFF,
        "ccoeff_normed": cv2.TM_CCOEFF_NORMED,
        "ccorr": cv2.TM_CCORR,
        "ccorr_normed": cv2.TM_CCORR_NORMED,
        "sqdiff": cv2.TM_SQDIFF,
        "sqdiff_normed": cv2.TM_SQDIFF_NORMED,
    }
    return methods.get(method_name, cv2.TM_CCOEFF_NORMED)


def find_template_matches(
        source_img: np.ndarray,
        template_img: np.ndarray,
        method: int,
        threshold: float,
        max_matches: int
) -> tuple:
    """
    使用模板匹配查找所有匹配位置

    Returns:
        (匹配结果列表, 最大置信度)
    """
    h, w = template_img.shape[:2]

    # 验证模板大小
    if h > source_img.shape[0] or w > source_img.shape[1]:
        raise ValueError("模板图像不能大于源图像")

    result = cv2.matchTemplate(source_img, template_img, method)

    is_sqdiff = method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]

    matches = []
    result_copy = result.copy().astype(np.float32)

    # 根据方法类型确定屏蔽值
    if is_sqdiff:
        mask_value = np.inf
    else:
        mask_value = -np.inf

    for iteration in range(max_matches):
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_copy)

        if is_sqdiff:
            confidence = 1 - (min_val / 255) if min_val != np.inf else 0
            location = min_loc
            val = min_val
            # 如果最小值是inf，说明已无有效匹配
            if np.isinf(val):
                break
        else:
            confidence = max_val
            location = max_loc
            val = max_val
            # 如果最大值是-inf，说明已无有效匹配
            if np.isinf(val):
                break

        # 检查阈值
        if not is_sqdiff and confidence < threshold:
            break
        if is_sqdiff and val > 100:
            break

        # 计算中心点
        center_x = int(location[0] + w / 2)
        center_y = int(location[1] + h / 2)

        matches.append({
            "top_left": {"x": int(location[0]), "y": int(location[1])},
            "center": {"x": center_x, "y": center_y},
            "confidence": float(confidence),
            "size": {"width": w, "height": h}
        })

        # 在匹配位置周围设置屏蔽值，防止重复检测
        # 屏蔽范围：模板大小
        y_start = max(0, location[1] - h // 2)
        y_end = min(result_copy.shape[0], location[1] + h + h // 2)
        x_start = max(0, location[0] - w // 2)
        x_end = min(result_copy.shape[1], location[0] + w + w // 2)

        result_copy[y_start:y_end, x_start:x_end] = mask_value

    max_confidence = matches[0]["confidence"] if matches else 0
    return matches, max_confidence
