# Frame-Metric API 接口文档

## 项目简介

**Frame-Metric** 是一个视频帧提取标注系统，支持异步处理、批量上传、进度追踪等功能。

- **版本**: 根据配置文件
- **基础路径**: `/api/v1`
- **文档地址**: `/docs` (Swagger UI) 或 `/redoc` (ReDoc)
-  celery -A app.tasks.celery_app worker --loglevel=info -Q video_processing


---

## 目录

1. [视频管理接口](#视频管理接口)
2. [任务管理接口](#任务管理接口)
3. [审核管理接口](#审核管理接口)


## 视频管理接口

**基础路径**: `/api/v1/video`

### 1. 上传单个视频
- **接口**: `POST /api/v1/video/upload`
- **标签**: `video`
- **描述**: 上传单个视频文件进行处理
- **请求参数**:
  - `file` (UploadFile, 必填): 视频文件
- **支持格式**: 根据配置文件中的 `ALLOWED_EXTENSIONS`
- **文件大小限制**: 根据配置文件中的 `MAX_VIDEO_SIZE`
- **响应示例**:
```json
{
  "video_id": "uuid-string",
  "task_id": "celery-task-id",
  "status": "processing",
  "message": "视频上传成功,正在后台处理"
}
```

### 2. 批量上传视频
- **接口**: `POST /api/v1/video/batch-upload`
- **标签**: `video`
- **描述**: 批量上传多个视频文件（最多20个）
- **请求参数**:
  - `files` (List[UploadFile], 必填): 视频文件列表
- **限制**: 单次最多上传20个视频
- **响应示例**:
```json
{
  "batch_id": "uuid-string",
  "total_count": 5,
  "videos": [
    {
      "video_id": "uuid-string",
      "task_id": "celery-task-id",
      "status": "processing",
      "message": "video1.mp4 上传成功"
    }
  ],
  "message": "批量上传完成,共5个文件"
}
```

### 3. 查询视频状态
- **接口**: `GET /api/v1/video/status/{video_id}`
- **标签**: `video`
- **描述**: 查询单个视频的处理状态和结果
- **路径参数**:
  - `video_id` (string, 必填): 视频ID
- **响应示例**:
```json
{
  "video_id": "uuid-string",
  "filename": "example.mp4",
  "status": "completed",
  "duration": 120.5,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "task_id": "celery-task-id",
  "error_message": null,
  "progress": 100,
  "current_step": "处理完成",
  "frames": [
    {
      "id": "frame-uuid",
      "type": "first",
      "url": "minio-url",
      "timestamp": 0.0,
      "frame_number": 0
    }
  ],
  "created_at": "2025-12-09T00:00:00"
}
```

### 4. 查询处理进度
- **接口**: `GET /api/v1/video/progress/{video_id}`
- **标签**: `video`
- **描述**: 实时查询视频处理进度
- **路径参数**:
  - `video_id` (string, 必填): 视频ID
- **响应示例**:
```json
{
  "video_id": "uuid-string",
  "task_id": "celery-task-id",
  "status": "processing",
  "progress": 50,
  "current_step": "正在提取帧",
  "error_message": null
}
```

---

## 任务管理接口

**基础路径**: `/api/v1/task`

### 1. 创建任务
- **接口**: `POST /api/v1/task/`
- **标签**: `task`
- **描述**: 创建新任务
- **请求体**:
```json
{
  "name": "任务名称",
  "description": "任务描述",
  "created_by": "用户名"
}
```
- **响应示例**:
```json
{
  "id": "uuid-string",
  "name": "任务名称",
  "description": "任务描述",
  "status": "draft",
  "total_videos": 0,
  "completed_videos": 0,
  "failed_videos": 0,
  "total_duration": null,
  "avg_duration": null,
  "min_duration": null,
  "max_duration": null,
  "created_by": "用户名",
  "created_at": "2025-12-09T00:00:00",
  "updated_at": "2025-12-09T00:00:00"
}
```

### 2. 获取任务列表
- **接口**: `GET /api/v1/task/`
- **标签**: `task`
- **描述**: 获取任务列表（支持分页和用户过滤）
- **查询参数**:
  - `user` (string, 可选): 按用户过滤
  - `skip` (int, 可选, 默认0): 跳过的记录数
  - `limit` (int, 可选, 默认20): 返回的记录数
- **响应示例**: 返回任务列表数组

### 3. 获取任务详情
- **接口**: `GET /api/v1/task/{task_id}`
- **标签**: `task`
- **描述**: 获取任务详情，包含所有关联的视频列表和首尾帧信息
- **路径参数**:
  - `task_id` (string, 必填): 任务ID
- **响应示例**:
```json
{
  "id": "uuid-string",
  "name": "任务名称",
  "description": "任务描述",
  "status": "in_progress",
  "total_videos": 5,
  "completed_videos": 3,
  "failed_videos": 0,
  "total_duration": 600.5,
  "avg_duration": 120.1,
  "min_duration": 80.0,
  "max_duration": 150.0,
  "created_by": "用户名",
  "created_at": "2025-12-09T00:00:00",
  "updated_at": "2025-12-09T00:00:00",
  "videos": [
    {
      "id": "task-video-uuid",
      "video_id": "video-uuid",
      "order": 1,
      "duration": 120.5,
      "first_frame_time": 0.0,
      "last_frame_time": 120.5,
      "notes": "备注",
      "added_at": "2025-12-09T00:00:00",
      "video_filename": "example.mp4",
      "video_status": "completed",
      "video_width": 1920,
      "video_height": 1080,
      "first_frame_url": "minio-url",
      "last_frame_url": "minio-url"
    }
  ]
}
```

### 4. 更新任务
- **接口**: `PUT /api/v1/task/{task_id}`
- **标签**: `task`
- **描述**: 更新任务基本信息
- **路径参数**:
  - `task_id` (string, 必填): 任务ID
- **请求体**:
```json
{
  "name": "新任务名称",
  "description": "新任务描述",
  "status": "in_progress"
}
```

### 5. 删除任务
- **接口**: `DELETE /api/v1/task/{task_id}`
- **标签**: `task`
- **描述**: 删除任务（级联删除所有关联的视频记录，不删除视频本身）
- **路径参数**:
  - `task_id` (string, 必填): 任务ID
- **响应示例**:
```json
{
  "message": "任务已删除",
  "task_id": "uuid-string"
}
```

### 6. 添加视频到任务
- **接口**: `POST /api/v1/task/{task_id}/videos`
- **标签**: `task`
- **描述**: 添加视频到任务（支持批量添加）
- **路径参数**:
  - `task_id` (string, 必填): 任务ID
- **请求体**:
```json
{
  "video_ids": ["video-uuid-1", "video-uuid-2"],
  "notes": "批量添加备注"
}
```
- **响应示例**:
```json
{
  "message": "成功添加 2 个视频",
  "task_id": "uuid-string",
  "added_count": 2
}
```

### 7. 从任务中移除视频
- **接口**: `DELETE /api/v1/task/{task_id}/videos/{video_id}`
- **标签**: `task`
- **描述**: 从任务中移除指定视频
- **路径参数**:
  - `task_id` (string, 必填): 任务ID
  - `video_id` (string, 必填): 视频ID
- **响应示例**:
```json
{
  "message": "视频已移除",
  "task_id": "uuid-string",
  "video_id": "video-uuid"
}
```

### 8. 计算任务统计
- **接口**: `POST /api/v1/task/{task_id}/calculate`
- **标签**: `task`
- **描述**: 计算任务统计信息（计算所有视频的耗时，更新任务的统计数据）
- **路径参数**:
  - `task_id` (string, 必填): 任务ID
- **响应示例**:
```json
{
  "message": "统计计算完成",
  "task_id": "uuid-string",
  "total_duration": 600.5,
  "avg_duration": 120.1,
  "completed_videos": 5
}
```

### 9. 获取任务统计
- **接口**: `GET /api/v1/task/{task_id}/stats`
- **标签**: `task`
- **描述**: 获取任务详细统计信息（视频处理状态统计、性能数据统计、帧数据统计）
- **路径参数**:
  - `task_id` (string, 必填): 任务ID
- **响应示例**:
```json
{
  "task_id": "uuid-string",
  "task_name": "任务名称",
  "total_videos": 5,
  "completed_videos": 3,
  "processing_videos": 1,
  "failed_videos": 1,
  "total_duration": 600.5,
  "avg_duration": 120.1,
  "min_duration": 80.0,
  "max_duration": 150.0,
  "total_frames": 1500,
  "avg_frames_per_video": 300.0
}
```

---

## 审核管理接口

### 1. 提交帧标记
- **接口**: `POST /api/v1/review/{video_id}/mark`
- **标签**: `review`
- **描述**: 提交人工标记的首尾帧
- **路径参数**:
  - `video_id` (string, 必填): 视频ID
- **请求体**:
```json
{
  "first_frame_id": "frame-uuid-1",
  "last_frame_id": "frame-uuid-2",
  "reviewer": "审核员名称",
  "review_notes": "审核备注"
}
```
- **响应示例**:
```json
{
  "video_id": "uuid-string",
  "status": "success",
  "message": "标记成功",
  "first_frame": {
    "id": "frame-uuid-1",
    "frame_number": 0,
    "timestamp": 0.0,
    "url": "minio-url",
    "frame_type": "first"
  },
  "last_frame": {
    "id": "frame-uuid-2",
    "frame_number": 3599,
    "timestamp": 119.97,
    "url": "minio-url",
    "frame_type": "last"
  }
}
```

## 数据模型

### 视频状态 (VideoStatus)
- `uploading`: 上传中
- `processing`: 处理中
- `pending_review`: 待审核
- `reviewed`: 已审核
- `completed`: 已完成
- `failed`: 失败
- `cancelled`: 已取消

### 任务状态 (TaskStatus)
- `draft`: 草稿
- `in_progress`: 进行中
- `completed`: 已完成
- `archived`: 已归档

### 帧类型 (FrameType)
- `first`: 首帧
- `last`: 尾帧
- `middle`: 中间帧

### 标记方法 (MarkingMethod)
- `ai`: AI自动标记
- `manual`: 人工标记
- `hybrid`: 混合标记

---

## 错误码

- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误
