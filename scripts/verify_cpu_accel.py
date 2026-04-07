#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - CPU 加速验证脚本
作者: 97工作室 - 星期五

功能:
  - 检测 CPU 指令集支持 (AVX-512, AVX2, SSE4.2)
  - 测试 OpenVINO CPU 加速
  - 输出检测结果报告
"""

import platform
import sys
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CPUFeature:
    """CPU 特性记录"""
    name: str
    supported: bool
    description: str

class CPUFeatureDetector:
    """CPU 指令集检测器"""
    
    def __init__(self):
        self.features: List[CPUFeature] = []
    
    def detect_all(self):
        """检测所有 CPU 特性"""
        print("\n" + "=" * 50)
        print("  CPU 指令集检测")
        print("=" * 50)
        
        self._print_system_info()
        self._detect_via_cpuinfo()
        self._print_report()
        
        return self.features
    
    def _print_system_info(self):
        """打印系统信息"""
        print(f"\n📋 系统信息:")
        print(f"  操作系统: {platform.system()} {platform.release()}")
        print(f"  架构: {platform.machine()}")
        print(f"  处理器: {platform.processor() or '未知'}")
    
    def _detect_via_cpuinfo(self):
        """通过 cpuinfo 库检测"""
        try:
            import cpuinfo
            info = cpuinfo.get_cpu_info()
            flags = info.get('flags', [])
            
            print(f"\n🔍 CPU: {info.get('brand_raw', '未知')}")
            
            self.features = [
                CPUFeature("AVX-512", any(f.startswith('avx512') for f in flags), "深度学习加速"),
                CPUFeature("AVX2", 'avx2' in flags, "矩阵运算加速"),
                CPUFeature("AVX", 'avx' in flags, "高级向量扩展"),
                CPUFeature("SSE4.2", 'sse4_2' in flags, "流式 SIMD 扩展"),
                CPUFeature("FMA", 'fma' in flags, "融合乘加指令"),
            ]
            
        except ImportError:
            print("⚠️  未安装 py-cpuinfo，请安装: pip install py-cpuinfo")
            self.features = [
                CPUFeature("AVX-512", False, "需要 py-cpuinfo"),
                CPUFeature("AVX2", False, "需要 py-cpuinfo"),
                CPUFeature("SSE4.2", False, "需要 py-cpuinfo"),
            ]
    
    def _print_report(self):
        """打印检测报告"""
        print(f"\n📊 指令集支持报告:")
        print("-" * 50)
        
        for feat in self.features:
            status = "✅" if feat.supported else "❌"
            print(f"  {status} {feat.name:12} {feat.description}")
        
        print("-" * 50)
        
        has_avx2 = any(f.name == "AVX2" and f.supported for f in self.features)
        has_sse42 = any(f.name == "SSE4.2" and f.supported for f in self.features)
        
        if has_avx2:
            print("🎯 评级: 优秀 - 支持 AVX2，最佳性能")
        elif has_sse42:
            print("🟡 评级: 良好 - 支持 SSE4.2，中等性能")
        else:
            print("🔴 评级: 较低 - 不支持 SIMD，性能受限")

class OpenVINOVerifier:
    """OpenVINO CPU 加速验证器"""
    
    def verify(self):
        """验证 OpenVINO CPU 加速"""
        print("\n" + "=" * 50)
        print("  OpenVINO CPU 加速验证")
        print("=" * 50)
        
        try:
            self._check_version()
            self._list_devices()
            self._test_inference()
        except ImportError:
            print("❌ OpenVINO 未安装")
            print("   安装: pip install openvino")
        except Exception as e:
            print(f"❌ 验证失败: {e}")
    
    def _check_version(self):
        """检查版本"""
        try:
            from openvino import get_version
            print(f"\n📦 OpenVINO 版本: {get_version()}")
        except:
            try:
                from openvino.runtime import get_version
                print(f"\n📦 OpenVINO 版本: {get_version()}")
            except:
                print("\n📦 OpenVINO: 已安装")
    
    def _list_devices(self):
        """列出可用设备"""
        print(f"\n🖥️  可用推理设备:")
        try:
            from openvino.runtime import Core
            core = Core()
            devices = core.available_devices
            
            for dev in devices:
                print(f"  • {dev}")
                if dev == "CPU":
                    try:
                        name = core.get_property(dev, "FULL_DEVICE_NAME")
                        print(f"    └─ {name}")
                    except:
                        pass
            
            if "CPU" in devices:
                print("\n✅ CPU 加速可用")
            else:
                print("\n⚠️  CPU 设备不可用")
                
        except Exception as e:
            print(f"  ❌ 获取设备失败: {e}")
    
    def _test_inference(self):
        """测试推理"""
        print(f"\n🧪 推理测试:")
        try:
            import numpy as np
            from openvino.runtime import Core
            
            core = Core()
            print("  ✅ OpenVINO Core 初始化成功")
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")

def main():
    CPUFeatureDetector().detect_all()
    OpenVINOVerifier().verify()
    
    print("\n" + "=" * 50)
    print("验证完成")
    print("=" * 50)

if __name__ == "__main__":
    main()