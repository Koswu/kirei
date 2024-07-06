from abc import ABC
from typing import Any, Callable


Task = Callable  # Any callable is a valid Task


class Application(ABC):
    def __call__(self) -> Any:
        # usage: app = XXApplication()
        # ... (register your task)
        # app()
        ...
