#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - DeepSORT 追踪器封装
解决"人在哪、去哪了"的问题
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from deep_sort_realtime.deepsort_tracker import DeepSort


@dataclass
class TrackResult:
    """追踪结果数据类"""
    track_id: int           # 追踪 ID
    bbox: List[float]       # 边界框 [left, top, width, height]
    confidence: float       # 置信度
    class_id: int           # 类别 ID
    class_name: str         # 类别名称
    frame_id: int           # 帧号
    timestamp: float        # 时间戳（秒）


class MultiObjectTracker:
    """
    多目标追踪器
    
    基于 DeepSORT 实现，支持：
    - 目标 ID 持久化追踪
    - 跨帧轨迹关联
    - Re-ID 特征匹配
    """
    
    # COCO 类别名称
    COCO_CLASSES = [
        'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
        'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
        'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
        'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
        'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
        'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
        'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
        'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
        'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
        'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
        'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
        'toothbrush'
    ]
    
    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
        max_cosine_distance: float = 0.2,
        nn_budget: Optional[int] = None
    ):
        """
        初始化追踪器
        
        Args:
            max_age: 最大丢失帧数，超过则删除轨迹
            min_hits: 最小命中次数，确认轨迹
            iou_threshold: IOU 匹配阈值
            max_cosine_distance: Re-ID 特征最大余弦距离
            nn_budget: 最近邻特征预算
        """
        self.tracker = DeepSort(
            max_age=max_age,
            n_init=min_hits,  # DeepSort uses n_init instead of min_hits
            max_iou_distance=iou_threshold,  # DeepSort uses max_iou_distance
            max_cosine_distance=max_cosine_distance,
            nn_budget=nn_budget
        )
        self.frame_count = 0
        
    def update(
        self,
        detections: List[Tuple[List[float], float, int]],
        frame: np.ndarray,
        fps: float = 30.0
    ) -> List[TrackResult]:
        """
        更新追踪器
        
        Args:
            detections: 检测结果列表 [(bbox, confidence, class_id), ...]
                        bbox 格式: [left, top, width, height]
            frame: 当前帧图像
            fps: 视频帧率
            
        Returns:
            追踪结果列表
        """
        self.frame_count += 1
        timestamp = self.frame_count / fps
        
        # 转换为 DeepSORT 格式
        # DeepSORT 需要: [[left, top, w, h], confidence, class_id]
        ds_detections = []
        for bbox, conf, cls_id in detections:
            ds_detections.append([bbox, conf, cls_id])
        
        # 更新追踪
        tracks = self.tracker.update_tracks(ds_detections, frame=frame)
        
        # 解析结果
        results = []
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            track_id = track.track_id
            bbox = track.to_ltwh()  # [left, top, width, height]
            class_id = track.det_conf if hasattr(track, 'det_conf') else 0
            
            result = TrackResult(
                track_id=track_id,
                bbox=bbox,
                confidence=track.det_conf if hasattr(track, 'det_conf') else 1.0,
                class_id=int(class_id) if class_id else 0,
                class_name=self.COCO_CLASSES[int(class_id)] if class_id and int(class_id) < len(self.COCO_CLASSES) else "unknown",
                frame_id=self.frame_count,
                timestamp=timestamp
            )
            results.append(result)
        
        return results
    
    def reset(self):
        """重置追踪器"""
        self.tracker = DeepSort()
        self.frame_count = 0


def create_tracker(config: dict) -> MultiObjectTracker:
    """
    工厂函数：创建追踪器实例
    
    Args:
        config: 配置字典
        
    Returns:
        MultiObjectTracker 实例
    """
    tracking_config = config.get('tracking', {})
    return MultiObjectTracker(
        max_age=tracking_config.get('max_age', 30),
        min_hits=tracking_config.get('min_hits', 3),
        iou_threshold=tracking_config.get('iou_threshold', 0.3),
        max_cosine_distance=tracking_config.get('max_cosine_distance', 0.2),
        nn_budget=tracking_config.get('nn_budget', None)
    )