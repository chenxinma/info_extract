
import logging
import os
from pathlib import Path
import textwrap
from typing import Any, TypedDict

from dotenv import load_dotenv
import pandas as pd
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from typing_extensions import Generator
from tqdm import tqdm

from ..pipeline import Step

# 配置日志
logger = logging.getLogger(__name__)

class SpreadInfoFile(TypedDict):
    """
    表示Excel文件中的一条记录
    """
    file_name: Path
    attachments: list[Path]

class SpreadsheetExtractor(Step):
    """
    从Excel文件中提取数据
    """
    def __init__(self, processing_dir: str = "processing", destination_dir: str = "destination") -> None:
        load_dotenv()
        self._model_id = os.environ.get("EXTRACT_MODEL_ID")
        self._api_key = os.environ.get("EXTRACT_API_KEY")
        self._base_url = os.environ.get("EXTRACT_BASE_URL")

        _provider = OpenAIProvider(base_url=self._base_url, api_key=self._api_key)
        _model = OpenAIChatModel(model_name=str(self._model_id), provider=_provider)
        self.agent = Agent(
            model=_model, 
            instructions=textwrap.dedent("""
            你是一个数据分析师，你需要根据提供的邮件要求筛选df0 df1 df2...中的数据，生成取数的Python脚本。
            脚本中需要包含对DataFrame df0 df1 df2...的引用，返回结果为一个DataFrame，命名为result_df。
            注意：结果仅包含Python脚本
            """))

        self.processing_dir = Path(processing_dir)
        self.destination_dir = Path(destination_dir)
    
    def run(self) -> Generator[Any, None, None]:
        if self.pre_results is None or len(self.pre_results) == 0:
            return
        _files: list[SpreadInfoFile] = []
        if self.pre_results is not None:
            for pre_result in self.pre_results:
                f = SpreadInfoFile(file_name=self.processing_dir / f"{pre_result[0]}", 
                                   attachments=[ fd for fd in pre_result[1] ])
                _files.append(f)
    
        for f in tqdm(_files, desc="信息提取"):
            mail_body = ""
            with open(f["file_name"], "r", encoding="utf-8") as mail_file:
                mail_body = mail_file.read()
            dfs = self._read_attachements(f["attachments"])
            prompt = textwrap.dedent(f"""{self._show_dfs(dfs)}
            根据以上数据，筛选出符合要求的数据。
            筛选要求的邮件正文：{mail_body}
            """)
            result = self.agent.run_sync(prompt)
            result_df = self._run_python_script(result.output, dfs)
            if result_df is not None:
                # 检查result_df是否为空
                if not result_df.empty:
                    output_path = self.destination_dir / f"{f['file_name'].stem[:-12]}.json"
                    result_df.to_json(output_path, 
                                      orient="records", 
                                      index=False,
                                      indent=4,
                                      force_ascii=False)
                    yield output_path, result_df
    
    def verify(self, pre_result: Any) -> bool:
        return not pre_result[1] is None # 仅对有附件的邮件进行处理
    
    def _show_dfs(self, dfs: dict[str, pd.DataFrame]) -> str:
        """
        显示所有DataFrame
        """
        dfs_description = "所有的dataframe定义如下:\n"
        idx = 0
        for name, df in dfs.items():
            dfs_description += f"df{idx} # {name}\n{df.head()}\n\n"
            idx += 1
        
        return dfs_description

    def _read_attachements(self, attachments: list[Path]) -> dict[str, pd.DataFrame]:
        """
        读取附件中的Excel文件
        """
        _dfs: dict[str, pd.DataFrame] = {}
        for attachment in attachments:
            if attachment.suffix.lower() in [".xlsx", ".xls"]:
                _all_sheets = pd.read_excel(attachment, sheet_name=None)
                for sheet_name, df in _all_sheets.items():
                    _dfs[f"{attachment.stem}_{sheet_name}"] = df  # pyright: ignore[reportArgumentType]
        return _dfs

    def _run_python_script(self, script: str, dfs: dict[str, pd.DataFrame]) -> Any:
        """
        运行Python脚本
        """
        if script.startswith("```python"):
            script = script[10:-3]
        locals = {}
        # 为每个DataFrame添加到locals中
        for idx, df in enumerate(dfs.values()):
            locals[f"df{idx}"] = df
        logger.debug("script:", script)
        exec(script, locals=locals)
        return locals.get("result_df", None)