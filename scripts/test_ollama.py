#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - Ollama API 测试脚本
验证 Ollama 服务是否正常运行
"""

import os
import sys

# 设置 Ollama 主机
os.environ["OLLAMA_HOST"] = "http://localhost:11434"

def test_ollama_connection():
    """测试 Ollama 连接"""
    import ollama
    
    print("=" * 50)
    print("  Ollama API 连接测试")
    print("=" * 50)
    
    # 列出模型
    try:
        models = ollama.list()
        print(f"\n可用模型数量: {len(models['models'])}")
        print("\n已安装模型:")
        for m in models['models']:
            size_gb = m['size'] / (1024**3)
            print(f"  - {m['name']}: {size_gb:.1f} GB ({m['details']['parameter_size']})")
    except Exception as e:
        print(f"ERROR: 无法连接 Ollama: {e}")
        return False
    
    return True


def test_embedding():
    """测试嵌入模型"""
    import ollama
    
    print("\n" + "=" * 50)
    print("  文本嵌入测试 (nomic-embed-text)")
    print("=" * 50)
    
    try:
        result = ollama.embeddings(
            model="nomic-embed-text",
            prompt="正在奔跑的人"
        )
        embedding = result['embedding']
        print(f"\n嵌入维度: {len(embedding)}")
        print(f"前 5 个值: {embedding[:5]}")
        return True
    except Exception as e:
        print(f"ERROR: 嵌入测试失败: {e}")
        return False


def test_chat():
    """测试聊天模型"""
    import ollama
    
    print("\n" + "=" * 50)
    print("  聊天模型测试 (qwen3.5:9b)")
    print("=" * 50)
    
    try:
        response = ollama.chat(
            model="qwen3.5:9b",
            messages=[
                {"role": "user", "content": "用一句话描述什么是视频分析"}
            ]
        )
        print(f"\n回复: {response['message']['content']}")
        return True
    except Exception as e:
        print(f"ERROR: 聊天测试失败: {e}")
        return False


def main():
    print("\n猎影 (Shadow Hunt) - Ollama 集成测试\n")
    
    results = []
    
    # 测试连接
    results.append(("连接测试", test_ollama_connection()))
    
    # 测试嵌入
    results.append(("嵌入测试", test_embedding()))
    
    # 测试聊天
    results.append(("聊天测试", test_chat()))
    
    # 汇总
    print("\n" + "=" * 50)
    print("  测试结果汇总")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("\nOllama 集成测试全部通过!")
        return 0
    else:
        print("\n部分测试失败，请检查 Ollama 服务")
        return 1


if __name__ == "__main__":
    sys.exit(main())