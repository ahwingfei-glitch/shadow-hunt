#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - 安全工具函数
"""

import os
import re
import hashlib
import secrets
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
import sqlite3


# ============ 路径安全 ============

def safe_path(base_dir: Path, user_path: str) -> Path:
    """
    安全拼接路径，防止路径遍历攻击
    
    Args:
        base_dir: 基础目录
        user_path: 用户提供的路径
        
    Returns:
        安全的完整路径
        
    Raises:
        ValueError: 如果路径不合法
    """
    # 解析为绝对路径
    base_dir = base_dir.resolve()
    full_path = (base_dir / user_path).resolve()
    
    # 检查是否在基础目录内
    if not str(full_path).startswith(str(base_dir)):
        raise ValueError(f"Path traversal detected: {user_path}")
    
    return full_path


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除危险字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    # 先移除路径分隔符和 ..
    filename = filename.replace('/', '_').replace('\\', '_')
    filename = filename.replace('..', '_')
    
    # 只保留字母、数字、下划线、点、连字符
    safe_name = re.sub(r'[^\w\.\-]', '_', filename)
    
    # 移除开头的点（防止隐藏文件）
    safe_name = safe_name.lstrip('.')
    
    # 限制长度
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:250] + ext
    
    return safe_name or "unnamed_file"


# ============ 输入验证 ============

def validate_file_type(filename: str, allowed_extensions: list) -> bool:
    """
    验证文件类型
    
    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表
        
    Returns:
        是否合法
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def sanitize_text_prompt(prompt: str, max_length: int = 500) -> str:
    """
    清理文本提示词
    
    Args:
        prompt: 原始提示词
        max_length: 最大长度
        
    Returns:
        清理后的提示词
        
    Raises:
        ValueError: 如果提示词过长
    """
    if len(prompt) > max_length:
        raise ValueError(f"Prompt too long: {len(prompt)} > {max_length}")
    
    # 移除控制字符
    prompt = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', prompt)
    
    return prompt.strip()


def validate_model_name(model_name: str) -> str:
    """
    验证模型名称
    
    Args:
        model_name: 模型名称
        
    Returns:
        安全的模型名称
        
    Raises:
        ValueError: 如果模型名称不合法
    """
    # 只允许字母、数字、下划线、连字符、点、斜杠
    if not re.match(r'^[\w\-\.\/]+$', model_name):
        raise ValueError(f"Invalid model name: {model_name}")
    
    # 禁止路径遍历
    if '..' in model_name:
        raise ValueError("Path traversal in model name")
    
    return model_name


# ============ 数据库连接管理 ============

@contextmanager
def get_db_connection(db_path: str):
    """
    安全的数据库连接上下文管理器
    
    Args:
        db_path: 数据库路径
        
    Yields:
        数据库连接对象
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ============ API 认证 ============

def generate_api_key() -> str:
    """生成 API Key"""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """哈希 API Key"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """
    验证 API Key
    
    Args:
        provided_key: 用户提供的 key
        stored_hash: 存储的哈希值
        
    Returns:
        是否匹配
    """
    return secrets.compare_digest(
        hash_api_key(provided_key),
        stored_hash
    )


# ============ 文件上传安全 ============

# 允许的视频文件类型
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']

# 最大文件大小 (2GB)
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024

# 允许的模型文件类型
ALLOWED_MODEL_EXTENSIONS = ['.pt', '.pth', '.onnx', '.gguf', '.bin']


def check_file_upload(
    filename: str,
    file_size: int,
    allowed_extensions: list = None,
    max_size: int = None
) -> tuple:
    """
    检查文件上传是否合法
    
    Args:
        filename: 文件名
        file_size: 文件大小
        allowed_extensions: 允许的扩展名
        max_size: 最大大小
        
    Returns:
        (is_valid, error_message)
    """
    allowed_extensions = allowed_extensions or ALLOWED_VIDEO_EXTENSIONS
    max_size = max_size or MAX_FILE_SIZE
    
    # 检查文件类型
    if not validate_file_type(filename, allowed_extensions):
        return False, f"Invalid file type. Allowed: {allowed_extensions}"
    
    # 检查文件大小
    if file_size > max_size:
        return False, f"File too large. Max: {max_size / (1024**3):.1f} GB"
    
    return True, None