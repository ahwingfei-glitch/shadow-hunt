#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - 视频处理流水线 (安全修复版)
整合检测 + 追踪 + 语义分析
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass, asdict
import numpy as np
import av

from .detector import HybridDetector, DetectionResult, create_detector
from .tracker import MultiObjectTracker, TrackResult, create_tracker
from ..utils.security import safe_path, get_db_connection


@dataclass
class VideoMetadata:
    """视频元数据"""
    video_id: int
    case_id: int
    filename: str
    filepath: str
    sha256_hash: str
    duration: float
    fps: float
    resolution: str
    file_size: int
    status: str = "pending"


@dataclass
class ProcessedFrame:
    """处理后的帧数据"""
    frame_id: int
    timestamp: float
    tracks: List[Dict[str, Any]]
    detections: List[Dict[str, Any]]


class VideoProcessor:
    """
    视频处理器（安全修复版）
    
    处理流程：
    1. 视频解码
    2. 目标检测
    3. 多目标追踪
    4. 语义检测
    5. 批量入库
    """
    
    def __init__(self, config: dict, db_path: str):
        """
        初始化视频处理器
        
        Args:
            config: 配置字典
            db_path: 数据库路径
        """
        self.config = config
        self.db_path = db_path
        self.data_dir = Path(config['paths']['data'])
        
        # 初始化检测器和追踪器
        self.detector = create_detector(config)
        self.tracker = create_tracker(config)
        
        # 语义检测提示词
        self.semantic_prompts = [
            "person holding phone",
            "person running",
            "person carrying object"
        ]
    
    def calculate_hash(self, filepath: str) -> str:
        """计算文件 SHA-256 哈希"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def get_video_info(self, filepath: str) -> Dict[str, Any]:
        """获取视频信息"""
        container = av.open(filepath)
        stream = container.streams.video[0]
        
        duration = float(stream.duration * stream.time_base) if stream.duration else 0
        fps = float(stream.average_rate) if stream.average_rate else 30.0
        width = stream.width
        height = stream.height
        file_size = os.path.getsize(filepath)
        
        container.close()
        
        return {
            'duration': duration,
            'fps': fps,
            'resolution': f"{width}x{height}",
            'file_size': file_size
        }
    
    def process_video(
        self,
        filepath: str,
        case_id: int,
        semantic_prompts: Optional[List[str]] = None
    ) -> Generator[ProcessedFrame, None, VideoMetadata]:
        """
        处理视频（安全修复版）
        
        Args:
            filepath: 视频文件路径（已校验）
            case_id: 案件 ID
            semantic_prompts: 语义检测提示词列表
            
        Yields:
            ProcessedFrame 每帧处理结果
        """
        if semantic_prompts:
            self.semantic_prompts = semantic_prompts
        
        # 获取视频信息
        video_info = self.get_video_info(filepath)
        sha256_hash = self.calculate_hash(filepath)
        
        # 创建视频记录
        video_id = self._create_video_record(
            filepath=filepath,
            case_id=case_id,
            sha256_hash=sha256_hash,
            video_info=video_info
        )
        
        # 重置追踪器
        self.tracker.reset()
        
        # 打开视频
        container = av.open(filepath)
        stream = container.streams.video[0]
        fps = video_info['fps']
        
        frame_id = 0
        track_buffer = []  # 批量缓冲
        
        try:
            # 处理每一帧
            for frame in container.decode(video=0):
                frame_id += 1
                
                # 转换为 numpy 数组 (BGR)
                img = frame.to_ndarray(format='bgr24')
                timestamp = frame_id / fps
                
                # 1. 目标检测
                detections = self.detector.detect_objects(img)
                
                # 2. 多目标追踪
                tracker_detections = self.detector.get_tracker_detections(img)
                tracks = self.tracker.update(tracker_detections, img, fps)
                
                # 3. 语义检测（每 30 帧执行一次）
                semantic_results = {}
                if frame_id % 30 == 0 and self.semantic_prompts:
                    for prompt in self.semantic_prompts:
                        sem_dets = self.detector.detect_semantic(img, prompt)
                        if sem_dets:
                            semantic_results[prompt] = [asdict(d) for d in sem_dets]
                
                # 构建结果
                processed = ProcessedFrame(
                    frame_id=frame_id,
                    timestamp=timestamp,
                    tracks=[asdict(t) for t in tracks],
                    detections=[asdict(d) for d in detections]
                )
                
                # 收集轨迹数据用于批量插入
                for track in tracks:
                    track_buffer.append({
                        'video_id': video_id,
                        'track_id': track.track_id,
                        'frame_id': frame_id,
                        'timestamp': timestamp,
                        'bbox': track.bbox
                    })
                
                # 每 100 帧批量写入一次
                if len(track_buffer) >= 100:
                    self._save_tracks_batch(track_buffer)
                    track_buffer = []
                
                yield processed
            
        finally:
            container.close()
            
            # 写入剩余数据
            if track_buffer:
                self._save_tracks_batch(track_buffer)
        
        # 更新视频状态
        self._update_video_status(video_id, "completed")
        
        # 返回元数据
        return VideoMetadata(
            video_id=video_id,
            case_id=case_id,
            filename=os.path.basename(filepath),
            filepath=filepath,
            sha256_hash=sha256_hash,
            **video_info,
            status="completed"
        )
    
    def _create_video_record(
        self,
        filepath: str,
        case_id: int,
        sha256_hash: str,
        video_info: Dict[str, Any]
    ) -> int:
        """创建视频记录（使用上下文管理器）"""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO videos (case_id, filename, filepath, sha256_hash, duration, fps, resolution, file_size, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'processing')
            """, (
                case_id,
                os.path.basename(filepath),
                filepath,
                sha256_hash,
                video_info['duration'],
                video_info['fps'],
                video_info['resolution'],
                video_info['file_size']
            ))
            
            video_id = cursor.lastrowid
            conn.commit()
        
        return video_id
    
    def _save_tracks_batch(self, tracks: List[Dict[str, Any]]):
        """
        批量保存轨迹（性能优化）
        
        Args:
            tracks: 轨迹数据列表
        """
        if not tracks:
            return
        
        # 准备批量数据
        track_data = [
            (
                t['video_id'],
                1,  # case_id
                t['track_id'],
                t['frame_id'],
                t['frame_id'],
                t['timestamp'],
                t['timestamp'],
                json.dumps([t['bbox']])
            )
            for t in tracks
        ]
        
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO tracks 
                (video_id, case_id, track_id, start_frame, end_frame, start_time, end_time, bbox_trajectory)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, track_data)
            conn.commit()
    
    def _update_video_status(self, video_id: int, status: str):
        """更新视频状态（使用上下文管理器）"""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE videos SET status = ?, processed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, video_id)
            )
            conn.commit()


def create_video_processor(config: dict, db_path: str) -> VideoProcessor:
    """工厂函数：创建视频处理器"""
    return VideoProcessor(config, db_path)