import cv2
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple


class SceneAnalyzer:
    """场景转折点分析器"""

    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            raise ValueError(f"无法打开视频: {video_path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_ms = int(self.total_frames / self.fps * 1000)

        print(
            f"视频信息: FPS={self.fps}, 总帧数={self.total_frames}, 时长={self.duration_ms}ms")

    def calculate_frame_difference(self, frame1, frame2) -> float:
        """计算两帧之间的差异度（使用直方图比较）"""
        if frame1 is None or frame2 is None:
            return 0.0

        # 转换为灰度图
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # 计算直方图
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])

        # 归一化
        cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

        # 计算相关性（0-1，越小差异越大）
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # 转换为差异度（0-1，越大差异越大）
        difference = 1 - correlation

        return difference

    def detect_turning_points(self, threshold: float = 0.3,
                              min_interval_ms: int = 500) -> List[Dict]:
        """
        检测场景转折点

        :param threshold: 差异阈值，超过此值认为是转折点
        :param min_interval_ms: 最小间隔时间（毫秒），避免连续检测
        :return: 转折点列表
        """
        print(
            f"\n开始检测转折点 (阈值={threshold}, 最小间隔={min_interval_ms}ms)...")

        turning_points = []
        prev_frame = None
        last_turning_point_ms = -min_interval_ms

        frame_idx = 0
        differences = []  # 记录所有差异值用于分析

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            current_ms = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))

            if prev_frame is not None:
                # 计算帧差异
                diff = self.calculate_frame_difference(prev_frame, frame)
                differences.append(diff)

                # 检测转折点
                if (diff > threshold and
                        current_ms - last_turning_point_ms >= min_interval_ms):
                    turning_point = {
                        "frame_number": frame_idx,
                        "timestamp_ms": current_ms,
                        "timestamp_sec": round(current_ms / 1000, 3),
                        "difference_score": round(diff, 4),
                        "type": "turning_point"
                    }
                    turning_points.append(turning_point)
                    last_turning_point_ms = current_ms

                    print(
                        f"  检测到转折点: 帧{frame_idx}, 时间{current_ms}ms, 差异度{diff:.4f}")

            prev_frame = frame.copy()
            frame_idx += 1

            # 显示进度
            if frame_idx % 100 == 0:
                progress = frame_idx / self.total_frames * 100
                print(
                    f"  分析进度: {frame_idx}/{self.total_frames} ({progress:.1f}%)")

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 重置视频位置

        # 统计信息
        if differences:
            avg_diff = np.mean(differences)
            max_diff = np.max(differences)
            print(f"\n差异度统计: 平均={avg_diff:.4f}, 最大={max_diff:.4f}")

        print(f"共检测到 {len(turning_points)} 个转折点")

        return turning_points

    def identify_scenes(self, turning_points: List[Dict]) -> List[Dict]:
        """
        根据转折点识别场景，并标注每个场景的首尾帧

        :param turning_points: 转折点列表
        :return: 场景列表
        """
        print("\n识别场景并标注首尾帧...")

        scenes = []

        # 添加视频起始点作为第一个场景的开始
        scene_starts = [0] + [tp["timestamp_ms"] for tp in turning_points]

        for i in range(len(scene_starts)):
            start_ms = scene_starts[i]
            end_ms = scene_starts[i + 1] if i + 1 < len(
                scene_starts) else self.duration_ms

            # 获取首尾帧号
            start_frame = int(start_ms / 1000 * self.fps)
            end_frame = int(end_ms / 1000 * self.fps) - 1

            duration_ms = end_ms - start_ms

            scene = {
                "scene_id": i,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "start_timestamp_ms": start_ms,
                "end_timestamp_ms": end_ms,
                "duration_ms": duration_ms,
                "duration_sec": round(duration_ms / 1000, 3),
                "frame_count": end_frame - start_frame + 1
            }

            scenes.append(scene)

            print(
                f"  场景{i}: {start_ms}ms - {end_ms}ms (时长{duration_ms}ms, 共{scene['frame_count']}帧)")

        return scenes

    def extract_scene_keyframes(self, scenes: List[Dict], output_folder: str):
        """
        提取每个场景的首尾关键帧

        :param scenes: 场景列表
        :param output_folder: 输出文件夹
        """
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        print(f"\n提取场景关键帧到: {output_folder}")

        for scene in scenes:
            scene_id = scene["scene_id"]
            start_frame = scene["start_frame"]
            end_frame = scene["end_frame"]

            # 提取首帧
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            ret, first_frame = self.cap.read()
            if ret:
                first_path = output_folder / f"scene_{scene_id:02d}_first_frame_{start_frame:06d}_{scene['start_timestamp_ms']}ms.jpg"
                cv2.imwrite(str(first_path), first_frame)
                scene["first_frame_path"] = str(first_path.name)

            # 提取尾帧
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, end_frame)
            ret, last_frame = self.cap.read()
            if ret:
                last_path = output_folder / f"scene_{scene_id:02d}_last_frame_{end_frame:06d}_{scene['end_timestamp_ms']}ms.jpg"
                cv2.imwrite(str(last_path), last_frame)
                scene["last_frame_path"] = str(last_path.name)

            print(f"  场景{scene_id}: 已保存首帧和尾帧")

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 重置位置

    def annotate_app_launch_scenario(self, scenes: List[Dict]) -> Dict:
        """
        针对APP启动场景进行标注
        适用于: 点击图标 -> 启动画面 -> 加载 -> 主界面显示
        """
        print("\n=== APP启动场景分析 ===")

        if len(scenes) < 2:
            print("场景数量不足，无法分析完整启动流程")
            return {}

        annotation = {
            "scenario_type": "app_launch",
            "analysis_time": datetime.now().isoformat(),
            "phases": []
        }

        # 定义启动阶段
        phase_names = [
            "待机状态",
            "点击响应/启动动画",
            "加载界面",
            "主界面显示",
            "后续交互"
        ]

        for i, scene in enumerate(scenes[:min(len(scenes), len(phase_names))]):
            phase = {
                "phase_name": phase_names[i],
                "scene_id": scene["scene_id"],
                "start_ms": scene["start_timestamp_ms"],
                "end_ms": scene["end_timestamp_ms"],
                "duration_ms": scene["duration_ms"],
                "first_frame": scene.get("first_frame_path"),
                "last_frame": scene.get("last_frame_path")
            }
            annotation["phases"].append(phase)

            print(
                f"  {phase_names[i]}: {scene['start_timestamp_ms']}ms - {scene['end_timestamp_ms']}ms "
                f"(耗时 {scene['duration_ms']}ms)")

        # 计算总启动时间（从第一个转折点到最后一个场景开始）
        if len(annotation["phases"]) >= 2:
            total_launch_time = annotation["phases"][-1]["start_ms"] - \
                                annotation["phases"][0]["start_ms"]
            annotation["total_launch_time_ms"] = total_launch_time
            print(
                f"\n总启动耗时: {total_launch_time}ms ({total_launch_time / 1000:.2f}秒)")

        return annotation

    def save_analysis_report(self, turning_points: List[Dict],
                             scenes: List[Dict],
                             annotation: Dict,
                             output_path: str):
        """保存分析报告"""
        report = {
            "video_info": {
                "path": self.video_path,
                "fps": self.fps,
                "total_frames": self.total_frames,
                "duration_ms": self.duration_ms
            },
            "turning_points": turning_points,
            "scenes": scenes,
            "scenario_annotation": annotation,
            "analysis_time": datetime.now().isoformat()
        }

        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n分析报告已保存: {output_path}")

    def close(self):
        """释放资源"""
        if self.cap:
            self.cap.release()


def analyze_video_scenes(video_path: str,
                         output_folder: str = "scene_analysis",
                         threshold: float = 0.3,
                         min_interval_ms: int = 500):
    """
    完整的视频场景分析流程

    :param video_path: 视频路径
    :param output_folder: 输出文件夹
    :param threshold: 转折点检测阈值
    :param min_interval_ms: 最小间隔时间
    """
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    # 创建分析器
    analyzer = SceneAnalyzer(video_path)

    try:
        # 1. 检测转折点
        turning_points = analyzer.detect_turning_points(
            threshold=threshold,
            min_interval_ms=min_interval_ms
        )

        # 2. 识别场景
        scenes = analyzer.identify_scenes(turning_points)

        # 3. 提取关键帧
        analyzer.extract_scene_keyframes(scenes, output_folder / "keyframes")

        # 4. 场景标注（APP启动场景）
        annotation = analyzer.annotate_app_launch_scenario(scenes)

        # 5. 保存报告
        analyzer.save_analysis_report(
            turning_points,
            scenes,
            annotation,
            output_folder / "analysis_report.json"
        )

        print(f"\n{'=' * 60}")
        print("✓ 分析完成！")
        print(f"  输出目录: {output_folder}")
        print(f"  转折点数量: {len(turning_points)}")
        print(f"  场景数量: {len(scenes)}")
        print(f"{'=' * 60}")

        return {
            "turning_points": turning_points,
            "scenes": scenes,
            "annotation": annotation
        }

    finally:
        analyzer.close()


# 使用示例
if __name__ == "__main__":
    # 示例1: 分析APP启动视频
    result = analyze_video_scenes(
        video_path="video.mp4",
        output_folder="app_launch_analysis",
        threshold=0.3,  # 差异阈值，越小越敏感
        min_interval_ms=100  # 最小间隔500ms
    )

    # 示例2: 分析模型加载场景
    # result = analyze_video_scenes(
    #     video_path="model_loading.mp4",
    #     output_folder="model_analysis",
    #     threshold=0.25,
    #     min_interval_ms=300
    # )

    # 打印关键信息
    if result:
        print("\n场景摘要:")
        for scene in result["scenes"]:
            print(f"  场景{scene['scene_id']}: {scene['duration_ms']}ms "
                  f"({scene['start_timestamp_ms']}ms - {scene['end_timestamp_ms']}ms)")