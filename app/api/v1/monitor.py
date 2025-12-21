#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: monitor
@Author  : shwezheng
@Time    : 2025/12/20 22:53
@Software: PyCharm
"""
import base64
import datetime
import io
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_db
from app.models.monitor import Metric, MonitorTask, ScriptTemplate
from app.schemas.match import ImageMatchResult, ImageMatchRequest
from app.schemas.monitor import MetricOut, MetricIn, MonitorTaskOut, MonitorTaskCreate, MonitorTaskUpdate, \
    ScriptTemplateOut, ScriptTemplateCreate, ScriptTemplateUpdate, MonitorTaskSummary

router = APIRouter()


@router.post("/metrics", response_model=MetricOut, status_code=201)
async def create_metric(metric_in: MetricIn, db: AsyncSession = Depends(get_async_db)):
    """创建监控样本"""
    sample = metric_in.sample

    # 将浮点数转换为整数存储（保留精度，例如 *100 存储百分比）
    metric = Metric(
        task_id=metric_in.taskId,
        timestamp=sample.timestamp,
        cpu=int(sample.cpu * 100) if sample.cpu is not None else None,
        memory=int(sample.memory) if sample.memory is not None else None,
        app_cpu_usage=int(sample.appCpuUsage * 100) if sample.appCpuUsage is not None else None,
        app_memory_usage=int(sample.appMemoryUsage) if sample.appMemoryUsage is not None else None,
        app_memory_percent=int(sample.appMemoryPercent * 100) if sample.appMemoryPercent is not None else None,
        fps=int(sample.fps) if sample.fps is not None else None,
        fps_stability=int(sample.fpsStability * 1000) if sample.fpsStability is not None else None,  # 转换为毫秒
        gpu_load=int(sample.gpuLoad * 100) if sample.gpuLoad is not None else None,
        power_consumption=int(sample.powerConsumption * 1000) if sample.powerConsumption is not None else None,  # 转换为毫瓦
        network_up_speed=int(sample.networkUpSpeed) if sample.networkUpSpeed is not None else None,
        network_down_speed=int(sample.networkDownSpeed) if sample.networkDownSpeed is not None else None,
        device_temperature=int(sample.deviceTemperature * 10) if sample.deviceTemperature is not None else None,
        # 转换为 0.1°C
        performance_score=sample.performanceScore.model_dump() if sample.performanceScore else None,
    )

    db.add(metric)
    await db.commit()
    await db.refresh(metric)

    # 转换为输出格式
    return MetricOut(
        id=metric.id,
        taskId=metric.task_id,
        timestamp=metric.timestamp,
        cpu=metric.cpu / 100.0 if metric.cpu is not None else None,
        memory=float(metric.memory) if metric.memory is not None else None,
        appCpuUsage=metric.app_cpu_usage / 100.0 if metric.app_cpu_usage is not None else None,
        appMemoryUsage=float(metric.app_memory_usage) if metric.app_memory_usage is not None else None,
        appMemoryPercent=metric.app_memory_percent / 100.0 if metric.app_memory_percent is not None else None,
        fps=float(metric.fps) if metric.fps is not None else None,
        fpsStability=metric.fps_stability / 1000.0 if metric.fps_stability is not None else None,
        gpuLoad=metric.gpu_load / 100.0 if metric.gpu_load is not None else None,
        powerConsumption=metric.power_consumption / 1000.0 if metric.power_consumption is not None else None,
        networkUpSpeed=float(metric.network_up_speed) if metric.network_up_speed is not None else None,
        networkDownSpeed=float(metric.network_down_speed) if metric.network_down_speed is not None else None,
        deviceTemperature=metric.device_temperature / 10.0 if metric.device_temperature is not None else None,
        performanceScore=sample.performanceScore,
    )


@router.get("/metrics", response_model=List[MetricOut])
async def list_metrics(
        task_id: str = Query(..., description="任务 ID"),
        limit: int = Query(200, ge=1, le=1000, description="返回条数上限"),
        offset: int = Query(0, ge=0, description="偏移量"),
        db: AsyncSession = Depends(get_async_db),
):
    """查询任务的监控样本列表"""
    result = await db.execute(
        select(Metric)
        .filter(Metric.task_id == task_id)
        .order_by(desc(Metric.timestamp))
        .offset(offset)
        .limit(limit)
    )
    metrics = result.scalars().all()

    result = []
    for metric in metrics:
        result.append(MetricOut(
            id=metric.id,
            taskId=metric.task_id,
            timestamp=metric.timestamp,
            cpu=metric.cpu / 100.0 if metric.cpu is not None else None,
            memory=float(metric.memory) if metric.memory is not None else None,
            appCpuUsage=metric.app_cpu_usage / 100.0 if metric.app_cpu_usage is not None else None,
            appMemoryUsage=float(metric.app_memory_usage) if metric.app_memory_usage is not None else None,
            appMemoryPercent=metric.app_memory_percent / 100.0 if metric.app_memory_percent is not None else None,
            fps=float(metric.fps) if metric.fps is not None else None,
            fpsStability=metric.fps_stability / 1000.0 if metric.fps_stability is not None else None,
            gpuLoad=metric.gpu_load / 100.0 if metric.gpu_load is not None else None,
            powerConsumption=metric.power_consumption / 1000.0 if metric.power_consumption is not None else None,
            networkUpSpeed=float(metric.network_up_speed) if metric.network_up_speed is not None else None,
            networkDownSpeed=float(metric.network_down_speed) if metric.network_down_speed is not None else None,
            deviceTemperature=metric.device_temperature / 10.0 if metric.device_temperature is not None else None,
            performanceScore=metric.performance_score,
        ))

    return result


@router.get("/metrics/{metric_id}", response_model=MetricOut)
async def get_metric(metric_id: int, db: AsyncSession = Depends(get_async_db)):
    """获取单个监控样本"""
    result = await db.execute(select(Metric).filter(Metric.id == metric_id))
    metric = result.scalar_one_or_none()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    return MetricOut(
        id=metric.id,
        taskId=metric.task_id,
        timestamp=metric.timestamp,
        cpu=metric.cpu / 100.0 if metric.cpu is not None else None,
        memory=float(metric.memory) if metric.memory is not None else None,
        appCpuUsage=metric.app_cpu_usage / 100.0 if metric.app_cpu_usage is not None else None,
        appMemoryUsage=float(metric.app_memory_usage) if metric.app_memory_usage is not None else None,
        appMemoryPercent=metric.app_memory_percent / 100.0 if metric.app_memory_percent is not None else None,
        fps=float(metric.fps) if metric.fps is not None else None,
        fpsStability=metric.fps_stability / 1000.0 if metric.fps_stability is not None else None,
        gpuLoad=metric.gpu_load / 100.0 if metric.gpu_load is not None else None,
        powerConsumption=metric.power_consumption / 1000.0 if metric.power_consumption is not None else None,
        networkUpSpeed=float(metric.network_up_speed) if metric.network_up_speed is not None else None,
        networkDownSpeed=float(metric.network_down_speed) if metric.network_down_speed is not None else None,
        deviceTemperature=metric.device_temperature / 10.0 if metric.device_temperature is not None else None,
        performanceScore=metric.performance_score,
    )


# ========== 任务 API ==========
@router.post("/tasks", response_model=MonitorTaskOut, status_code=201)
async def create_task(task_in: MonitorTaskCreate, db: AsyncSession = Depends(get_async_db)):
    """创建任务"""
    import time
    now = int(time.time() * 1000)

    task = MonitorTask(
        id=task_in.id,
        name=task_in.name,
        package_name=task_in.packageName,
        script_template_id=task_in.scriptTemplateId,
        metrics=task_in.metrics,
        status="idle",
        monitor_config=task_in.monitorConfig.model_dump() if task_in.monitorConfig else None,
        archived=False,
        created_at=now,
        updated_at=now,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return MonitorTaskOut(
        id=task.id,
        name=task.name,
        packageName=task.package_name,
        scriptTemplateId=task.script_template_id,
        metrics=task.metrics,
        status=task.status,
        monitorConfig=task.monitor_config,
        errorMessage=task.error_message,
        archived=task.archived,
        createdAt=task.created_at,
        updatedAt=task.updated_at,
    )


@router.get("/tasks", response_model=List[MonitorTaskOut])
async def list_tasks(
        status: Optional[str] = Query(None, description="按状态筛选"),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        db: AsyncSession = Depends(get_async_db),
):
    """查询任务列表"""
    query = select(MonitorTask)
    if status:
        query = query.filter(MonitorTask.status == status)
    query = query.order_by(desc(MonitorTask.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        MonitorTaskOut(
            id=task.id,
            name=task.name,
            packageName=task.package_name,
            scriptTemplateId=task.script_template_id,
            errorMessage=task.error_message,
            metrics=task.metrics,
            status=task.status,
            monitorConfig=task.monitor_config,
            archived=task.archived,
            createdAt=task.created_at,
            updatedAt=task.updated_at,
        )
        for task in tasks
    ]


@router.get("/tasks/summary", response_model=List[MonitorTaskSummary])
async def list_task_summary(
        status: Optional[str] = Query(None, description="按状态筛选"),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        db: AsyncSession = Depends(get_async_db),
):
    """查询任务摘要列表（包含统计信息）"""
    query = select(MonitorTask)
    if status:
        query = query.filter(MonitorTask.status == status)
    query = query.order_by(desc(MonitorTask.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    result_list = []
    for task in tasks:
        # 统计该任务的样本数量和时间范围
        stats_result = await db.execute(
            select(
                func.count(Metric.id).label("count"),
                func.min(Metric.timestamp).label("first_ts"),
                func.max(Metric.timestamp).label("last_ts"),
            )
            .filter(Metric.task_id == task.id)
        )
        stats = stats_result.first()

        result_list.append(MonitorTaskSummary(
            id=task.id,
            name=task.name,
            packageName=task.package_name,
            status=task.status,
            archived=task.archived,
            createdAt=task.created_at,
            updatedAt=task.updated_at,
            sampleCount=stats.count or 0 if stats else 0,
            firstSampleTime=stats.first_ts if stats else None,
            lastSampleTime=stats.last_ts if stats else None,
        ))

    return result_list


@router.get("/tasks/{task_id}", response_model=MonitorTaskOut)
async def get_task(task_id: str, db: AsyncSession = Depends(get_async_db)):
    """获取单个任务"""
    result = await db.execute(select(MonitorTask).filter(MonitorTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return MonitorTaskOut(
        id=task.id,
        name=task.name,
        packageName=task.package_name,
        scriptTemplateId=task.script_template_id,
        metrics=task.metrics,
        status=task.status,
        monitorConfig=task.monitor_config,
        errorMessage=task.error_message,
        createdAt=task.created_at,
        updatedAt=task.updated_at,
    )


@router.patch("/tasks/{task_id}", response_model=MonitorTaskOut)
async def update_task(task_id: str, task_update: MonitorTaskUpdate, db: AsyncSession = Depends(get_async_db)):
    """更新任务"""
    result = await db.execute(select(MonitorTask).filter(MonitorTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    import time
    if task_update.name is not None:
        task.name = task_update.name
    if task_update.status is not None:
        task.status = task_update.status
    if task_update.monitorConfig is not None:
        task.monitor_config = task_update.monitorConfig.model_dump()
    if task_update.errorMessage is not None:
        task.error_message = task_update.errorMessage
    if task_update.archived is not None:
        task.archived = task_update.archived

    task.updated_at = int(time.time() * 1000)

    await db.commit()
    await db.refresh(task)

    return MonitorTaskOut(
        id=task.id,
        name=task.name,
        packageName=task.package_name,
        scriptTemplateId=task.script_template_id,
        metrics=task.metrics,
        status=task.status,
        monitorConfig=task.monitor_config,
        errorMessage=task.error_message,
        createdAt=task.created_at,
        updatedAt=task.updated_at,
    )


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_async_db)):
    """删除任务（同时删除关联的监控样本）"""
    result = await db.execute(select(MonitorTask).filter(MonitorTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 删除关联的监控样本
    metrics_result = await db.execute(select(Metric).filter(Metric.task_id == task_id))
    metrics = metrics_result.scalars().all()
    for metric in metrics:
        await db.delete(metric)

    # 删除任务
    await db.delete(task)
    await db.commit()

    return None


@router.patch("/tasks/{task_id}/archive", response_model=MonitorTaskOut)
async def archive_task(
        task_id: str,
        archived: bool = Query(..., description="是否归档"),
        db: AsyncSession = Depends(get_async_db)
):
    """归档/取消归档任务"""
    result = await db.execute(select(MonitorTask).filter(MonitorTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    import time
    task.archived = archived
    task.updated_at = int(time.time() * 1000)

    await db.commit()
    await db.refresh(task)

    return MonitorTaskOut(
        id=task.id,
        name=task.name,
        packageName=task.package_name,
        scriptTemplateId=task.script_template_id,
        metrics=task.metrics,
        status=task.status,
        monitorConfig=task.monitor_config,
        errorMessage=task.error_message,
        archived=task.archived,
        createdAt=task.created_at,
        updatedAt=task.updated_at,
    )


# ========== 脚本模板 API ==========
@router.post("/script-templates", response_model=ScriptTemplateOut, status_code=201)
async def create_script_template(template_in: ScriptTemplateCreate, db: AsyncSession = Depends(get_async_db)):
    """创建脚本模板"""
    import time
    now = int(time.time() * 1000)

    template = ScriptTemplate(
        id=template_in.id,
        name=template_in.name,
        description=template_in.description,
        code=template_in.code,
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return ScriptTemplateOut(
        id=template.id,
        name=template.name,
        description=template.description,
        code=template.code,
        createdAt=template.created_at,
        updatedAt=template.updated_at,
    )


@router.get("/script-templates", response_model=List[ScriptTemplateOut])
async def list_script_templates(
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        db: AsyncSession = Depends(get_async_db),
):
    """查询脚本模板列表"""
    result = await db.execute(
        select(ScriptTemplate)
        .order_by(ScriptTemplate.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    templates = result.scalars().all()

    return [
        ScriptTemplateOut(
            id=template.id,
            name=template.name,
            description=template.description,
            code=template.code,
            createdAt=template.created_at,
            updatedAt=template.updated_at,
        )
        for template in templates
    ]


@router.get("/script-templates/{template_id}", response_model=ScriptTemplateOut)
async def get_script_template(template_id: str, db: AsyncSession = Depends(get_async_db)):
    """获取单个脚本模板"""
    result = await db.execute(select(ScriptTemplate).filter(ScriptTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Script template not found")

    return ScriptTemplateOut(
        id=template.id,
        name=template.name,
        description=template.description,
        code=template.code,
        createdAt=template.created_at,
        updatedAt=template.updated_at,
    )


@router.patch("/script-templates/{template_id}", response_model=ScriptTemplateOut)
async def update_script_template(
        template_id: str,
        template_update: ScriptTemplateUpdate,
        db: AsyncSession = Depends(get_async_db),
):
    """更新脚本模板"""
    result = await db.execute(select(ScriptTemplate).filter(ScriptTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Script template not found")

    import time
    if template_update.name is not None:
        template.name = template_update.name
    if template_update.description is not None:
        template.description = template_update.description
    if template_update.code is not None:
        template.code = template_update.code

    template.updated_at = int(time.time() * 1000)

    await db.commit()
    await db.refresh(template)

    return ScriptTemplateOut(
        id=template.id,
        name=template.name,
        description=template.description,
        code=template.code,
        createdAt=template.created_at,
        updatedAt=template.updated_at,
    )


@router.delete("/script-templates/{template_id}", status_code=204)
async def delete_script_template(template_id: str, db: AsyncSession = Depends(get_async_db)):
    """删除脚本模板"""
    result = await db.execute(select(ScriptTemplate).filter(ScriptTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Script template not found")

    await db.delete(template)
    await db.commit()

    return None


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


# ========== 图片模板匹配 API ==========
@router.post("/image-template/match", response_model=ImageMatchResult)
async def match_image_template(request: ImageMatchRequest):
    """
    图片模板匹配接口，用于脚本元素定位

    返回匹配结果，包括：
    - found: 是否找到匹配
    - confidence: 置信度
    - position: 匹配位置 (x, y, width, height)
    """
    try:
        # 清理 Base64 字符串（移除 data URL 前缀等）
        def clean_base64(data: str) -> str:
            # 移除 data URL 前缀（如 data:image/png;base64,）
            if ',' in data:
                data = data.split(',')[-1]
            # 移除空白字符
            data = data.strip().replace('\n', '').replace('\r', '').replace(' ', '')
            return data

        # 解码 Base64 图片数据
        screenshot_clean = clean_base64(request.screenshot)
        template_clean = clean_base64(request.template)

        # 添加必要的填充字符
        def add_padding(data: str) -> str:
            missing_padding = len(data) % 4
            if missing_padding:
                data += '=' * (4 - missing_padding)
            return data

        screenshot_clean = add_padding(screenshot_clean)
        template_clean = add_padding(template_clean)

        screenshot_data = base64.b64decode(screenshot_clean)
        template_data = base64.b64decode(template_clean)
        threshold = request.threshold

        # 尝试使用 OpenCV 进行模板匹配

        import cv2
        import numpy as np

        # 将字节数据转换为 numpy 数组
        screenshot_array = np.frombuffer(screenshot_data, dtype=np.uint8)
        template_array = np.frombuffer(template_data, dtype=np.uint8)

        # 解码图片
        screenshot_img = cv2.imdecode(screenshot_array, cv2.IMREAD_COLOR)
        template_img = cv2.imdecode(template_array, cv2.IMREAD_COLOR)

        if screenshot_img is None or template_img is None:
            raise ValueError("无法解码图片")

        # 转换为灰度图
        screenshot_gray = cv2.cvtColor(screenshot_img, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

        # 模板匹配
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # 检查是否匹配
        if max_val >= threshold:
            h, w = template_gray.shape
            return {
                "found": True,
                "confidence": float(max_val),
                "position": {
                    "x": int(max_loc[0]),
                    "y": int(max_loc[1]),
                    "width": int(w),
                    "height": int(h)
                },
                "center": {
                    "x": int(max_loc[0] + w / 2),
                    "y": int(max_loc[1] + h / 2)
                }
            }
        else:
            return {
                "found": False,
                "confidence": float(max_val),
                "position": None,
                "center": None
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片匹配失败: {str(e)}")
