import json
import logging
import os
from pathlib import Path
import textwrap
import time
from typing import AsyncGenerator

from dotenv import load_dotenv
import langextract as lx
from langextract.data import AnnotatedDocument
from tqdm import tqdm
from typing_extensions import Generator

from ..config.profile_manager import ProfileManager
from ..pipeline import Step, StepResult
from .tokenizer import tokenize
from .type import ExtractResult

lx.core.tokenizer.tokenize = tokenize

# 配置日志
logger = logging.getLogger(__name__)

class PlainExtractor(Step):
    def __init__(self, processing_dir: str = "processing") -> None:
        load_dotenv()
        self._model_id = os.environ.get("EXTRACT_MODEL_ID")
        self._api_key = os.environ.get("EXTRACT_API_KEY")
        self._base_url = os.environ.get("EXTRACT_BASE_URL")
        
        config = lx.factory.ModelConfig(
            model_id=self._model_id,
            provider="OpenAILanguageModel",
            provider_kwargs={
                "api_key": self._api_key,
                "base_url": self._base_url
            },
        )
        self.model = lx.factory.create_model(config)
        
        self.processing_dir = Path(processing_dir)

        # 确保目录存在
        self.processing_dir.mkdir(exist_ok=True)
    
    async def run(self, profile_manager: ProfileManager) -> AsyncGenerator[StepResult, None]:
        if self.pre_results is None or len(self.pre_results) == 0:
            return
        _files = [self.processing_dir / f"{pre_result[0]}" for pre_result in self.pre_results]
        logger.debug("plain extract _files:", _files)
        # 准备文档
        docs = []
        
        for fp in _files:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
                doc = lx.data.Document(content,
                                       document_id=fp.stem)
                docs.append(doc)
    
        # 处理结果
        async for extract_result in self.fetch_all(docs, profile_manager):   
            assert extract_result is not None, "extract_result must not be None"
            filename = self._save_json(extract_result)
            yield str(filename), extract_result
    
    def verify(self, pre_result: StepResult) -> bool:
        return pre_result[0].endswith(".txt") and pre_result[1] is None # 仅对纯文本没有附件
    
    def _push_rows(self, result:AnnotatedDocument)->ExtractResult:
        assert result is not None, "result must not be None"
        assert result.extractions is not None, "extractions must not be None"

        data = {}
        for extraction in result.extractions:
            if len(extraction.extraction_text) == 0 or extraction.attributes is None:
                continue
            line_group:str = \
                extraction.attributes.get("line_group", None)  # pyright: ignore[reportOptionalMemberAccess, reportAssignmentType]
            if line_group is None:
                continue
            if line_group not in data:
                data[line_group] = {}
            data[line_group][extraction.extraction_class] = \
                extraction.extraction_text
        return ExtractResult(document=result.document_id, data=list(data.values()))

    def _save_json(self, result:ExtractResult):
        filename = self.processing_dir / f"{result.document}.json"
        with open(filename, "w", encoding='utf-8') as fp:
            json.dump(result.data, fp, ensure_ascii = False, indent=4)
        logger.info(f"已保存文本文件: {filename}")
        return filename

    async def fetch_all(self, docs: list[lx.data.Document], profile_manager: ProfileManager, debug: bool = False)->AsyncGenerator[ExtractResult, None]:
        lx_prompt = textwrap.dedent(f"""
        你是人力资源服务专业，接受来自客户HR的人员入职、离职的信息。
        严格按照邮件内容抽取，不要遗漏任何人员信息。
        请忽略邮件开通的寒暄和邮件结尾的名片信息。
        ** 注意：** 姓名时保持原始姓名格式，英文或拼音名字不要进行任何修        你是人力资源服务专业，接受来自客户HR的人员入职、离职的信息。
        严格按照邮件内容抽取，不要遗漏任何人员信息。
        请忽略邮件开通的寒暄和邮件结尾的名片信息。
        ** 注意：** 姓名时保持原始姓名格式，英文或拼音名字不要进行任何修改或翻译。改或翻译。
        {profile_manager.generate_info_item_define_prompt()}
        """)
        examples = profile_manager.get_examples()

        result = lx.extract(
                text_or_documents=docs,
                prompt_description=lx_prompt,
                examples=examples,
                model = self.model,
                max_workers=1,            # Parallel processing for speed
                max_char_buffer=512,      # Smaller contexts for better accuracy
                debug=debug,
                prompt_validation_level=\
                    (lx.prompt_validation.PromptValidationLevel.OFF \
                        if debug == False else lx.prompt_validation.PromptValidationLevel.WARNING),
            )
        if isinstance(result, AnnotatedDocument):
            yield self._push_rows(result)
        else:
            # _start_time = time.time()
            for r in tqdm(result, desc="信息提取", total=len(docs)):
                # tqdm.write(f"已处理文档ID: {r.document_id}, 耗时: {time.time() - _start_time:.2f}秒")
                yield self._push_rows(r)
                # _start_time = time.time()
