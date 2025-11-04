import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, TypedDict
import warnings
from openpyxl import load_workbook
from openpyxl.styles.proxy import StyleProxy
from openpyxl.styles.colors import RGB, COLOR_INDEX
import pandas as pd
from typing_extensions import Generator

from ..pipeline import Step, StepResult

logger = logging.getLogger(__name__)
warnings.simplefilter("ignore", category=UserWarning)

class SheetMeta(TypedDict):
    sheet_name: str
    header_row: int
    columns: list[str]
    sample_data: list[dict[str, Any]]

class ExcelReader(Step):
    """处理Excel文件，提取sheet内容"""
    def __init__(self, source_dir: str = "source", processing_dir: str = "processing"):
        """
        初始化Excel处理器
        
        Args:
            source_dir: 源文件目录路径
            processing_dir: 处理后文件保存目录路径
        """
        self.source_dir = Path(source_dir)
        self.processing_dir = Path(processing_dir)
        
        # 确保目录存在
        self.source_dir.mkdir(exist_ok=True)
        self.processing_dir.mkdir(exist_ok=True)
        self.meta_list:list[SheetMeta] = []
    
    async def run(self) -> AsyncGenerator[StepResult, None]:
        """
        处理Excel文件xls或xlsx，提取sheet内容
        
        Yields:
            按sheet返回parquest文件路径
        """
        for excel_file in self.source_dir.glob("*.xls*"):
            if excel_file.stem.endswith("~"):
                continue
            book = load_workbook(str(excel_file))
            for sheet_name in book.sheetnames:
                sheet = book[sheet_name]
                # 检查sheet是否为隐藏状态，如果是则跳过
                if sheet.sheet_state == 'hidden' or sheet.sheet_state == 'veryHidden':
                    logger.debug(f"sheet {sheet_name} 是隐藏状态，已跳过处理")
                    continue
                
                header_row = self.find_header_row(sheet, header_candidates=["姓名","身份证"])
                if header_row == -1:
                    continue
                
                fname = f"{excel_file.stem}_{sheet_name}"
                # 读取数据
                df = pd.read_excel(excel_file, 
                                   sheet_name=sheet_name, 
                                   header=header_row,
                                   dtype=str)
                df.dropna(subset=["姓名"], inplace=True) # 姓名为空的行，删除
                n_rows = len(df)
                if n_rows == 0:
                    logger.warning(f"sheet {fname} 无数据")
                    continue
                # 添加行颜色列
                df["行颜色"] = self.fetch_row_colors(sheet, header_row, n_rows)
                meta = SheetMeta(
                    sheet_name=fname,
                    header_row=header_row,
                    columns=list(df.columns),
                    sample_data=df.sample(min(3, n_rows)).to_dict(orient="records")
                )
                self.meta_list.append(meta)
                parquet_file = self.processing_dir / f"{fname}.parquet"
                df.to_parquet(parquet_file, index=False)
                yield str(parquet_file), excel_file.stem
        
        with open(self.processing_dir / "excel_meta", "w", encoding="utf-8") as f:
            json.dump(self.meta_list, f, ensure_ascii=False, indent=4)
        
    def fetch_row_colors(self, sheet, header_row: int, row_count: int) -> list[str]:
        """
        获取指定行的背景颜色
        
        Args:
            sheet: 工作表对象
            header_row: 表头行号（从0开始）
            row_count: 要获取的行数
            
        Returns:
            行的背景颜色（RGB值），如果没有颜色则返回"无颜色"
        """
        # 获取数据行的背景色
        row_colors = []
        # 注意：dataframe的索引从0开始，而Excel行号从1开始，且需要跳过表头行
        for row_idx in range(header_row + 2, min(header_row + 2 + row_count, sheet.max_row + 1)):
            # 获取整行第一个非空单元格的填充色（通常整行颜色一致）
            fill_color = None
            for col_idx in range(1, sheet.max_column + 1):
                cell = sheet.cell(row=row_idx, column=col_idx)
                if cell.value is not None and str(cell.value).strip():
                    if isinstance(cell.fill, StyleProxy) and cell.fill.fgColor.rgb:
                        if cell.fill.fgColor.indexed == 64 or \
                           cell.fill.fgColor.rgb == "00000000" or \
                           str(cell.fill.fgColor.rgb) == "Values must be of type <class 'str'>":
                            continue
         
                        fill_color = str(cell.fill.fgColor.rgb)[2:]
                    break
            row_colors.append(fill_color if fill_color else "")
        
        # 确保row_colors长度与row_count一致
        if len(row_colors) < row_count:
            row_colors.extend([""] * (row_count - len(row_colors)))
        elif len(row_colors) > row_count:
            row_colors = row_colors[:row_count]
        
        return row_colors
    
    def find_header_row(self, sheet,
                              header_candidates=None,
                              max_scan_rows=10,
                              blanks_ratio=0.5):
        """
        在 Excel 工作表中自动定位“表头”所在行号。

        Args
        ----
        sheet : xlrd.sheet.Sheet
            已经打开的工作表
        header_candidates : list[str] | None
            如果你已经知道表头里必须出现哪些关键字，可以写进来，
            例如 ["姓名","年龄"]，函数会优先返回同时包含这些关键字的第一行。
            留 None 则按“空值比例”策略自动判断。
        max_scan_rows : int
            最多从前 N 行里扫描，避免整张表都扫一遍
        blanks_ratio : float
            允许的行空值比例阈值，小于该比例才认为可能是表头
            （0.5 表示“该行一半以上有值”就合格）

        Returns
        -------
        int
            表头行号（从 0 开始），找不到则返回 -1
        """
        ncols = max(sheet.max_column, 1)
        for r_idx, row in enumerate(sheet.iter_rows(min_row=1,
                                         max_row=min(max_scan_rows, sheet.max_row)),
                                start=0):
            row_values = [cell.value for cell in row]        
            # 1. 空值比例策略
            non_blanks = sum(1 for v in row_values if v is not None and str(v).strip())
            if non_blanks / ncols < (1 - blanks_ratio):
                continue

            # 2. 关键字策略（如果调用者给了关键字列表）
            if header_candidates:
                hit = all(any(key in str(cv).strip() for cv in row_values)
                        for key in header_candidates)
                if not hit:
                    continue
            # 同时满足两个策略，就认为找到了
            return r_idx
        return -1