#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: amazing-qr
@Author  : shwezheng
@Time    : 2025/11/29 23:33
@Software: PyCharm
"""
import os
import shutil
import tempfile
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from amzqr import amzqr
from loguru import logger
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

router = APIRouter()


class QRCodeRequest(BaseModel):
    """二维码生成请求模型"""
    words: str = Field(..., description="要编码的文本内容（URL或文字）",
                       min_length=1)
    version: Optional[int] = Field(1, ge=1, le=40,
                                   description="二维码大小版本，1-40")
    level: Optional[str] = Field("H", pattern="^[LMQH]$",
                                 description="纠错级别：L, M, Q, H")
    contrast: Optional[float] = Field(1.0, ge=0.1, le=3.0,
                                      description="对比度，0.1-3.0")
    brightness: Optional[float] = Field(1.0, ge=0.1, le=3.0,
                                        description="亮度，0.1-3.0")


@router.post("/simple")
async def generate_simple_qr(request: QRCodeRequest):
    """
    生成普通二维码，直接返回图片流

    - **words**: 要编码的内容（必填）
    - **version**: 二维码版本 1-40（可选，默认1）
    - **level**: 纠错级别 L/M/Q/H（可选，默认H）
    - **contrast**: 对比度 0.1-3.0（可选，默认1.0）
    - **brightness**: 亮度 0.1-3.0（可选，默认1.0）
    """
    temp_dir = None
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        output_file = os.path.join(temp_dir, "qr_code.png")

        # 生成二维码
        version, level, qr_name = amzqr.run(
            words=request.words,
            version=request.version,
            level=request.level,
            picture=None,
            colorized=False,
            contrast=request.contrast,
            brightness=request.brightness,
            save_name="qr_code.png",
            save_dir=temp_dir
        )

        # 读取生成的文件到内存
        with open(output_file, "rb") as f:
            image_data = BytesIO(f.read())

        # 返回图片流
        return StreamingResponse(
            image_data,
            media_type="image/png",
            headers={
                "Content-Disposition": "inline; filename=qrcode.png",
                "X-QR-Version": str(version),
                "X-QR-Level": level
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成二维码失败: {str(e)}")

    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/artistic")
async def generate_artistic_qr(
        words: str = Form(..., description="要编码的文本内容", min_length=1),
        picture: UploadFile = File(..., description="背景图片文件"),
        version: int = Form(1, ge=1, le=40, description="二维码版本"),
        level: str = Form("H", description="纠错级别"),
        colorized: bool = Form(False, description="是否彩色化"),
        contrast: float = Form(1.0, ge=0.1, le=3.0, description="对比度"),
        brightness: float = Form(1.0, ge=0.1, le=3.0, description="亮度")
):
    """
    生成艺术二维码（带背景图片），直接返回图片流

    需要上传一张图片作为二维码背景
    - 建议使用接近正方形的图片
    - 支持格式：PNG, JPG, JPEG, BMP
    - 如果图片有透明层，建议先转换为白色背景
    """
    temp_dir = None
    try:
        # 验证纠错级别
        if level not in ['L', 'M', 'Q', 'H']:
            raise HTTPException(status_code=400,
                                detail="纠错级别必须是 L, M, Q 或 H")

        # 验证文件格式
        file_ext = os.path.splitext(picture.filename)[1].lower()
        if file_ext not in ['.png', '.jpg', '.jpeg', '.bmp']:
            raise HTTPException(
                status_code=400,
                detail="不支持的图片格式，请上传 PNG, JPG, JPEG 或 BMP 文件"
            )

        # 创建临时目录
        temp_dir = tempfile.mkdtemp()

        # 保存上传的图片到临时文件
        upload_file = os.path.join(temp_dir, f"upload{file_ext}")
        with open(upload_file, "wb") as buffer:
            shutil.copyfileobj(picture.file, buffer)

        # 生成艺术二维码
        output_file = os.path.join(temp_dir, "qr_artistic.png")
        version_result, level_result, qr_name = amzqr.run(
            words=words,
            version=version,
            level=level,
            picture=upload_file,
            colorized=colorized,
            contrast=contrast,
            brightness=brightness,
            save_name="qr_artistic.png",
            save_dir=temp_dir
        )

        # 读取生成的文件到内存
        with open(output_file, "rb") as f:
            image_data = BytesIO(f.read())

        # 返回图片流
        return StreamingResponse(
            image_data,
            media_type="image/png",
            headers={
                "Content-Disposition": "inline; filename=qrcode_artistic.png",
                "X-QR-Version": str(version_result),
                "X-QR-Level": level_result,
                "X-QR-Colorized": str(colorized)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成艺术二维码失败: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"生成艺术二维码失败: {str(e)}")

    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/animated")
async def generate_animated_qr(
        words: str = Form(..., description="要编码的文本内容", min_length=1),
        gif_file: UploadFile = File(..., description="GIF动画文件"),
        version: int = Form(1, ge=1, le=40, description="二维码版本"),
        level: str = Form("H", description="纠错级别"),
        colorized: bool = Form(False, description="是否彩色化"),
        contrast: float = Form(1.0, ge=0.1, le=3.0, description="对比度"),
        brightness: float = Form(1.0, ge=0.1, le=3.0, description="亮度")
):
    """
    生成动态GIF二维码，直接返回GIF流

    需要上传一个GIF动画文件
    - 必须是 .gif 格式
    - 输出文件也将是 .gif 格式
    """
    temp_dir = None
    try:
        # 验证纠错级别
        if level not in ['L', 'M', 'Q', 'H']:
            raise HTTPException(status_code=400,
                                detail="纠错级别必须是 L, M, Q 或 H")

        # 验证是否为GIF文件
        if not gif_file.filename.lower().endswith('.gif'):
            raise HTTPException(
                status_code=400,
                detail="请上传 GIF 格式的动画文件"
            )

        # 创建临时目录
        temp_dir = tempfile.mkdtemp()

        # 保存上传的GIF到临时文件
        upload_file = os.path.join(temp_dir, "upload.gif")
        with open(upload_file, "wb") as buffer:
            shutil.copyfileobj(gif_file.file, buffer)

        # 生成动态二维码
        output_file = os.path.join(temp_dir, "qr_animated.gif")
        version_result, level_result, qr_name = amzqr.run(
            words=words,
            version=version,
            level=level,
            picture=upload_file,
            colorized=colorized,
            contrast=contrast,
            brightness=brightness,
            save_name="qr_animated.gif",
            save_dir=temp_dir
        )

        # 读取生成的文件到内存
        with open(output_file, "rb") as f:
            image_data = BytesIO(f.read())

        # 返回GIF流
        return StreamingResponse(
            image_data,
            media_type="image/gif",
            headers={
                "Content-Disposition": "inline; filename=qrcode_animated.gif",
                "X-QR-Version": str(version_result),
                "X-QR-Level": level_result,
                "X-QR-Colorized": str(colorized)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"生成动态二维码失败: {str(e)}")

    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
