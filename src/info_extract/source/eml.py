import email
from email.header import decode_header
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional

from markdownify import markdownify as md

from ..pipeline import StepResult
from .email import EmailReader

logger = logging.getLogger(__name__)

class EMLReader(EmailReader):
    """处理eml邮件文件，提取正文内容"""

    async def run(self) -> AsyncGenerator[StepResult, None]:
        eml_files = self.source_files(self.source_dir, "*.eml")
        logger.info(f"找到 {len(eml_files)} 个eml文件")

        for eml_fp in eml_files:
            step_result = await self._process_file(eml_fp)
            if step_result:
                yield step_result
    
    async def _process_file(self, eml_file_path: Path) -> StepResult | None:
        """
        处理单个eml文件
        
        Args:
            eml_file_path: eml文件路径
        """
        try:
            # 读取eml文件
            with open(eml_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_email = f.read()
            
            # 解析邮件
            email_message = email.message_from_string(raw_email)            
            # 提取正文
            body = self._extract_body(email_message)            
            # 保存为txt文件
            text_file = self._save_text_file(body, eml_file_path.stem)
            
            # 提取并保存Excel附件
            attachments = self._extract_excel_attachments(email_message, eml_file_path.stem)
            
            logger.info(f"成功处理eml文件: {eml_file_path.name}")
            return text_file, attachments
            
        except Exception as e:
            logger.error(f"处理eml文件 {eml_file_path.name} 时出错: {str(e)}")
            # 移动到error目录
            error_dir = self.source_dir.parent / "error"
            error_dir.mkdir(exist_ok=True)
            eml_file_path.rename(error_dir / eml_file_path.name)
            return None
    
    def _extract_body(self, email_message):
        """
        从email.message.Message对象中提取正文，保持HTML格式内容不变
        
        Args:
            email_message: email.message.Message对象
            
        Returns:
            str: 邮件正文内容
        """
        body = ""
        text_body = ""
        html_body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # 跳过附件
                if "attachment" not in content_disposition:
                    charset = part.get_content_charset()
                    try:
                        part_text = part.get_payload(decode=True)
                        if part_text:
                            payload = part_text.decode(charset or 'utf-8', errors='ignore')
                            
                            if content_type == "text/plain":
                                text_body = payload
                            elif content_type == "text/html":
                                html_body = payload
                    except Exception as e:
                        logger.error(f"解码邮件部分内容时出错: {str(e)}")
            
            # 优先返回HTML内容，如果存在的话
            if html_body:
                body = md(html_body)
            else:
                body = text_body
        else:
            # 非多部分邮件，直接获取正文内容
            content_type = email_message.get_content_type()
            charset = email_message.get_content_charset()
            try:
                body = email_message.get_payload(decode=True).decode(charset or 'utf-8', errors='ignore')
                logger.info(f"非多部分邮件内容类型: {content_type}")
            except Exception as e:
                logger.error(f"解码非多部分邮件内容时出错: {str(e)}")
                body = ""
            
        return body
    
    def _extract_excel_attachments(self, email_message, email_filename: str) -> Optional[list[str]]:
        """
        提取邮件中的Excel附件并保存到指定目录
        
        Args:
            email_message: email.message.Message对象
            email_filename: 原始邮件文件名(不含扩展名)
            
        Returns:
            Optional[list[str]]: 保存的Excel附件文件名列表，若没有附件则返回None
        """
        # 创建与邮件文件同名的目录
        attachments_dir = self.processing_dir / email_filename
        attachments = []
        # Excel文件扩展名列表
        excel_extensions = ['.xls', '.xlsx']
        
        if email_message.is_multipart():
            for part in email_message.walk():
                # 获取附件文件名
                filename = part.get_filename()
                if not filename:
                    continue
                content_disposition = str(part.get("Content-Disposition"))
                if filename.startswith("=?"):
                    _fname, _charset = decode_header(filename)[0]
                    filename = _fname.decode(_charset) if _charset else _fname.decode('utf-8', errors='ignore')

                # 检查是否为附件且文件名不为空
                if "attachment" in content_disposition or "inline" in content_disposition:
                    # 检查文件是否为Excel文件
                    if any(filename.lower().endswith(ext) for ext in excel_extensions):
                        try:
                            attachments_dir.mkdir(exist_ok=True)
                            # 解码附件内容
                            attachment_data = part.get_payload(decode=True)
                            if attachment_data:
                                # 保存附件到指定目录
                                attachment_path = attachments_dir / filename
                                with open(attachment_path, 'wb') as f:
                                    f.write(attachment_data)
                                logger.info(f"已保存Excel附件: {filename} 到 {attachments_dir.name}")
                                attachments.append(attachment_path)
                        except Exception as e:
                            logger.error(f"保存Excel附件 {filename} 时出错: {str(e)}")
        if len(attachments) > 0:
            return attachments
        else:
            return None

