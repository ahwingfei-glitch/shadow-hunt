#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - 语义检索模块
Ollama + FAISS 实现动作/语义搜索
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import faiss
import ollama

# 安全工具
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.utils.security import sanitize_text_prompt

# 设置 Ollama 主机
os.environ["OLLAMA_HOST"] = "http://localhost:11434"


@dataclass
class SearchResult:
    """搜索结果"""
    track_id: int
    video_id: int
    score: float
    tag_value: str
    frame_start: int
    frame_end: int
    confidence: float


class TextEmbedder:
    """
    文本嵌入器

    使用 Ollama nomic-embed-text 模型
    输出维度: 768
    """

    def __init__(self, model: str = "nomic-embed-text"):
        """
        初始化嵌入器

        Args:
            model: 嵌入模型名称
        """
        self.model = model
        self.dimension = 768  # nomic-embed-text 输出维度

    def embed(self, text: str) -> np.ndarray:
        """
        生成文本嵌入向量

        Args:
            text: 输入文本

        Returns:
            嵌入向量 (768,)
        """
        response = ollama.embeddings(
            model=self.model,
            prompt=text
        )
        return np.array(response['embedding'], dtype=np.float32)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        批量生成嵌入向量

        Args:
            texts: 文本列表

        Returns:
            嵌入矩阵 (N, 768)
        """
        embeddings = []
        for text in texts:
            emb = self.embed(text)
            embeddings.append(emb)
        return np.array(embeddings, dtype=np.float32)


class SemanticIndex:
    """
    语义索引

    使用 FAISS 构建向量索引,支持快速相似度搜索
    """

    def __init__(self, dimension: int = 768):
        """
        初始化索引

        Args:
            dimension: 向量维度
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata: List[Dict[str, Any]] = []

    def add(self, vector: np.ndarray, metadata: Dict[str, Any]):
        """
        添加向量

        Args:
            vector: 嵌入向量 (768,)
            metadata: 元数据
        """
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)
        self.index.add(vector)
        self.metadata.append(metadata)

    def add_batch(self, vectors: np.ndarray, metadata_list: List[Dict[str, Any]]):
        """
        批量添加向量

        Args:
            vectors: 嵌入矩阵 (N, 768)
            metadata_list: 元数据列表
        """
        self.index.add(vectors)
        self.metadata.extend(metadata_list)

    def search(self, query: np.ndarray, k: int = 10) -> List[Tuple[int, float]]:
        """
        搜索最相似的向量

        Args:
            query: 查询向量
            k: 返回数量

        Returns:
            [(索引, 距离), ...]
        """
        if query.ndim == 1:
            query = query.reshape(1, -1)

        distances, indices = self.index.search(query, k)

        results = []
        for i, d in zip(indices[0], distances[0]):
            if i < len(self.metadata):
                results.append((int(i), float(d)))

        return results

    def save(self, filepath: str):
        """保存索引"""
        faiss.write_index(self.index, filepath)
        with open(filepath + '.meta', 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def load(self, filepath: str):
        """加载索引"""
        self.index = faiss.read_index(filepath)
        with open(filepath + '.meta', 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)


class SemanticSearcher:
    """
    语义搜索器

    整合文本嵌入和向量检索
    支持动作/语义搜索:"正在奔跑的人"、"正在打电话的人"
    """

    def __init__(self, config: dict):
        """
        初始化搜索器

        Args:
            config: 配置字典
        """
        text_emb_config = config.get('text_embedding', {})
        self.embedder = TextEmbedder(
            model=text_emb_config.get('model', 'nomic-embed-text')
        )
        self.index = SemanticIndex(
            dimension=text_emb_config.get('dimension', 768)
        )

    def index_tracks(
        self,
        tracks: List[Dict[str, Any]],
        descriptions: Optional[List[str]] = None
    ):
        """
        索引轨迹数据

        Args:
            tracks: 轨迹列表
            descriptions: 描述文本列表(可选)
        """
        if descriptions is None:
            # 生成默认描述
            descriptions = [
                f"Track {t['track_id']}: {t.get('class_name', 'unknown')} moving in video"
                for t in tracks
            ]

        # 生成嵌入
        vectors = self.embedder.embed_batch(descriptions)

        # 添加到索引
        metadata_list = []
        for i, track in enumerate(tracks):
            metadata_list.append({
                'track_id': track['track_id'],
                'video_id': track.get('video_id', 0),
                'description': descriptions[i],
                'bbox': track.get('bbox', []),
                'start_time': track.get('start_time', 0),
                'end_time': track.get('end_time', 0)
            })

        self.index.add_batch(vectors, metadata_list)

    def search(
        self,
        query: str,
        k: int = 10
    ) -> List[SearchResult]:
        """
        语义搜索

        Args:
            query: 搜索查询(如"正在奔跑的人")
            k: 返回数量

        Returns:
            搜索结果列表
        """
        # 清理并验证查询
        query = sanitize_text_prompt(query, max_length=500)

        # 生成查询向量
        query_vector = self.embedder.embed(query)

        # 搜索
        results = self.index.search(query_vector, k)

        # 构建结果
        search_results = []
        for idx, distance in results:
            meta = self.index.metadata[idx]
            search_results.append(SearchResult(
                track_id=meta['track_id'],
                video_id=meta['video_id'],
                score=1.0 / (1.0 + distance),  # 转换为相似度分数
                tag_value=meta['description'],
                frame_start=int(meta.get('start_time', 0) * 30),  # 假设 30fps
                frame_end=int(meta.get('end_time', 0) * 30),
                confidence=meta.get('confidence', 1.0)
            ))

        return search_results

    def search_by_action(
        self,
        action: str,
        tracks: List[Dict[str, Any]]
    ) -> List[SearchResult]:
        """
        按动作搜索

        Args:
            action: 动作描述(如"打电话"、"奔跑")
            tracks: 轨迹列表

        Returns:
            匹配结果
        """
        # 构建查询
        query = f"正在{action}的人"

        # 如果索引为空,先建立索引
        if len(self.index.metadata) == 0:
            self.index_tracks(tracks)

        return self.search(query, k=len(tracks))


class ActionAnalyzer:
    """
    动作分析器

    使用 Ollama LLM 分析动作意图
    """

    def __init__(self, model: str = "qwen3.5:9b"):
        """
        初始化分析器

        Args:
            model: LLM 模型名称
        """
        self.model = model

    def analyze_action(
        self,
        description: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析动作

        Args:
            description: 动作描述
            context: 上下文

        Returns:
            分析结果
        """
        # 输入校验
        if len(description) > 500:
            raise ValueError(f"Description too long: {len(description)} > 500")

        prompt = f"""分析以下视频场景描述，判断人物的动作和意图。

描述:{description}

请以 JSON 格式返回:
{{
    "action": "动作类型",
    "intent": "意图",
    "risk_level": "风险等级 (low/medium/high)",
    "keywords": ["关键词1", "关键词2"]
}}
"""

        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            # 尝试解析 JSON
            content = response['message']['content']
            # 提取 JSON 部分
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]

            return json.loads(content.strip())
        except:
            return {
                "action": "unknown",
                "intent": "unknown",
                "risk_level": "unknown",
                "keywords": [],
                "raw_response": response['message']['content']
            }

    def describe_scene(
        self,
        tracks: List[Dict[str, Any]],
        detections: List[Dict[str, Any]]
    ) -> str:
        """
        描述场景

        Args:
            tracks: 轨迹数据
            detections: 检测数据

        Returns:
            场景描述
        """
        prompt = f"""描述以下视频帧的场景:

追踪目标数:{len(tracks)}
检测目标数:{len(detections)}

追踪详情:{json.dumps(tracks[:5], ensure_ascii=False)}
检测详情:{json.dumps(detections[:5], ensure_ascii=False)}

请用简洁的中文描述场景中正在发生的事情。
"""

        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        return response['message']['content']


def create_semantic_searcher(config: dict) -> SemanticSearcher:
    """工厂函数:创建语义搜索器"""
    return SemanticSearcher(config)