import cv2
import numpy as np
import os
import time
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import json


class VideoSceneAnalyzer:
    """视频场景分析器：提取关键帧、检测场景变化、标注转折点"""

    def __init__(self, video_path: str, output_dir: str = "output"):
        """
        初始化视频分析器

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
        """
        self.video_path = video_path
        self.output_dir = output_dir
        self.cap = None
        self.fps = 0
        self.frame_count = 0
        self.duration = 0
        self.frame_width = 0
        self.frame_height = 0

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "frames"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "key_frames"), exist_ok=True)

        # 初始化视频信息
        self._init_video_info()

    def _init_video_info(self):
        """初始化视频基本信息"""
        self.cap = cv2.VideoCapture(self.video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.frame_count / self.fps if self.fps > 0 else 0

        print(f"视频信息:")
        print(f"  文件: {os.path.basename(self.video_path)}")
        print(f"  帧率: {self.fps:.2f} fps")
        print(f"  总帧数: {self.frame_count}")
        print(f"  分辨率: {self.frame_width}x{self.frame_height}")
        print(f"  时长: {timedelta(seconds=self.duration)}")

    def extract_frames(self, interval: int = 1, max_frames: int = 1000) -> \
    List[np.ndarray]:
        """
        按固定间隔提取视频帧

        Args:
            interval: 提取间隔（帧数）
            max_frames: 最大提取帧数

        Returns:
            帧图像列表
        """
        print(f"\n开始提取视频帧，间隔: {interval}帧...")
        frames = []
        frame_indices = []

        for i in range(0, min(self.frame_count, max_frames * interval),
                       interval):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = self.cap.read()
            if ret:
                frames.append(frame)
                frame_indices.append(i)

                # 保存帧图片
                frame_filename = os.path.join(
                    self.output_dir, "frames",
                    f"frame_{i:06d}_{i / self.fps:.2f}s.jpg"
                )
                cv2.imwrite(frame_filename, frame)

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        print(f"提取完成，共提取 {len(frames)} 帧")
        return frames, frame_indices

    def calculate_frame_differences(self,
                                    frames: List[np.ndarray]) -> np.ndarray:
        """
        计算帧间差异度

        Args:
            frames: 帧图像列表

        Returns:
            差异度数组
        """
        print("计算帧间差异度...")
        differences = []

        for i in range(1, len(frames)):
            # 转换为灰度图
            gray1 = cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)

            # 计算结构相似性（SSIM）
            diff = cv2.absdiff(gray1, gray2)
            mean_diff = np.mean(diff)

            # 计算直方图差异
            hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
            hist_diff = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CHISQR)

            # 综合差异度
            combined_diff = mean_diff * 0.7 + hist_diff * 0.3
            differences.append(combined_diff)

        return np.array(differences)

    def detect_scene_changes(self, differences: np.ndarray,
                             threshold_ratio: float = 0.1,
                             min_distance: int = 5) -> List[int]:
        """
        检测场景变化点（转折点）

        Args:
            differences: 差异度数组
            threshold_ratio: 阈值比例（相对于最大差异）
            min_distance: 最小峰值距离

        Returns:
            转折点索引列表
        """
        print("检测场景转折点...")

        # 使用峰值检测
        mean_diff = np.mean(differences)
        std_diff = np.std(differences)
        threshold = mean_diff + threshold_ratio * (
                    np.max(differences) - mean_diff)

        # 寻找峰值
        peaks, properties = find_peaks(
            differences,
            height=threshold,
            distance=min_distance,
            prominence=std_diff * 0.5
        )

        # 对差异进行归一化以便可视化
        normalized_diff = (differences - np.min(differences)) / (
                    np.max(differences) - np.min(differences))

        # 绘制差异曲线
        plt.figure(figsize=(15, 6))
        plt.plot(normalized_diff, label='帧间差异', alpha=0.7)
        plt.axhline(y=threshold / np.max(differences), color='r',
                    linestyle='--',
                    label=f'阈值 ({threshold_ratio * 100:.1f}%)')
        plt.scatter(peaks, normalized_diff[peaks], color='red', s=50,
                    label='转折点', zorder=5)
        plt.xlabel('帧索引')
        plt.ylabel('归一化差异度')
        plt.title('帧间差异度与转折点检测')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # 保存差异图
        diff_plot_path = os.path.join(self.output_dir, "frame_differences.png")
        plt.savefig(diff_plot_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"检测到 {len(peaks)} 个场景转折点")
        return list(peaks)

    def extract_key_frames_around_turning_points(self,
                                                 turning_points: List[int],
                                                 frame_indices: List[int],
                                                 frames: List[np.ndarray],
                                                 context_frames: int = 2) -> \
    List[Dict]:
        """
        提取转折点附近的关键帧作为场景首尾

        Args:
            turning_points: 转折点索引
            frame_indices: 原始帧索引
            frames: 帧图像列表
            context_frames: 上下文帧数

        Returns:
            关键帧信息列表
        """
        print("\n提取场景首尾关键帧...")
        key_frames_info = []

        # 添加视频开始作为第一个转折点
        all_points = [0] + turning_points + [len(frames) - 1]

        for i in range(len(all_points) - 1):
            start_idx = max(0, all_points[i] - context_frames)
            end_idx = min(len(frames) - 1, all_points[i + 1] + context_frames)

            # 获取实际帧索引
            start_frame_idx = frame_indices[start_idx]
            end_frame_idx = frame_indices[end_idx]

            # 计算时间
            start_time = start_frame_idx / self.fps
            end_time = end_frame_idx / self.fps
            duration = end_time - start_time

            # 获取帧图像
            start_frame = frames[start_idx]
            end_frame = frames[end_idx]

            # 场景信息
            scene_info = {
                "scene_id": i + 1,
                "start_frame": start_frame_idx,
                "end_frame": end_frame_idx,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "start_frame_path": "",
                "end_frame_path": ""
            }

            # 保存关键帧
            start_filename = os.path.join(
                self.output_dir, "key_frames",
                f"scene_{scene_info['scene_id']:03d}_start_{start_frame_idx:06d}_{start_time:.2f}s.jpg"
            )
            end_filename = os.path.join(
                self.output_dir, "key_frames",
                f"scene_{scene_info['scene_id']:03d}_end_{end_frame_idx:06d}_{end_time:.2f}s.jpg"
            )

            cv2.imwrite(start_filename, start_frame)
            cv2.imwrite(end_filename, end_frame)

            scene_info["start_frame_path"] = start_filename
            scene_info["end_frame_path"] = end_filename

            key_frames_info.append(scene_info)

            print(f"场景 {scene_info['scene_id']}:")
            print(f"  开始: 帧{start_frame_idx} ({start_time:.2f}s)")
            print(f"  结束: 帧{end_frame_idx} ({end_time:.2f}s)")
            print(f"  耗时: {duration:.2f}秒")

        return key_frames_info

    def annotate_specific_scenarios(self, key_frames_info: List[Dict],
                                    scenario_type: str = "app_launch") -> List[
        Dict]:
        """
        标注特定场景（如应用启动、问答交互）

        Args:
            key_frames_info: 关键帧信息
            scenario_type: 场景类型

        Returns:
            标注后的场景信息
        """
        print(f"\n标注特定场景: {scenario_type}")

        annotated_scenes = []

        for scene in key_frames_info:
            if scenario_type == "app_launch":
                # 应用启动场景检测逻辑
                is_app_launch = self._detect_app_launch(scene)
                if is_app_launch:
                    scene["scenario"] = "应用启动"
                    scene["description"] = "检测到应用启动场景"
                    annotated_scenes.append(scene)

            elif scenario_type == "qa_interaction":
                # 问答交互场景检测逻辑
                is_qa = self._detect_qa_interaction(scene)
                if is_qa:
                    scene["scenario"] = "问答交互"
                    scene["description"] = "检测到问答交互场景"
                    annotated_scenes.append(scene)

            elif scenario_type == "all":
                # 通用场景标注
                scene["scenario"] = f"场景_{scene['scene_id']}"
                scene["description"] = "通用场景"
                annotated_scenes.append(scene)

        return annotated_scenes

    def _detect_app_launch(self, scene_info: Dict) -> bool:
        """检测应用启动场景（简化版，实际可能需要图像识别）"""
        # 这里可以实现更复杂的检测逻辑
        # 例如：检测启动画面、加载动画等
        duration = scene_info["duration"]
        # 假设启动时间在0.5-5秒之间
        return 0.5 <= duration <= 5.0

    def _detect_qa_interaction(self, scene_info: Dict) -> bool:
        """检测问答交互场景（简化版）"""
        duration = scene_info["duration"]
        # 假设问答交互时间在2-30秒之间
        return 2.0 <= duration <= 30.0

    def create_summary_report(self, annotated_scenes: List[Dict],
                              output_format: str = "json"):
        """
        创建分析报告

        Args:
            annotated_scenes: 标注的场景信息
            output_format: 输出格式
        """
        print("\n生成分析报告...")

        report_data = {
            "video_info": {
                "path": self.video_path,
                "fps": self.fps,
                "frame_count": self.frame_count,
                "duration": self.duration,
                "resolution": f"{self.frame_width}x{self.frame_height}"
            },
            "analysis_summary": {
                "total_scenes": len(annotated_scenes),
                "total_turning_points": len(annotated_scenes) - 1,
                "average_scene_duration": np.mean(
                    [s["duration"] for s in annotated_scenes]),
                "analysis_time": datetime.now().isoformat()
            },
            "scenes": annotated_scenes
        }

        # 保存报告
        if output_format == "json":
            report_path = os.path.join(self.output_dir, "analysis_report.json")
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

        elif output_format == "txt":
            report_path = os.path.join(self.output_dir, "analysis_report.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("视频场景分析报告\n")
                f.write("=" * 60 + "\n\n")

                f.write(f"视频文件: {report_data['video_info']['path']}\n")
                f.write(f"帧率: {report_data['video_info']['fps']:.2f} fps\n")
                f.write(
                    f"时长: {timedelta(seconds=report_data['video_info']['duration'])}\n")
                f.write(f"分辨率: {report_data['video_info']['resolution']}\n")
                f.write(
                    f"总场景数: {report_data['analysis_summary']['total_scenes']}\n")
                f.write(
                    f"平均场景时长: {report_data['analysis_summary']['average_scene_duration']:.2f}秒\n\n")

                f.write("-" * 60 + "\n")
                f.write("场景详情:\n")
                f.write("-" * 60 + "\n")

                for scene in annotated_scenes:
                    f.write(f"\n场景 {scene['scene_id']}:\n")
                    f.write(f"  类型: {scene.get('scenario', '未标注')}\n")
                    f.write(
                        f"  开始时间: {scene['start_time']:.2f}s (帧{scene['start_frame']})\n")
                    f.write(
                        f"  结束时间: {scene['end_time']:.2f}s (帧{scene['end_frame']})\n")
                    f.write(f"  耗时: {scene['duration']:.2f}秒\n")
                    if 'description' in scene:
                        f.write(f"  描述: {scene['description']}\n")

        print(f"报告已保存至: {report_path}")

        # 生成可视化报告
        self._create_visual_report(annotated_scenes)

    def _create_visual_report(self, scenes: List[Dict]):
        """创建可视化报告"""
        # 场景时间线
        fig, ax = plt.subplots(1, 2, figsize=(16, 6))

        # 场景持续时间条形图
        durations = [s["duration"] for s in scenes]
        scene_ids = [s["scene_id"] for s in scenes]
        scenarios = [s.get("scenario", "未知") for s in scenes]

        colors = plt.cm.Set3(np.linspace(0, 1, len(scenes)))
        bars = ax[0].barh(scene_ids, durations, color=colors)
        ax[0].set_xlabel('持续时间 (秒)')
        ax[0].set_ylabel('场景ID')
        ax[0].set_title('场景持续时间分布')

        # 添加持续时间标签
        for bar, duration in zip(bars, durations):
            width = bar.get_width()
            ax[0].text(width + max(durations) * 0.01,
                       bar.get_y() + bar.get_height() / 2,
                       f'{duration:.2f}s', va='center')

        # 场景时间线图
        time_axis = []
        labels = []
        for i, scene in enumerate(scenes):
            time_axis.append([scene['start_time'], scene['end_time']])
            labels.append(
                f"场景{scene['scene_id']}\n({scene.get('scenario', '未知')})")

        for i, (start_end, label) in enumerate(zip(time_axis, labels)):
            ax[1].plot(start_end, [i, i], linewidth=10, solid_capstyle='butt')
            ax[1].text(start_end[0] - max([t[1] for t in time_axis]) * 0.02, i,
                       f"{start_end[0]:.1f}s", va='center', ha='right')
            ax[1].text(start_end[1] + max([t[1] for t in time_axis]) * 0.02, i,
                       f"{start_end[1]:.1f}s", va='center')

        ax[1].set_yticks(range(len(labels)))
        ax[1].set_yticklabels(labels)
        ax[1].set_xlabel('时间 (秒)')
        ax[1].set_title('场景时间线')
        ax[1].grid(True, alpha=0.3)

        plt.tight_layout()
        timeline_path = os.path.join(self.output_dir, "scene_timeline.png")
        plt.savefig(timeline_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"时间线图已保存至: {timeline_path}")

    def process_video(self,
                      extraction_interval: int = 10,
                      threshold_ratio: float = 0.15,
                      scenario_type: str = "all"):
        """
        完整处理流程

        Args:
            extraction_interval: 帧提取间隔
            threshold_ratio: 转折点检测阈值比例
            scenario_type: 场景类型
        """
        start_time = time.time()

        try:
            # 1. 提取视频帧
            frames, frame_indices = self.extract_frames(
                interval=extraction_interval,
                max_frames=1000
            )

            # 2. 计算帧差异
            differences = self.calculate_frame_differences(frames)

            # 3. 检测场景转折点
            turning_points = self.detect_scene_changes(
                differences,
                threshold_ratio=threshold_ratio,
                min_distance=3
            )

            # 4. 提取场景首尾帧
            key_frames_info = self.extract_key_frames_around_turning_points(
                turning_points,
                frame_indices,
                frames
            )

            # 5. 标注特定场景
            annotated_scenes = self.annotate_specific_scenarios(
                key_frames_info,
                scenario_type=scenario_type
            )

            # 6. 生成报告
            self.create_summary_report(annotated_scenes, output_format="json")
            self.create_summary_report(annotated_scenes, output_format="txt")

            # 7. 显示统计信息
            elapsed_time = time.time() - start_time
            print(f"\n{'=' * 60}")
            print("分析完成!")
            print(f"总耗时: {elapsed_time:.2f}秒")
            print(f"输出目录: {os.path.abspath(self.output_dir)}")
            print(f"{'=' * 60}")

            return annotated_scenes

        finally:
            if self.cap:
                self.cap.release()

    def export_to_csv(self, scenes: List[Dict], csv_path: str = None):
        """导出为CSV格式"""
        if csv_path is None:
            csv_path = os.path.join(self.output_dir, "scene_analysis.csv")

        import csv

        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['场景ID', '场景类型', '开始时间(s)', '结束时间(s)',
                             '耗时(s)', '开始帧', '结束帧', '描述'])

            for scene in scenes:
                writer.writerow([
                    scene['scene_id'],
                    scene.get('scenario', '未知'),
                    f"{scene['start_time']:.3f}",
                    f"{scene['end_time']:.3f}",
                    f"{scene['duration']:.3f}",
                    scene['start_frame'],
                    scene['end_frame'],
                    scene.get('description', '')
                ])

        print(f"CSV文件已导出至: {csv_path}")


# 使用示例
def main():
    # 初始化分析器
    analyzer = VideoSceneAnalyzer(
        video_path="your_video.mp4",  # 替换为你的视频路径
        output_dir="video_analysis_output"
    )

    # 执行完整分析流程
    scenes = analyzer.process_video(
        extraction_interval=15,  # 每15帧提取一帧
        threshold_ratio=0.15,  # 转折点检测阈值
        scenario_type="all"  # 分析所有场景
    )

    # 导出为CSV
    analyzer.export_to_csv(scenes)

    # 单独分析特定场景
    app_launch_scenes = analyzer.annotate_specific_scenarios(
        scenes,
        scenario_type="app_launch"
    )

    qa_scenes = analyzer.annotate_specific_scenarios(
        scenes,
        scenario_type="qa_interaction"
    )

    print(f"\n检测到 {len(app_launch_scenes)} 个应用启动场景")
    print(f"检测到 {len(qa_scenes)} 个问答交互场景")


# 简化的命令行接口
def simple_analyze(video_path: str, output_dir: str = None):
    """简化分析接口"""
    if output_dir is None:
        output_dir = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    analyzer = VideoSceneAnalyzer(video_path, output_dir)
    scenes = analyzer.process_video(
        extraction_interval=10,
        threshold_ratio=0.15
    )
    return scenes


if __name__ == "__main__":
    simple_analyze("video.mp4", "output")