#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: export_service
@Author  : wieszheng
@Time    : 2025/12/16 12:52
@Software: PyCharm
"""
import io
from typing import List
import pandas as pd
from datetime import datetime

from app.schemas.task import TaskExportData, ExportFormat


class ExportService:
    """导出服务"""
    
    @staticmethod
    def export_task_data(
        export_data: List[TaskExportData],
        format: ExportFormat,
        task_name: str = "task"
    ) -> tuple[bytes, str, str]:
        """
        导出任务数据
        
        Args:
            export_data: 导出数据列表
            format: 导出格式 (csv/excel)
            task_name: 任务名称（用于文件名）
            
        Returns:
            tuple: (文件内容bytes, 文件名, content_type)
        """
        # 转换为DataFrame
        df = ExportService._prepare_dataframe(export_data)

        # 根据格式导出
        if format == ExportFormat.CSV:
            return ExportService._export_csv(df, task_name)
        elif format == ExportFormat.EXCEL:
            return ExportService._export_excel(df, task_name)
        else:
            raise ValueError(f"不支持的导出格式: {format}")
    
    @staticmethod
    def _prepare_dataframe(export_data: List[TaskExportData]) -> pd.DataFrame:
        """准备DataFrame数据"""
        data_list = []
        
        for item in export_data:
            row = {
                "任务名称": item.task_name,
                "任务ID": item.task_id,
                "序号": item.sequence,
                "视频文件名": item.video_filename,
                "视频ID": item.video_id,
                "首帧时间戳(秒)": item.first_frame_timestamp,
                "尾帧时间戳(秒)": item.last_frame_timestamp,
                "首帧编号": item.first_frame_number,
                "尾帧编号": item.last_frame_number,
                "耗时(毫秒)": item.duration_ms,
                "耗时(秒)": item.duration_seconds,
                "视频时长(秒)": item.video_duration,
                "视频帧率": item.video_fps,
                "视频分辨率": item.video_resolution,
                "备注": item.notes,
                "添加时间": item.added_at.strftime("%Y-%m-%d %H:%M:%S") if item.added_at else None
            }
            data_list.append(row)
        
        df = pd.DataFrame(data_list)
        return df
    
    @staticmethod
    def _export_csv(df: pd.DataFrame, task_name: str) -> tuple[bytes, str, str]:
        """导出为CSV"""
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_name}_timing_data_{timestamp}.csv"
        
        # 转换为CSV
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')  # utf-8-sig for Excel compatibility
        content = output.getvalue().encode('utf-8-sig')
        
        return content, filename, "text/csv"
    
    @staticmethod
    def _export_excel(df: pd.DataFrame, task_name: str) -> tuple[bytes, str, str]:
        """导出为Excel"""
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_name}_timing_data_{timestamp}.xlsx"
        
        # 转换为Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='任务耗时数据')
            
            # 获取工作表
            worksheet = writer.sheets['任务耗时数据']
            
            # 自动调整列宽
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        content = output.getvalue()
        
        return content, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


export_service = ExportService()
