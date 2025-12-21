#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: base
@Author  : shwezheng
@Time    : 2025/12/20 22:12
@Software: PyCharm
"""
from sqlalchemy.orm import DeclarativeBase


# 声明式基类
class Base(DeclarativeBase):
    """所有模型的基类"""
    pass
