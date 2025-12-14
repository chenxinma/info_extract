import logging
import os
import threading
from typing import AsyncGenerator, List, Optional

from .config.profile_manager import ProfileManager
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
        self.specific_files = specific_files
        
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
    
    async def run(self, profile_manager : ProfileManager, cancellation_event: Optional[threading.Event] = None) -> AsyncGenerator[str, None]:
        """
        运行所有步骤
        
        Args:
            cancellation_event: 用于中断任务的事件对象
        """
        source_results = []
        # 运行source步骤
        for name, step in self.pipeline.source:
            logger.info(f"Running step {name}")
            # 检查中断事件
            if cancellation_event and cancellation_event.is_set():
                yield f"任务已取消: {name}"
                return
            async for result in step.set_specific_files(self.specific_files).run(profile_manager):
                # 检查中断事件
                if cancellation_event and cancellation_event.is_set():
                    yield f"任务已取消: {name}"
                    return
                source_results.append(result)
                yield f"读取{result[0]}"

        extract_results = []
        # 运行extractors步骤
        for name, step in self.pipeline.extractors:
            logger.info(f"Running step {name}")
            # 检查中断事件
            if cancellation_event and cancellation_event.is_set():
                yield f"任务已取消: {name}"
                return
            pre_enabled_result = [result for result in source_results if step.verify(result)]
            step.pre_results = pre_enabled_result
            async for result in step.run(profile_manager):
                # 检查中断事件
                if cancellation_event and cancellation_event.is_set():
                    yield f"任务已取消: {name}"
                    return
                extract_results.append(result)
                yield f"提取{result[0]}"
        
        # 运行destination步骤
        if self.pipeline.destination:
            for name, step in self.pipeline.destination:
                logger.info(f"Running step {name}")
                # 检查中断事件
                if cancellation_event and cancellation_event.is_set():
                    yield f"任务已取消: {name}"
                    return
                step.pre_results = extract_results
                async for result in step.run(profile_manager):
                    # 检查中断事件
                    if cancellation_event and cancellation_event.is_set():
                        yield f"任务已取消: {name}"
                        return
                    logger.info(f"Step {name} result: {result}")
                    yield f"{result[0]}处理完成"



