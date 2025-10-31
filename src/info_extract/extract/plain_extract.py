import json
import logging
import os
from pathlib import Path
import time
from typing import Any, AsyncGenerator

from dotenv import load_dotenv
import langextract as lx
from langextract.data import AnnotatedDocument
from tqdm import tqdm
from typing_extensions import Generator

from ..pipeline import Step, StepResult
from .example import load_examples
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
        self.examples_file = Path(os.environ.get("EXTRACT_EXAMPLES", "./config/email.yaml"))

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
    
    async def run(self) -> AsyncGenerator[StepResult, None]:
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
        for extract_result in self.fetch_all(docs):   
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
        filename = self.processing_dir / f"{result.document[:-14]}.json"
        with open(filename, "w", encoding='utf-8') as fp:
            json.dump(result.data, fp, ensure_ascii = False, indent=4)
        logger.info(f"已保存文本文件: {filename}")
        return filename

    def fetch_all(self, docs: list[lx.data.Document], debug: bool = False)->Generator[ExtractResult]:
        lx_prompt, examples = load_examples(self.examples_file)

        result = lx.extract(
                text_or_documents=docs,
                prompt_description=lx_prompt,
                examples=examples,
                model = self.model,
                max_workers=5,            # Parallel processing for speed
                max_char_buffer=512,      # Smaller contexts for better accuracy
                debug=debug,
                prompt_validation_level=\
                    (lx.prompt_validation.PromptValidationLevel.OFF \
                        if debug == False else lx.prompt_validation.PromptValidationLevel.WARNING),
            )
        if isinstance(result, AnnotatedDocument):
            yield self._push_rows(result)
        else:
            _start_time = time.time()
            for r in tqdm(result, desc="信息提取", total=len(docs)):
                tqdm.write(f"已处理文档ID: {r.document_id}, 耗时: {time.time() - _start_time:.2f}秒")
                yield self._push_rows(r)
                _start_time = time.time()
