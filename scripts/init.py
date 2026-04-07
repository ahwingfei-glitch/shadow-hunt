#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - 环境初始化脚本
作者: 97工作室 - 班纳
版本: 1.0.0

功能:
  - 克隆必要开源库
  - 安装 pip 依赖
  - 生成配置文件模板
"""

import os
import sys
import subprocess
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

# ============================================================================
# 配置区
# ============================================================================

PROJECT_ROOT = Path(r"D:\Project_ShadowHunt")
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
LIBS_DIR = PROJECT_ROOT / "libs"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "output"

# 开源库配置
REPOS = {
    "supervision": {
        "url": "https://github.com/roboflow/supervision.git",
        "path": LIBS_DIR / "supervision",
        "description": "Roboflow 计算机视觉工具库",
    },
    "deep_sort": {
        "url": "https://github.com/nwojke/deep_sort.git",
        "path": LIBS_DIR / "deep_sort",
        "description": "DeepSORT 目标追踪算法",
    },
}

# pip 依赖 (核心库，init.py 只安装基础依赖，完整依赖用 requirements.txt)
PIP_DEPENDENCIES = [
    # 核心依赖
    "numpy>=1.24.0",
    "opencv-contrib-python>=4.9.0",
    "pyav>=12.0.5",
    "pillow>=10.0.0",
    
    # 机器学习
    "torch>=2.0.0",
    "torchvision>=0.15.0",
    "ultralytics>=8.0.0",
    
    # DeepSORT
    "easydict",
    "scipy",
    "scikit-learn",
    "deep-sort-realtime",
    
    # LLM
    "llama-cpp-python>=0.2.0",
    
    # 异步任务
    "celery>=5.3.0",
    "redis>=5.0.0",
    
    # 向量检索
    "faiss-cpu>=1.7.4",
    
    # 认证
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    
    # PDF 报告
    "reportlab>=4.0.0",
    
    # 工具
    "tqdm",
    "pyyaml",
    "requests",
    "rich",
    "psutil",
    "py-cpuinfo",
]

# ============================================================================
# 日志配置
# ============================================================================

def setup_logging() -> logging.Logger:
    """配置日志记录器"""
    log_format = "%(asctime)s | %(levelname)-8s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"init_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    logger = logging.getLogger("ShadowHunt.Init")
    logger.info(f"日志文件: {log_file}")
    return logger

# ============================================================================
# Git 操作
# ============================================================================

def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    timeout: int = 600,
) -> Tuple[bool, str]:
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"命令超时 ({timeout}秒)"
    except FileNotFoundError:
        return False, f"命令未找到: {cmd[0]}"
    except Exception as e:
        return False, f"执行错误: {e}"

def check_git() -> bool:
    """检查 Git 是否可用"""
    success, _ = run_command(["git", "--version"])
    return success

def clone_repository(name: str, url: str, target_path: Path, description: str) -> bool:
    """克隆 Git 仓库"""
    logger.info(f"📦 {name}: {description}")
    
    if target_path.exists():
        logger.info(f"  ⚠️  已存在: {target_path}")
        git_dir = target_path / ".git"
        if git_dir.exists():
            logger.info(f"  🔄 拉取最新代码...")
            success, output = run_command(["git", "pull"], cwd=target_path)
            if success:
                logger.info(f"  ✓ 更新成功")
            return True
        else:
            logger.warning(f"  ⚠️  目录存在但不是 Git 仓库，跳过")
            return True
    
    logger.info(f"  🔄 克隆中: {url}")
    success, output = run_command(
        ["git", "clone", "--depth", "1", url, str(target_path)],
        timeout=300,
    )
    
    if success:
        logger.info(f"  ✅ 克隆成功")
        return True
    else:
        logger.error(f"  ❌ 克隆失败: {output}")
        return False

def clone_repositories() -> bool:
    """克隆所有仓库"""
    logger.info("=" * 60)
    logger.info("📦 克隆开源库")
    logger.info("=" * 60)
    
    if not check_git():
        logger.error("❌ Git 未安装或不可用")
        logger.info("   下载地址: https://git-scm.com/download/win")
        return False
    
    all_success = True
    for name, config in REPOS.items():
        success = clone_repository(
            name=name,
            url=config["url"],
            target_path=config["path"],
            description=config["description"],
        )
        if not success:
            all_success = False
    
    return all_success

# ============================================================================
# pip 安装
# ============================================================================

def check_pip() -> bool:
    """检查 pip 是否可用"""
    success, _ = run_command([sys.executable, "-m", "pip", "--version"])
    return success

def install_pip_dependencies() -> bool:
    """安装 pip 依赖"""
    logger.info("=" * 60)
    logger.info("📦 安装 pip 依赖")
    logger.info("=" * 60)
    
    if not check_pip():
        logger.error("❌ pip 不可用")
        return False
    
    # 升级 pip
    logger.info("🔄 升级 pip...")
    success, output = run_command(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        timeout=120,
    )
    if success:
        logger.info("  ✓ pip 升级成功")
    
    # 安装依赖
    all_success = True
    for dep in PIP_DEPENDENCIES:
        logger.info(f"  📦 安装: {dep}")
        success, output = run_command(
            [sys.executable, "-m", "pip", "install", dep],
            timeout=300,
        )
        if success:
            logger.info(f"    ✓ 成功")
        else:
            logger.error(f"    ✗ 失败: {output[:200]}")
            all_success = False
    
    return all_success

# ============================================================================
# 配置文件生成
# ============================================================================

def generate_config_templates() -> bool:
    """生成配置文件模板"""
    logger.info("=" * 60)
    logger.info("📄 生成配置文件模板")
    logger.info("=" * 60)
    
    # main.yaml - 主配置
    main_config = {
        "project": {
            "name": "Shadow Hunt",
            "version": "3.0.0",
            "description": "AI 视频法证工作站",
        },
        "paths": {
            "data": str(DATA_DIR),
            "models": str(MODELS_DIR),
            "output": str(OUTPUT_DIR),
            "logs": str(LOGS_DIR),
        },
        "detection": {
            "model": "yolov8n.pt",
            "confidence": 0.5,
            "iou_threshold": 0.45,
            "classes": None,
        },
        "tracking": {
            "tracker": "deepsort",
            "max_age": 30,
            "min_hits": 3,
            "iou_threshold": 0.3,
        },
        "llm": {
            "enabled": False,
            "model_path": str(MODELS_DIR / "llm" / "model.gguf"),
            "n_ctx": 2048,
            "n_threads": 8,
        },
        "celery": {
            "broker": "redis://localhost:6379/0",
            "backend": "redis://localhost:6379/1",
        },
    }
    
    main_config_path = CONFIG_DIR / "config.yaml"
    try:
        import yaml
        with open(main_config_path, "w", encoding="utf-8") as f:
            yaml.dump(main_config, f, default_flow_style=False, allow_unicode=True)
        logger.info(f"  ✓ config.yaml")
    except ImportError:
        main_config_path = CONFIG_DIR / "config.json"
        with open(main_config_path, "w", encoding="utf-8") as f:
            json.dump(main_config, f, indent=2, ensure_ascii=False)
        logger.info(f"  ✓ config.json (JSON 格式)")
    
    # deepsort.yaml
    deepsort_config = {
        "max_age": 30,
        "min_hits": 3,
        "iou_threshold": 0.3,
        "max_cosine_distance": 0.2,
        "nn_budget": None,
        "reid_model": {
            "type": "osnet_x0_25",
            "path": str(MODELS_DIR / "reid" / "osnet_x0_25.msmt17.pt"),
        },
    }
    
    deepsort_config_path = CONFIG_DIR / "deepsort.yaml"
    try:
        import yaml
        with open(deepsort_config_path, "w", encoding="utf-8") as f:
            yaml.dump(deepsort_config, f, default_flow_style=False, allow_unicode=True)
        logger.info(f"  ✓ deepsort.yaml")
    except ImportError:
        pass
    
    logger.info("✅ 配置文件生成完成")
    return True

# ============================================================================
# 主函数
# ============================================================================

logger = None

def main():
    global logger
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("  猎影 (Shadow Hunt) 环境初始化")
    logger.info("  97工作室 - 班纳")
    logger.info("=" * 60)
    
    # 确保目录存在
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    
    # 1. 克隆仓库
    clone_repositories()
    
    # 2. 安装依赖
    install_pip_dependencies()
    
    # 3. 生成配置
    generate_config_templates()
    
    logger.info("=" * 60)
    logger.info("✅ 猎影环境初始化完成!")
    logger.info(f"   项目目录: {PROJECT_ROOT}")
    logger.info(f"   配置文件: {CONFIG_DIR}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()