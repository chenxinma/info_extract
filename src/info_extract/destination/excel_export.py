import logging
import os
import json
from pathlib import Path
from openpyxl import Workbook
from typing import AsyncGenerator, List, Dict, Any, TypedDict

from ..config import output_info_items
from ..pipeline import Step, StepResult
from tqdm import tqdm

# 配置日志
logger = logging.getLogger(__name__)

class ColumnDefine(TypedDict):
    name: str
    type: str

class ExcelExporter(Step):
    def __init__(self, processing_dir: str, destination_dir: str):
        super().__init__()
        self.processing_dir = processing_dir
        self.destination_dir = destination_dir
        
        self.columns = output_info_items()
        
        # 确保输出目录存在
        os.makedirs(self.destination_dir, exist_ok=True)

    async def run(self) -> AsyncGenerator[StepResult, None]:
        # 收集所有 JSON 文件
        if not self.pre_results:
            logger.warning("未找到任何 JSON 文件，跳过导出。")
            return

        # 按文件分组
        grouped = self._grouping([file_path for file_path, _ in self.pre_results])
        for group_name, file_list in tqdm(grouped.items(), desc="导出工作表"):
            res = self._export_workbook(group_name, file_list)
            if res:
                yield res

    def _export_workbook(self, workbook_name: str, file_list: list[str]) -> tuple[str, int] | None:
        """导出工作簿
            Args:
                workbook_name (str): 工作簿名称
                file_list (list[str]): 文件列表
        """
        # 创建新的工作簿
        wb = Workbook()
        ws = wb.active
        if not ws:
            logger.error(f"工作簿 {workbook_name} 创建失败")
            return
        ws.title = "Sheet1"

        # 用于存储所有数据的列表
        all_data: List[Dict[str, Any]] = []

        # 遍历所有JSON文件，收集数据和确定表头
        for file_path in file_list:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    
                    # 处理JSON数组格式
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                all_data.append(item)
                                # 收集所有可能的键作为表头候选
                    # 也支持单个对象格式
                    elif isinstance(content, dict):
                        all_data.append(content)
                    else:
                        print(f"警告：文件 {file_path} 中的JSON格式不符合预期（应为对象或对象数组）")
            except json.JSONDecodeError as e:
                logger.error(f"解析文件 {file_path} 时出错：{e}")
            except Exception as e:
                logger.error(f"处理文件 {file_path} 时出错：{e}")

        if not all_data:
            logger.warning(f"工作簿 {workbook_name} 未找到有效的数据，跳过导出。")
            return

        # 从配置中提取表头
        headers = [col["name"] for col in self.columns]

        # 写入表头
        ws.append(headers)

        # 写入数据行
        for data in all_data:
            row = [data.get(h, "") if data.get(h) is not None else "" for h in headers]
            ws.append(row)

        # 保存到目标目录
        output_path = os.path.join(self.destination_dir, f"{workbook_name}_formated.xlsx")
        wb.save(output_path)
        return output_path, len(all_data)


    def _grouping(self, file_path_list: list[str]) -> Dict[str, list[str]]:
        """按文件分组 
            源文件名： data_sheet1.json, data_sheet2.json
            分组结果：
            {
                "data": [
                    "data_sheet1.json",
                    "data_sheet2.json"
                ]
            }
            Args:
                file_path_list (list[str]): 文件名列表
            Returns:
                Dict[str, list[str]]: 分组结果
        """
        grouped = {}
        for fname in file_path_list:
            path = Path(fname)
            group_name = "_".join(path.stem.split("_")[:-1])
            grouped.setdefault(group_name, []).append(fname)
        return grouped