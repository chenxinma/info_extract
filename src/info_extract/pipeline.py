import abc
import logging
import threading
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Iterator, List, Optional, Self, Tuple, TypeAlias, overload

from .config.profile_manager import ProfileManager


logger = logging.getLogger(__name__)


StepResult: TypeAlias = Tuple[str, Optional[Any]]

class Step(abc.ABC):
    pre_results: List[StepResult] = []

    @abc.abstractmethod
    async def run(self, profile_manager : ProfileManager) -> AsyncGenerator[StepResult, None]:
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
