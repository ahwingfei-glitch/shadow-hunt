#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""集成测试脚本 - 测试感知层 → 认知层 → 报告生成完整流程"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from datetime import datetime


def test_section(name: str):
    """测试分段装饰器"""
    print(f"\n{'='*50}")
    print(f"[{name}]")
    print('='*50)
    return name


def main():
    results = []
    
    # === 第一段：感知层测试 ===
    test_section("感知层测试")
    try:
        from src.core.perception import (
            create_detector, create_tracker, create_video_processor,
            DetectionResult
        )
        print("✓ 感知层模块导入成功")
        
        # 模拟检测结果
        detections = [
            DetectionResult(label="person", confidence=0.92, box=[100, 100, 200, 300], track_id=1),
            DetectionResult(label="person", confidence=0.88, box=[150, 120, 250, 320], track_id=2),
        ]
        print(f"✓ 模拟检测: {len(detections)} 个目标")
        results.append(("感知层", "PASS", "模块导入与数据结构正常"))
    except Exception as e:
        print(f"✗ 感知层测试失败: {e}")
        results.append(("感知层", "FAIL", str(e)))
    
    # === 第二段：认知层测试 ===
    test_section("认知层测试")
    try:
        from src.core.cognition import (
            CognitionEngine, create_cognition_engine,
            VLMEngine, create_vlm_engine,
            ActionAnalyzer, create_action_analyzer
        )
        print("✓ 认知层模块导入成功")
        
        # 测试工厂函数（使用空配置）
        config = {"vlm": {"model": "test"}, "embedder": {"model": "test"}}
        # 不实际创建引擎（需要模型），只验证接口存在
        assert hasattr(CognitionEngine, 'analyze_scene')
        assert hasattr(CognitionEngine, 'search_action')
        assert hasattr(CognitionEngine, 'understand')
        print("✓ CognitionEngine 接口验证通过")
        results.append(("认知层", "PASS", "模块导入与接口验证正常"))
    except Exception as e:
        print(f"✗ 认知层测试失败: {e}")
        results.append(("认知层", "FAIL", str(e)))
    
    # === 第三段：报告生成测试 ===
    test_section("报告生成测试")
    try:
        from src.core.report import (
            ForensicReportGenerator, CaseInfo, DetectionResult as ReportDetection,
            create_report_generator
        )
        print("✓ 报告模块导入成功")
        
        # 创建测试数据
        case = CaseInfo(
            case_id="TEST-2026-001",
            location="测试地点",
            start_time="2026-04-07 10:00:00",
            end_time="2026-04-07 11:00:00",
            description="集成测试案件"
        )
        detections = [
            ReportDetection(label="可疑行为", confidence=0.95, timestamp="10:15:32"),
            ReportDetection(label="入侵检测", confidence=0.87, timestamp="10:23:45"),
        ]
        
        # 生成测试报告
        output_path = Path(__file__).parent.parent / "test_report.pdf"
        generator = create_report_generator()
        pdf_path = generator.generate(case, detections, str(output_path))
        print(f"✓ 报告生成成功: {pdf_path}")
        results.append(("报告生成", "PASS", f"PDF生成于 {pdf_path}"))
    except Exception as e:
        print(f"✗ 报告测试失败: {e}")
        results.append(("报告生成", "FAIL", str(e)))
    
    # === 输出测试报告 ===
    test_section("测试汇总")
    passed = sum(1 for r in results if r[1] == "PASS")
    failed = len(results) - passed
    
    print(f"\n{'模块':<15} {'状态':<8} {'详情'}")
    print("-" * 60)
    for name, status, detail in results:
        icon = "✓" if status == "PASS" else "✗"
        print(f"{name:<15} {icon} {status:<6} {detail}")
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())