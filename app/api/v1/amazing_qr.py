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

from PIL import Image
from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from amzqr import amzqr
from loguru import logger
from pydantic import BaseModel, Field

from app.services.minio_service import minio_service

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


class QRCodeResponse(BaseModel):
    """二维码生成响应模型"""
    success: bool
    message: str
    object_name: str
    url: str
    version: Optional[int] = None
    level: Optional[str] = None
    file_size: Optional[int] = None


@router.post("/simple", response_model=QRCodeResponse)
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

        # 读取生成的文件
        with open(output_file, "rb") as f:
            qr_data = f.read()

        # 上传到MinIO
        object_name, url = minio_service.upload_qrcode(
            qr_data=qr_data,
            qr_type="simple",
            file_extension="png"
        )

        return QRCodeResponse(
            success=True,
            message="二维码生成成功并已上传",
            object_name=object_name,
            url=url,
            version=version,
            level=level,
            file_size=len(qr_data)
        )

    except Exception as e:
        logger.error(f"Generate simple QR error: {e}")
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

        # 读取生成的文件
        with open(output_file, "rb") as f:
            qr_data = f.read()

        # 上传到MinIO
        object_name, url = minio_service.upload_qrcode(
            qr_data=qr_data,
            qr_type="artistic",
            file_extension="png"
        )

        return QRCodeResponse(
            success=True,
            message="艺术二维码生成成功并已上传",
            object_name=object_name,
            url=url,
            version=version_result,
            level=level_result,
            file_size=len(qr_data)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate artistic QR error: {e}")
        raise HTTPException(status_code=500,
                            detail=f"生成艺术二维码失败: {str(e)}")

    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/animated", response_model=QRCodeResponse)
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

        # 使用 Pillow 重新保存 GIF，确保无限循环
        final_output = os.path.join(temp_dir, "qr_final.gif")
        try:
            img = Image.open(output_file)
            frames = []
            durations = []

            # 提取所有帧和持续时间
            try:
                while True:
                    frames.append(img.copy())
                    durations.append(img.info.get('duration', 100))
                    img.seek(img.tell() + 1)
            except EOFError:
                pass

            # 保存为无限循环的 GIF
            if frames:
                frames[0].save(
                    final_output,
                    save_all=True,
                    append_images=frames[1:],
                    duration=durations,
                    loop=0,  # 0 表示无限循环
                    optimize=False
                )
                logger.info(f"GIF 已设置为无限循环，共 {len(frames)} 帧")
            else:
                # 如果提取帧失败，使用原文件
                shutil.copy(output_file, final_output)
                logger.warning("无法提取 GIF 帧，使用原文件")
        except Exception as e:
            logger.warning(f"处理 GIF 循环失败: {e}，使用原文件")
            shutil.copy(output_file, final_output)

        # 读取最终文件
        with open(final_output, "rb") as f:
            qr_data = f.read()

        # 上传到MinIO
        object_name, url = minio_service.upload_qrcode(
            qr_data=qr_data,
            qr_type="animated",
            file_extension="gif"
        )

        return QRCodeResponse(
            success=True,
            message="动态二维码生成成功并已上传（无限循环）",
            object_name=object_name,
            url=url,
            version=version_result,
            level=level_result,
            file_size=len(qr_data)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate animated QR error: {e}")
        raise HTTPException(status_code=500,
                            detail=f"生成动态二维码失败: {str(e)}")

    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
