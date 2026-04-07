-- ============================================================
-- 猎影 (Shadow Hunt) v3.0 数据库初始化脚本
-- 作者: 97工作室 - 贾维斯
-- 日期: 2026-04-06
-- ============================================================

-- ===== 一案一档系统 =====

-- 案件表
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT UNIQUE NOT NULL,
    case_name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP,
    metadata TEXT
);

-- ===== 三权分立权限系统 =====

-- 角色表
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT UNIQUE NOT NULL,
    permissions TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 预置角色
INSERT OR IGNORE INTO roles (role_name, permissions, description) VALUES
    ('admin', '{"system": ["config", "users", "cases"], "analysis": ["all"], "export": ["all"]}', '系统管理员'),
    ('investigator', '{"analysis": ["search", "track", "export"], "cases": ["view", "create"]}', '侦查员'),
    ('auditor', '{"audit": ["view_logs", "export_logs"], "cases": ["view"]}', '审计员');

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE,
    role_id INTEGER NOT NULL DEFAULT 2,
    is_active BOOLEAN DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    details TEXT,
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ===== 视频管理 =====

-- 视频表
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    duration REAL,
    fps REAL,
    resolution TEXT,
    status TEXT DEFAULT 'pending',
    file_size INTEGER,
    upload_user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id),
    FOREIGN KEY (upload_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_videos_case ON videos(case_id);
CREATE INDEX IF NOT EXISTS idx_videos_hash ON videos(sha256_hash);

-- ===== 目标追踪 =====

-- 轨迹表
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    case_id INTEGER NOT NULL,
    track_id INTEGER NOT NULL,
    class_id INTEGER,
    start_frame INTEGER,
    end_frame INTEGER,
    start_time REAL,
    end_time REAL,
    bbox_trajectory TEXT,
    zone_ids TEXT,
    thumbnail_path TEXT,
    reid_features_path TEXT,
    synopsis_offset REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id),
    FOREIGN KEY (case_id) REFERENCES cases(id)
);

CREATE INDEX IF NOT EXISTS idx_tracks_case ON tracks(case_id);
CREATE INDEX IF NOT EXISTS idx_tracks_video ON tracks(video_id);
CREATE INDEX IF NOT EXISTS idx_tracks_time ON tracks(start_time, end_time);

-- ===== 动作标签 =====

-- 动作标签表
CREATE TABLE IF NOT EXISTS action_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    case_id INTEGER NOT NULL,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    confidence REAL,
    frame_start INTEGER,
    frame_end INTEGER,
    vlm_model TEXT,
    verified BOOLEAN DEFAULT 0,
    verified_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (track_id) REFERENCES tracks(id),
    FOREIGN KEY (case_id) REFERENCES cases(id),
    FOREIGN KEY (verified_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_action_tags_track ON action_tags(track_id);
CREATE INDEX IF NOT EXISTS idx_action_tags_case ON action_tags(case_id);
CREATE INDEX IF NOT EXISTS idx_action_tags_value ON action_tags(tag_value);

-- ===== FAISS 向量元数据 =====

-- 特征向量表
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    case_id INTEGER NOT NULL,
    embedding_path TEXT NOT NULL,
    embedding_dim INTEGER DEFAULT 128,
    model_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (track_id) REFERENCES tracks(id),
    FOREIGN KEY (case_id) REFERENCES cases(id)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_track ON embeddings(track_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_case ON embeddings(case_id);

-- ===== 语义索引 =====

-- 语义索引表
CREATE TABLE IF NOT EXISTS semantic_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    embedding_path TEXT,
    text_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);

-- ===== 任务队列 =====

-- 任务表
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    case_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    celery_task_id TEXT,
    status TEXT DEFAULT 'pending',
    progress REAL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id),
    FOREIGN KEY (case_id) REFERENCES cases(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_case ON tasks(case_id);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority, status);

-- ===== 系统配置 =====

-- 配置表
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT DEFAULT 'string',
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 默认配置
INSERT OR IGNORE INTO config (key, value, value_type, description) VALUES
    ('vlm_model_path', '', 'string', 'Open-VILA/Gemma 模型路径'),
    ('llama_cpp_path', '', 'string', 'llama.cpp 动态库路径'),
    ('cpu_threads', '8', 'int', 'CPU推理线程数'),
    ('memory_threshold_mb', '4096', 'int', '内存阈值(MB)'),
    ('openvino_enabled', 'true', 'bool', '启用OpenVINO加速'),
    ('avx512_enabled', 'true', 'bool', '启用AVX-512指令集'),
    ('faiss_nlist', '100', 'int', 'FAISS聚类中心数'),
    ('max_concurrent_tracks', '50', 'int', '最大并发追踪数');