#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: monitor
@Author  : shwezheng
@Time    : 2025/12/20 22:08
@Software: PyCharm
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, Index, Integer, JSON, DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base



class MonitorTask(Base):
    """任务表"""
    __tablename__ = "monitor_tasks"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True, comment="任务 ID")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="任务名称")
    package_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="应用包名")
    script_template_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="脚本模板 ID")
    metrics: Mapped[List[str]] = mapped_column(JSON, nullable=False, comment="监控指标列表")
    status: Mapped[str] = mapped_column(String(255), nullable=False, default="idle",
                                        comment="任务状态: idle/running/finished/error")
    monitor_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True,
                                                                     comment="监控配置: interval/enableAlerts/thresholds")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True,
                                                         comment="错误信息（当 status 为 error 时使用）")
    archived: Mapped[bool] = mapped_column(nullable=False, default=False, comment="是否已归档")
    created_at: Mapped[datetime] = mapped_column(DATETIME, nullable=False, comment="创建时间戳（毫秒）")
    updated_at: Mapped[datetime] = mapped_column(DATETIME, nullable=False, comment="更新时间戳（毫秒）")

    # 索引
    __table_args__ = (
        Index("idx_task_status", "status"),
        Index("idx_task_created", "created_at"),
        Index("idx_task_archived", "archived"),
    )


class Metric(Base):
    """监控样本表"""
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="任务 ID")
    timestamp: Mapped[datetime] = mapped_column(DATETIME, nullable=False, comment="采样时间戳（毫秒）")

    # 基础指标
    cpu: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="CPU 使用率（%）")
    memory: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="内存使用量（MB）")

    # 扩展指标
    app_cpu_usage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="应用 CPU 使用率（%）")
    app_memory_usage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="应用内存使用量（MB）")
    app_memory_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="应用内存使用率（%）")
    fps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="FPS")
    fps_stability: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="FPS 稳定性")
    gpu_load: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="GPU 负载（%）")
    power_consumption: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="功耗（W）")
    network_up_speed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="网络上传速度（KB/s）")
    network_down_speed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="网络下载速度（KB/s）")
    device_temperature: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="设备温度（°C）")
    performance_score: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, comment="性能评分")

    # 索引
    __table_args__ = (
        Index("idx_metric_task_timestamp", "task_id", "timestamp"),
    )


class ScriptTemplate(Base):
    """脚本模板表"""
    __tablename__ = "script_templates"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True, comment="脚本模板 ID")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="脚本模板名称")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="脚本模板描述")
    code: Mapped[str] = mapped_column(Text, nullable=False, comment="脚本代码（JavaScript/TypeScript）")
    created_at: Mapped[datetime] = mapped_column(DATETIME, nullable=False, comment="创建时间戳（毫秒）")
    updated_at: Mapped[datetime] = mapped_column(DATETIME, nullable=False, comment="更新时间戳（毫秒）")

    # 索引
    __table_args__ = (
        Index("idx_script_template_name", "name"),
    )
