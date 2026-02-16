#!/usr/bin/env bash
# 单独启动 API 服务（可选）

cd "$(dirname "$0")/.."
python -c "
import sys
sys.path.insert(0, 'src')
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path('.').resolve() / '.env')
except ImportError:
    pass
import uvicorn
from api import app
port = int(__import__('os').environ.get('ZHYX_PORT', '8000'))
uvicorn.run(app, host='0.0.0.0', port=port)
"
