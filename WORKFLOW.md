# Frame-Metric 业务流程文档

## 📋 完整业务流程

### 流程概览
```
1. 创建任务 (Task)
   ↓
2. 上传视频 (关联到任务)
   ↓
3. 提取分析视频帧 (自动)
   ↓
4. 算法标记首尾帧 (自动)
   ↓
5. 人工审核确认/修改 (手动)
   ↓
6. 完成标记
```

---

## 🔄 详细流程说明

### 步骤1: 创建任务

**接口**: `POST /api/v1/task/create`

**请求示例**:
```json
{
  "name": "性能测试任务-20251211",
  "description": "测试首尾帧识别准确性",
  "created_by": "zhangsan"
}
```

**响应示例**:
```json
{
  "id": "task-uuid-123",
  "name": "性能测试任务-20251211",
  "status": "draft",
  "total_videos": 0,
  "created_at": "2025-12-11T13:00:00"
}
```

**说明**:
- 任务初始状态为 `draft`（草稿）
- 此时任务中还没有视频
- 记录任务ID，用于后续上传视频时关联

---

### 步骤2: 上传视频并关联任务

**接口**: `POST /api/v1/video/upload`

**请求示例** (multipart/form-data):
```bash
curl -X POST "http://localhost:8000/api/v1/video/upload" \
  -F "file=@test_video.mp4" \
  -F "task_id=task-uuid-123"
```

**Python示例**:
```python
import requests

with open('test_video.mp4', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/video/upload',
        files={'file': f},
        data={'task_id': 'task-uuid-123'}
    )
    result = response.json()
    video_id = result['video_id']
```

**响应示例**:
```json
{
  "video_id": "video-uuid-456",
  "task_id": "celery-task-id-789",
  "status": "processing",
  "message": "视频上传成功,正在后台处理 (已关联到任务)"
}
```

**说明**:
- `task_id` 参数是可选的，如果不提供，视频不会关联到任务
- 上传后会自动触发 Celery 异步任务处理
- 视频会自动添加到指定任务的视频列表中

---

### 步骤3: 提取分析视频帧 (自动执行)

**Celery任务**: `process_video_frames_full`

**处理流程**:
1. **提取视频信息** (10%)
   - 分辨率、帧率、时长等
   
2. **提取所有帧** (20%-60%)
   - 根据采样率提取帧
   - 计算每帧的亮度、清晰度
   - 上传到 MinIO
   - 保存到数据库

3. **计算场景变化** (65%)
   - 分析帧间差异
   - 计算场景变化分数

**查询进度**:
```bash
GET /api/v1/video/progress/{video_id}
```

**响应示例**:
```json
{
  "video_id": "video-uuid-456",
  "task_id": "celery-task-id-789",
  "status": "extracting",
  "progress": 45,
  "current_step": "已提取 450 帧"
}
```

---

### 步骤4: 算法标记首尾帧 (自动执行)

**处理流程** (75%-100%):

1. **智能分析** (75%)
   - 使用 `FrameAnalyzer` 算法
   - 分析场景变化模式
   - 识别转场点

2. **标记首尾帧** (85%)
   - 标记最可能的首帧
   - 标记最可能的尾帧
   - 计算置信度分数

3. **生成候选帧** (90%)
   - 生成 Top 5 首帧候选
   - 生成 Top 5 尾帧候选
   - 按置信度排序

4. **创建标注记录** (95%)
   - 记录算法标记历史
   - 保存置信度和原因

5. **设置待审核状态** (100%)
   - 状态更新为 `pending_review`
   - 等待人工审核

**算法标记结果**:
```json
{
  "video_id": "video-uuid-456",
  "status": "pending_review",
  "extracted_frames": 500,
  "first_frame": 15,
  "last_frame": 485,
  "confidence": 0.85
}
```

**视频状态变化**:
```
uploading → extracting → analyzing → pending_review
```

---

### 步骤5: 人工审核确认/修改

#### 5.1 获取待审核视频列表

**接口**: `GET /api/v1/review/pending`

**响应示例**:
```json
[
  {
    "video_id": "video-uuid-456",
    "filename": "test_video.mp4",
    "status": "pending_review",
    "ai_confidence": 0.85,
    "needs_review": true
  }
]
```

---

#### 5.2 获取审核数据

**接口**: `GET /api/v1/review/{video_id}`

**响应示例**:
```json
{
  "video_id": "video-uuid-456",
  "filename": "test_video.mp4",
  "status": "pending_review",
  "total_frames": 500,
  "extracted_frames": 500,
  "marking_method": "algorithm",
  "ai_confidence": 0.85,
  
  "marked_first_frame": {
    "id": "frame-uuid-001",
    "frame_number": 15,
    "timestamp": 0.5,
    "url": "http://minio:9000/bucket/frame_15.jpg",
    "frame_type": "first",
    "confidence_score": 0.9,
    "brightness": 0.65,
    "sharpness": 0.78,
    "scene_change_score": 0.82
  },
  
  "marked_last_frame": {
    "id": "frame-uuid-485",
    "frame_number": 485,
    "timestamp": 16.17,
    "url": "http://minio:9000/bucket/frame_485.jpg",
    "frame_type": "last",
    "confidence_score": 0.88
  },
  
  "first_candidates": [
    {
      "id": "frame-uuid-001",
      "frame_number": 15,
      "timestamp": 0.5,
      "url": "http://minio:9000/bucket/frame_15.jpg",
      "confidence_score": 0.9,
      "is_first_candidate": true
    },
    {
      "id": "frame-uuid-002",
      "frame_number": 18,
      "timestamp": 0.6,
      "url": "http://minio:9000/bucket/frame_18.jpg",
      "confidence_score": 0.85,
      "is_first_candidate": true
    }
    // ... 更多候选帧
  ],
  
  "last_candidates": [
    // ... 尾帧候选列表
  ],
  
  "all_frames": [
    // ... 所有帧的缩略图列表（可选）
  ],
  
  "needs_review": true,
  "reviewed_by": null,
  "reviewed_at": null
}
```

---

#### 5.3 前端展示建议

**界面布局**:
```
┌─────────────────────────────────────────────────────┐
│  视频信息                                            │
│  文件名: test_video.mp4                              │
│  算法置信度: 85%                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────┬─────────────────────────────┐
│  当前标记的首帧      │  当前标记的尾帧              │
│  ┌───────────────┐  │  ┌───────────────┐          │
│  │               │  │  │               │          │
│  │  [首帧图片]   │  │  │  [尾帧图片]   │          │
│  │               │  │  │               │          │
│  └───────────────┘  │  └───────────────┘          │
│  帧号: 15           │  帧号: 485                   │
│  时间: 0.5s         │  时间: 16.17s                │
│  置信度: 90%        │  置信度: 88%                 │
└─────────────────────┴─────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  首帧候选列表 (Top 5)                                │
│  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐                    │
│  │ 1 │ │ 2 │ │ 3 │ │ 4 │ │ 5 │                    │
│  └───┘ └───┘ └───┘ └───┘ └───┘                    │
│  90%   85%   80%   75%   70%                        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  尾帧候选列表 (Top 5)                                │
│  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐                    │
│  │ 1 │ │ 2 │ │ 3 │ │ 4 │ │ 5 │                    │
│  └───┘ └───┘ └───┘ └───┘ └───┘                    │
│  88%   83%   78%   73%   68%                        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  所有帧时间轴 (可选)                                 │
│  ═══════════════════════════════════════════════    │
│  ▲                                           ▲      │
│  首帧                                        尾帧    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  操作按钮                                            │
│  [确认算法标记] [选择其他帧] [重新分析]             │
└─────────────────────────────────────────────────────┘
```

**交互逻辑**:
1. 默认显示算法标记的首尾帧
2. 显示候选帧列表供选择
3. 用户可以点击候选帧进行切换
4. 用户可以在时间轴上选择任意帧
5. 确认后提交标记

---

#### 5.4 提交人工标记

**接口**: `POST /api/v1/review/{video_id}/mark`

**场景1: 确认算法标记**
```json
{
  "first_frame_id": "frame-uuid-001",
  "last_frame_id": "frame-uuid-485",
  "reviewer": "zhangsan",
  "review_notes": "算法识别准确，确认无误"
}
```

**场景2: 修改标记**
```json
{
  "first_frame_id": "frame-uuid-002",  // 选择了候选帧2
  "last_frame_id": "frame-uuid-483",   // 选择了候选帧3
  "reviewer": "zhangsan",
  "review_notes": "算法识别的首帧有黑屏，选择候选帧2"
}
```

**响应示例**:
```json
{
  "video_id": "video-uuid-456",
  "status": "reviewed",
  "message": "标记成功",
  "first_frame": {
    "id": "frame-uuid-002",
    "frame_number": 18,
    "timestamp": 0.6,
    "url": "http://minio:9000/bucket/frame_18.jpg",
    "frame_type": "first"
  },
  "last_frame": {
    "id": "frame-uuid-483",
    "frame_number": 483,
    "timestamp": 16.1,
    "url": "http://minio:9000/bucket/frame_483.jpg",
    "frame_type": "last"
  }
}
```

**处理逻辑**:
1. 清除旧的首尾帧标记
2. 设置新的首尾帧标记
3. 创建人工标注记录
4. 更新视频状态为 `reviewed`
5. 更新标记方法为 `manual`
6. 记录审核人和审核时间

---

### 步骤6: 查看任务统计

**接口**: `GET /api/v1/task/{task_id}`

**响应示例**:
```json
{
  "id": "task-uuid-123",
  "name": "性能测试任务-20251211",
  "status": "processing",
  "total_videos": 5,
  "completed_videos": 3,
  "failed_videos": 0,
  "videos": [
    {
      "id": "task-video-uuid-1",
      "video_id": "video-uuid-456",
      "order": 1,
      "duration": 15.67,
      "first_frame_time": 0.6,
      "last_frame_time": 16.1,
      "video_filename": "test_video.mp4",
      "video_status": "reviewed",
      "first_frame_url": "http://minio:9000/bucket/frame_18.jpg",
      "last_frame_url": "http://minio:9000/bucket/frame_483.jpg"
    }
    // ... 更多视频
  ]
}
```

---

## 🔄 状态流转图

### 视频状态流转
```
uploading (上传中)
    ↓
extracting (提取帧中)
    ↓
analyzing (分析中)
    ↓
pending_review (待审核) ← AI分析完成
    ↓
reviewed (已审核) ← 人工确认
    ↓
completed (完成)

异常流程:
    ↓
failed (失败)
    ↓
cancelled (已取消)
```

### 任务状态流转
```
draft (草稿) ← 创建任务
    ↓
processing (处理中) ← 有视频在处理
    ↓
completed (已完成) ← 所有视频已审核
    ↓
failed (失败) ← 有视频失败
```

---

## 🎯 关键数据字段

### 视频表 (videos)
- `status`: 视频处理状态
- `marking_method`: 标记方法 (algorithm/ai_model/manual)
- `ai_confidence`: AI置信度
- `needs_review`: 是否需要审核
- `reviewed_by`: 审核人
- `reviewed_at`: 审核时间

### 帧表 (frames)
- `frame_type`: 帧类型 (first/last/middle)
- `is_first_candidate`: 是否为首帧候选
- `is_last_candidate`: 是否为尾帧候选
- `confidence_score`: 置信度分数
- `scene_change_score`: 场景变化分数

### 标注表 (frame_annotations)
- `marking_method`: 标记方法
- `marked_as_first`: 是否标记为首帧
- `marked_as_last`: 是否标记为尾帧
- `annotator`: 标注者
- `confidence`: 置信度
- `reason`: 标注原因

---

## 📊 完整示例代码

### Python完整流程示例

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

# 1. 创建任务
def create_task():
    response = requests.post(f"{BASE_URL}/task/create", json={
        "name": "性能测试任务-20251211",
        "description": "测试首尾帧识别",
        "created_by": "zhangsan"
    })
    task = response.json()
    print(f"✓ 任务创建成功: {task['id']}")
    return task['id']

# 2. 上传视频
def upload_video(task_id, video_path):
    with open(video_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/video/upload",
            files={'file': f},
            data={'task_id': task_id}
        )
    result = response.json()
    print(f"✓ 视频上传成功: {result['video_id']}")
    return result['video_id']

# 3. 等待处理完成
def wait_for_processing(video_id):
    while True:
        response = requests.get(f"{BASE_URL}/video/progress/{video_id}")
        progress = response.json()
        
        print(f"  进度: {progress['progress']}% - {progress['current_step']}")
        
        if progress['status'] == 'pending_review':
            print("✓ 处理完成，等待审核")
            break
        elif progress['status'] in ['failed', 'cancelled']:
            print(f"✗ 处理失败: {progress.get('error_message')}")
            break
        
        time.sleep(2)

# 4. 获取审核数据
def get_review_data(video_id):
    response = requests.get(f"{BASE_URL}/review/{video_id}")
    data = response.json()
    
    print(f"✓ 获取审核数据:")
    print(f"  - 总帧数: {data['total_frames']}")
    print(f"  - 算法置信度: {data['ai_confidence']}")
    print(f"  - 首帧: 第{data['marked_first_frame']['frame_number']}帧")
    print(f"  - 尾帧: 第{data['marked_last_frame']['frame_number']}帧")
    print(f"  - 首帧候选数: {len(data['first_candidates'])}")
    print(f"  - 尾帧候选数: {len(data['last_candidates'])}")
    
    return data

# 5. 提交审核
def submit_review(video_id, first_frame_id, last_frame_id):
    response = requests.post(
        f"{BASE_URL}/review/{video_id}/mark",
        json={
            "first_frame_id": first_frame_id,
            "last_frame_id": last_frame_id,
            "reviewer": "zhangsan",
            "review_notes": "确认无误"
        }
    )
    result = response.json()
    print(f"✓ 审核完成: {result['status']}")
    return result

# 6. 查看任务详情
def get_task_detail(task_id):
    response = requests.get(f"{BASE_URL}/task/{task_id}")
    task = response.json()
    
    print(f"✓ 任务详情:")
    print(f"  - 总视频数: {task['total_videos']}")
    print(f"  - 已完成: {task['completed_videos']}")
    print(f"  - 状态: {task['status']}")
    
    return task

# 执行完整流程
if __name__ == "__main__":
    print("=== 开始完整流程 ===\n")
    
    # 1. 创建任务
    task_id = create_task()
    
    # 2. 上传视频
    video_id = upload_video(task_id, "test_video.mp4")
    
    # 3. 等待处理
    wait_for_processing(video_id)
    
    # 4. 获取审核数据
    review_data = get_review_data(video_id)
    
    # 5. 提交审核（确认算法标记）
    submit_review(
        video_id,
        review_data['marked_first_frame']['id'],
        review_data['marked_last_frame']['id']
    )
    
    # 6. 查看任务详情
    get_task_detail(task_id)
    
    print("\n=== 流程完成 ===")
```

---

## 🔧 配置说明

### 采样率配置
在 `app/services/frame_extractor.py` 中配置帧提取采样率：

```python
# 每秒提取的帧数
SAMPLE_FPS = 1  # 每秒1帧

# 或者每N帧提取一次
SAMPLE_INTERVAL = 30  # 每30帧提取一次
```

### 候选帧数量
在 `app/tasks/video_tasks.py` 中配置候选帧数量：

```python
# 首帧候选数
first_candidates = analyzer.get_candidate_frames(
    frames_info, 'first', top_k=5  # 可调整
)

# 尾帧候选数
last_candidates = analyzer.get_candidate_frames(
    frames_info, 'last', top_k=5  # 可调整
)
```

---

## 📝 注意事项

1. **任务ID是可选的**
   - 上传视频时可以不提供task_id
   - 后续可以通过 `POST /task/{task_id}/videos` 添加到任务

2. **审核是必需的**
   - 所有视频处理完成后状态为 `pending_review`
   - 必须经过人工审核才能变为 `reviewed`

3. **可以重新分析**
   - 如果对算法结果不满意，可以调用重新分析接口
   - `POST /api/v1/video/{video_id}/reanalyze`

4. **支持批量上传**
   - 使用 `POST /api/v1/video/batch-upload`
   - 但目前批量上传不支持task_id参数（可以后续添加）

---

**文档版本**: v1.0  
**最后更新**: 2025-12-11  
**维护者**: wieszheng
