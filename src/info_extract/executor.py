import logging
import os
from typing import List, Optional

from .extract import PlainExtractor, SpreadsheetExtractor #, DataFrameMappingExtract
from .pipeline import Pipeline
from .source import EMLReader, ExcelReader, MSGReader
from .destination import ExcelExporter

logger = logging.getLogger(__name__)

class Executor:
    def __init__(self, work_dir:str, specific_files:Optional[List[str]]=None) -> None:
        self.source_dir = os.path.join(work_dir, 'source')
        self.processing_dir = os.path.join(work_dir, 'processing')
        self.destination_dir = os.path.join(work_dir, 'destination')
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.processing_dir, exist_ok=True)
        os.makedirs(self.destination_dir, exist_ok=True)

        self._pipeline = Pipeline(
            source=[("eml_reader", EMLReader(source_dir=self.source_dir, processing_dir=self.processing_dir)),
                    ("msg_reader", MSGReader(source_dir=self.source_dir, processing_dir=self.processing_dir)),
                    ("excel_reader", ExcelReader(source_dir=self.source_dir, processing_dir=self.processing_dir))],
            extractors=[
                ("plain_extractor", PlainExtractor(processing_dir=self.processing_dir)),
                ("spreadsheet_extractor", SpreadsheetExtractor(processing_dir=self.processing_dir))
                # ("spreadsheet_extractor", DataFrameMappingExtract(processing_dir=processing_dir))
            ],
            destination=[
                ("excel_exporter", ExcelExporter(processing_dir=self.processing_dir, destination_dir=self.destination_dir))
            ]
        )
        if specific_files:
            self._pipeline.specific_files = specific_files
    
    def clean_processing_dir(self):
        """清理处理目录下的所有文件"""
        # 清理 processing_dir 下的所有 文件
        for root, dirs, files in os.walk(self.processing_dir, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"删除文件失败: {file_path}, 错误: {e}")
            for d in dirs:
                dir_path = os.path.join(root, d)
                try:
                    os.rmdir(dir_path)
                except Exception as e:
                    logger.error(f"删除目录失败: {dir_path}, 错误: {e}")
    
    @property
    def pipeline(self) -> Pipeline:
        return self._pipeline


