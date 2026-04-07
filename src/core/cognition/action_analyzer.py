#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""猎影 - 动作分析器: 分析轨迹动作类型、风险等级、动作标签"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.cognition.vlm_engine import VLMEngine
from core.cognition.semantic_search import TextEmbedder, SemanticIndex
from core.utils.security import sanitize_text_prompt

@dataclass
class ActionResult:
    """动作分析结果"""
    action_type: str
    risk_level: str  # low/medium/high
    tags: List[str]
    confidence: float
    intent: Optional[str] = None

class ActionAnalyzer:
    """动作分析器 - VLM + FAISS"""
    RISK_KEYWORDS = {"high": ["打架", "持刀", "奔跑", "翻越", "攀爬", "偷窃"],
                     "medium": ["徘徊", "窥视", "尾随", "聚集"], "low": ["行走", "站立", "坐下"]}

    def __init__(self, vlm_engine: VLMEngine):
        self.vlm, self.embedder, self.action_index = vlm_engine, TextEmbedder(), SemanticIndex()
        self._init_templates()

    def _init_templates(self):
        """初始化动作模板"""
        templates = [("行走","low"),("奔跑","high"),("站立","low"),("坐下","low"),("交谈","low"),
                     ("徘徊","medium"),("窥视","medium"),("攀爬","high"),("打架","high"),("偷窃","high")]
        for action, risk in templates:
            self.action_index.add(self.embedder.embed(action), {"action": action, "risk": risk})

    def analyze(self, track: Dict[str, Any], context: Optional[str] = None) -> ActionResult:
        """分析轨迹动作"""
        if context:
            context = sanitize_text_prompt(context, max_length=500)
        desc = f"{track.get('class_name','人')}以{track.get('avg_speed',0):.1f}速度移动"
        intent_result = self.vlm.understand_intent(desc, context)
        similar = self._match_action(desc)
        return ActionResult(action_type=similar.get("action","unknown"),
            risk_level=self._assess_risk(intent_result, similar),
            tags=self._gen_tags(intent_result, similar),
            confidence=intent_result.get("confidence",0.8), intent=intent_result.get("intent"))

    def _match_action(self, desc: str) -> Dict[str, Any]:
        """FAISS 匹配相似动作"""
        results = self.action_index.search(self.embedder.embed(desc), k=1)
        return self.action_index.metadata[results[0][0]] if results else {"action":"unknown","risk":"low"}

    def _assess_risk(self, intent: Dict, similar: Dict) -> str:
        """评估风险等级"""
        order = {"low":0,"medium":1,"high":2}
        return max([intent.get("risk_level","low"),similar.get("risk","low")], key=lambda r: order.get(r,0))

    def _gen_tags(self, intent: Dict, similar: Dict) -> List[str]:
        """生成动作标签"""
        tags = [similar.get("action","未分类")]
        if intent.get("intent"): tags.append(intent["intent"])
        if intent.get("risk_level")=="high": tags.append("需关注")
        elif intent.get("risk_level")=="medium": tags.append("可疑")
        return list(set(tags))[:5]

    def batch_analyze(self, tracks: List[Dict]) -> List[ActionResult]:
        return [self.analyze(t) for t in tracks]

def create_action_analyzer(config: dict) -> ActionAnalyzer:
    """工厂函数"""
    from core.cognition.vlm_engine import create_vlm_engine
    return ActionAnalyzer(create_vlm_engine(config))