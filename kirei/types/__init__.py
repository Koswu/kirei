from abc import ABC, abstractmethod
import gettext
import pathlib
from typing import Annotated, Callable, TypeVar
from kirei.types.validate import PostValidator


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


def _validate_file_exist(path: pathlib.Path):
    if not path.exists():
        raise ValueError(_("Path not exists"))
    if not path.is_file():
        raise ValueError(_("Path is not file"))


UserInputFilePath = Annotated[pathlib.Path, PostValidator(_validate_file_exist)]
UserOutputFilePath = Annotated[pathlib.Path, PostValidator(_validate_file_exist)]
