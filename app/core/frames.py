# !/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Version  : Python 3.12
@Time     : 2025/12/12 15:43
@Author   : wieszheng
@Software : PyCharm
"""
import cv2
import os
import json
from pathlib import Path


def extract_all_frames_with_timestamp(video_path, output_folder):
    """
    提取视频的所有帧，并记录每帧的时间戳（毫秒）

    :param video_path: 视频文件路径
    :param output_folder: 输出文件夹路径
    :return: 包含帧信息的字典列表
    """
    # 创建输出文件夹
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    # 打开视频
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise ValueError(f"无法打开视频文件: {video_path}")

    # 获取视频信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_ms = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps * 1000)

    print(f"视频信息:")
    print(f"  FPS: {fps}")
    print(f"  总帧数: {total_frames}")
    print(f"  时长: {duration_ms}ms ({duration_ms / 1000:.2f}秒)")
    print(f"\n开始提取帧...")

    frame_info_list = []
    frame_count = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        # 获取当前帧的时间戳（毫秒）
        timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))

        # 保存帧图片
        frame_filename = f"frame_{frame_count:06d}.jpg"
        frame_path = output_folder / frame_filename
        cv2.imwrite(str(frame_path), frame)

        # 记录帧信息
        frame_info = {
            "frame_number": frame_count,
            "timestamp_ms": timestamp_ms,
            "timestamp_sec": round(timestamp_ms / 1000, 3),
            "filename": frame_filename
        }
        frame_info_list.append(frame_info)

        # 显示进度
        if (frame_count + 1) % 100 == 0 or frame_count == 0:
            progress = (frame_count + 1) / total_frames * 100
            print(f"  进度: {frame_count + 1}/{total_frames} ({progress:.1f}%)")

        frame_count += 1

    cap.release()

    # 保存时间戳信息到JSON文件
    json_path = output_folder / "frames_info.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "video_info": {
                "fps": fps,
                "total_frames": total_frames,
                "duration_ms": duration_ms
            },
            "frames": frame_info_list
        }, f, indent=2, ensure_ascii=False)

    # 同时保存一个简单的CSV格式
    csv_path = output_folder / "frames_timestamps.csv"
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("frame_number,timestamp_ms,timestamp_sec,filename\n")
        for info in frame_info_list:
            f.write(f"{info['frame_number']},{info['timestamp_ms']},"
                    f"{info['timestamp_sec']},{info['filename']}\n")

    print(f"\n✓ 提取完成！")
    print(f"  保存帧数: {frame_count}")
    print(f"  输出目录: {output_folder}")
    print(f"  时间戳文件: {json_path.name}, {csv_path.name}")

    return frame_info_list

if __name__ == '__main__':
    extract_all_frames_with_timestamp('video.mp4', 'output')