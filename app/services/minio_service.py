#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: minio_service
@Author  : shwezheng
@Time    : 2025/11/27 00:05
@Software: PyCharm
"""
from minio import Minio
from minio.error import S3Error

import io
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class MinIOService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        """确保bucket存在"""
        try:
            if not self.client.bucket_exists(bucket_name=settings.MINIO_BUCKET):
                self.client.make_bucket(bucket_name=settings.MINIO_BUCKET)
                # 设置bucket为公开读
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET}/*"]
                    }]
                }
                import json
                self.client.set_bucket_policy(bucket_name=settings.MINIO_BUCKET, policy=json.dumps(policy))
        except S3Error as e:
            logger.error(f"MinIO bucket setup error: {e}")

    def upload_frame(self, video_id: str, frame_data: bytes, frame_type: str,
                     timestamp: float, content_type: str = "image/jpeg") -> str:
        """上传帧图片到MinIO"""
        try:
            object_name = f"{video_id}/frame_{frame_type}_{timestamp:.2f}.jpg"

            self.client.put_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
                data=io.BytesIO(frame_data),
                length=len(frame_data),
                content_type=content_type
            )

            # 返回访问URL
            url = f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{object_name}"
            return url

        except S3Error as e:
            logger.error(f"Upload frame error: {e}")
            raise

    def upload_video(self, video_id: str, file_path: str, filename: str) -> str:
        """上传原始视频到MinIO"""
        try:
            object_name = f"{video_id}/original/{filename}"

            self.client.fput_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
                file_path=file_path
            )

            return object_name

        except S3Error as e:
            logger.error(f"Upload video error: {e}")
            raise

    def delete_video_objects(self, video_id: str):
        """删除视频相关的所有对象"""
        try:
            objects = self.client.list_objects(
                bucket_name=settings.MINIO_BUCKET,
                prefix=f"{video_id}/",
                recursive=True
            )
            for obj in objects:
                self.client.remove_object(bucket_name=settings.MINIO_BUCKET, object_name=obj.object_name)
        except S3Error as e:
            logger.error(f"Delete objects error: {e}")


minio_service = MinIOService()
