import argparse
import asyncio
import logging
import os
import sys
import textwrap

from .log_setup import setup_logging
from .executor import Executor
from .config import profile_manager

# 配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def main():
    """主函数：处理source目录中的邮件文件"""

    p_list = [ f"{p["id"]}-{ p['name']}" \
              for p in profile_manager.get_available_profiles() ]

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(f'''\
        从邮件文件、Excel等按要求提取结构化信息输出标准Excel。
        指定工作目录 work-dir
        workdir
            ├── source      原始文件放置位置
            ├── processing
            └── destination 结果文件输出位置
        可选选择Profile: 
        {"; ".join(p_list) }
        ''')
    )
    parser.add_argument('--work-dir', type=str, required=True, help='工作目录')
    parser.add_argument('--profile', type=int, default=1, help="配置ID")
    
    # 解析命令行参数
    args = parser.parse_args()

    profile_manager.switch_profile(args.profile)
    
    print(f"开始处理文件...")
    print(f"工作目录: {args.work_dir}, 配置ID: {args.profile}")
    executor = Executor(args.work_dir)

    executor.clean_processing_dir()
    
    async for _ in executor.run(profile_manager):
        pass

    print("文件处理完成！")


def async_main():
    asyncio.run(main())