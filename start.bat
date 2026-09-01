@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM =========================================================
REM DC-IOC 平台 一键启动 (Windows)
REM
REM 用法:
REM   start.bat             默认: 开发环境 (Docker Compose)
REM   start.bat dev         开发环境 (热重载 + Prometheus)
REM   start.bat staging     预发环境 (2副本 + Grafana)
REM   start.bat prod        生产环境模板
REM   start.bat local       本地开发模式 (不依赖 Docker)
REM =========================================================

set MODE=%~1
if "%MODE%"=="" set MODE=dev

REM ---- 参数校验 ----
if /i "%MODE%"=="dev"     goto :check
if /i "%MODE%"=="staging" goto :check
if /i "%MODE%"=="prod"    goto :check
if /i "%MODE%"=="local"   goto :local

echo [错误] 未知模式: %MODE%
echo   可用: dev, staging, prod, local
pause
exit /b 1

:check
REM =========================================================
REM Docker Compose 模式
REM =========================================================
echo.
echo ===========================================
echo   DC-IOC 平台 启动 (模式: %MODE%)
echo ===========================================
echo.

REM ---- 检查 Docker ----
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Docker, 请先安装 Docker Desktop:
    echo   https://www.docker.com/products/docker-desktop
    echo   或使用 'start.bat local' 进入本地开发模式
    pause
    exit /b 1
)

docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] Docker 守护进程未运行, 请启动 Docker Desktop 后重试。
    pause
    exit /b 1
)

REM ---- 生成 .env (若不存在) ----
if not exist "backend\.env" (
    if /i "%MODE%"=="dev" (
        if exist "backend\.env.dev" (
            echo [初始化] 复制 backend\.env.dev -^> backend\.env
            copy "backend\.env.dev" "backend\.env" >nul
        )
    ) else (
        if exist "backend\.env.example" (
            echo [警告] 未找到 backend\.env.%MODE%, 使用 .env.example 模板
            echo [警告] 生产环境请务必替换 SECRET_KEY 和数据库密码!
            copy "backend\.env.example" "backend\.env" >nul
        )
    )
) else (
    echo [跳过] backend\.env 已存在
)

REM ---- 选择 Compose 文件 ----
set COMPOSE_FILES=-f docker-compose.yml

if /i "%MODE%"=="dev" (
    set COMPOSE_FILES=!COMPOSE_FILES! -f deploy/docker-compose.dev.yml
) else if /i "%MODE%"=="staging" (
    set COMPOSE_FILES=!COMPOSE_FILES! -f deploy/docker-compose.staging.yml
) else if /i "%MODE%"=="prod" (
    set COMPOSE_FILES=!COMPOSE_FILES! -f deploy/docker-compose.prod.yml
)

REM ---- 安全提示 (非 dev 模式) ----
if /i not "%MODE%"=="dev" (
    echo.
    echo [安全提示] %MODE% 环境启动前请确认:
    echo   1. SECRET_KEY 已替换为非默认值
    echo   2. 数据库密码已修改
    echo   3. EXTERNAL_COLLECTOR_TOKEN 已配置 (生产)
    echo.
    choice /c yn /m "确认继续?"
    if errorlevel 2 exit /b 0
)

REM ---- 构建共享 UI 组件库 (@dc-ioc/ui) ----
echo.
echo [UI库] 安装并构建 @dc-ioc/ui (dist 已存在则跳过, 避免每次重复 build)...
cd packages\dc-ioc-ui
if not exist "node_modules" (
    echo   npm install...
    call npm install
)
if not exist "dist" (
    echo   vite build...
    call npx vite build
) else (
    echo   跳过: dist 已存在, UI 库有改动请手动 cd packages\dc-ioc-ui ^&^& npx vite build
)
cd ..\..

REM ---- 启动 ----
echo.
REM dev 模式后端经 ./backend:/app 卷挂载源码 + --reload 热更新, 无需每次重建镜像/容器;
REM   仅当 requirements.txt / Dockerfile 变更时才需手动加 --build。
REM staging/prod 仍每次 --build 以确保镜像与配置最新。
echo [启动] docker compose %COMPOSE_FILES% up -d (dev 跳过镜像重建)
echo.
if /i "%MODE%"=="dev" (
    docker compose %COMPOSE_FILES% up -d
) else (
    docker compose %COMPOSE_FILES% up -d --build
)
if %errorlevel% neq 0 (
    echo [错误] 启动失败, 请查看上方日志。
    pause
    exit /b 1
)

REM ---- 等待就绪 ----
echo.
echo [等待] 服务启动中 (约 20 秒)...
timeout /t 20 >nul

echo.
echo [状态] 服务健康检查:
docker compose ps 2>nul

REM ---- 检查端点 ----
echo.
echo [检查] 端点可达性:
curl -s http://localhost:8000/health 2>nul || echo   (后端未就绪, 请稍后重试)
curl -s http://localhost:8000/metrics 2>nul >nul && echo   /metrics (Prometheus) OK
if /i "%MODE%"=="dev" (
    curl -s http://localhost:9090/-/healthy 2>nul >nul && echo   Prometheus OK
)

REM ---- 输出访问地址 ----
echo.
echo ============================================
echo   启动完成! (%MODE% 环境)
echo ============================================
echo.
REM ---- 前端访问地址 (dev 走 Vite 5173 热重载, 其余走 Docker 8080) ----
if /i "%MODE%"=="dev" (
    set FRONTEND_URL=http://localhost:5173
) else (
    set FRONTEND_URL=http://localhost:8080
)

echo   核心服务:
echo     前端      : !FRONTEND_URL!
echo     后端 API  : http://localhost:8000/docs
echo     健康检查  : http://localhost:8000/health
echo     Prometheus: http://localhost:8000/metrics
echo     默认账户  : admin / admin123
echo.
if /i "%MODE%"=="dev" (
    echo   开发服务:
    echo     Prometheus: http://localhost:9090
    echo     前端 Dev  : http://localhost:5173 (热重载)
)
if /i "%MODE%"=="staging" (
    echo   监控:
    echo     Prometheus: http://localhost:9090
    echo     Grafana   : http://localhost:3000
)
if /i "%MODE%"=="prod" (
    echo   监控:
    echo     Prometheus: http://localhost:9090
    echo     Grafana   : http://localhost:3000
    echo     Loki API  : http://localhost:3100
)
echo.
echo   常用命令:
echo     查看日志 : docker compose logs -f backend
echo     停止服务 : docker compose down
echo     重置数据 : docker compose down -v (谨慎!)
echo.
echo   按任意键在浏览器打开前端 (!FRONTEND_URL!)...
pause >nul
start !FRONTEND_URL!
goto :end

:local
REM =========================================================
REM 本地开发模式 (不依赖 Docker, 需手动启动 PostgreSQL/Redis)
REM =========================================================
echo.
echo ===========================================
echo   DC-IOC 平台 本地开发模式
echo ===========================================
echo.
echo [前提] 请确保已启动 PostgreSQL 和 Redis
echo   默认: localhost:5432 (dcuser/dcpass/dc_ioc)
echo   默认: localhost:6379
echo.

REM ---- 后端 ----
if not exist "backend\.env" (
    if exist "backend\.env.dev" (
        echo [初始化] 复制 backend\.env.dev -^> backend\.env
        copy "backend\.env.dev" "backend\.env" >nul
    )
)

echo [后端] 安装依赖...
cd backend
if not exist ".venv" (
    python -m venv .venv
    echo [后端] 虚拟环境已创建
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
echo [后端] 启动 uvicorn (http://localhost:8000)...
start "DC-IOC Backend" cmd /c ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
cd ..

REM ---- 前端 ----
echo [前端] 安装依赖...
cd frontend
if not exist "node_modules" (
    call npm install
)

REM ---- 构建共享 UI 组件库 ----
echo [UI库] 构建 @dc-ioc/ui...
cd ..\packages\dc-ioc-ui
if not exist "node_modules" (
    call npm install
)
call npx vite build
cd ..\..\frontend

echo [前端] 启动 Vite dev server (http://localhost:5173)...
start "DC-IOC Frontend" cmd /c "npm run dev"
cd ..

echo.
echo ============================================
echo   本地开发模式已启动!
echo ============================================
echo   前端      : http://localhost:5173
echo   后端 API  : http://localhost:8000/docs
echo   健康检查  : http://localhost:8000/health
echo   默认登录  : admin / admin123
echo ============================================
echo.
echo   关闭: 分别关闭弹出的两个命令行窗口
echo.

goto :end

:end
endlocal
