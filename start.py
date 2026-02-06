#!/usr/bin/env python3
"""启动脚本 - 方便用户快速启动服务"""

import os
import sys
from pathlib import Path

def main():
    """主函数"""
    # 添加src目录到Python路径
    src_dir = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_dir))

    # 启动服务
    from src.main import main as start_app
    start_app()

if __name__ == "__main__":
    main()



