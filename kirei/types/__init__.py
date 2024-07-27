from abc import ABC, abstractmethod
import gettext
import pathlib
from typing import Annotated, Callable, TypeVar
from kirei.types._param_annotation import ParamAnnotation as ParamAnnotation
from kirei.types._func_parser import (
    FuncParam as FuncParam,
    ParsedFunc as ParsedFunc,
    FuncParser as FuncParser,
)
from kirei.types._inquirer import ParamInquirerCollection as ParamInquirerCollection
from kirei.types._replier import ReplierCollection as ReplierCollection
from kirei.types.annotated.basic_types import PathType

UserInputFilePath = Annotated[pathlib.Path, PathType(type="user_input_file")]
OutputFilePath = Annotated[pathlib.Path, PathType(type="out_file")]
TempDirPath = Annotated[pathlib.Path, PathType(type="temp_dir")]


Task = Callable  # Any callable is a valid Task
Task_T = TypeVar("Task_T", bound=Task)

_ = gettext.gettext


class Application(ABC):
    @abstractmethod
    def register(self) -> Callable[[Task_T], Task_T]: ...

    @abstractmethod
    def __call__(self):
        # usage: app = XXApplication()
        # ... (register your task)
        # app()
        ...
