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

from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from fastapi.responses import FileResponse
from amzqr import amzqr

from PIL import Image

router = APIRouter()


@router.post("/generate")
async def generate_qr(
        # 必需参数
        words: str = Form(..., description="要编码的数据"),

        # 基本参数
        version: int = Form(1, ge=1, le=40, description="二维码版本 (1-40)"),
        level: str = Form("H", description="纠错级别 (L, M, Q, H)"),

        # 图片相关参数
        picture: UploadFile = File(None, description="背景图片文件 (支持PNG, JPG, GIF)"),
        colorized: bool = Form(False, description="是否生成彩色二维码"),
        contrast: float = Form(1.0, ge=0.1, le=3.0, description="对比度 (0.1-3.0)"),
        brightness: float = Form(1.0, ge=0.1, le=3.0, description="亮度 (0.1-3.0)"),

        # 高级功能
        logo: UploadFile = File(None, description="Logo图片 (PNG格式最佳)"),
        output_format: str = Form("png", description="输出格式 (png, jpg, gif)")
):
    """
    集成二维码生成接口 - 支持所有AmazingQR功能
    """
    picture_path = None
    logo_path = None
    temp_files = []

    try:
        # 1. 处理背景图片文件
        if picture and picture.filename:
            file_ext = os.path.splitext(picture.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                content = await picture.read()
                tmp.write(content)
                picture_path = tmp.name
                temp_files.append(picture_path)

        # 2. 处理Logo图片文件
        if logo and logo.filename:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                content = await logo.read()
                tmp.write(content)
                logo_path = tmp.name
                temp_files.append(logo_path)

        # 3. 使用临时目录生成二维码
        with tempfile.TemporaryDirectory() as temp_dir:
            # 设置输出文件名
            save_name = f"qrcode.{output_format}"

            # 调用AmazingQR生成二维码
            result = amzqr.run(
                words=words,
                version=version,
                level=level,
                picture=picture_path,
                colorized=colorized,
                contrast=contrast,
                brightness=brightness,
                save_name=save_name,
                save_dir=temp_dir
            )

            if not result or len(result) != 3:
                raise HTTPException(status_code=500, detail="二维码生成失败")

            version, level, qr_name = result

            # 4. 如果提供了Logo，添加到二维码中心
            final_output_path = qr_name
            if logo_path and os.path.exists(qr_name):
                try:
                    qr_img = Image.open(qr_name)
                    logo_img = Image.open(logo_path)

                    # 调整Logo大小
                    qr_width, qr_height = qr_img.size
                    logo_size = min(qr_width, qr_height) // 4
                    logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

                    # 确保Logo支持透明度
                    if logo_img.mode != 'RGBA':
                        logo_img = logo_img.convert('RGBA')

                    # 计算Logo位置并粘贴
                    pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
                    final_qr = qr_img.copy()
                    final_qr.paste(logo_img, pos, logo_img)

                    # 保存带Logo的最终版本
                    final_output_path = os.path.join(temp_dir, f"qrcode_with_logo.{output_format}")
                    final_qr.save(final_output_path, format=output_format.upper())

                except Exception as logo_error:
                    # Logo处理失败，使用原始二维码
                    print(f"Logo处理失败: {logo_error}")
                    final_output_path = qr_name

            # 5. Move the file to a temporary location that persists beyond the with block
            if os.path.exists(final_output_path):
                # Create a temporary file that won't be auto-deleted
                temp_output_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}")
                temp_output_file.close()

                # Copy the generated file to the persistent temporary file
                shutil.copy2(final_output_path, temp_output_file.name)
                temp_files.append(temp_output_file.name)  # Add to cleanup list

                # 确定媒体类型
                media_types = {
                    'png': 'image/png',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'gif': 'image/gif'
                }
                media_type = media_types.get(output_format.lower(), 'image/png')

                return FileResponse(
                    temp_output_file.name,
                    media_type=media_type,
                    filename=f"qrcode.{output_format}"
                )
            else:
                raise HTTPException(status_code=500, detail="二维码文件未生成")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成二维码失败: {str(e)}")

    finally:
        # 清理临时文件
        for file_path in temp_files:
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except:
                    pass
