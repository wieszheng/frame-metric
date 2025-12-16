# Project API 文档补充

## 6. 项目管理模块 (`/project`)

项目管理模块用于组织和管理多个任务，提供项目级别的统计和归档功能。

---

### 6.1 创建项目
**端点**: `POST /api/v1/project`

**描述**: 创建一个新项目

**请求**: `ProjectCreate`
```json
{
  "name": "视频性能测试项目",
  "description": "2025年Q1视频处理性能测试",
  "code": "VPT-2025-Q1",
  "owner": "zhangsan",
  "members": "[\"zhangsan\", \"lisi\", \"wangwu\"]",
  "created_by": "zhangsan",
  "start_date": "2025-01-01T00:00:00",
  "end_date": "2025-03-31T23:59:59"
}
```

**字段说明**:
- `name`: 项目名称（必填，1-200字符）
- `description`: 项目描述（可选）
- `code`: 项目代码/编号（可选，唯一，1-100字符）
- `owner`: 项目负责人（必填）
- `members`: 项目成员（可选，JSON格式字符串）
- `created_by`: 创建人（必填）
- `start_date`: 开始日期（可选）
- `end_date`: 结束日期（可选）

**响应**: `ProjectResponse`
```json
{
  "id": "project-uuid",
  "name": "视频性能测试项目",
  "description": "2025年Q1视频处理性能测试",
  "code": "VPT-2025-Q1",
  "status": "active",
  "owner": "zhangsan",
  "members": "[\"zhangsan\", \"lisi\", \"wangwu\"]",
  "created_by": "zhangsan",
  "updated_by": null,
  "created_at": "2025-12-16T10:00:00",
  "updated_at": "2025-12-16T10:00:00",
  "start_date": "2025-01-01T00:00:00",
  "end_date": "2025-03-31T23:59:59",
  "archived_at": null,
  "statistics": {
    "total_tasks": 0,
    "active_tasks": 0,
    "completed_tasks": 0,
    "total_videos": 0
  },
  "tasks": []
}
```

**状态码**:
- `200`: 创建成功
- `400`: 项目代码已存在
- `422`: 数据验证失败

---

### 6.2 获取项目列表
**端点**: `GET /api/v1/project`

**描述**: 获取项目列表，支持分页和筛选

**查询参数**:
- `status`: 筛选状态（可选）
  - `active`: 进行中
  - `archived`: 已归档
  - `completed`: 已完成
  - `on_hold`: 暂停
- `owner`: 筛选负责人（可选）
- `skip`: 跳过记录数（默认: 0）
- `limit`: 返回记录数（默认: 20，最大: 100）

**响应**: `List[ProjectListResponse]`
```json
[
  {
    "id": "project-uuid",
    "name": "视频性能测试项目",
    "code": "VPT-2025-Q1",
    "status": "active",
    "owner": "zhangsan",
    "created_by": "zhangsan",
    "created_at": "2025-12-16T10:00:00",
    "total_tasks": 5,
    "completed_tasks": 2,
    "total_videos": 15
  }
]
```

**示例**:
```bash
# 获取所有项目
GET /api/v1/project

# 获取进行中的项目
GET /api/v1/project?status=active

# 获取某个负责人的项目
GET /api/v1/project?owner=zhangsan

# 分页查询
GET /api/v1/project?skip=20&limit=10
```

---

### 6.3 获取项目详情
**端点**: `GET /api/v1/project/{project_id}`

**描述**: 获取项目详细信息，包含所有任务列表和统计信息

**路径参数**:
- `project_id`: 项目ID

**响应**: `ProjectResponse`
```json
{
  "id": "project-uuid",
  "name": "视频性能测试项目",
  "description": "2025年Q1视频处理性能测试",
  "code": "VPT-2025-Q1",
  "status": "active",
  "owner": "zhangsan",
  "members": "[\"zhangsan\", \"lisi\", \"wangwu\"]",
  "created_by": "zhangsan",
  "updated_by": null,
  "created_at": "2025-12-16T10:00:00",
  "updated_at": "2025-12-16T10:00:00",
  "start_date": "2025-01-01T00:00:00",
  "end_date": "2025-03-31T23:59:59",
  "archived_at": null,
  "statistics": {
    "total_tasks": 5,
    "active_tasks": 3,
    "completed_tasks": 2,
    "total_videos": 15
  },
  "tasks": [
    {
      "id": "task-uuid-1",
      "name": "性能测试任务1",
      "status": "completed",
      "total_videos": 5,
      "completed_videos": 5,
      "created_at": "2025-12-16T10:00:00"
    },
    {
      "id": "task-uuid-2",
      "name": "性能测试任务2",
      "status": "processing",
      "total_videos": 10,
      "completed_videos": 7,
      "created_at": "2025-12-16T11:00:00"
    }
  ]
}
```

**状态码**:
- `200`: 成功
- `404`: 项目不存在

---

### 6.4 更新项目
**端点**: `PUT /api/v1/project/{project_id}`

**描述**: 更新项目信息

**路径参数**:
- `project_id`: 项目ID

**请求**: `ProjectUpdate`
```json
{
  "name": "更新后的项目名称",
  "description": "更新后的描述",
  "status": "on_hold",
  "owner": "lisi",
  "updated_by": "zhangsan",
  "end_date": "2025-06-30T23:59:59"
}
```

**字段说明**（所有字段均可选）:
- `name`: 项目名称
- `description`: 项目描述
- `code`: 项目代码（需确保唯一）
- `status`: 项目状态
- `owner`: 项目负责人
- `members`: 项目成员
- `updated_by`: 更新人
- `start_date`: 开始日期
- `end_date`: 结束日期

**响应**: `ProjectResponse`

**状态码**:
- `200`: 更新成功
- `400`: 项目代码重复
- `404`: 项目不存在
- `422`: 数据验证失败

---

### 6.5 删除项目
**端点**: `DELETE /api/v1/project/{project_id}`

**描述**: 删除项目（级联删除项目下的所有任务和任务视频关联）

**路径参数**:
- `project_id`: 项目ID

**响应**:
```json
{
  "message": "项目已删除",
  "project_id": "project-uuid"
}
```

**注意**: 
- 删除项目会级联删除所有关联的任务
- 删除任务会级联删除所有任务视频关联
- 不会删除视频本身

**状态码**:
- `200`: 删除成功
- `404`: 项目不存在

---

### 6.6 归档项目
**端点**: `POST /api/v1/project/{project_id}/archive`

**描述**: 归档项目，将项目状态设置为 ARCHIVED 并记录归档时间

**路径参数**:
- `project_id`: 项目ID

**响应**: `ProjectResponse`
```json
{
  "id": "project-uuid",
  "name": "视频性能测试项目",
  "status": "archived",
  "archived_at": "2025-12-16T15:30:00",
  ...
}
```

**状态码**:
- `200`: 归档成功
- `404`: 项目不存在

---

### 6.7 获取项目统计信息
**端点**: `GET /api/v1/project/{project_id}/statistics`

**描述**: 获取项目的详细统计信息

**路径参数**:
- `project_id`: 项目ID

**响应**: `ProjectStatistics`
```json
{
  "total_tasks": 5,
  "active_tasks": 3,
  "completed_tasks": 2,
  "total_videos": 15
}
```

**字段说明**:
- `total_tasks`: 总任务数
- `active_tasks`: 进行中的任务数（包括 draft, processing, pending_review 状态）
- `completed_tasks`: 已完成的任务数
- `total_videos`: 所有任务的总视频数

**状态码**:
- `200`: 成功
- `404`: 项目不存在

---

### 6.8 获取项目的所有任务
**端点**: `GET /api/v1/project/{project_id}/tasks`

**描述**: 获取项目下的所有任务，支持分页和状态筛选

**路径参数**:
- `project_id`: 项目ID

**查询参数**:
- `status`: 筛选任务状态（可选）
  - `draft`: 草稿
  - `processing`: 处理中
  - `pending_review`: 待审核
  - `completed`: 已完成
  - `cancelled`: 已取消
- `skip`: 跳过记录数（默认: 0）
- `limit`: 返回记录数（默认: 100，最大: 100）

**响应**: `List[TaskBriefInfo]`
```json
[
  {
    "id": "task-uuid-1",
    "name": "性能测试任务1",
    "status": "completed",
    "total_videos": 5,
    "completed_videos": 5,
    "created_at": "2025-12-16T10:00:00"
  },
  {
    "id": "task-uuid-2",
    "name": "性能测试任务2",
    "status": "processing",
    "total_videos": 10,
    "completed_videos": 7,
    "created_at": "2025-12-16T11:00:00"
  }
]
```

**示例**:
```bash
# 获取项目的所有任务
GET /api/v1/project/{project_id}/tasks

# 获取项目中已完成的任务
GET /api/v1/project/{project_id}/tasks?status=completed

# 分页查询
GET /api/v1/project/{project_id}/tasks?skip=10&limit=20
```

**状态码**:
- `200`: 成功
- `400`: 无效的任务状态
- `404`: 项目不存在

---

## 项目状态枚举 (ProjectStatus)

```python
ACTIVE = "active"          # 进行中
ARCHIVED = "archived"      # 已归档
COMPLETED = "completed"    # 已完成
ON_HOLD = "on_hold"        # 暂停
```

---

## 项目与任务关联

### 创建关联任务
在创建任务时，可以指定 `project_id` 将任务关联到项目：

**端点**: `POST /api/v1/task`

**请求**:
```json
{
  "name": "性能测试任务1",
  "description": "测试首尾帧识别准确性",
  "project_id": "project-uuid",
  "created_by": "zhangsan"
}
```

### 更新任务的项目关联
可以通过更新任务来修改其所属项目：

**端点**: `PUT /api/v1/task/{task_id}`

**请求**:
```json
{
  "project_id": "new-project-uuid"
}
```

---

## 项目管理业务流程

### 1. 完整项目流程
```
1. 创建项目 → POST /api/v1/project
2. 创建任务并关联到项目 → POST /api/v1/task (带 project_id)
3. 上传并处理视频 → POST /api/v1/video/upload
4. 添加视频到任务 → POST /api/v1/task/{task_id}/videos
5. 查看项目统计 → GET /api/v1/project/{project_id}/statistics
6. 查看项目详情 → GET /api/v1/project/{project_id}
7. 项目完成后归档 → POST /api/v1/project/{project_id}/archive
```

### 2. 项目层级结构
```
Project (项目)
  └── Task (任务)
        └── TaskVideo (任务视频)
              └── Video (视频)
                    └── Frame (帧)
```

---

## API 交互示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 创建项目
project_data = {
    "name": "视频性能测试项目",
    "description": "2025年Q1视频处理性能测试",
    "code": "VPT-2025-Q1",
    "owner": "zhangsan",
    "created_by": "zhangsan"
}
response = requests.post(f"{BASE_URL}/project", json=project_data)
project = response.json()
project_id = project["id"]

# 2. 创建任务并关联到项目
task_data = {
    "name": "性能测试任务1",
    "description": "测试首尾帧识别",
    "project_id": project_id,
    "created_by": "zhangsan"
}
response = requests.post(f"{BASE_URL}/task", json=task_data)
task = response.json()

# 3. 获取项目详情
response = requests.get(f"{BASE_URL}/project/{project_id}")
project_detail = response.json()
print(f"项目任务数: {project_detail['statistics']['total_tasks']}")

# 4. 获取项目的所有任务
response = requests.get(f"{BASE_URL}/project/{project_id}/tasks")
tasks = response.json()

# 5. 归档项目
response = requests.post(f"{BASE_URL}/project/{project_id}/archive")
archived_project = response.json()
print(f"项目状态: {archived_project['status']}")
```

### cURL 示例

```bash
# 创建项目
curl -X POST "http://localhost:8000/api/v1/project" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "视频性能测试项目",
    "code": "VPT-2025-Q1",
    "owner": "zhangsan",
    "created_by": "zhangsan"
  }'

# 获取项目列表
curl "http://localhost:8000/api/v1/project?status=active"

# 获取项目详情
curl "http://localhost:8000/api/v1/project/{project_id}"

# 更新项目
curl -X PUT "http://localhost:8000/api/v1/project/{project_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "updated_by": "zhangsan"
  }'

# 归档项目
curl -X POST "http://localhost:8000/api/v1/project/{project_id}/archive"

# 获取项目统计
curl "http://localhost:8000/api/v1/project/{project_id}/statistics"

# 获取项目的所有任务
curl "http://localhost:8000/api/v1/project/{project_id}/tasks?status=completed"

# 删除项目
curl -X DELETE "http://localhost:8000/api/v1/project/{project_id}"
```

---

## 最佳实践

### 1. 项目代码规范
建议使用统一的项目代码格式，例如：
- `PRJ-2025-001`: 项目-年份-序号
- `VPT-Q1-2025`: 视频性能测试-季度-年份
- `TEST-PERF-001`: 测试-性能-序号

### 2. 项目生命周期管理
1. **创建阶段**: 设置项目基本信息和成员
2. **执行阶段**: 创建任务，上传视频，进行测试
3. **监控阶段**: 定期查看统计信息，跟踪进度
4. **完成阶段**: 标记项目为完成状态
5. **归档阶段**: 归档已完成的项目

### 3. 权限控制建议
- 项目负责人（owner）有完整的项目管理权限
- 项目成员（members）可以创建和管理任务
- 建议在应用层实现基于角色的访问控制

### 4. 统计信息更新
- 项目统计信息是实时计算的
- 每次查询项目详情时会重新统计
- 对于大型项目，建议使用缓存优化性能

---
