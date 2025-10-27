import abc
import logging
from typing import Any, List, Optional, Tuple, TypeAlias, overload
from typing_extensions import Generator

logger = logging.getLogger(__name__)

class Step(abc.ABC):
    pre_results: List[Any] = []

    @abc.abstractmethod
    def run(self) -> Generator[Any, None, None]:
        pass

    def verify(self, pre_result: Any) -> bool:
        return True

StepGroup: TypeAlias = List[Tuple[str, Step]]

class Pipeline:
    def __init__(self, source:StepGroup, 
                       extractors:StepGroup, 
                       destination:Optional[StepGroup] = None) -> None:
        self.source  = source
        self.extractors = extractors
        self.destination = destination

    def run(self):
        """
        运行所有步骤
        """
        source_results = []
        # 运行source步骤
        for name, step in self.source:
            logger.info(f"Running step {name}")
            for result in step.run():
                source_results.append(result)

        extract_results = []
        # 运行extractors步骤
        for name, step in self.extractors:
            logger.info(f"Running step {name}")
            pre_enabled_result = [result for result in source_results if step.verify(result)]
            step.pre_results = pre_enabled_result
            for result in step.run():
                extract_results.append(result)
        
        # 运行destination步骤
        if self.destination:
            for name, step in self.destination:
                logger.info(f"Running step {name}")
                step.run()
