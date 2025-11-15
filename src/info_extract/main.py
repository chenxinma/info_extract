import argparse
import asyncio
import logging
import os
import sys

from .extract import PlainExtractor, SpreadsheetExtractor
from .log_setup import setup_logging
from .pipeline import Pipeline
from .source import EMLReader, ExcelReader, MSGReader
from .destination import ExcelExporter
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
    source_dir = os.path.join(args.work_dir, 'source')
    processing_dir = os.path.join(args.work_dir, 'processing')
    destination_dir = os.path.join(args.work_dir, 'destination')
    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(processing_dir, exist_ok=True)
    os.makedirs(destination_dir, exist_ok=True)

    clean_processing_dir(processing_dir)
    
    pipeline = Pipeline(
        source=[("eml_reader", EMLReader(source_dir=source_dir, processing_dir=processing_dir)),
                ("msg_reader", MSGReader(source_dir=source_dir, processing_dir=processing_dir)),
                ("excel_reader", ExcelReader(source_dir=source_dir, processing_dir=processing_dir))],
        extractors=[
            ("plain_extractor", PlainExtractor(processing_dir=processing_dir)),
            ("spreadsheet_extractor", SpreadsheetExtractor(processing_dir=processing_dir))
        ],
        destination=[
            ("excel_exporter", ExcelExporter(processing_dir=processing_dir, destination_dir=destination_dir))
        ]
    )
    await pipeline.run()

    print("文件处理完成！")

def clean_processing_dir(processing_dir: str):
    """清理处理目录下的所有文件"""
     # 清理 processing_dir 下的所有 文件
    for root, dirs, files in os.walk(processing_dir, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"删除文件失败: {file_path}, 错误: {e}")
        for d in dirs:
            dir_path = os.path.join(root, d)
            try:
                os.rmdir(dir_path)
            except Exception as e:
                logger.error(f"删除目录失败: {dir_path}, 错误: {e}")

def async_main():
    asyncio.run(main())