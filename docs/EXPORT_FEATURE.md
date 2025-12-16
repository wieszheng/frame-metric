# 任务视频首尾帧耗时数据导出功能

## 功能概述

新增了任务视频首尾帧耗时信息的导出功能，支持将任务中所有视频的时间戳、耗时等关键数据导出为 CSV 或 Excel 格式，方便进行数据分析和报告生成。

## API 端点

### 导出任务耗时数据

**端点**: `GET /api/v1/task/{task_id}/export`

**描述**: 导出指定任务的所有视频首尾帧耗时数据

**路径参数**:
- `task_id` (string, 必填): 任务ID

**查询参数**:
- `format` (string, 可选): 导出格式
  - `excel`: Excel格式 (默认)
  - `csv`: CSV格式

**响应**: 
- 成功: 返回文件下载流
- 失败: 返回错误信息

**状态码**:
- `200`: 成功
- `400`: 任务中没有视频数据
- `404`: 任务不存在
- `500`: 导出失败

## 导出数据字段

导出的数据包含以下字段：

| 字段名 | 说明 | 类型 | 示例 |
|--------|------|------|------|
| 任务名称 | 任务的名称 | string | "性能测试任务1" |
| 任务ID | 任务的唯一标识 | string | "uuid-xxx" |
| 序号 | 视频在任务中的序号 | integer | 1 |
| 视频文件名 | 原始视频文件名 | string | "test_video.mp4" |
| 视频ID | 视频的唯一标识 | string | "uuid-yyy" |
| 首帧时间戳(秒) | 首帧的时间戳 | float | 0.5 |
| 尾帧时间戳(秒) | 尾帧的时间戳 | float | 3.2 |
| 首帧编号 | 首帧的帧编号 | integer | 15 |
| 尾帧编号 | 尾帧的帧编号 | integer | 96 |
| 耗时(毫秒) | 首尾帧之间的耗时（毫秒） | integer | 2700 |
| 耗时(秒) | 首尾帧之间的耗时（秒） | float | 2.7 |
| 视频时长(秒) | 视频总时长 | float | 10.5 |
| 视频帧率 | 视频帧率 | float | 30.0 |
| 视频分辨率 | 视频分辨率 | string | "1920x1080" |
| 备注 | 视频备注信息 | string | "测试视频" |
| 添加时间 | 视频添加到任务的时间 | datetime | "2025-12-16 13:00:00" |

## 使用示例

### cURL 示例

#### 导出为 Excel (默认)
```bash
curl -X GET "http://localhost:8000/api/v1/task/{task_id}/export" \
  -H "accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  --output task_data.xlsx
```

#### 导出为 CSV
```bash
curl -X GET "http://localhost:8000/api/v1/task/{task_id}/export?format=csv" \
  -H "accept: text/csv" \
  --output task_data.csv
```

### Python 示例

```python
import requests

# 导出为 Excel
task_id = "your-task-id"
response = requests.get(
    f"http://localhost:8000/api/v1/task/{task_id}/export",
    params={"format": "excel"}
)

if response.status_code == 200:
    with open("task_data.xlsx", "wb") as f:
        f.write(response.content)
    print("导出成功!")
else:
    print(f"导出失败: {response.json()}")

# 导出为 CSV
response = requests.get(
    f"http://localhost:8000/api/v1/task/{task_id}/export",
    params={"format": "csv"}
)

if response.status_code == 200:
    with open("task_data.csv", "wb") as f:
        f.write(response.content)
    print("导出成功!")
```

### JavaScript 示例

```javascript
// 导出为 Excel
async function exportTaskData(taskId, format = 'excel') {
    try {
        const response = await fetch(
            `http://localhost:8000/api/v1/task/${taskId}/export?format=${format}`
        );
        
        if (!response.ok) {
            throw new Error('导出失败');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `task_data.${format === 'csv' ? 'csv' : 'xlsx'}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        console.log('导出成功!');
    } catch (error) {
        console.error('导出失败:', error);
    }
}

// 使用示例
exportTaskData('your-task-id', 'excel');
```

## 文件命名规则

导出的文件名格式为：`{任务名称}_timing_data_{时间戳}.{扩展名}`

示例：
- Excel: `性能测试任务1_timing_data_20251216_130000.xlsx`
- CSV: `性能测试任务1_timing_data_20251216_130000.csv`

## Excel 文件特性

Excel 导出包含以下特性：
- 工作表名称：`任务耗时数据`
- 自动列宽调整（最大50字符）
- UTF-8 编码
- 包含表头

## CSV 文件特性

CSV 导出包含以下特性：
- UTF-8 BOM 编码（兼容 Excel 打开）
- 逗号分隔
- 包含表头

## 数据处理逻辑

1. **查询任务**: 验证任务是否存在
2. **查询视频列表**: 获取任务中的所有视频
3. **收集数据**: 对每个视频收集以下信息：
   - 视频基本信息（文件名、ID、属性）
   - 首尾帧时间戳和编号
   - 计算耗时（毫秒和秒）
   - 备注信息
4. **格式化数据**: 使用 pandas 处理数据
5. **生成文件**: 根据格式生成 CSV 或 Excel 文件
6. **返回下载**: 返回文件流供下载

## 错误处理

### 任务不存在 (404)
```json
{
  "detail": "任务不存在"
}
```

### 任务中没有视频 (400)
```json
{
  "detail": "任务中没有视频数据"
}
```

### 导出失败 (500)
```json
{
  "detail": "导出失败: {错误详情}"
}
```

## 性能考虑

- 导出操作是同步的，大量数据可能需要较长时间
- 建议对于超过 1000 个视频的任务，考虑分批导出或异步处理
- Excel 格式比 CSV 格式生成速度稍慢，但包含更好的格式化

## 依赖项

新增的依赖项：
- `pandas==2.2.0`: 数据处理和导出
- `openpyxl==3.1.2`: Excel 文件生成

安装依赖：
```bash
pip install pandas==2.2.0 openpyxl==3.1.2
```

## 代码结构

### 新增文件
- `app/services/export_service.py`: 导出服务实现
- `docs/EXPORT_FEATURE.md`: 功能文档

### 修改文件
- `app/api/v1/task.py`: 添加导出端点
- `app/schemas/task.py`: 添加导出相关 Schema
- `app/crud/task.py`: 添加辅助查询方法
- `requirements.txt`: 添加新依赖

## 测试建议

### 单元测试
```python
import pytest
from app.services.export_service import export_service, ExportFormat
from app.schemas.task import TaskExportData
from datetime import datetime

def test_export_csv():
    data = [
        TaskExportData(
            task_name="测试任务",
            task_id="task-1",
            video_filename="test.mp4",
            video_id="video-1",
            sequence=1,
            first_frame_timestamp=0.5,
            last_frame_timestamp=3.2,
            duration_ms=2700,
            duration_seconds=2.7,
            first_frame_number=15,
            last_frame_number=96,
            video_duration=10.5,
            video_fps=30.0,
            video_resolution="1920x1080",
            notes="测试",
            added_at=datetime.now()
        )
    ]
    
    content, filename, content_type = export_service.export_task_data(
        data, ExportFormat.CSV, "测试任务"
    )
    
    assert content is not None
    assert filename.endswith('.csv')
    assert content_type == "text/csv"

def test_export_excel():
    # 类似的测试用例
    pass
```

### 集成测试
```python
async def test_export_endpoint(client, db_session):
    # 创建测试任务和视频
    # 调用导出端点
    # 验证返回的文件内容
    pass
```

## 未来改进

1. **异步导出**: 对于大量数据，使用 Celery 异步任务
2. **自定义字段**: 允许用户选择导出的字段
3. **多种格式**: 支持 JSON、PDF 等格式
4. **数据过滤**: 支持按状态、时间范围等过滤
5. **统计汇总**: 在导出文件中添加统计汇总行
6. **批量导出**: 支持一次导出多个任务

## 更新日志

### v1.1.0 (2025-12-16)
- ✨ 新增任务视频首尾帧耗时数据导出功能
- ✨ 支持 CSV 和 Excel 两种导出格式
- ✨ 自动生成带时间戳的文件名
- ✨ Excel 文件自动调整列宽
- 📝 添加完整的 API 文档和使用示例
