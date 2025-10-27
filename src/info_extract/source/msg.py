import logging
import os
from pathlib import Path
from typing import Optional

import extract_msg
from markdownify import markdownify as md
from typing_extensions import Generator

from .email import EmailReader, SourceResult


logger = logging.getLogger(__name__)

class MSGReader(EmailReader):
    """处理msg邮件文件，提取正文内容"""

    def run(self) -> Generator[SourceResult | None, None, None]:
        """处理source目录下的所有eml和msg文件"""
        # 获取所有msg文件
        
        msg_files = list(self.source_dir.glob("*.msg"))

        for msg_fp in msg_files:
            yield self._process_msg_file(msg_fp)

    def _process_msg_file(self, msg_file_path: Path) -> SourceResult | None:
        """
        处理单个msg文件
        
        Args:
            msg_file_path: msg文件路径
        """
        try:
            # 使用extract-msg处理msg文件
            msg_obj = extract_msg.Message(msg_file_path)
            
            # 提取正文（优先获取HTML，然后是纯文本）
            body = None
            if msg_obj.htmlBody:
                body = md(msg_obj.htmlBody.decode('utf-8', errors='ignore'))
            if not body and msg_obj.body:
                body = msg_obj.body.decode('utf-8', errors='ignore')  # pyright: ignore[reportAttributeAccessIssue]
            
            # 保存为txt文件
            text_file = self._save_text_file(body, msg_file_path.stem)   # pyright: ignore[reportArgumentType]
            
            # 提取并保存Excel附件
            attachments = self._extract_excel_attachments_from_msg(msg_obj, msg_file_path.stem)
            
            logger.info(f"成功处理msg文件: {msg_file_path.name}")
            return text_file, attachments
            
        except Exception as e:
            logger.error(f"处理msg文件 {msg_file_path.name} 时出错: {str(e)}")
            # 如果msg-parser无法处理，则尝试按文本文件处理
            try:
                with open(msg_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    body = f.read()
                self._save_text_file(body, msg_file_path.stem + "_fallback")
                logger.info(f"回退处理msg文件成功: {msg_file_path.name}")
            except Exception as fallback_error:
                logger.error(f"回退处理msg文件 {msg_file_path.name} 时也出错: {str(fallback_error)}")
    
    def _extract_excel_attachments_from_msg(self, msg_obj: extract_msg.Message, email_filename: str) -> Optional[list[str]]:
        """
        从msg文件中提取Excel附件并保存到指定目录
        
        Args:
            msg_obj: extract_msg.Message对象
            email_filename: 原始邮件文件名(不含扩展名)
            
        Returns:
            Optional[list[str]]: 提取到的Excel附件文件名列表(如果有)，否则为None
        """
  
        # 获取附件
        attachments = msg_obj.attachments
        if attachments:
            # 创建与邮件文件同名的目录
            attachments_dir = self.processing_dir / email_filename
                            
            # Excel文件扩展名列表
            excel_extensions = ['.xls', '.xlsx']
            saved_attachments = []
            # 遍历附件
            for attachment in attachments:
                try:
                    # 获取附件名称
                    attachment_name = attachment.longFilename if attachment.longFilename else attachment.shortFilename
                    # 检查文件是否为Excel文件
                    if attachment_name and any(attachment_name.lower().endswith(ext) for ext in excel_extensions):
                        attachments_dir.mkdir(exist_ok=True)
                        # 保存附件到指定目录
                        # attachment_path = attachments_dir / attachment_name
                        attachment.save(customPath=str(attachments_dir))
                        saved_attachments.append(attachments_dir / attachment_name)
                        logger.info(f"已保存msg文件中的Excel附件: {attachment_name} 到 {attachments_dir.name}")
                except Exception as e:
                    logger.error(f"处理msg附件时出错: {str(e)}")
                    continue
            
            # 返回保存的Excel附件文件名列表
            return saved_attachments

    
