import logging
from pathlib import Path
import re
from typing import AsyncGenerator, Optional

from bs4 import BeautifulSoup
import chardet
import extract_msg
from msg_parser import MsOxMessage
from markdownify import markdownify as md
from typing_extensions import Generator

from ..pipeline import StepResult
from .email import EmailReader


logger = logging.getLogger(__name__)

class MSGReader(EmailReader):
    """处理msg邮件文件，提取正文内容"""

    async def run(self) -> AsyncGenerator[StepResult, None]:
        """处理source目录下的所有eml和msg文件"""
        # 获取所有msg文件
        
        msg_files = list(self.source_dir.glob("*.msg"))

        for msg_fp in msg_files:
            step_result = await self._process_msg_file(msg_fp)
            if step_result:
                yield step_result

    async def _process_msg_file(self, msg_file_path: Path) -> StepResult | None:
        """
        处理单个msg文件
        
        Args:
            msg_file_path: msg文件路径
            
        Returns:
            StepResult | None: 处理结果(包含txt文件路径和Excel附件列表)，如果出错则为None
        """
        try:
            # 使用extract-msg处理msg文件
            msg_obj = extract_msg.Message(msg_file_path)
            
            # 提取正文（优先获取HTML，然后是纯文本）
            body = None
            try:
                htmlBody = msg_obj.htmlBody
                if not htmlBody:
                    body = msg_obj.body.decode('utf-8', errors='ignore')  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
                else:
                    body = md(htmlBody.decode('utf-8', errors='ignore'))
            except UnicodeDecodeError:
                
                msg_obj2 = MsOxMessage(msg_file_path)
                msg_properties = msg_obj2.get_properties()
                if 'Body' in msg_properties:
                    body = msg_properties['Body']
                if 'HtmlBody' in msg_properties:
                    htmlBody = msg_properties['HtmlBody']
                    body = md(htmlBody)   
            finally:
                msg_obj.close()


            # 保存为txt文件
            text_file = self._save_text_file(body, msg_file_path.stem)   # pyright: ignore[reportArgumentType]
            
            msg_obj = extract_msg.Message(msg_file_path)
            # 提取并保存Excel附件
            attachments = self._extract_excel_attachments_from_msg(msg_obj, msg_file_path.stem)

            logger.info(f"成功处理msg文件: {msg_file_path.name}")
            return text_file, attachments

        except Exception as e:
            logger.error(f"处理msg文件 {msg_file_path.name} 时出错: {str(e)}")
            
            # 移动到error目录
            error_dir = self.source_dir.parent / "error"
            error_dir.mkdir(exist_ok=True)
            msg_file_path.rename(error_dir / msg_file_path.name)
            return None
    
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
            if len(saved_attachments) > 0:
                return saved_attachments
            else:
                return None

    def _get_html_charset(self, msg):
        html_body = msg.getSaveHtmlBody(charset='latin-1')
        # 1. 从 HTML meta 标签提取
        soup = BeautifulSoup(html_body, "html.parser")
        meta_tag = soup.find("meta", attrs={"http-equiv": "Content-Type"}) or soup.find("meta", attrs={"charset": True})
        charset = None
        if meta_tag:
            if "http-equiv" in meta_tag.attrs:  # pyright: ignore[reportAttributeAccessIssue]
                content = meta_tag.get("content", "")  # pyright: ignore[reportAttributeAccessIssue]
                charset_match = re.search(r'charset=([\w-]+)', content, re.IGNORECASE)  # pyright: ignore[reportCallIssue, reportArgumentType]
                if charset_match:
                    charset = charset_match.group(1).strip()
            else:
                charset = meta_tag.get("charset", "").strip()  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]

        # 2. 从邮件头提取
        if not charset:
            content_type = msg.header.get("Content-Type", "")
            header_match = re.search(r'charset=([\w-]+)', content_type, re.IGNORECASE)
            if header_match:
                charset = header_match.group(1).strip()

        # 3. 自动检测
        if not charset:
            if isinstance(html_body, str):
                html_bytes = html_body.encode("latin-1")
            else:
                html_bytes = html_body
            detected = chardet.detect(html_bytes)
            charset = detected["encoding"]

        return charset.lower() if charset else "utf-8"  # 默认 utf-8
