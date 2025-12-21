#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: match
@Author  : shwezheng
@Time    : 2025/12/19 23:10
@Software: PyCharm
"""
from pydantic import BaseModel
from typing import List, Optional, Dict


class MatchResult(BaseModel):
    """匹配结果"""
    found: bool
    confidence: float
    center: Optional[dict]  # {"x": int, "y": int} 中心点坐标
    size: Optional[dict]  # {"width": int, "height": int} 元素尺寸
    top_left: Optional[dict]  # {"x": int, "y": int} 左上角坐标
    centers: Optional[List[dict]]  # 多个匹配的中心点

class Base64MatchRequest(BaseModel):
    """Base64格式的模板匹配请求"""
    source_image: str  # Base64编码的源图像
    template_image: str  # Base64编码的模板图像
    threshold: float = 0.8
    method: str = "ccoeff_normed"
    max_matches: int = 5

class Base64BatchMatchRequest(BaseModel):
    """Base64格式的批量匹配请求"""
    source_image: str  # Base64编码的源图像
    template_images: List[str]  # 多个Base64编码的模板图像
    threshold: float = 0.8
    method: str = "ccoeff_normed"
    template_names: Optional[List[str]] = None  # 模板名称标识


# ========== 图片模板匹配相关 ==========
class ImageMatchRequest(BaseModel):
    screenshot: str  # Base64 编码的截图
    template: str  # Base64 编码的模板图片
    threshold: float = 0.8  # 匹配阈值（0-1）


class ImageMatchResult(BaseModel):
    found: bool
    confidence: float
    position: Optional[Dict[str, int]] = None  # {x, y, width, height}
    center: Optional[Dict[str, int]] = None  # {x, y}
