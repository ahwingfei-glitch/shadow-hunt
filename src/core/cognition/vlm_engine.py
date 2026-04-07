#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - VLM 推理引擎
封装 Ollama VLM 调用，提供动作识别和意图理解功能
"""

import os
import json
import ollama
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.utils.security import sanitize_text_prompt, validate_model_name

os.environ["OLLAMA_HOST"] = os.getenv("OLLAMA_HOST", "http://localhost:11434")


def _extract_json(content: str) -> dict:
    """从响应中提取 JSON"""
    try:
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        return json.loads(content.strip())
    except:
        return {"error": True, "raw": content}


class VLMEngine:
    """VLM 推理引擎 - 封装 Ollama 多模态模型调用"""
    
    def __init__(self, model: str = "qwen3.5:9b", embed_model: str = "nomic-embed-text"):
        self.model = validate_model_name(model)
        self.embed_model = validate_model_name(embed_model)
    
    def recognize_action(self, image_data: bytes, context: Optional[str] = None) -> Dict[str, Any]:
        """动作识别 - 从图像中识别正在进行的动作"""
        prompt = "分析图片中人物的动作。JSON格式返回: {\"action\": \"动作\", \"confidence\": 0-1, \"description\": \"描述\"}"
        if context:
            context = sanitize_text_prompt(context, max_length=500)
            prompt += f"\n上下文: {context}"
        
        try:
            resp = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt, "images": [image_data]}]
            )
            return _extract_json(resp['message']['content'])
        except Exception as e:
            return {"action": "unknown", "confidence": 0.0, "error": True, "message": str(e)}
    
    def understand_intent(self, action_description: str, scene_context: Optional[str] = None) -> Dict[str, Any]:
        """意图理解 - 分析动作背后的意图"""
        action_description = sanitize_text_prompt(action_description, max_length=500)
        
        prompt = f"""分析动作意图:
动作: {action_description}
{f"场景: {scene_context}" if scene_context else ""}
JSON返回: {{"intent": "分类", "risk_level": "low/medium/high", "reason": "理由"}}"""
        
        try:
            resp = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            return _extract_json(resp['message']['content'])
        except Exception as e:
            return {"intent": "unknown", "risk_level": "unknown", "error": True, "message": str(e)}
    
    def embed_text(self, text: str) -> List[float]:
        """文本嵌入"""
        text = sanitize_text_prompt(text, max_length=1000)
        return ollama.embeddings(model=self.embed_model, prompt=text)['embedding']
    
    def batch_analyze(self, descriptions: List[str]) -> List[Dict[str, Any]]:
        """批量分析意图"""
        return [self.understand_intent(d) for d in descriptions]


def create_vlm_engine(config: dict) -> VLMEngine:
    """工厂函数：创建 VLM 引擎实例"""
    vlm = config.get('vlm', {})
    return VLMEngine(
        model=vlm.get('model', 'qwen3.5:9b'),
        embed_model=vlm.get('embed_model', 'nomic-embed-text')
    )