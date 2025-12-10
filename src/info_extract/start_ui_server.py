#!/usr/bin/env python3
"""
Script to start the UI server
"""
import argparse
from pathlib import Path
from .ui import UI


def start_server():
    """Start the UI server."""
    parser = argparse.ArgumentParser(description='处理指定目录中的邮件文件')
    parser.add_argument('--work-dir', type=str, required=True, help='工作目录')
    # 解析命令行参数
    args = parser.parse_args()

    print(f"工作目录: {args.work_dir}")

    print("Starting UI server...")

    # Initialize the UI with the correct database path
    db_path = Path("./config") / "standard.db"
    ui = UI(db_path=str(db_path), work_dir=args.work_dir)

    # Run the server
    ui.run()

