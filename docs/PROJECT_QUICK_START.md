# 项目管理功能使用指南

## 快速开始

### 1. 创建项目

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 创建项目
project_data = {
    "name": "我的第一个项目",
    "description": "这是一个测试项目",
    "code": "PRJ-001",  # 可选，但建议填写
    "owner": "zhangsan",
    "created_by": "zhangsan"
}

response = requests.post(f"{BASE_URL}/project", json=project_data)
project = response.json()
project_id = project["id"]

print(f"项目创建成功！ID: {project_id}")
```

### 2. 创建任务并关联到项目

```python
# 创建任务
task_data = {
    "name": "任务1",
    "description": "第一个测试任务",
    "project_id": project_id,  # 关联到项目
    "created_by": "zhangsan"
}

response = requests.post(f"{BASE_URL}/task", json=task_data)
task = response.json()

print(f"任务创建成功！ID: {task['id']}")
```

### 3. 查看项目详情

```python
# 获取项目详情
response = requests.get(f"{BASE_URL}/project/{project_id}")
project_detail = response.json()

print(f"项目名称: {project_detail['name']}")
print(f"项目状态: {project_detail['status']}")
print(f"总任务数: {project_detail['statistics']['total_tasks']}")
print(f"已完成任务: {project_detail['statistics']['completed_tasks']}")
print(f"总视频数: {project_detail['statistics']['total_videos']}")

# 查看项目下的所有任务
for task in project_detail['tasks']:
    print(f"  - {task['name']}: {task['status']} ({task['completed_videos']}/{task['total_videos']} 视频完成)")
```

### 4. 完整工作流程

```python
# 1. 创建项目
project = requests.post(f"{BASE_URL}/project", json={
    "name": "视频测试项目",
    "code": "VTP-2025-001",
    "owner": "zhangsan",
    "created_by": "zhangsan"
}).json()

# 2. 创建任务
task = requests.post(f"{BASE_URL}/task", json={
    "name": "性能测试",
    "project_id": project["id"],
    "created_by": "zhangsan"
}).json()

# 3. 上传视频
with open("test_video.mp4", "rb") as f:
    files = {"file": f}
    video = requests.post(f"{BASE_URL}/video/upload", files=files).json()

# 4. 添加视频到任务
requests.post(f"{BASE_URL}/task/{task['id']}/videos", json={
    "video_id": video["video_id"],
    "notes": "测试视频"
})

# 5. 查看项目统计
stats = requests.get(f"{BASE_URL}/project/{project['id']}/statistics").json()
print(f"项目统计: {stats}")

# 6. 项目完成后归档
archived = requests.post(f"{BASE_URL}/project/{project['id']}/archive").json()
print(f"项目已归档，状态: {archived['status']}")
```

---

## 常用操作

### 查询项目列表

```python
# 获取所有项目
projects = requests.get(f"{BASE_URL}/project").json()

# 获取进行中的项目
active_projects = requests.get(f"{BASE_URL}/project?status=active").json()

# 获取某个负责人的项目
my_projects = requests.get(f"{BASE_URL}/project?owner=zhangsan").json()

# 分页查询
page_2 = requests.get(f"{BASE_URL}/project?skip=20&limit=10").json()
```

### 更新项目

```python
# 更新项目信息
updated = requests.put(f"{BASE_URL}/project/{project_id}", json={
    "description": "更新后的描述",
    "status": "completed",
    "updated_by": "zhangsan"
}).json()
```

### 查询项目的任务

```python
# 获取项目的所有任务
tasks = requests.get(f"{BASE_URL}/project/{project_id}/tasks").json()

# 获取项目中已完成的任务
completed_tasks = requests.get(
    f"{BASE_URL}/project/{project_id}/tasks?status=completed"
).json()
```

---

## cURL 命令示例

```bash
# 创建项目
curl -X POST "http://localhost:8000/api/v1/project" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试项目",
    "code": "TEST-001",
    "owner": "zhangsan",
    "created_by": "zhangsan"
  }'

# 获取项目列表
curl "http://localhost:8000/api/v1/project"

# 获取项目详情
curl "http://localhost:8000/api/v1/project/{project_id}"

# 归档项目
curl -X POST "http://localhost:8000/api/v1/project/{project_id}/archive"

# 删除项目
curl -X DELETE "http://localhost:8000/api/v1/project/{project_id}"
```

---

## 项目状态说明

- **active**: 进行中 - 项目正在执行
- **completed**: 已完成 - 项目已完成所有任务
- **archived**: 已归档 - 项目已归档，不再活跃
- **on_hold**: 暂停 - 项目暂时暂停

---

## 注意事项

1. **项目代码唯一性**: 如果设置了 `code`，必须确保在系统中唯一
2. **级联删除**: 删除项目会同时删除其下的所有任务和任务视频关联（但不会删除视频本身）
3. **统计信息**: 项目统计信息是实时计算的，反映最新的任务状态
4. **归档操作**: 归档后项目状态变为 `archived`，可以通过更新接口恢复为其他状态

---

## 更多信息

- 完整 API 文档: `/docs/PROJECT_API.md`
- 实现总结: `/docs/PROJECT_IMPLEMENTATION_SUMMARY.md`
- Swagger 文档: `http://localhost:8000/docs`
