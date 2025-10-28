import logging
import os
import sys
import argparse

from .log_setup import setup_logging
# 配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .pipeline import Pipeline
from .source import EMLReader, MSGReader
from .extract import PlainExtractor, SpreadsheetExtractor

def main():
    """主函数：处理source目录中的邮件文件"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='处理指定目录中的邮件文件')
    parser.add_argument('--source_dir', type=str, default='./source', help='源邮件文件目录')
    parser.add_argument('--processing_dir', type=str, default='./processing', help='处理中的邮件文件目录')
    parser.add_argument('--destination_dir', type=str, default='./destination', help='处理结果输出目录')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    print(f"开始处理文件...")
    print(f"源目录: {args.source_dir}")
    print(f"处理目录: {args.processing_dir}")
    print(f"结果目录: {args.destination_dir}")

    clean_processing_dir(args.processing_dir)
    
    pipeline = Pipeline(
        source=[("eml_reader", EMLReader(source_dir=args.source_dir, processing_dir=args.processing_dir)),
                ("msg_reader", MSGReader(source_dir=args.source_dir, processing_dir=args.processing_dir))],
        extractors=[
            ("plain_extractor", PlainExtractor(processing_dir=args.processing_dir, 
                                               destination_dir=args.destination_dir)),
            ("spreadsheet_extractor", SpreadsheetExtractor(processing_dir=args.processing_dir, 
                                                           destination_dir=args.destination_dir))
        ]
    )
    pipeline.run()

    print("文件处理完成！")

def clean_processing_dir(processing_dir: str):
    """清理处理目录下的所有文件"""
     # 清理 processing_dir 下的所有 txt 文件
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

if __name__ == "__main__":
    main()
