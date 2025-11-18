from collections import defaultdict
import logging
from pathlib import Path
import re
from typing import Any, AsyncGenerator, Optional, Tuple, TypedDict, TypeAlias

import numpy as np
import pandas as pd
from tqdm import tqdm
from text2vec import SentenceModel
from sklearn.metrics.pairwise import cosine_similarity

from ..pipeline import StepResult
from ..config import output_info_items

# 配置日志
logger = logging.getLogger(__name__)

Normalized : TypeAlias = Tuple[str, Optional[str], float]

class NormalizeOutput(TypedDict):
    normalized: list[Normalized]
    unmatched: list
    
class ColumnUtil:
    clean_patterns = [
        (r'[\n\r\t]', ' '),  # 换行符和制表符
        (r'\s+', ' '),       # 多个空格
        # (r'[\(（].*?[\)）]', ''),  # 括号内容
        (r'[\(\)（）]', ''),  # 括号
        (r'[①②③④⑤⑥⑦⑧⑨⑩]', ''), # 序号
        (r'[#@$%^&*]', ''),  # 特殊符号
    ]

    
    @classmethod
    def advanced_clean_text(cls, text: str) -> str:
        """高级文本清洗"""
        if not text:
            return ""
        
        # 应用清洗规则
        cleaned = text
        for pattern, replacement in cls.clean_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)

        # 如果过滤后为空，返回原始文本的主要部分
        if not cleaned:
            # 提取最长连续中文字符串
            chinese_parts = re.findall(r'[\u4e00-\u9fff]+', text)
            if chinese_parts:
                cleaned = max(chinese_parts, key=len)
            else:
                cleaned = text[:20]  # 截取前20个字符
        
        return cleaned

class DataFrameMappingExtract:
    def __init__(self, processing_dir: str = "processing") -> None:
        self.processing_dir = Path(processing_dir)

        info_items = output_info_items()
        self.standard_headers = [ item["name"] for item in info_items ]
        standard_describes = [ item["describe"] for item in info_items ]
        self.normalizer = SemanticHeaderNormalizer(self.standard_headers, standard_describes)

    async def run(self) -> AsyncGenerator[StepResult, None]:
        """
        运行DataFrame映射提取
        """
        if self.pre_results is None or len(self.pre_results) == 0:
            return
        
        if self.pre_results is not None:
            for sheet_pq, _ in tqdm(self.pre_results, desc="信息表提取"):
                _sheet_pq_path = Path(sheet_pq)
                res = await self._fetch_one(_sheet_pq_path)
                if res:
                    yield res


    async def _fetch_one(self, sheet_pq_path:Path) -> Tuple[str, Any] | None:
        """
        提取单个DataFrame映射
        """
        raw_df = pd.read_parquet(sheet_pq_path)
        raw_df = self._clean_columns(raw_df)

        df_headers = raw_df.columns.tolist()
        result = self.normalizer.normalize(df_headers, min_confidence=0.4)

        for i, (orig, normalized) in enumerate(zip(df_headers, result['normalized_headers'])):
            confidence = result['confidence_scores'][i] if i < len(result['confidence_scores']) else 0
            logger.info(f"  '{orig}' -> '{normalized}' (置信度: {confidence:.3f})")
        
        return "", len(raw_df)

    def _clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        columns = list(df.columns)
        _clean_columns = [ ColumnUtil.advanced_clean_text(c) for c in columns ]
        df.columns = _clean_columns
        return df

LEARNING_PATH = './config/header_normalizer_learning.pkl'

class SemanticHeaderNormalizer:
    def __init__(self, standard_headers: list[str], standard_describes: list[str]) -> None:
        self.standard_headers = standard_headers        
        self.model = SentenceModel('../../models/bert/text2vec-base-chinese')
        self.standard_header_index = defaultdict(int)

        # 加载说明信息
        for i, (label, describe) in enumerate(zip(standard_headers, standard_describes)):
            self.standard_header_index[label] = i
            for synonym in self._get_synonyms(describe):
                self.standard_header_index[synonym] = i
        
        self.standard_representations = self._get_representations(list(self.standard_header_index.keys()))

    def _get_synonyms(self, describe: str):
        """
        从说明中获取同义词
        label = 证件号码
        describe = 同义词，例如："身份证号"、"身份证号码"等
        将 "身份证号" 、"身份证号码" 取出
        """
        if describe is None or not "同义词" in describe:
            return
        
        pattern = r"(\"(?P<word>[^\"]+)\")"
        matches = re.finditer(pattern, describe, re.MULTILINE)

        for m in matches:
            w = m.group("word")
            if w:
                yield w
    
    def _get_representations(self, texts: list[str]) -> np.ndarray:
        """获取文本的语义表示"""
        embeddings = []
        for text in texts:
            embedding = self.model.encode(text)
            embeddings.append(embedding)
        return np.array(embeddings)
    
    def semantic_similarity(self, 
                            input_headers: list[str], 
                            input_representations: np.ndarray, 
                            min_confidence: float) -> list[Normalized]:
        """计算语义相似度"""
        mapping = []
        sim_matrix = cosine_similarity(self.standard_representations, input_representations) 

        for i, (_, pos) in enumerate(self.standard_header_index.items()):
            best_idx = np.argmax(sim_matrix[i])
            best_score = sim_matrix[i][best_idx]

            if best_score > min_confidence:
                mapping.append((self.standard_headers[pos], input_headers[best_idx], best_score))
        return mapping

    def normalize(self, input_headers: list[str], 
                  min_confidence: float = 0.5) -> NormalizeOutput:
        """
        基于上下文进行表头标准化
        
        Args:
            input_headers: 输入表头列表
            context_headers: 上下文表头列表（可选）
            min_confidence: 最小置信度
        """
        mapping = []
        unmatched = []

        input_representations = self._get_representations(input_headers)
        mapping = self.semantic_similarity(input_headers, input_representations, min_confidence)
        normalized = self._contextual_reassessment(mapping)

        _matched_headers = [ matched[1] for matched in normalized if matched[1]]
        for header in input_headers:
            if not header in _matched_headers:
                unmatched.append(header)
        
        return NormalizeOutput(normalized=normalized, unmatched=unmatched)
    
    def _contextual_reassessment(self, normalized: list[Normalized])->list[Normalized]:
        """基于上下文重新评估匹配结果"""
        fixed_normalized = []

        header_positions = defaultdict(list)
        for i, match in enumerate(normalized):
            if match[1]:
                header_positions[match[1]].append(i)
        
        # 检查重复匹配（同一个标准表头匹配多个输入）
        for _, positions in header_positions.items():
            if len(positions) > 1:
                # 找到置信度最高的一个，其他的重新匹配
                best_pos = max(positions, 
                               key=lambda pos: normalized[pos][2])
                for pos in positions:
                    if pos != best_pos:
                        normalized[pos] = (normalized[pos][0], None, 0)

        # 清理多余的置空匹配结果
        _normalized_map = defaultdict(list)
        for nz in normalized:
            if nz[2] == 0:
                continue
            _normalized_map[nz[0]].append(nz)
        
        for header in self.standard_headers:
            if header in _normalized_map:
                fixed_normalized.append(max(_normalized_map[header],
                                               key=lambda nz: nz[2]))
            else:
                fixed_normalized.append((header, None, 0))
        
        return fixed_normalized

