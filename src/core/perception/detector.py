#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - 目标检测器
整合 YOLO + Grounding DINO
"""

import os
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from PIL import Image
import torch

# YOLO
from ultralytics import YOLO

# Grounding DINO
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

from ..utils.security import validate_model_name, sanitize_text_prompt


@dataclass
class DetectionResult:
    """检测结果数据类"""
    bbox: List[float]           # [left, top, width, height]
    confidence: float           # 置信度
    class_id: int               # 类别 ID
    class_name: str             # 类别名称
    label: str                  # 标签（语义检测时使用）


class YOLODetector:
    """
    YOLO 目标检测器
    
    用于检测视频中的物体（人、车等）
    """
    
    # COCO 类别
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
        model_name: str = "yolov8n.pt",
        confidence: float = 0.5,
        iou_threshold: float = 0.45,
        classes: Optional[List[int]] = None
    ):
        """
        初始化 YOLO 检测器
        
        Args:
            model_name: 模型名称 (yolov8n/s/m/l/x.pt)
            confidence: 置信度阈值
            iou_threshold: IOU 阈值
            classes: 只检测指定类别 (None = 全部)
        """
        self.model = YOLO(model_name)
        self.confidence = confidence
        self.iou_threshold = iou_threshold
        self.classes = classes
        
    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        检测目标
        
        Args:
            frame: 图像帧 (BGR 格式)
            
        Returns:
            检测结果列表
        """
        # 运行检测
        results = self.model(
            frame,
            conf=self.confidence,
            iou=self.iou_threshold,
            classes=self.classes,
            verbose=False
        )
        
        # 解析结果
        detections = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                # 获取边界框 [x1, y1, x2, y2]
                xyxy = boxes.xyxy[i].cpu().numpy()
                # 转换为 [left, top, width, height]
                bbox = [
                    float(xyxy[0]),  # left
                    float(xyxy[1]),  # top
                    float(xyxy[2] - xyxy[0]),  # width
                    float(xyxy[3] - xyxy[1])   # height
                ]
                confidence = float(boxes.conf[i].cpu().numpy())
                class_id = int(boxes.cls[i].cpu().numpy())
                class_name = self.COCO_CLASSES[class_id] if class_id < len(self.COCO_CLASSES) else "unknown"
                
                detections.append(DetectionResult(
                    bbox=bbox,
                    confidence=confidence,
                    class_id=class_id,
                    class_name=class_name,
                    label=class_name
                ))
        
        return detections
    
    def get_detections_for_tracker(self, frame: np.ndarray) -> List[Tuple[List[float], float, int]]:
        """
        获取用于 DeepSORT 的检测结果
        
        Args:
            frame: 图像帧
            
        Returns:
            [(bbox, confidence, class_id), ...]
        """
        detections = self.detect(frame)
        return [(d.bbox, d.confidence, d.class_id) for d in detections]


class GroundingDINODetector:
    """
    Grounding DINO 零样本语义检测器
    
    支持自然语言指令，如：
    - "正在打电话的人"
    - "正在撬锁的人"
    - "穿红衣服的人"
    """
    
    def __init__(
        self,
        model_name: str = "IDEA-Research/grounding-dino-base",
        box_threshold: float = 0.35,
        text_threshold: float = 0.25,
        device: str = "cpu"
    ):
        """
        初始化 Grounding DINO
        
        Args:
            model_name: 模型名称
            box_threshold: 边界框阈值
            text_threshold: 文本阈值
            device: 设备 (cpu/cuda)
        """
        # 验证模型名称
        model_name = validate_model_name(model_name)
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(model_name)
        self.model.eval()
        self.box_threshold = box_threshold
        self.text_threshold = text_threshold
        self.device = device
        
        if device == "cuda" and torch.cuda.is_available():
            self.model = self.model.to(device)
    
    def detect(
        self,
        frame: np.ndarray,
        text_prompt: str
    ) -> List[DetectionResult]:
        """
        语义检测
        
        Args:
            frame: 图像帧 (BGR 格式)
            text_prompt: 文本提示词（中英文均可）
            
        Returns:
            检测结果列表
        """
        # 清理并验证文本提示词（最大500字符）
        text_prompt = sanitize_text_prompt(text_prompt, max_length=500)
        
        # BGR -> RGB
        image = Image.fromarray(frame[..., ::-1])
        
        # 预处理
        inputs = self.processor(
            images=image,
            text=text_prompt,
            return_tensors="pt"
        )
        
        if self.device == "cuda" and torch.cuda.is_available():
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # 推理
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # 后处理
        results = self.processor.post_process_grounded_object_detection(
            outputs,
            inputs["input_ids"],
            box_threshold=self.box_threshold,
            text_threshold=self.text_threshold
        )
        
        # 解析结果
        detections = []
        if len(results) > 0:
            boxes = results[0]["boxes"].cpu().numpy()
            scores = results[0]["scores"].cpu().numpy()
            labels = results[0]["labels"]
            
            for i in range(len(boxes)):
                box = boxes[i]  # [x1, y1, x2, y2]
                bbox = [
                    float(box[0]),  # left
                    float(box[1]),  # top
                    float(box[2] - box[0]),  # width
                    float(box[3] - box[1])   # height
                ]
                
                detections.append(DetectionResult(
                    bbox=bbox,
                    confidence=float(scores[i]),
                    class_id=0,
                    class_name=text_prompt,
                    label=labels[i] if i < len(labels) else text_prompt
                ))
        
        return detections


class HybridDetector:
    """
    混合检测器
    
    结合 YOLO（快速检测）和 Grounding DINO（语义检测）
    """
    
    def __init__(self, config: dict):
        """
        初始化混合检测器
        
        Args:
            config: 配置字典
        """
        # YOLO 检测器
        det_config = config.get('detection', {})
        self.yolo = YOLODetector(
            model_name=det_config.get('model', 'yolov8n.pt'),
            confidence=det_config.get('confidence', 0.5),
            iou_threshold=det_config.get('iou_threshold', 0.45),
            classes=det_config.get('classes', None)
        )
        
        # Grounding DINO 检测器
        cog_config = config.get('cognition', {}).get('grounding_dino', {})
        self.grounding_dino = None
        if cog_config.get('enabled', True):
            self.grounding_dino = GroundingDINODetector(
                box_threshold=cog_config.get('box_threshold', 0.35),
                text_threshold=cog_config.get('text_threshold', 0.25)
            )
    
    def detect_objects(self, frame: np.ndarray) -> List[DetectionResult]:
        """快速检测物体（YOLO）"""
        return self.yolo.detect(frame)
    
    def detect_semantic(
        self,
        frame: np.ndarray,
        text_prompt: str
    ) -> List[DetectionResult]:
        """语义检测（Grounding DINO）"""
        if self.grounding_dino is None:
            return []
        return self.grounding_dino.detect(frame, text_prompt)
    
    def get_tracker_detections(self, frame: np.ndarray) -> List[Tuple[List[float], float, int]]:
        """获取用于追踪器的检测结果"""
        return self.yolo.get_detections_for_tracker(frame)


def create_detector(config: dict) -> HybridDetector:
    """工厂函数：创建检测器"""
    return HybridDetector(config)