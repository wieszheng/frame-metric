#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: monitor
@Author  : shwezheng
@Time    : 2025/12/20 22:41
@Software: PyCharm
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict


class PerformanceScore(BaseModel):
    overall: int
    fpsScore: int
    cpuScore: int
    memoryScore: int
    temperatureScore: int
    powerScore: int
    grade: str


class MonitorSample(BaseModel):
    timestamp: int
    cpu: Optional[float] = None
    memory: Optional[float] = None
    appCpuUsage: Optional[float] = None
    appMemoryUsage: Optional[float] = None
    appMemoryPercent: Optional[float] = None
    fps: Optional[float] = None
    fpsStability: Optional[float] = None
    gpuLoad: Optional[float] = None
    powerConsumption: Optional[float] = None
    networkUpSpeed: Optional[float] = None
    networkDownSpeed: Optional[float] = None
    deviceTemperature: Optional[float] = None
    performanceScore: Optional[PerformanceScore] = None


class MetricIn(BaseModel):
    taskId: str
    sample: MonitorSample


class MetricOut(BaseModel):
    id: int
    taskId: str
    timestamp: int
    cpu: Optional[float] = None
    memory: Optional[float] = None
    appCpuUsage: Optional[float] = None
    appMemoryUsage: Optional[float] = None
    appMemoryPercent: Optional[float] = None
    fps: Optional[float] = None
    fpsStability: Optional[float] = None
    gpuLoad: Optional[float] = None
    powerConsumption: Optional[float] = None
    networkUpSpeed: Optional[float] = None
    networkDownSpeed: Optional[float] = None
    deviceTemperature: Optional[float] = None
    performanceScore: Optional[PerformanceScore] = None

    model_config = ConfigDict(from_attributes=True)


# ========== 任务相关 ==========
class AlertThresholds(BaseModel):
    fpsWarning: Optional[float] = None
    fpsCritical: Optional[float] = None
    cpuWarning: Optional[float] = None
    cpuCritical: Optional[float] = None
    memoryWarning: Optional[float] = None
    memoryCritical: Optional[float] = None
    temperatureWarning: Optional[float] = None
    temperatureCritical: Optional[float] = None


class MonitorConfig(BaseModel):
    interval: Optional[int] = None
    enableAlerts: Optional[bool] = None
    thresholds: Optional[AlertThresholds] = None


class MonitorTaskCreate(BaseModel):
    id: str
    name: str
    packageName: str
    scriptTemplateId: str
    metrics: List[str]  # MonitoringMetric[]
    monitorConfig: Optional[MonitorConfig] = None


class MonitorTaskUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None  # SceneTaskStatus
    monitorConfig: Optional[MonitorConfig] = None
    errorMessage: Optional[str] = None
    archived: Optional[bool] = None


class MonitorTaskOut(BaseModel):
    id: str
    name: str
    packageName: str
    scriptTemplateId: str
    metrics: List[str]
    status: str
    monitorConfig: Optional[Dict[str, Any]] = None
    errorMessage: Optional[str] = None
    archived: bool = False
    createdAt: int
    updatedAt: int
    model_config = ConfigDict(from_attributes=True)


class MonitorTaskSummary(BaseModel):
    """任务摘要（包含统计信息）"""
    id: str
    name: str
    packageName: str
    status: str
    archived: bool = False
    createdAt: int
    updatedAt: int
    sampleCount: int
    firstSampleTime: Optional[int] = None
    lastSampleTime: Optional[int] = None


# ========== 脚本模板相关 ==========
class ScriptTemplateCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    code: str  # JavaScript/TypeScript 代码


class ScriptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None


class ScriptTemplateOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    code: str
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)
