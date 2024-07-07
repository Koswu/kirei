from abc import ABC, abstractmethod
import gettext
import pathlib
from tempfile import TemporaryDirectory
from typing import Callable, NewType, TypeVar


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


UserInputFilePath = NewType("UserInputFilePath", pathlib.Path)
UserOutputFilePath = NewType("UserOutputFilePath", pathlib.Path)
TempDirectory = NewType("TempDirectory", TemporaryDirectory)
