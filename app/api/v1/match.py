#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: match
@Author  : shwezheng
@Time    : 2025/12/19 23:12
@Software: PyCharm
"""
import logging

import cv2
from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse

from app.schemas.match import MatchResult, Base64MatchRequest, Base64BatchMatchRequest
from app.services.template_matches import base64_to_image, get_match_method, find_template_matches, image_to_base64

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/match", response_model=MatchResult)
async def match_template(request: Base64MatchRequest) -> MatchResult:
    """
    Base64格式的模板匹配接口

    Args:
        request.source_image: Base64编码的源图像
        request.template_image: Base64编码的模板图像
        request.threshold: 置信度阈值(0-1)
        request.method: 匹配方法
        request.max_matches: 最多返回几个匹配

    Returns:
        匹配结果
    """
    try:
        # 解码Base64图像
        source_img = base64_to_image(request.source_image)
        template_img = base64_to_image(request.template_image)

        # 获取匹配方法
        match_method = get_match_method(request.method)

        # 执行匹配
        matches, max_conf = find_template_matches(
            source_img,
            template_img,
            match_method,
            request.threshold,
            request.max_matches
        )

        logger.info(
            f"匹配完成: 源图{source_img.shape}, "
            f"模板{template_img.shape}, 最高置信度{max_conf:.3f}"
        )

        if not matches:
            return MatchResult(found=False, confidence=0.0)

        return MatchResult(
            found=True,
            confidence=max_conf,
            center=matches[0]["center"],
            size=matches[0]["size"],
            top_left=matches[0]["top_left"],
            centers=[m["center"] for m in matches]
        )

    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"匹配失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match-batch")
async def match_multiple_templates(request: Base64BatchMatchRequest) -> JSONResponse:
    """
    Base64格式的批量模板匹配接口
    """
    try:
        source_img = base64_to_image(request.source_image)
        match_method = get_match_method(request.method)

        results = {}

        for i, template_b64 in enumerate(request.template_images):
            template_img = base64_to_image(template_b64)

            # 先尝试找所有匹配
            matches, max_conf = find_template_matches(
                source_img,
                template_img,
                match_method,
                request.threshold,
                max_matches=10  # 先找10个
            )

            # 使用提供的名称或使用默认名称
            key = (request.template_names[i] if request.template_names
                                                and i < len(request.template_names) else f"template_{i}")

            results[key] = {
                "found": len(matches) > 0,
                "confidence": max_conf,
                "match_count": len(matches),
                "centers": [m["center"] for m in matches],
                "top_lefts": [m["top_left"] for m in matches]
            }

        return JSONResponse(content=results)

    except Exception as e:
        logger.error(f"批量匹配失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/match-with-visualization")
async def match_with_visualization(request: Base64MatchRequest):
    """
    匹配并直接返回可视化结果图片（PNG格式）
    在源图像上标记所有匹配位置的矩形框、中心点和置信度
    """
    try:
        from fastapi.responses import StreamingResponse

        source_img = base64_to_image(request.source_image)
        template_img = base64_to_image(request.template_image)

        match_method = get_match_method(request.method)
        matches, max_conf = find_template_matches(
            source_img,
            template_img,
            match_method,
            request.threshold,
            request.max_matches
        )

        # 在源图像上绘制匹配框和中心点
        visualization = source_img.copy()
        h, w = template_img.shape[:2]

        for i, match in enumerate(matches):
            # 获取坐标信息
            x_tl, y_tl = match["top_left"]["x"], match["top_left"]["y"]
            cx, cy = match["center"]["x"], match["center"]["y"]
            confidence = match["confidence"]

            # 绘制矩形框 (绿色，线宽2)
            cv2.rectangle(
                visualization,
                (x_tl, y_tl),
                (x_tl + w, y_tl + h),
                (0, 255, 0),
                2
            )

            # 绘制中心点 (红色实心圆)
            cv2.circle(visualization, (cx, cy), 5, (0, 0, 255), -1)

            # 绘制置信度文字 (绿色)
            cv2.putText(
                visualization,
                f"Conf: {confidence:.3f}",
                (x_tl, y_tl - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )

            # 绘制匹配序号 (蓝色)
            cv2.putText(
                visualization,
                f"#{i + 1}",
                (cx - 15, cy - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 0, 0),
                1
            )

        # 编码为PNG并返回
        success, buffer = cv2.imencode(".png", visualization)

        if not success:
            raise ValueError("图像编码失败")

        return StreamingResponse(
            iter([buffer.tobytes()]),
            media_type="image/png"
        )

    except Exception as e:
        logger.error(f"可视化匹配失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match-unique", response_model=MatchResult)
async def match_unique_element(request: Base64MatchRequest) -> MatchResult:
    """
    唯一元素匹配接口

    仅在恰好找到一个匹配时返回成功，否则返回错误
    用于需要唯一定位的场景（如唯一按钮、唯一标签等）

    Args:
        request: 匹配请求 (置信度阈值自动设置较高以确保唯一性)

    Returns:
        匹配结果，如果找到多个匹配或未找到都返回found=False
    """
    try:
        # 唯一匹配模式: 只查找1个匹配
        source_img = base64_to_image(request.source_image)
        template_img = base64_to_image(request.template_image)

        # 强制阈值至少为0.85以确保高精度
        threshold = max(request.threshold, 0.85)

        match_method = get_match_method(request.method)

        # 只查找1个匹配
        matches, max_conf = find_template_matches(
            source_img,
            template_img,
            match_method,
            threshold,
            max_matches=1  # 仅查找一个
        )

        if not matches:
            logger.info(f"唯一匹配失败: 未找到匹配 (阈值: {threshold})")
            return MatchResult(found=False, confidence=0.0)

        if len(matches) > 1 or max_conf < threshold:
            logger.warning(
                f"唯一匹配失败: 找到多个匹配或置信度不足 "
                f"(个数: {len(matches)}, 最高置信度: {max_conf:.3f})"
            )
            return MatchResult(found=False, confidence=max_conf)

        logger.info(f"唯一匹配成功: 置信度{max_conf:.3f}, 中心点{matches[0]['center']}")

        return MatchResult(
            found=True,
            confidence=max_conf,
            center=matches[0]["center"],
            size=matches[0]["size"],
            top_left=matches[0]["top_left"]
        )

    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"唯一匹配失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/methods")
async def get_available_methods():
    """获取可用的匹配方法"""
    return {
        "methods": [
            "ccoeff",
            "ccoeff_normed",
            "ccorr",
            "ccorr_normed",
            "sqdiff",
            "sqdiff_normed"
        ],
        "recommended": "ccoeff_normed",
        "description": {
            "ccoeff_normed": "相关系数匹配（推荐，速度快，鲁棒性好）",
            "ccorr_normed": "相关性匹配（速度快）",
            "sqdiff_normed": "平方差匹配（对光照变化敏感）"
        }
    }
