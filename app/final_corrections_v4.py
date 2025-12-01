# ============================================================
# 文件: app/config.py (修正 - Pydantic Settings 2.0)
# ============================================================
CONFIG_V2 = """
\"\"\"应用配置 - Pydantic Settings 2.0语法\"\"\"

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Set
from functools import lru_cache


class Settings(BaseSettings):
    \"\"\"应用配置\"\"\"
    
    # ⚠️ Pydantic Settings 2.0 使用 model_config 而不是 Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # 忽略.env中的额外字段
    )
    
    # 应用信息
    APP_NAME: str = "video-annotation"
    DEBUG: bool = False
    VERSION: str = "4.0.0"
    
    # 数据库配置
    DATABASE_URL: str
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # MinIO配置
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "video-frames"
    MINIO_SECURE: bool = False
    
    # 上传配置
    UPLOAD_DIR: str = "/tmp/video_uploads"
    MAX_VIDEO_SIZE: int = 500 * 1024 * 1024
    ALLOWED_EXTENSIONS: Set[str] = {".mp4", ".avi", ".mov", ".mkv"}
    
    # 帧提取配置
    FRAME_SAMPLING_RATE: int = 1
    
    # AI配置
    USE_AI_ANALYSIS: bool = False
    ANTHROPIC_API_KEY: str = ""
    AI_ANALYSIS_TIMEOUT: int = 60
    MAX_FRAMES_FOR_AI: int = 10
    
    # 并发配置
    MAX_CONCURRENT_UPLOADS: int = 5
    CELERY_WORKER_CONCURRENCY: int = 3
    
    @property
    def SYNC_DATABASE_URL(self) -> str:
        \"\"\"将异步数据库URL转换为同步URL (供Celery使用)\"\"\"
        url = self.DATABASE_URL
        
        if "postgresql+asyncpg" in url:
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        if "mysql+aiomysql" in url:
            return url.replace("mysql+aiomysql://", "mysql+pymysql://")
        if "sqlite+aiosqlite" in url:
            return url.replace("sqlite+aiosqlite:///", "sqlite:///")
        
        return url


@lru_cache()
def get_settings() -> Settings:
    \"\"\"获取配置单例\"\"\"
    return Settings()


settings = get_settings()
"""

# ============================================================
# 文件: app/services/frame_analyzer.py (修正 - 移除位置权重，全视频识别)
# ============================================================
FRAME_ANALYZER_V3 = """
\"\"\"
帧分析服务 - 全视频范围识别优化版

核心改进:
1. 移除位置权重限制 - 在整个视频中搜索最佳首尾帧
2. 基于内容特征识别 - 不依赖帧的位置
3. 更准确的场景检测 - 适应各种视频长度

场景说明:
- 首帧: 检测从静止/稳定到开始变化的转折点（用户操作触发）
- 尾帧: 检测从变化到完全稳定的转折点（操作完成）
\"\"\"

import logging
import cv2
import numpy as np
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class FrameAnalyzer:
    \"\"\"帧分析器 - 全视频范围智能识别\"\"\"
    
    def __init__(self):
        self.method = "algorithm"
        
        # 参数配置
        self.config = {
            # 场景变化检测
            'scene_change_threshold': 0.2,      # 显著场景变化阈值
            'scene_stable_threshold': 0.05,     # 场景稳定阈值
            
            # 首帧检测参数
            'first_min_change': 0.15,           # 首帧最小变化幅度
            'first_pre_stable_frames': 5,       # 首帧前需要的稳定帧数
            
            # 尾帧检测参数  
            'last_stable_frames': 10,           # 尾帧需要的连续稳定帧数
            'last_max_change': 0.05,            # 尾帧最大变化幅度
            
            # 质量要求
            'min_brightness': 30.0,             # 最低亮度要求
            'min_sharpness': 80.0,              # 最低清晰度要求
        }
    
    def analyze_first_last_frames(
        self, 
        frames_info: List[Dict],
        scene_scores: List[float]
    ) -> Tuple[int, int, float]:
        \"\"\"
        分析并标记首尾帧 - 全视频范围搜索
        
        Returns:
            (first_frame_idx, last_frame_idx, confidence)
        \"\"\"
        if not frames_info or len(frames_info) < 10:
            raise ValueError("帧数太少，无法分析")
        
        logger.info(f"开始全视频分析，总帧数: {len(frames_info)}")
        
        # 1. 寻找首帧 - 从稳定到变化的转折点（全视频搜索）
        first_idx = self._find_transition_start(frames_info, scene_scores)
        
        # 2. 寻找尾帧 - 从变化到稳定的转折点（全视频搜索）
        last_idx = self._find_transition_end(frames_info, scene_scores, first_idx)
        
        # 3. 计算置信度
        confidence = self._calculate_confidence(
            frames_info, 
            first_idx, 
            last_idx,
            scene_scores
        )
        
        logger.info(
            f"识别完成: 首帧={first_idx}/{len(frames_info)} ({first_idx/len(frames_info)*100:.1f}%), "
            f"尾帧={last_idx}/{len(frames_info)} ({last_idx/len(frames_info)*100:.1f}%), "
            f"置信度={confidence:.2%}"
        )
        
        return first_idx, last_idx, confidence
    
    def _find_transition_start(
        self, 
        frames_info: List[Dict], 
        scene_scores: List[float]
    ) -> int:
        \"\"\"
        寻找转场开始点（首帧）- 全视频搜索
        
        策略:
        1. 在整个视频中搜索，不限制搜索范围
        2. 找到从稳定到变化的转折点
        3. 转折点特征：前面几帧稳定（变化小），该帧开始有显著变化
        \"\"\"
        min_change = self.config['first_min_change']
        pre_stable = self.config['first_pre_stable_frames']
        
        candidates = []  # 候选点列表 [(index, score)]
        
        # 遍历整个视频，跳过开头和结尾的极端帧
        start_offset = 2  # 跳过前2帧（录屏开始不稳定）
        end_offset = 10   # 跳过后10帧（为尾帧留空间）
        
        for i in range(start_offset, len(frames_info) - end_offset):
            if i >= len(scene_scores):
                continue
            
            # 检查当前帧是否有显著变化
            current_change = scene_scores[i]
            
            if current_change < min_change:
                continue  # 变化不够显著
            
            # 检查前面的帧是否稳定（低变化）
            pre_stable_count = 0
            for j in range(max(0, i - pre_stable), i):
                if j < len(scene_scores) and scene_scores[j] < self.config['scene_stable_threshold']:
                    pre_stable_count += 1
            
            # 如果前面有足够的稳定帧，这是一个好的转折点
            if pre_stable_count >= min(pre_stable, i):
                # 计算得分：变化幅度 + 前置稳定度
                stability_score = pre_stable_count / pre_stable
                change_score = min(current_change / 0.5, 1.0)  # 归一化到0-1
                
                # 检查帧质量
                frame = frames_info[i]
                quality_score = self._calculate_frame_quality(frame)
                
                # 综合得分
                total_score = change_score * 0.4 + stability_score * 0.3 + quality_score * 0.3
                
                candidates.append((i, total_score))
                logger.debug(
                    f"首帧候选 frame={i}: change={current_change:.3f}, "
                    f"stability={stability_score:.2f}, quality={quality_score:.2f}, "
                    f"total={total_score:.3f}"
                )
        
        # 选择得分最高的候选
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_idx = candidates[0][0]
            logger.info(f"首帧识别成功: frame={best_idx}, score={candidates[0][1]:.3f}, 候选数={len(candidates)}")
            return best_idx
        
        # 如果没有找到合适的候选，使用备用策略
        logger.warning("未找到明显的转场开始点，使用备用策略")
        return self._find_first_frame_fallback(frames_info, scene_scores)
    
    def _find_transition_end(
        self, 
        frames_info: List[Dict], 
        scene_scores: List[float],
        first_idx: int
    ) -> int:
        \"\"\"
        寻找转场结束点（尾帧）- 全视频搜索
        
        策略:
        1. 在首帧之后的整个视频中搜索
        2. 找到从变化到稳定的转折点
        3. 转折点特征：该帧及后续N帧持续稳定（变化小）
        \"\"\"
        stable_count_required = self.config['last_stable_frames']
        max_change = self.config['last_max_change']
        
        candidates = []  # 候选点列表 [(index, score)]
        
        # 从首帧之后开始搜索，跳过结尾的极端帧
        search_start = first_idx + 10  # 至少在首帧10帧之后
        end_offset = 2  # 跳过最后2帧
        
        for i in range(search_start, len(frames_info) - end_offset):
            if i >= len(scene_scores):
                continue
            
            # 检查从该帧开始的连续N帧是否都稳定
            stable_count = 0
            max_change_in_sequence = 0.0
            
            for j in range(i, min(i + stable_count_required, len(scene_scores))):
                if scene_scores[j] <= max_change:
                    stable_count += 1
                    max_change_in_sequence = max(max_change_in_sequence, scene_scores[j])
                else:
                    break  # 遇到不稳定的帧，停止
            
            # 如果找到足够多的连续稳定帧
            if stable_count >= stable_count_required:
                # 检查帧质量
                frame = frames_info[i]
                quality_score = self._calculate_frame_quality(frame)
                
                # 计算得分：稳定度 + 质量
                stability_score = stable_count / stable_count_required
                change_penalty = max_change_in_sequence / max_change  # 变化越小越好
                
                total_score = stability_score * 0.4 + quality_score * 0.4 + (1 - change_penalty) * 0.2
                
                candidates.append((i, total_score))
                logger.debug(
                    f"尾帧候选 frame={i}: stable_count={stable_count}, "
                    f"quality={quality_score:.2f}, total={total_score:.3f}"
                )
        
        # 选择得分最高的候选（如果有多个，选最后一个高分候选）
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            # 在高分候选中选择位置最靠后的（更可能是真正的结束）
            top_score = candidates[0][1]
            top_candidates = [c for c in candidates if c[1] >= top_score * 0.95]  # 得分相近的候选
            
            best_idx = max(top_candidates, key=lambda x: x[0])[0]  # 选位置最靠后的
            logger.info(
                f"尾帧识别成功: frame={best_idx}, score={top_score:.3f}, "
                f"候选数={len(candidates)}, 高分候选={len(top_candidates)}"
            )
            return best_idx
        
        # 如果没有找到合适的候选，使用备用策略
        logger.warning("未找到明显的转场结束点，使用备用策略")
        return self._find_last_frame_fallback(frames_info, scene_scores, first_idx)
    
    def _calculate_frame_quality(self, frame: Dict) -> float:
        \"\"\"
        计算帧的质量分数
        
        Returns:
            0.0-1.0的质量分数
        \"\"\"
        brightness = frame['brightness']
        sharpness = frame['sharpness']
        
        # 亮度分数（40-200范围内最好）
        if brightness < 30:
            brightness_score = 0.0
        elif brightness < 40:
            brightness_score = (brightness - 30) / 10
        elif brightness < 200:
            brightness_score = 1.0
        else:
            brightness_score = max(0.0, 1.0 - (brightness - 200) / 55)
        
        # 清晰度分数（归一化）
        sharpness_score = min(sharpness / 300.0, 1.0)
        
        # 综合质量分数
        quality = brightness_score * 0.4 + sharpness_score * 0.6
        
        return quality
    
    def _find_first_frame_fallback(
        self, 
        frames_info: List[Dict], 
        scene_scores: List[float]
    ) -> int:
        \"\"\"备用策略：找到第一个质量合格的帧\"\"\"
        for i in range(len(frames_info)):
            frame = frames_info[i]
            if (frame['brightness'] > self.config['min_brightness'] and 
                frame['sharpness'] > self.config['min_sharpness']):
                logger.info(f"使用备用策略找到首帧: frame={i}")
                return i
        return 0
    
    def _find_last_frame_fallback(
        self, 
        frames_info: List[Dict], 
        scene_scores: List[float],
        first_idx: int
    ) -> int:
        \"\"\"备用策略：找到首帧之后质量最好的帧\"\"\"
        best_idx = first_idx + 10
        best_quality = 0.0
        
        for i in range(first_idx + 10, len(frames_info) - 2):
            quality = self._calculate_frame_quality(frames_info[i])
            if quality > best_quality:
                best_quality = quality
                best_idx = i
        
        logger.info(f"使用备用策略找到尾帧: frame={best_idx}, quality={best_quality:.2f}")
        return best_idx
    
    def _calculate_confidence(
        self,
        frames_info: List[Dict],
        first_idx: int,
        last_idx: int,
        scene_scores: List[float]
    ) -> float:
        \"\"\"计算识别置信度\"\"\"
        confidence = 0.5  # 基础置信度
        
        # 1. 首帧质量
        first_quality = self._calculate_frame_quality(frames_info[first_idx])
        confidence += first_quality * 0.15
        
        # 2. 首帧是否有明显变化
        if first_idx < len(scene_scores):
            first_change = scene_scores[first_idx]
            if first_change > self.config['first_min_change']:
                confidence += 0.15
        
        # 3. 尾帧质量
        last_quality = self._calculate_frame_quality(frames_info[last_idx])
        confidence += last_quality * 0.15
        
        # 4. 尾帧附近是否稳定
        if last_idx < len(scene_scores) - 5:
            nearby_changes = scene_scores[last_idx:last_idx + 5]
            avg_change = np.mean(nearby_changes)
            if avg_change < self.config['last_max_change']:
                confidence += 0.15
        
        # 5. 首尾帧间隔合理性
        frame_gap = last_idx - first_idx
        if frame_gap > 10:  # 至少有10帧的间隔
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def get_candidate_frames(
        self, 
        frames_info: List[Dict],
        scene_scores: List[float],
        frame_type: str = 'first',
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        \"\"\"
        获取候选帧列表 - 全视频范围搜索
        
        Args:
            frames_info: 帧信息
            scene_scores: 场景分数
            frame_type: 'first' 或 'last'
            top_k: 返回前k个候选
            
        Returns:
            List[(frame_idx, score)]: 候选帧列表
        \"\"\"
        candidates = []
        
        if frame_type == 'first':
            # 首帧候选：全视频搜索有显著变化的点
            for i in range(2, len(frames_info) - 10):
                if i >= len(scene_scores):
                    continue
                
                # 检查场景变化
                change_score = scene_scores[i] if i < len(scene_scores) else 0
                if change_score < self.config['first_min_change']:
                    continue
                
                # 计算质量
                quality = self._calculate_frame_quality(frames_info[i])
                
                # 综合得分
                score = change_score * 0.6 + quality * 0.4
                candidates.append((i, score))
        
        else:  # last
            # 尾帧候选：全视频搜索稳定的点
            for i in range(10, len(frames_info) - 2):
                if i >= len(scene_scores):
                    continue
                
                # 检查稳定性（当前及后续几帧）
                stable_count = 0
                for j in range(i, min(i + 5, len(scene_scores))):
                    if scene_scores[j] < self.config['last_max_change']:
                        stable_count += 1
                
                if stable_count < 3:
                    continue
                
                # 计算质量
                quality = self._calculate_frame_quality(frames_info[i])
                
                # 综合得分
                stability_score = stable_count / 5
                score = stability_score * 0.5 + quality * 0.5
                candidates.append((i, score))
        
        # 排序并返回top_k
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]
"""

# ============================================================
# 配置对比说明
# ============================================================
CONFIG_COMPARISON = """
# ============================================================
# Pydantic Settings 2.0 配置语法对比
# ============================================================

# ❌ 错误写法 (会报错)
class Settings(BaseSettings):
    APP_NAME: str = "my-app"
    
    class Config:  # ❌ Pydantic Settings 2.0 不再支持
        env_file = ".env"

# ✅ 正确写法 (Pydantic Settings 2.0)
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    APP_NAME: str = "my-app"

# ============================================================
# 常用 SettingsConfigDict 参数
# ============================================================

model_config = SettingsConfigDict(
    # 环境变量文件
    env_file=".env",                    # 从.env文件读取
    env_file_encoding="utf-8",          # 文件编码
    
    # 字段配置
    case_sensitive=True,                # 区分大小写
    extra="ignore",                     # 忽略额外字段（推荐）
    # extra="allow",                    # 允许额外字段
    # extra="forbid",                   # 禁止额外字段
    
    # 环境变量前缀
    env_prefix="APP_",                  # 环境变量前缀，如 APP_NAME
    
    # 嵌套配置
    env_nested_delimiter="__",          # 嵌套分隔符，如 DB__HOST
    
    # JSON模式
    json_schema_extra={                 # 额外的JSON Schema信息
        "example": {"APP_NAME": "demo"}
    }
)
"""

print("=" * 60)
print("✅ v4.0 最终修正完成")
print("=" * 60)
print("\n核心修正:")
print("1. ✅ Pydantic Settings 2.0 - 使用 SettingsConfigDict")
print("2. ✅ 移除位置权重 - 全视频范围搜索首尾帧")
print("\n优化详情:")
print("📍 首帧识别: 在整个视频中找从稳定到变化的转折点")
print("📍 尾帧识别: 在整个视频中找从变化到稳定的转折点")
print("📍 不再限制搜索范围，适应任意长度视频")
print("📍 基于内容特征识别，而非位置权重")
