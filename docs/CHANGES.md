# Frame-Metric 业务流程调整总结

## 📝 调整概述

根据你的需求，已对系统进行了调整，确保业务流程符合：
**创建任务 → 上传视频 → 提取分析 → 算法标记 → 人工审核**

---

## ✅ 已完成的调整

### 1. 修改视频上传接口
**文件**: `app/api/v1/video.py`

**变更**:
- ✅ 添加 `task_id` 参数（可选）
- ✅ 上传时验证任务是否存在
- ✅ 自动将视频关联到任务
- ✅ 创建 `TaskVideo` 关联记录

**新接口签名**:
```python
@router.post("/upload")
async def upload_video(
    file: UploadFile,
    task_id: str = Form(None),  # 新增参数
    db: AsyncSession = Depends(get_async_db)
)
```

**使用示例**:
```bash
# 上传并关联到任务
curl -X POST "http://localhost:8000/api/v1/video/upload" \
  -F "file=@test.mp4" \
  -F "task_id=your-task-id"

# 或者不关联任务
curl -X POST "http://localhost:8000/api/v1/video/upload" \
  -F "file=@test.mp4"
```

---

### 2. 业务流程已就绪

当前系统已经支持完整的业务流程：

#### ✅ 步骤1: 创建任务
```
POST /api/v1/task/create
```
- 创建空任务
- 状态: `draft`

#### ✅ 步骤2: 上传视频
```
POST /api/v1/video/upload (带task_id参数)
```
- 上传视频文件
- 关联到任务
- 触发异步处理

#### ✅ 步骤3: 提取分析视频帧 (自动)
```
Celery任务: process_video_frames_full
```
- 提取所有帧
- 计算特征（亮度、清晰度、场景变化）
- 上传到MinIO
- 状态: `extracting` → `analyzing`

#### ✅ 步骤4: 算法标记首尾帧 (自动)
```
FrameAnalyzer.analyze_first_last_frames()
```
- 智能识别首尾帧
- 生成候选帧列表（Top 5）
- 计算置信度
- 创建标注记录
- 状态: `pending_review`

#### ✅ 步骤5: 人工审核
```
GET /api/v1/review/{video_id}        # 获取审核数据
POST /api/v1/review/{video_id}/mark  # 提交审核结果
```
- 查看算法标记结果
- 查看候选帧列表
- 确认或修改标记
- 状态: `reviewed`

---

## 📋 完整流程示例

### Python代码示例
```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 创建任务
task_response = requests.post(f"{BASE_URL}/task/create", json={
    "name": "测试任务",
    "created_by": "zhangsan"
})
task_id = task_response.json()['id']
print(f"任务ID: {task_id}")

# 2. 上传视频（关联任务）
with open('test.mp4', 'rb') as f:
    video_response = requests.post(
        f"{BASE_URL}/video/upload",
        files={'file': f},
        data={'task_id': task_id}  # 关联任务
    )
video_id = video_response.json()['video_id']
print(f"视频ID: {video_id}")

# 3. 等待处理完成（自动执行步骤3和4）
import time
while True:
    progress = requests.get(f"{BASE_URL}/video/progress/{video_id}").json()
    print(f"进度: {progress['progress']}% - {progress['current_step']}")
    
    if progress['status'] == 'pending_review':
        print("算法标记完成，等待审核")
        break
    time.sleep(2)

# 4. 获取审核数据
review_data = requests.get(f"{BASE_URL}/review/{video_id}").json()
print(f"算法置信度: {review_data['ai_confidence']}")
print(f"首帧: 第{review_data['marked_first_frame']['frame_number']}帧")
print(f"尾帧: 第{review_data['marked_last_frame']['frame_number']}帧")

# 5. 人工审核（确认或修改）
review_response = requests.post(
    f"{BASE_URL}/review/{video_id}/mark",
    json={
        "first_frame_id": review_data['marked_first_frame']['id'],
        "last_frame_id": review_data['marked_last_frame']['id'],
        "reviewer": "zhangsan",
        "review_notes": "确认无误"
    }
)
print(f"审核完成: {review_response.json()['status']}")

# 6. 查看任务详情
task_detail = requests.get(f"{BASE_URL}/task/{task_id}").json()
print(f"任务状态: {task_detail['status']}")
print(f"已完成视频: {task_detail['completed_videos']}/{task_detail['total_videos']}")
```

---

## 🔄 状态流转

### 视频状态
```
uploading → extracting → analyzing → pending_review → reviewed
```

### 任务状态
```
draft → processing → completed
```

---

## 📊 数据关系

```
Task (任务)
  ├── TaskVideo (关联表)
  │     ├── video_id
  │     ├── order
  │     └── duration
  └── Video (视频)
        ├── status
        ├── marking_method
        └── Frames (帧)
              ├── frame_type (first/last)
              ├── is_first_candidate
              ├── is_last_candidate
              └── FrameAnnotations (标注历史)
```

---

## 🎯 关键特性

### 1. 灵活的任务关联
- ✅ 上传时可以关联任务
- ✅ 上传后可以添加到任务
- ✅ 一个视频可以属于多个任务

### 2. 智能标记
- ✅ 算法自动识别首尾帧
- ✅ 生成候选帧列表
- ✅ 计算置信度分数
- ✅ 支持重新分析

### 3. 人工审核
- ✅ 查看算法标记结果
- ✅ 查看候选帧列表
- ✅ 确认或修改标记
- ✅ 记录审核历史

### 4. 完整的追踪
- ✅ 实时进度查询
- ✅ 状态流转记录
- ✅ 标注历史记录
- ✅ 任务统计数据

---

## 📁 相关文档

1. **WORKFLOW.md** - 详细业务流程文档
   - 完整的API调用示例
   - 前端界面设计建议
   - 状态流转说明

2. **API_DOCUMENTATION.md** - API接口文档
   - 所有接口的详细说明
   - 请求/响应格式
   - 数据模型定义

3. **OPTIMIZATION_ANALYSIS.md** - 优化分析报告
   - 安全问题分析
   - 性能优化建议
   - 代码冗余识别

---

## 🚀 下一步建议

### 立即可用
当前调整已完成，系统可以按照新流程使用：
1. ✅ 创建任务
2. ✅ 上传视频（带task_id）
3. ✅ 等待自动处理
4. ✅ 人工审核
5. ✅ 查看结果

### 可选增强
如果需要进一步优化，可以参考 `OPTIMIZATION_ANALYSIS.md`：
1. 🔴 **高优先级**: 添加认证授权（安全）
2. 🟡 **中优先级**: 优化N+1查询（性能）
3. 🟢 **低优先级**: 添加单元测试（质量）

---

## 💡 使用提示

### 前端开发建议
参考 `WORKFLOW.md` 中的界面布局建议：
- 任务列表页
- 视频上传页（带任务选择）
- 审核页面（展示候选帧）
- 任务详情页（统计数据）

### API调用顺序
```
1. POST /task/create
2. POST /video/upload (带task_id)
3. GET /video/progress/{video_id} (轮询)
4. GET /review/{video_id}
5. POST /review/{video_id}/mark
6. GET /task/{task_id}
```

### 测试建议
```bash
# 1. 启动服务
uvicorn app.main:app --reload

# 2. 启动Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info

# 3. 测试完整流程
python test_workflow.py
```

---

## 📞 技术支持

如有问题，请查看：
1. Swagger文档: http://localhost:8000/docs
2. 日志文件: logs/app.log
3. Celery监控: http://localhost:5555 (Flower)

---

**调整完成时间**: 2025-12-11  
**版本**: v1.1  
**状态**: ✅ 已完成并可用
