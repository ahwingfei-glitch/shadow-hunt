#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - FastAPI 入口 (安全修复版)
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.perception.video_processor import VideoProcessor, create_video_processor
from core.cognition.semantic_search import SemanticSearcher, create_semantic_searcher
from core.utils.security import (
    safe_path, sanitize_filename, get_db_connection,
    check_file_upload, sanitize_text_prompt
)


# ============ 配置加载 ============

def load_config() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


CONFIG = load_config()
DB_PATH = str(Path(__file__).parent.parent.parent / "data" / "shadowhunt.db")

# API Key 配置（生产环境应从环境变量读取）
API_KEY = os.environ.get("SHADOWHUNT_API_KEY", "dev-key-change-in-production")


# ============ API 认证 ============

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """验证 API Key"""
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


# ============ 请求模型 ============

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    video_id: Optional[int] = None
    case_id: Optional[int] = None
    top_k: int = 10


class VideoProcessRequest(BaseModel):
    """视频处理请求"""
    video_path: str
    case_id: int
    semantic_prompts: Optional[List[str]] = None


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    key: str
    value: str


# ============ 响应模型 ============

class SearchResult(BaseModel):
    """搜索结果"""
    track_id: int
    video_id: int
    score: float
    tag_value: str
    frame_start: int
    frame_end: int
    confidence: float


# ============ 全局实例 ============

video_processor = None
semantic_searcher = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    global video_processor, semantic_searcher
    
    video_processor = create_video_processor(CONFIG, DB_PATH)
    semantic_searcher = create_semantic_searcher(CONFIG)
    
    yield


# ============ 创建应用 ============

app = FastAPI(
    title="猎影 API",
    description="AI 视频法证工作站",
    version="3.0.0",
    lifespan=lifespan
)

# CORS - 生产环境应限制来源
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ============ 前端页面路由 ============

WEB_DIR = Path(__file__).parent.parent / "web"

@app.get("/app")
async def home_page():
    """首页"""
    return FileResponse(WEB_DIR / "index.html")

@app.get("/app/login")
async def login_page():
    """登录页面"""
    return FileResponse(WEB_DIR / "login.html")

@app.get("/app/player")
async def player_page():
    """播放中心"""
    return FileResponse(WEB_DIR / "player.html")

@app.get("/app/cases")
async def cases_page():
    """案件管理"""
    return FileResponse(WEB_DIR / "cases.html")

@app.get("/app/settings")
async def settings_page():
    """设置面板"""
    return FileResponse(WEB_DIR / "settings.html")


# ============ 首页（无需认证） ============

@app.get("/")
async def root():
    """首页"""
    return {
        "name": "猎影 (Shadow Hunt)",
        "version": "3.0.0",
        "description": "AI 视频法证工作站",
        "docs": "/docs"
    }


# ============ 搜索 API ============

@app.post("/api/search", response_model=List[SearchResult], dependencies=[Depends(verify_api_key)])
async def search(request: SearchRequest):
    """
    语义搜索（需认证）
    
    支持自然语言查询："正在打电话的人"、"正在奔跑的人"
    """
    # 清理输入
    query = sanitize_text_prompt(request.query, max_length=500)
    
    if semantic_searcher is None:
        raise HTTPException(status_code=500, detail="搜索器未初始化")
    
    results = semantic_searcher.search(query, k=request.top_k)
    
    return [
        SearchResult(
            track_id=r.track_id,
            video_id=r.video_id,
            score=r.score,
            tag_value=r.tag_value,
            frame_start=r.frame_start,
            frame_end=r.frame_end,
            confidence=r.confidence
        )
        for r in results
    ]


@app.get("/api/search/action/{action}", dependencies=[Depends(verify_api_key)])
async def search_by_action(action: str):
    """按动作搜索（需认证）"""
    action = sanitize_text_prompt(action, max_length=100)
    
    if semantic_searcher is None:
        raise HTTPException(status_code=500, detail="搜索器未初始化")
    
    results = semantic_searcher.search(f"正在{action}的人")
    return results


# ============ 视频 API ============

@app.post("/api/videos/upload", dependencies=[Depends(verify_api_key)])
async def upload_video(
    file: UploadFile = File(...),
    case_id: int = 1,
    background_tasks: BackgroundTasks = None
):
    """
    上传视频（需认证）
    
    安全措施：
    - 文件名清理
    - 文件类型校验
    - 文件大小限制
    - 流式写入
    """
    # 清理文件名
    safe_filename = sanitize_filename(file.filename)
    
    # 校验文件类型
    is_valid, error = check_file_upload(safe_filename, 0)  # 大小稍后检查
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # 安全路径
    raw_dir = Path(CONFIG['paths']['data']) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    save_path = safe_path(raw_dir, safe_filename)
    
    # 流式写入，限制大小
    MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
    total_size = 0
    
    try:
        with open(save_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_size += len(chunk)
                if total_size > MAX_SIZE:
                    f.close()
                    save_path.unlink()
                    raise HTTPException(status_code=413, detail="File too large (max 2GB)")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    return {
        "filename": safe_filename,
        "path": str(save_path),
        "case_id": case_id,
        "size": total_size,
        "status": "uploaded"
    }


@app.post("/api/videos/process", dependencies=[Depends(verify_api_key)])
async def process_video(
    request: VideoProcessRequest,
    background_tasks: BackgroundTasks
):
    """处理视频（需认证）"""
    # 校验路径
    try:
        video_path = safe_path(Path(CONFIG['paths']['data']), request.video_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if video_processor is None:
        raise HTTPException(status_code=500, detail="处理器未初始化")
    
    def process_task():
        for frame in video_processor.process_video(
            str(video_path),
            request.case_id,
            request.semantic_prompts
        ):
            pass
    
    background_tasks.add_task(process_task)
    
    return {
        "video_path": str(video_path),
        "case_id": request.case_id,
        "status": "processing"
    }


@app.get("/api/videos/{video_id}", dependencies=[Depends(verify_api_key)])
async def get_video(video_id: int):
    """获取视频信息（需认证）"""
    with get_db_connection(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
    
    if row is None:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    return dict(row)


@app.get("/api/videos", dependencies=[Depends(verify_api_key)])
async def list_videos(case_id: Optional[int] = None):
    """列出视频（需认证）"""
    with get_db_connection(DB_PATH) as conn:
        cursor = conn.cursor()
        if case_id:
            cursor.execute("SELECT id, filename, status FROM videos WHERE case_id = ?", (case_id,))
        else:
            cursor.execute("SELECT id, filename, status FROM videos")
        rows = cursor.fetchall()
    
    return [dict(r) for r in rows]


# ============ 配置 API ============

@app.get("/api/config", dependencies=[Depends(verify_api_key)])
async def get_config():
    """获取配置（需认证）"""
    # 过滤敏感配置
    safe_config = {k: v for k, v in CONFIG.items() if k not in ['secrets', 'api_keys']}
    return safe_config


@app.put("/api/config", dependencies=[Depends(verify_api_key)])
async def update_config(request: ConfigUpdateRequest):
    """更新配置（需认证）"""
    # 白名单允许更新的配置项
    ALLOWED_KEYS = ['cpu_threads', 'memory_threshold_mb', 'box_threshold', 'text_threshold']
    
    if request.key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Cannot update key: {request.key}")
    
    with get_db_connection(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE config SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
            (request.value, request.key)
        )
        conn.commit()
    
    return {"key": request.key, "value": request.value, "status": "updated"}


# ============ 案件 API ============

@app.post("/api/cases", dependencies=[Depends(verify_api_key)])
async def create_case(name: str):
    """创建案件（需认证）"""
    name = sanitize_text_prompt(name, max_length=200)
    
    with get_db_connection(DB_PATH) as conn:
        cursor = conn.cursor()
        count = cursor.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        case_number = f"CASE-{count + 1:04d}"
        
        cursor.execute(
            "INSERT INTO cases (case_number, case_name) VALUES (?, ?)",
            (case_number, name)
        )
        case_id = cursor.lastrowid
        conn.commit()
    
    return {"id": case_id, "case_number": case_number, "name": name}


@app.get("/api/cases", dependencies=[Depends(verify_api_key)])
async def list_cases():
    """列出案件（需认证）"""
    with get_db_connection(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, case_number, case_name, status FROM cases")
        rows = cursor.fetchall()
    
    return [dict(r) for r in rows]


# ============ 健康检查（无需认证） ============

@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)