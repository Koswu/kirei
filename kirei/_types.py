from abc import ABC, abstractmethod
from typing import Callable, NoReturn, TypeVar


Task = Callable  # Any callable is a valid Task


class Application(ABC):
    @abstractmethod
    def register[Task_T: Task](self) -> Callable[[Task_T], Task_T]: ...

    @abstractmethod
    def __call__(self) -> NoReturn:
        # usage: app = XXApplication()
        # ... (register your task)
        # app()
        ...
