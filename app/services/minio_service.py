#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: minio_service
@Author  : shwezheng
@Time    : 2025/11/27 00:05
@Software: PyCharm
"""
import json

from minio import Minio
from minio.error import S3Error

import io
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class MinIOService:
    """MinIO服务类"""

    def __init__(self):
        """初始化MinIO客户端"""
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        """确保bucket存在并设置访问策略"""
        try:
            # 检查bucket是否存在
            if not self.client.bucket_exists(settings.MINIO_BUCKET):
                self.client.make_bucket(settings.MINIO_BUCKET)
                logger.info(f"Created bucket: {settings.MINIO_BUCKET}")

            # 设置bucket为公开读
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET}/*"]
                    }
                ]
            }

            self.client.set_bucket_policy(
                settings.MINIO_BUCKET,
                json.dumps(policy)
            )

            logger.info(f"Bucket configured: {settings.MINIO_BUCKET}")

        except S3Error as e:
            logger.error(f"MinIO bucket setup error: {e}")
            raise

    def upload_frame(
            self,
            video_id: str,
            frame_data: bytes,
            frame_type: str,
            timestamp: float,
            content_type: str = "image/jpeg"
    ) -> str:
        """
        上传帧图片到MinIO

        Args:
        video_id: 视频ID
        frame_data: 图片字节数据
        frame_type: 帧类型(first / last)
        timestamp: 时间戳
        content_type: 内容类型

        Returns:
        str: 访问URL

        """
        try:
            object_name = f"{video_id}/frame_{frame_type}_{timestamp:.2f}.jpg"

            self.client.put_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
                data=io.BytesIO(frame_data),
                length=len(frame_data),
                content_type=content_type
            )

            # 生成访问URL
            url = f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{object_name}"

            logger.info(f"Uploaded frame: {object_name}")

            return url

        except S3Error as e:
            logger.error(f"Upload frame error: {e}")
            raise

    def upload_video(
            self,
            video_id: str,
            file_path: str,
            filename: str
    ) -> str:
        """
        上传原始视频到MinIO

        Args:
        video_id: 视频ID
        file_path: 本地文件路径
        filename: 文件名


        Returns:
        str: MinIO中的对象名称
        """
        try:
            object_name = f"{video_id}/original/{filename}"

            self.client.fput_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
                file_path=file_path
            )

            logger.info(f"Uploaded video: {object_name}")

            return object_name

        except S3Error as e:
            logger.error(f"Upload video error: {e}")
            raise

    def delete_video_objects(self, video_id: str):
        """
        删除视频相关的所有对象

        Args:
        video_id: 视频ID

        """
        try:
            objects = self.client.list_objects(
                settings.MINIO_BUCKET,
                prefix=f"{video_id}/",
                recursive=True
            )

            for obj in objects:
                self.client.remove_object(settings.MINIO_BUCKET,
                                          obj.object_name)
                logger.info(f"Deleted object: {obj.object_name}")

        except S3Error as e:
            logger.error(f"Delete objects error: {e}")
            raise

    def get_object_url(self, object_name: str, expires: int = 3600) -> str:
        """
        获取对象的预签名URL

        Args:
        object_name: 对象名称
        expires: 过期时间(秒)


        Returns:
        str: 预签名URL
        """
        try:
            from datetime import timedelta

            url = self.client.presigned_get_object(
                settings.MINIO_BUCKET,
                object_name,
                expires=timedelta(seconds=expires)
            )

            return url

        except S3Error as e:
            logger.error(f"Get object URL error: {e}")
            raise


# 全局单例
minio_service = MinIOService()
