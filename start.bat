@echo off
chcp 65001 >nul 2>&1
REM ============================================================
REM 猎影 (Shadow Hunt) 一键启动脚本
REM 97工作室 - AI 视频法证工作站
REM ============================================================

setlocal enabledelayedexpansion

REM ===== 配置区域 =====
set "PROJECT_NAME=猎影 (Shadow Hunt)"
set "CONDA_ENV=shadowhunt"
set "REDIS_HOST=127.0.0.1"
set "REDIS_PORT=6379"
set "API_HOST=0.0.0.0"
set "API_PORT=8080"
set "API_MODULE=src.api.main:app"

REM ===== 颜色定义 =====
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "CYAN=[96m"
set "RESET=[0m"

REM ===== 显示横幅 =====
echo.
echo %CYAN%============================================================%RESET%
echo %CYAN%  %PROJECT_NAME% v3.0%RESET%
echo %CYAN%  AI 视频法证工作站%RESET%
echo %CYAN%============================================================%RESET%
echo.

REM ===== 检查并初始化 Conda =====
echo %YELLOW%[Step 1/4] 检查 Conda 环境...%RESET%

REM 初始化 Conda（支持不同安装路径）
if exist "%USERPROFILE%\miniconda3\Scripts\conda.bat" (
    call "%USERPROFILE%\miniconda3\Scripts\conda.bat" hook
) else if exist "%USERPROFILE%\anaconda3\Scripts\conda.bat" (
    call "%USERPROFILE%\anaconda3\Scripts\conda.bat" hook
) else if exist "C:\ProgramData\miniconda3\Scripts\conda.bat" (
    call "C:\ProgramData\miniconda3\Scripts\conda.bat" hook
) else if exist "C:\ProgramData\anaconda3\Scripts\conda.bat" (
    call "C:\ProgramData\anaconda3\Scripts\conda.bat" hook
) else (
    echo %RED%[错误] 未找到 Conda 安装，请确认已安装 Miniconda 或 Anaconda%RESET%
    goto :error_exit
)

REM 激活项目环境
call conda activate %CONDA_ENV% 2>nul
if errorlevel 1 (
    echo %RED%[错误] 无法激活 Conda 环境: %CONDA_ENV%%RESET%
    echo %YELLOW%提示: 请先运行 'conda create -n shadowhunt python=3.10' 创建环境%RESET%
    goto :error_exit
)
echo %GREEN%[OK] Conda 环境已激活: %CONDA_ENV%%RESET%

REM ===== 初始化数据库 =====
echo.
echo %YELLOW%[Step 2/4] 初始化数据库...%RESET%

if not exist "scripts\init_db.py" (
    echo %RED%[错误] 数据库初始化脚本不存在: scripts\init_db.py%RESET%
    goto :error_exit
)

python scripts\init_db.py
if errorlevel 1 (
    echo %RED%[错误] 数据库初始化失败%RESET%
    goto :error_exit
)
echo %GREEN%[OK] 数据库初始化完成%RESET%

REM ===== 启动 Redis =====
echo.
echo %YELLOW%[Step 3/4] 启动 Redis 服务...%RESET%

REM 检查 Redis 是否已在运行
redis-cli -h %REDIS_HOST% -p %REDIS_PORT% ping >nul 2>&1
if errorlevel 1 (
    REM Redis 未运行，尝试启动
    where redis-server >nul 2>&1
    if errorlevel 1 (
        echo %RED%[错误] 未找到 redis-server，请确认 Redis 已安装并加入 PATH%RESET%
        goto :error_exit
    )
    
    echo 正在后台启动 Redis...
    start /B redis-server --bind %REDIS_HOST% --port %REDIS_PORT% --daemonize yes 2>nul
    
    REM 等待 Redis 启动
    set "redis_ready=0"
    for /L %%i in (1,1,10) do (
        timeout /t 1 >nul 2>&1
        redis-cli -h %REDIS_HOST% -p %REDIS_PORT% ping >nul 2>&1
        if not errorlevel 1 (
            set "redis_ready=1"
            goto :redis_done
        )
    )
    :redis_done
    
    if "!redis_ready!"=="0" (
        echo %RED%[错误] Redis 启动超时%RESET%
        goto :error_exit
    )
    echo %GREEN%[OK] Redis 已启动 (%REDIS_HOST%:%REDIS_PORT%)%RESET%
) else (
    echo %GREEN%[OK] Redis 已在运行 (%REDIS_HOST%:%REDIS_PORT%)%RESET%
)

REM ===== 启动 API 服务 =====
echo.
echo %YELLOW%[Step 4/4] 启动 API 服务...%RESET%

REM 设置环境变量
set OLLAMA_HOST=http://localhost:11434

REM 检查 uvicorn 是否安装
python -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo %RED%[错误] uvicorn 未安装，请运行 'pip install uvicorn'%RESET%
    goto :error_exit
)

REM 检查 API 模块是否存在
if not exist "src\api\main.py" (
    echo %RED%[错误] API 模块不存在: src\api\main.py%RESET%
    goto :error_exit
)

echo.
echo %CYAN%============================================================%RESET%
echo %GREEN%  服务已启动！%RESET%
echo %CYAN%============================================================%RESET%
echo.
echo   服务地址: %CYAN%http://localhost:%API_PORT%%RESET%
echo   API 文档: %CYAN%http://localhost:%API_PORT%/docs%RESET%
echo   ReDoc:   %CYAN%http://localhost:%API_PORT%/redoc%RESET%
echo.
echo %YELLOW%按 Ctrl+C 停止服务%RESET%
echo %CYAN%============================================================%RESET%
echo.

REM 启动 FastAPI 服务
python -m uvicorn %API_MODULE% --host %API_HOST% --port %API_PORT% --reload

REM ===== 正常退出 =====
endlocal
exit /b 0

REM ===== 错误处理 =====
:error_exit
echo.
echo %RED%============================================================%RESET%
echo %RED%  启动失败，请检查上述错误信息%RESET%
echo %RED%============================================================%RESET%
echo.
endlocal
exit /b 1