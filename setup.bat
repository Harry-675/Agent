@echo off
REM Setup script for One News Aggregator (Windows)

echo Setting up One News Aggregator...

REM Check Python version
echo Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo Dependencies installed

REM Copy environment file if not exists
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo .env file created. Please edit it with your configuration.
) else (
    echo .env file already exists
)

REM Copy news sources config if not exists
if not exist "config\news_sources.json" (
    echo Creating news sources config from template...
    copy config\news_sources.example.json config\news_sources.json
    echo news_sources.json created. Please edit it with your news sources.
) else (
    echo news_sources.json already exists
)

REM Start Docker services
echo Starting Docker services (PostgreSQL and Redis)...
docker-compose up -d
echo Docker services started

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Edit .env file with your Alibaba Bailian API key
echo 2. Edit config\news_sources.json with your news sources
echo 3. Run tests: pytest
echo 4. Start the application: uvicorn src.main:app --reload
echo.
echo To activate the virtual environment in the future, run:
echo   venv\Scripts\activate.bat

pause
