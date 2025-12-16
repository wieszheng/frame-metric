# Frame-Metric API 文档

## 项目概述

**项目名称**: frame-metric  
**版本**: v1.0.0  
**描述**: 视频帧提取标注系统 - 支持异步处理、批量上传、进度追踪

这是一个基于 FastAPI 的视频处理系统，主要功能包括：
- 视频上传与批量处理
- 智能首尾帧识别
- 任务管理与统计
- 人工审核与标注
- 二维码生成（艺术二维码）
现在有一个app应用场景性能监控需求，需求说明：支持配置监控项，创建场景监控任务执行，监控图表数据实时展示（内存cpu等指标），任务管理列表，场景脚本编写等，采用electron客户端技术，请你帮我梳理开发框架以及流程，实现方式
重点在任务执行，需要执行监控同时还要执行场景脚本
---

## 技术栈

- **Web框架**: FastAPI 0.122.0
- **数据库**: SQLAlchemy 2.0.44 (支持 PostgreSQL/MySQL/SQLite)
- **异步任务**: Celery 5.5.3 + Redis
- **对象存储**: MinIO 7.2.20
- **视频处理**: OpenCV 4.12.0
- **图像处理**: Pillow 12.0.0, NumPy 2.2.6

---

## 基础信息

### Base URL
```
http://localhost:8000/api/v1
```

### 通用响应格式
所有API遵循RESTful设计，使用标准HTTP状态码。

---

## API 端点详情

## 1. 视频管理模块 (`/video`)

### 1.1 上传单个视频
**端点**: `POST /video/upload`

**描述**: 上传单个视频文件并异步处理

**请求**:
- Content-Type: `multipart/form-data`
- Body:
  - `file`: 视频文件 (必填)

**响应**: `VideoUploadResponse`
```json
{
  "video_id": "uuid",
  "task_id": "celery_task_id",
  "status": "uploading",
  "message": "视频上传成功，开始处理"
}
```

**处理流程**:
1. 验证文件格式（.mp4）
2. 保存到临时目录
3. 创建数据库记录
4. 上传到MinIO
5. 触发Celery异步任务处理

---

### 1.2 批量上传视频
**端点**: `POST /video/batch-upload`

**描述**: 批量上传多个视频文件

**请求**:
- Content-Type: `multipart/form-data`
- Body:
  - `files`: 视频文件列表 (必填)

**响应**: `BatchUploadResponse`
```json
{
  "batch_id": "uuid",
  "total_count": 5,
  "videos": [
    {
      "video_id": "uuid",
      "task_id": "celery_task_id",
      "status": "uploading",
      "message": "上传成功"
    }
  ],
  "message": "批量上传完成"
}
```

**限制**:
- 最大文件大小: 500MB
- 允许格式: .mp4
- 最大并发上传: 5个

---

### 1.3 查询视频状态
**端点**: `GET /video/{video_id}/status`

**描述**: 查询单个视频的处理状态和结果

**路径参数**:
- `video_id`: 视频ID

**响应**: `VideoStatusResponse`
```json
{
  "video_id": "uuid",
  "filename": "test.mp4",
  "status": "completed",
  "duration": 120.5,
  "fps": 30.0,
  "width": 1920,
  "height": 1080,
  "task_id": "celery_task_id",
  "error_message": null,
  "frames": [
    {
      "id": "frame_uuid",
      "type": "first",
      "url": "http://minio/bucket/frame.jpg",
      "timestamp": 0.5,
      "frame_number": 15
    }
  ],
  "progress": 100,
  "current_step": "completed",
  "created_at": "2025-12-11T10:00:00"
}
```

**视频状态枚举**:
- `uploading`: 上传中
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 失败
- `cancelled`: 已取消

---

### 1.4 查询视频处理进度
**端点**: `GET /video/{video_id}/progress`

**描述**: 实时查询视频处理进度

**路径参数**:
- `video_id`: 视频ID

**响应**: `TaskProgress`
```json
{
  "video_id": "uuid",
  "task_id": "celery_task_id",
  "status": "processing",
  "progress": 65,
  "current_step": "extracting_frames",
  "error_message": null
}
```

---

### 1.5 取消视频处理任务
**端点**: `POST /video/{video_id}/cancel`

**描述**: 取消正在处理的视频任务

**路径参数**:
- `video_id`: 视频ID

**响应**: `CancelTaskResponse`
```json
{
  "video_id": "uuid",
  "task_id": "celery_task_id",
  "status": "cancelled",
  "message": "任务已取消"
}
```

---

### 1.6 列出视频
**端点**: `GET /video/list`

**描述**: 分页列出视频，支持状态过滤

**查询参数**:
- `skip`: 跳过记录数 (默认: 0)
- `limit`: 返回记录数 (默认: 20)
- `status`: 状态过滤 (可选)

**响应**: `List[VideoStatusResponse]`

---

## 2. 任务管理模块 (`/task`)

### 2.1 创建任务
**端点**: `POST /task/create`

**描述**: 创建一个新的测试任务

**请求**: `TaskCreate`
```json
{
  "name": "性能测试任务1",
  "description": "测试首尾帧识别准确性",
  "created_by": "zhangsan"
}
```

**响应**: `TaskResponse`
```json
{
  "id": "uuid",
  "name": "性能测试任务1",
  "description": "测试首尾帧识别准确性",
  "status": "draft",
  "total_videos": 0,
  "completed_videos": 0,
  "failed_videos": 0,
  "total_duration": null,
  "avg_duration": null,
  "min_duration": null,
  "max_duration": null,
  "created_by": "zhangsan",
  "created_at": "2025-12-11T10:00:00",
  "updated_at": "2025-12-11T10:00:00"
}
```

---

### 2.2 获取任务列表
**端点**: `GET /task/list`

**描述**: 获取任务列表，支持分页和用户过滤

**查询参数**:
- `user`: 创建者过滤 (可选)
- `skip`: 跳过记录数 (默认: 0)
- `limit`: 返回记录数 (默认: 20)

**响应**: `List[TaskResponse]`

---

### 2.3 获取任务详情
**端点**: `GET /task/{task_id}`

**描述**: 获取任务详情，包含所有关联视频和首尾帧信息

**路径参数**:
- `task_id`: 任务ID

**响应**: `TaskDetailResponse`
```json
{
  "id": "uuid",
  "name": "性能测试任务1",
  "status": "processing",
  "total_videos": 3,
  "completed_videos": 2,
  "failed_videos": 0,
  "videos": [
    {
      "id": "task_video_uuid",
      "video_id": "video_uuid",
      "order": 1,
      "duration": 2.5,
      "first_frame_time": 0.5,
      "last_frame_time": 3.0,
      "notes": null,
      "added_at": "2025-12-11T10:00:00",
      "video_filename": "test.mp4",
      "video_status": "completed",
      "video_width": 1920,
      "video_height": 1080,
      "first_frame_url": "http://minio/bucket/first.jpg",
      "last_frame_url": "http://minio/bucket/last.jpg"
    }
  ],
  "created_at": "2025-12-11T10:00:00",
  "updated_at": "2025-12-11T10:00:00"
}
```

---

### 2.4 更新任务
**端点**: `PUT /task/{task_id}`

**描述**: 更新任务基本信息

**路径参数**:
- `task_id`: 任务ID

**请求**: `TaskUpdate`
```json
{
  "name": "更新后的任务名",
  "description": "更新后的描述"
}
```

**响应**: `TaskResponse`

---

### 2.5 删除任务
**端点**: `DELETE /task/{task_id}`

**描述**: 删除任务（级联删除关联记录，不删除视频本身）

**路径参数**:
- `task_id`: 任务ID

**响应**:
```json
{
  "message": "任务删除成功"
}
```

---

### 2.6 添加视频到任务
**端点**: `POST /task/{task_id}/videos`

**描述**: 批量添加已处理完成的视频到任务

**路径参数**:
- `task_id`: 任务ID

**请求**: `VideoAddToTask`
```json
{
  "video_ids": ["video_uuid1", "video_uuid2"],
  "notes": "第一批测试视频"
}
```

**响应**:
```json
{
  "message": "成功添加 2 个视频到任务",
  "added_count": 2,
  "failed_videos": []
}
```

---

### 2.7 从任务移除视频
**端点**: `DELETE /task/{task_id}/videos/{video_id}`

**描述**: 从任务中移除指定视频

**路径参数**:
- `task_id`: 任务ID
- `video_id`: 视频ID

**响应**:
```json
{
  "message": "视频已从任务中移除"
}
```

---

### 2.8 计算任务统计
**端点**: `POST /task/{task_id}/calculate-stats`

**描述**: 重新计算任务的统计信息（通常在视频处理完成后自动调用）

**路径参数**:
- `task_id`: 任务ID

**响应**: `TaskResponse`

---

### 2.10 导出任务耗时数据
**端点**: `GET /task/{task_id}/export`

**描述**: 导出任务的视频首尾帧耗时数据为 CSV 或 Excel 文件

**路径参数**:
- `task_id`: 任务ID

**查询参数**:
- `format`: 导出格式（可选，默认: excel）
  - `excel`: Excel格式
  - `csv`: CSV格式

**响应**: 文件下载流

**导出数据字段**:
- 任务信息（名称、ID）
- 视频信息（文件名、ID、序号）
- 首尾帧时间戳和编号
- 耗时信息（毫秒、秒）
- 视频属性（时长、帧率、分辨率）
- 备注和添加时间

**示例**:
```bash
# 导出为 Excel
curl "http://localhost:8000/api/v1/task/{task_id}/export" \
  --output task_data.xlsx

# 导出为 CSV
curl "http://localhost:8000/api/v1/task/{task_id}/export?format=csv" \
  --output task_data.csv
```

**文件命名**: `{任务名称}_timing_data_{时间戳}.{扩展名}`

---

### 2.11 获取任务统计详情
**端点**: `GET /task/{task_id}/statistics`

**描述**: 获取任务的详细统计信息

**路径参数**:
- `task_id`: 任务ID

**响应**: `TaskStatsResponse`
```json
{
  "task_id": "uuid",
  "task_name": "性能测试任务1",
  "total_videos": 10,
  "completed_videos": 8,
  "processing_videos": 1,
  "failed_videos": 1,
  "total_duration": 25.5,
  "avg_duration": 3.19,
  "min_duration": 1.2,
  "max_duration": 5.8,
  "total_frames": 1500,
  "avg_frames_per_video": 187.5
}
```

---

## 3. 审核模块 (`/review`)

### 3.1 获取审核数据
**端点**: `GET /review/{video_id}`

**描述**: 获取视频审核所需的所有数据，包括AI识别的候选帧

**路径参数**:
- `video_id`: 视频ID

**响应**: `VideoReviewResponse`
```json
{
  "video_id": "uuid",
  "filename": "test.mp4",
  "status": "completed",
  "total_frames": 200,
  "extracted_frames": 200,
  "marking_method": "algorithm",
  "ai_confidence": 0.85,
  "marked_first_frame": {
    "id": "frame_uuid",
    "frame_number": 15,
    "timestamp": 0.5,
    "url": "http://minio/bucket/frame.jpg",
    "frame_type": "first",
    "is_first_candidate": true,
    "confidence_score": 0.9,
    "brightness": 0.65,
    "sharpness": 0.78,
    "scene_change_score": 0.82
  },
  "marked_last_frame": { /* 同上结构 */ },
  "first_candidates": [ /* 首帧候选列表 */ ],
  "last_candidates": [ /* 尾帧候选列表 */ ],
  "all_frames": [ /* 所有帧列表 */ ],
  "needs_review": true,
  "reviewed_by": null,
  "reviewed_at": null
}
```

---

### 3.2 提交人工标记
**端点**: `POST /review/{video_id}/mark`

**描述**: 提交人工标记的首尾帧

**路径参数**:
- `video_id`: 视频ID

**请求**: `FrameMarkingRequest`
```json
{
  "first_frame_id": "frame_uuid1",
  "last_frame_id": "frame_uuid2",
  "reviewer": "zhangsan",
  "review_notes": "AI识别准确"
}
```

**响应**: `FrameMarkingResponse`
```json
{
  "video_id": "uuid",
  "status": "reviewed",
  "message": "标记成功",
  "first_frame": { /* FrameDetailResponse */ },
  "last_frame": { /* FrameDetailResponse */ }
}
```

**处理逻辑**:
1. 更新视频的 `marking_method` 为 `manual`
2. 更新帧的 `frame_type` 标记
3. 创建标注历史记录
4. 更新视频的审核状态

---

### 3.3 获取待审核视频列表
**端点**: `GET /review/pending`

**描述**: 获取所有需要人工审核的视频

**查询参数**:
- `skip`: 跳过记录数 (默认: 0)
- `limit`: 返回记录数 (默认: 20)

**响应**: `List[VideoReviewResponse]`

---

## 4. 二维码生成模块 (`/qr`)

### 4.1 生成普通二维码
**端点**: `POST /qr/simple`

**描述**: 生成普通二维码

**请求**: `QRCodeRequest`
```json
{
  "words": "https://example.com",
  "version": 1,
  "level": "H",
  "contrast": 1.0,
  "brightness": 1.0
}
```

**响应**: 直接返回图片流 (image/png)

**参数说明**:
- `words`: 要编码的内容（必填）
- `version`: 二维码版本 1-40（可选，默认1）
- `level`: 纠错级别 L/M/Q/H（可选，默认H）
- `contrast`: 对比度 0.1-3.0（可选，默认1.0）
- `brightness`: 亮度 0.1-3.0（可选，默认1.0）

---

### 4.2 生成艺术二维码
**端点**: `POST /qr/artistic`

**描述**: 生成带背景图片的艺术二维码

**请求**:
- Content-Type: `multipart/form-data`
- Body:
  - `words`: 要编码的内容 (必填)
  - `picture`: 背景图片文件 (必填)
  - `version`: 二维码版本 (可选)
  - `level`: 纠错级别 (可选)
  - `colorized`: 是否彩色化 (可选, 默认false)
  - `contrast`: 对比度 (可选)
  - `brightness`: 亮度 (可选)

**响应**: 直接返回图片流 (image/png)

**支持格式**: PNG, JPG, JPEG, BMP

---

### 4.3 生成动态GIF二维码
**端点**: `POST /qr/animated`

**描述**: 生成动态GIF二维码

**请求**:
- Content-Type: `multipart/form-data`
- Body:
  - `words`: 要编码的内容 (必填)
  - `picture`: GIF动画文件 (必填)
  - `version`: 二维码版本 (可选)
  - `level`: 纠错级别 (可选)
  - `colorized`: 是否彩色化 (可选)
  - `contrast`: 对比度 (可选)
  - `brightness`: 亮度 (可选)

**响应**: 直接返回GIF流 (image/gif)

**注意**: 必须上传 .gif 格式文件

---

## 5. 系统端点

### 5.1 根路径
**端点**: `GET /`

**响应**:
```json
{
  "name": "frame-metric",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

---

### 5.2 健康检查
**端点**: `GET /health`

**响应**:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## 数据模型

### 视频状态枚举 (VideoStatus)
```python
UPLOADING = "uploading"      # 上传中
PROCESSING = "processing"    # 处理中
COMPLETED = "completed"      # 已完成
FAILED = "failed"           # 失败
CANCELLED = "cancelled"     # 已取消
```

### 任务状态枚举 (TaskStatus)
```python
DRAFT = "draft"             # 草稿
PROCESSING = "processing"   # 处理中
COMPLETED = "completed"     # 已完成
FAILED = "failed"          # 失败
```

### 标记方法枚举 (MarkingMethod)
```python
ALGORITHM = "algorithm"     # 算法自动识别
MANUAL = "manual"          # 人工标记
HYBRID = "hybrid"          # 混合方式
```

### 帧类型枚举 (FrameType)
```python
FIRST = "first"            # 首帧
LAST = "last"             # 尾帧
MIDDLE = "middle"         # 中间帧
```

---

## 核心业务流程

### 1. 视频处理流程
```
1. 用户上传视频 → POST /video/upload
2. 系统验证并保存文件
3. 创建数据库记录 (status: uploading)
4. 上传到MinIO对象存储
5. 触发Celery异步任务
6. Celery Worker处理:
   a. 提取视频信息 (fps, duration, resolution)
   b. 提取所有帧
   c. 计算场景变化分数
   d. AI智能识别首尾帧
   e. 上传帧图片到MinIO
   f. 更新数据库 (status: completed)
7. 用户查询结果 → GET /video/{video_id}/status
```

### 2. 任务管理流程
```
1. 创建任务 → POST /task/create
2. 上传并处理视频 → POST /video/upload
3. 添加视频到任务 → POST /task/{task_id}/videos
4. 系统自动计算统计 → 自动触发
5. 查看任务详情 → GET /task/{task_id}
6. 查看统计数据 → GET /task/{task_id}/statistics
```

### 3. 审核流程
```
1. 获取待审核列表 → GET /review/pending
2. 查看审核数据 → GET /review/{video_id}
3. 前端展示:
   - AI识别的首尾帧
   - 候选帧列表
   - 所有帧缩略图
4. 人工选择正确的首尾帧
5. 提交标记 → POST /review/{video_id}/mark
6. 系统更新标记方法和审核状态
```

---

## 配置说明

### 环境变量 (.env)
```bash
# 应用配置
APP_NAME=frame-metric
DEBUG=False
VERSION=1.0.0

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# MinIO配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio123
MINIO_BUCKET=video-frames
MINIO_SECURE=False

# 上传配置
UPLOAD_DIR=/tmp/video_uploads
MAX_VIDEO_SIZE=524288000  # 500MB
ALLOWED_EXTENSIONS=.mp4

# 并发配置
MAX_CONCURRENT_UPLOADS=5
CELERY_WORKER_CONCURRENCY=3
```

---

## 错误处理

### 常见错误码
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `422 Unprocessable Entity`: 数据验证失败
- `500 Internal Server Error`: 服务器内部错误

### 错误响应格式
```json
{
  "detail": "错误描述信息"
}
```

---

## API交互示例

### Python示例
```python
import requests

# 上传视频
with open('test.mp4', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/video/upload',
        files={'file': f}
    )
    result = response.json()
    video_id = result['video_id']

# 查询状态
status = requests.get(
    f'http://localhost:8000/api/v1/video/{video_id}/status'
).json()

print(f"Status: {status['status']}, Progress: {status['progress']}%")
```

### cURL示例
```bash
# 上传视频
curl -X POST "http://localhost:8000/api/v1/video/upload" \
  -F "file=@test.mp4"

# 查询状态
curl "http://localhost:8000/api/v1/video/{video_id}/status"

# 创建任务
curl -X POST "http://localhost:8000/api/v1/task/create" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试任务","created_by":"user1"}'
```

---

## 性能优化建议

### 当前实现
- ✅ 异步数据库操作 (AsyncSession)
- ✅ Celery异步任务处理
- ✅ MinIO对象存储
- ✅ Redis缓存和消息队列
- ✅ 批量上传支持

### 可优化点
- 添加API限流 (Rate Limiting)
- 实现结果缓存 (Redis)
- 添加CDN支持
- 优化数据库查询索引
- 实现视频预处理队列

---

## 部署说明

### 依赖服务
1. **PostgreSQL/MySQL**: 主数据库
2. **Redis**: 缓存和消息队列
3. **MinIO**: 对象存储
4. **Celery Worker**: 异步任务处理

### 启动命令
```bash
# 启动Web服务
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 启动Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info

# 启动Flower监控
celery -A app.tasks.celery_app flower
```

---

## 文档链接

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

**最后更新**: 2025-12-11  
**维护者**: wieszheng
