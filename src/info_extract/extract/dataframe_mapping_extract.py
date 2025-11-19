import os
from collections import defaultdict
import logging
from pathlib import Path
import re
import textwrap
from typing import Any, AsyncGenerator, Optional, Tuple, TypedDict, TypeAlias

from dotenv import load_dotenv
import duckdb
import numpy as np
import pandas as pd
import torch
from tqdm import tqdm
from transformers import BertTokenizer, BertModel
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
        sql = self.make_sql(result['normalized'], sheet_pq_path.stem)
        
        # 运行取数脚本
        result_df = self._run_sql(sql, raw_df)
        
        if result_df is None:
            logger.error(f"没有数据 {sheet_pq_path}")
            return "", None

        result_df = self._fix_date(result_df)
        result_df = self._fix_ym(result_df)
        # 保存结果
        result_json = self.processing_dir / f"{sheet_pq_path.stem}.json"
        result_df.to_json(result_json, 
                            index=False, 
                            orient="records", 
                            force_ascii=False,
                            indent=4)
        return str(result_json), len(result_df)
    
    def distinguish_work_type(self, normalized: Normalized, sheet_name:str) -> str:
        if not "入离职" in sheet_name:
            if any([ w in sheet_name for w in ["离职", "减员"]]):
                return "'离职' as \"作业\""
            elif any([ w in sheet_name for w in ["入职", "增员"]]):
                return "'入职' as \"作业\""
        
        has_join_date = any([ not n[1] is None for n in normalized if n[0] == "入职日期"])
        has_leave_date = any([ not n[1] is None for n in normalized if n[0] == "离职日期"])
        if has_join_date and not has_leave_date:
            return "'入职' as \"作业\""
        elif not has_join_date and has_leave_date:
            return "'离职' as \"作业\""
        elif has_join_date and has_leave_date:
            return textwrap.dedent("""case 
                        when not "离职日期" is null then '离职'
                        when not "入职日期" is null then '入职'
                        else ''
                    end as "作业" """)
        else:
            return "'' as \"作业\""

    def make_sql(self, normalized: Normalized, sheet_name:str) -> str:
        select_columns = [self.distinguish_work_type(normalized, sheet_name)]
        for std_header, input_header, _ in normalized:
            if "作业" == std_header:
                continue

            if input_header:
                select_columns.append(f"\"{input_header}\" as \"{std_header}\"")
            else:
                select_columns.append(f"null as \"{std_header}\"")
        
        sql = f"SELECT {",".join(select_columns)} FROM df"
        return sql
    
    def verify(self, pre_result: StepResult) -> bool:
        return pre_result[0].endswith(".parquet")

    def _clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        columns = list(df.columns)
        _clean_columns = [ ColumnUtil.advanced_clean_text(c) for c in columns ]
        df.columns = _clean_columns
        return df

    def _run_sql(self, sql:str, df: pd.DataFrame) -> pd.DataFrame | None:
        """
        运行SQL脚本
        """
        return duckdb.sql(sql).df().copy()

    def _fix_column(self, col: str) -> str:
        return col.replace('\n', '').replace('\r', '') \
            .replace('（', '').replace('）', '') \
            .replace('(', '').replace(')', '') \
            .replace('"', '').replace('\'', '') \
            .replace(' ', '').strip()
    
    def _fix_date(self, df:pd.DataFrame) -> pd.DataFrame:
        def _tanse_dt(dt):
            try:
                return pd.to_datetime(dt).strftime('%Y-%m-%d')
            except:
                return dt

        for col in df.columns:
            if col.endswith("日期"):
                df[col] = df[col].apply(_tanse_dt)
        return df
    
    def _fix_ym(self, df:pd.DataFrame) -> pd.DataFrame:
        def _tanse_dt(dt):
            try:
                return pd.to_datetime(dt).strftime('%Y-%m')
            except:
                return dt
    
        for col in df.columns:
            if col.endswith("月"):
                df[col] = df[col].apply(_tanse_dt)
        return df
    

LEARNING_PATH = './config/header_normalizer_learning.pkl'
load_dotenv()
MODEL_PATH = os.environ.get("TEXT2VEC_MODEL", "Jerry0/text2vec-base-chinese")

class SemanticHeaderNormalizer:
    def __init__(self, standard_headers: list[str], standard_describes: list[str]) -> None:
        self.standard_headers = standard_headers        
        # self.model = SentenceModel('')
        self.tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
        self.model = BertModel.from_pretrained(MODEL_PATH)
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

    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0]  # First element of model_output contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    def _get_representations(self, texts: list[str]) -> np.ndarray:
        """获取文本的语义表示"""
        # embeddings = []
        # for text in texts:
        #     embedding = self.model.encode(text)
        #     embeddings.append(embedding)
        # return np.array(embeddings)
        # Tokenize texts
        encoded_input = self.tokenizer(texts, padding=True, truncation=True, return_tensors='pt')
        # Compute token embeddings
        with torch.no_grad():
            model_output = self.model(**encoded_input)
        # Perform pooling. In this case, mean pooling.
        sentence_embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])
        return sentence_embeddings
    
    def semantic_similarity(
        self,
        input_headers: list[str],
        input_representations: np.ndarray,
        min_confidence: float
    ) -> list[Normalized]:
        # Step 1: 计算原始相似度矩阵 (num_synonyms x num_inputs)
        sim_matrix = cosine_similarity(self.standard_representations, input_representations)
        
        # Step 2: 为每个标准字段聚合其所有同义词的最大相似度
        num_std = len(self.standard_headers)
        num_input = len(input_headers)
        std_to_input_sim = np.full((num_std, num_input), -1.0)  # 初始化为 -1

        for syn_idx, (_, std_pos) in enumerate(self.standard_header_index.items()):
            # 对每个输入，取该标准字段下所有同义词的最大相似度
            std_to_input_sim[std_pos] = np.maximum(std_to_input_sim[std_pos], sim_matrix[syn_idx])

        # Step 3: 构建候选匹配列表 (score, std_idx, input_idx)
        candidates = []
        for std_idx in range(num_std):
            for inp_idx in range(num_input):
                score = std_to_input_sim[std_idx, inp_idx]
                if score >= min_confidence:
                    candidates.append((score, std_idx, inp_idx))

        # 按置信度降序排序（高分优先分配）
        candidates.sort(key=lambda x: x[0], reverse=True)

        # Step 4: 贪心分配，避免冲突
        assigned_std = set()
        assigned_input = set()
        result = [None] * num_std  # 每个标准字段的匹配结果

        for score, std_idx, inp_idx in candidates:
            if std_idx in assigned_std or inp_idx in assigned_input:
                continue  # 已被分配，跳过
            # 分配成功
            assigned_std.add(std_idx)
            assigned_input.add(inp_idx)
            result[std_idx] = (
                self.standard_headers[std_idx],
                input_headers[inp_idx],
                float(score)
            )

        # Step 5: 补全未匹配的标准字段
        for std_idx in range(num_std):
            if result[std_idx] is None:
                result[std_idx] = (self.standard_headers[std_idx], None, 0.0)

        return result  # list of (std_header, input_header, score)

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

