import abc
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Iterator, List, Optional, Self, Tuple, TypeAlias, overload


logger = logging.getLogger(__name__)


StepResult: TypeAlias = Tuple[str, Optional[Any]]

class Step(abc.ABC):
    pre_results: List[StepResult] = []

    @abc.abstractmethod
    async def run(self) -> AsyncGenerator[StepResult, None]:
        yield ("", None)

    def verify(self, pre_result: StepResult) -> bool:
        return True
    
    def set_specific_files(self, specific_files: Optional[List[str]]=None) -> Self:
        self.specific_files = specific_files
        return self
    
    def source_files(self, source_dir: Path, pattern:str)-> List[Path]:
        if self.specific_files:
            return [ Path(f) for f in self.specific_files if Path(f).match(pattern) ]
        else:
            return [ f for f in source_dir.glob(pattern) ]


StepGroup: TypeAlias = List[Tuple[str, Step]]

class Pipeline:
    def __init__(self, source:StepGroup, 
                       extractors:StepGroup, 
                       destination:Optional[StepGroup] = None) -> None:
        self.source  = source
        self.extractors = extractors
        self.destination = destination
        self._specific_files = None
    
    @property
    def specific_files(self) -> Optional[List[str]]:
        return self._specific_files
    
    @specific_files.setter
    def specific_files(self, specific_files: Optional[List[str]]=None):
        self._specific_files = specific_files

    async def run(self) -> AsyncGenerator[str, None]:
        """
        运行所有步骤
        """
        source_results = []
        # 运行source步骤
        for name, step in self.source:
            logger.info(f"Running step {name}")            
            async for result in step.set_specific_files(self.specific_files).run():
                source_results.append(result)
                yield f"读取{result[0]}"

        extract_results = []
        # 运行extractors步骤
        for name, step in self.extractors:
            logger.info(f"Running step {name}")
            pre_enabled_result = [result for result in source_results if step.verify(result)]
            step.pre_results = pre_enabled_result
            async for result in step.run():
                extract_results.append(result)
                yield f"提取{result[0]}"
        
        # 运行destination步骤
        if self.destination:
            for name, step in self.destination:
                step.pre_results = extract_results
                logger.info(f"Running step {name}")
                async for result in step.run():
                    logger.info(f"Step {name} result: {result}")
                    yield f"{result[0]}处理完成"
