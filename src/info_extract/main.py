import os
import sys
import argparse

from .extract.plain_extract import PlainExtractor

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .source import EmailReader

def main():
    """主函数：处理source目录中的邮件文件"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='处理指定目录中的邮件文件')
    parser.add_argument('--source_dir', type=str, default='./source', help='源邮件文件目录')
    parser.add_argument('--processing_dir', type=str, default='./processing', help='处理中的邮件文件目录')
    parser.add_argument('--destination_dir', type=str, default='./destination', help='处理结果输出目录')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    print(f"开始处理邮件文件...")
    print(f"源目录: {args.source_dir}")
    print(f"处理目录: {args.processing_dir}")
    print(f"结果目录: {args.destination_dir}")
    
    # # 创建邮件处理器实例
    # processor = EmailReader(source_dir=args.source_dir, processing_dir=args.processing_dir)
    
    # # 处理邮件文件
    # processor.read()

    extractor = PlainExtractor(processing_dir=args.processing_dir, 
                               destination_dir=args.destination_dir)
    extractor.extract()
    
    print("邮件文件处理完成！")


if __name__ == "__main__":
    main()
