# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/2 19:20
@Author   : wieszheng
@Software : PyCharm
"""
from app.crud.video import video_crud, frame_crud, frame_annotation_crud

__all__ = ["video_crud", "frame_crud", "frame_annotation_crud"]