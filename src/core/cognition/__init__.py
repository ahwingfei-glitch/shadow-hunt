#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""猎影 (Shadow Hunt) - 认知层入口模块"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

# 导入组件
from .semantic_search import (
    SearchResult, TextEmbedder, SemanticIndex,
    SemanticSearcher, create_semantic_searcher
)
from .vlm_engine import VLMEngine, create_vlm_engine
from .action_analyzer import (
    ActionResult, ActionAnalyzer, create_action_analyzer
)
from ..utils.security import sanitize_text_prompt


@dataclass
class CognitionEngine:
    """认知引擎 - 整合 VLM、语义搜索、动作分析"""
    vlm: VLMEngine
    searcher: SemanticSearcher
    action_analyzer: ActionAnalyzer

    def analyze_scene(self, tracks: List[Dict], context: str = None) -> List[ActionResult]:
        """批量分析轨迹动作"""
        if context:
            context = sanitize_text_prompt(context, max_length=500)
        return self.action_analyzer.batch_analyze(tracks)

    def search_action(self, query: str, k: int = 10) -> List[SearchResult]:
        """语义搜索动作"""
        query = sanitize_text_prompt(query, max_length=500)
        return self.searcher.search(query, k)

    def understand(self, action: str, context: str = None) -> Dict[str, Any]:
        """理解动作意图"""
        action = sanitize_text_prompt(action, max_length=500)
        if context:
            context = sanitize_text_prompt(context, max_length=500)
        return self.vlm.understand_intent(action, context)


def create_cognition_engine(config: Dict[str, Any]) -> CognitionEngine:
    """工厂函数：创建认知引擎实例"""
    return CognitionEngine(
        vlm=create_vlm_engine(config),
        searcher=create_semantic_searcher(config),
        action_analyzer=create_action_analyzer(config)
    )


__all__ = [
    'CognitionEngine', 'create_cognition_engine',
    'VLMEngine', 'create_vlm_engine',
    'SemanticSearcher', 'TextEmbedder', 'SemanticIndex',
    'SearchResult', 'create_semantic_searcher',
    'ActionAnalyzer', 'ActionResult', 'create_action_analyzer'
]