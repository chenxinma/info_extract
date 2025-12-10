import argparse
import asyncio
import logging
import os
import sys

from .log_setup import setup_logging
from .executor import Executor

# 配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def main():
    """主函数：处理source目录中的邮件文件"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='处理指定目录中的邮件文件')
    parser.add_argument('--work-dir', type=str, required=True, help='工作目录')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    print(f"开始处理文件...")
    print(f"工作目录: {args.work_dir}")
    executor = Executor(args.work_dir)

    executor.clean_processing_dir()
    
    async for _ in executor.pipeline.run():
        pass

    print("文件处理完成！")


def async_main():
    asyncio.run(main())