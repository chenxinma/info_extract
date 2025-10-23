import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
import langextract as lx
from langextract.data import AnnotatedDocument
from tqdm import tqdm

from .example import load_examples
from .qwen import QwenProvider
from .type import ExtractResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlainExtractor:
    def __init__(self, processing_dir: str = "processing", destination_dir: str = "dist") -> None:
        load_dotenv()
        self._model_id = os.environ.get("EXTRACT_MODEL_ID")
        self._api_key = os.environ.get("EXTRACT_API_KEY")
        self._base_url = os.environ.get("EXTRACT_BASE_URL")
        self.examples_file = Path(os.environ.get("EXTRACT_EXAMPLES", "./config/email.yaml"))

        config = lx.factory.ModelConfig(
            model_id=self._model_id,
            provider="QwenProvider",
            provider_kwargs={
                "api_key": self._api_key,
                "base_url": self._base_url
            },
        )
        self.model = lx.factory.create_model(config)
        
        self.processing_dir = Path(processing_dir)
        self.destination_dir = Path(destination_dir)

        # 确保目录存在
        self.processing_dir.mkdir(exist_ok=True)
        self.destination_dir.mkdir(exist_ok=True)
    
    def extract(self):
        _files = list(self.processing_dir.glob("*.txt"))
        # 准备文档
        docs = []
        
        for fp in _files:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
                doc = lx.data.Document(content,
                                       document_id=fp.stem)
                docs.append(doc)

        result = self._fetch(docs)
        # 处理结果
        if isinstance(result, AnnotatedDocument):
            result = [result]

        for r in tqdm(result, desc="信息提取"):
            data = []
            extract_result = ExtractResult(document=r.document_id, data=[])
            for extraction in r.extractions:   # pyright: ignore[reportOptionalIterable]
                if len(extraction.extraction_text) == 0:
                    continue
                
                data.append({
                        extraction.extraction_class: extraction.extraction_text, 
                        'index': extraction.extraction_index,
                        'group_index': extraction.group_index
                    })
            extract_result.data = data
            self._save_json(extract_result)

    def _save_json(self, result: ExtractResult):
        filename = self.destination_dir / f"{result.document}.json"
        with open(filename, "w", encoding='utf-8') as fp:
            json.dump(result.data, fp, ensure_ascii = False, indent=2)
        logger.info(f"已保存文本文件: {filename}")

    def _fetch(self, docs: list[lx.data.Document]):
        lx_prompt, examples = load_examples(self.examples_file)

        result = lx.extract(
                text_or_documents=docs,
                prompt_description=lx_prompt,
                examples=examples,
                model = self.model,
                max_char_buffer=2000,
                debug=False,
            )
        return result
        