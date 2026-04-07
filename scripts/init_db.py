#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎影 (Shadow Hunt) - 数据库初始化
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "shadowhunt.db"
SCHEMA_PATH = Path(__file__).parent.parent / "data" / "schema.sql"


def init_database():
    """初始化数据库"""
    # 确保目录存在
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 读取 schema
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = f.read()
    
    # 执行
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.executescript(schema)
    conn.commit()
    conn.close()
    
    print(f"数据库已初始化: {DB_PATH}")


if __name__ == "__main__":
    init_database()