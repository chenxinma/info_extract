import logging
import os
from pathlib import Path
import textwrap
from typing import Any, AsyncGenerator, Tuple

import hashlib
from dotenv import load_dotenv
import duckdb
import pandas as pd
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from tqdm import tqdm

from ..config.profile_manager import ProfileManager
from ..ace import PlaybookManager, curate, reflect
from ..config import (get_cached_mapping_sql, 
                      save_mapping_sql)
from ..pipeline import Step, StepResult

# 配置日志
logger = logging.getLogger(__name__)

playbookManager = PlaybookManager("./config", "spreadsheet")

class SpreadsheetExtractor(Step):
    """
    从Excel文件中提取数据
    """
    def __init__(self, processing_dir: str = "processing") -> None:
        load_dotenv()
        self._model_id = os.environ.get("SPREAD_MODEL_ID")
        self._api_key = os.environ.get("SPREAD_API_KEY")
        self._base_url = os.environ.get("SPREAD_BASE_URL")

        _provider = OpenAIProvider(base_url=self._base_url, api_key=self._api_key)
        _model = OpenAIChatModel(model_name=str(self._model_id), provider=_provider)
        self.agent = Agent(
            model=_model, 
            instructions=self.agent_instructions)

        self.processing_dir = Path(processing_dir)
    
    def agent_instructions(self) -> str:
        return textwrap.dedent(f"""
            你是一个数据分析师，你需要根据提供DataFrame中的数据，生成取数的SQL脚本。SQL遵守duckdb的SQL方言。
            注意：
            - 结果仅包含SQL脚本
            - 只要完成列与信息项的映射。
            """)
    
    async def run(self, profile_manager: ProfileManager) -> AsyncGenerator[StepResult, None]:
        if self.pre_results is None or len(self.pre_results) == 0:
            return
        
        if self.pre_results is not None:
            for sheet_pq, _ in tqdm(self.pre_results, desc="信息表提取"):
                _sheet_pq_path = Path(sheet_pq)
                res = await self._fetch_one(_sheet_pq_path, profile_manager)
                if res:
                    yield res

    async def _fetch_one(self, sheet_pq_path:Path, profile_manager: ProfileManager) -> Tuple[str, Any] | None:
        raw_df = pd.read_parquet(sheet_pq_path)
        raw_df = self._clean_columns(raw_df)

        hash_key = self._hash_columns(raw_df.columns)
        cached_sql = get_cached_mapping_sql(profile_manager.get_config_db(), hash_key)
        result_df = None
        
        if cached_sql:
            # 运行取数脚本
            result_df = self._run_sql(cached_sql, raw_df)
        else:
            # 生成取数脚本
            result = await self.agent.run(
                textwrap.dedent(f"""
                {profile_manager.generate_info_item_define_prompt()}
                {playbookManager.list_playbooks()}
                {profile_manager.generate_sample_sql()}
                df's column names：{raw_df.columns}
                df_sheet_name：{sheet_pq_path.stem}
                生成查询 **df** 获取信息项的SQL。
                """)
            )
            try:
                # 运行取数脚本
                result_df = self._run_sql(result.output, raw_df)
                save_mapping_sql(profile_manager.get_config_db(), hash_key, result.output)
            except Exception as exp:
                logger.warning(f"取数异常 {str(exp)}")
                logger.warning(result.output)
                logger.warning(f"sheet 表头：{raw_df.columns}")
                ref = await reflect(playbookManager, result.all_messages(), exp)
                _ = await curate(playbookManager, ref)
        
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

    def verify(self, pre_result: StepResult) -> bool:
        return pre_result[0].endswith(".parquet")
    
    def _run_sql(self, sql:str, df: pd.DataFrame) -> pd.DataFrame | None:
        """
        运行SQL脚本
        """
        if sql.startswith("```sql"):
            sql = sql[7:-3]
        
        _hash_key = self._hash_columns(df.columns)
        with open(self.processing_dir / f"{_hash_key}.log", "w", encoding="utf-8") as fp:
            fp.write(sql)
            fp.write('\n')
            fp.write('---\n')
            fp.writelines("\n".join(df.columns))
        
        return duckdb.sql(sql).df().copy()
    
    def _clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        columns = list(df.columns)
        _clean_columns = [ self._fix_column(c) for c in columns ]
        df.columns = _clean_columns
        return df
    
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
    
    def _hash_columns(self, columns) -> str:
        _cols = str(columns)

        h = hashlib.sha1()
        h.update(_cols.encode())
        return h.hexdigest()

