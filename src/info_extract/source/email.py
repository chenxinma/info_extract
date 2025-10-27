from datetime import datetime
import logging
from pathlib import Path
from typing import Optional, Tuple, TypeAlias

from ..pipeline import Step

logger = logging.getLogger(__name__)

SourceResult: TypeAlias = Tuple[str, Optional[list[str]]]

class EmailReader(Step):
    """处理邮件文件，提取正文内容"""
    
    def __init__(self, source_dir: str = "source", processing_dir: str = "processing"):
        """
        初始化邮件处理器
        
        Args:
            source_dir: 源文件目录路径
            processing_dir: 处理后文件保存目录路径
        """
        self.source_dir = Path(source_dir)
        self.processing_dir = Path(processing_dir)
        
        # 确保目录存在
        self.source_dir.mkdir(exist_ok=True)
        self.processing_dir.mkdir(exist_ok=True)
    
    def _save_text_file(self, content: str, original_filename: str) -> str:
        """
        将内容保存为txt文件到processing目录
        
        Args:
            content: 要保存的内容
            original_filename: 原始文件名(不含扩展名)
        """
        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{original_filename}_{timestamp}.txt"
        file_path = self.processing_dir / filename
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.strip_body(content))
        
        logger.info(f"已保存文本文件: {filename}")
        return filename

    def strip_body(self, body: str) -> str:
        """
        清理邮件正文内容，移除多余的空白行和空格
        
        Args:
            body: 原始邮件正文内容
            
        Returns:
            清理后的正文内容
        """
        # 移除首尾空白
        body = body.strip()
        # 移除多余的空白行
        lines = []
        for line in body.splitlines():
            line = line.strip()
            # if any( end_words in line for end_words in 
            #         ["Respectfully", "Regards", "Sincerely", "Best regards", "Kind regards"]):
            #     break
            if line:
                lines.append(line)
        body = '\n'.join(lines)
        return body




