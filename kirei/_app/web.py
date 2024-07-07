from typing import Callable, Generic, List, Optional, Self
from typing_extensions import TypeVar

from attr import dataclass
from pydantic import BaseModel, ConfigDict
from kirei.types import Application, Task_T, Task
import gradio as gr


class WebApplicationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    external_accessible: bool = False
    port: int = 8080

    @property
    def listen_addr(self):
        return "0.0.0.0" if self.external_accessible else "127.0.0.1"


_T = TypeVar("_T")


@dataclass(frozen=True)
class _TaskInputParam(Generic[_T]):
    component: gr.components.Component
    converter: Callable[[_T]]


@dataclass(frozen=True)
class _TaskOutputParam(Generic[_T]):
    name: str
    component: gr.components.Component


@dataclass(frozen=True)
class _WebTask:
    name: str
    input_parameters: List[_TaskInputParam]
    output_parameters: List[_TaskOutputParam]

    @classmethod
    def parse_by_task(cls, func: Task) -> Self: ...

    def to_interface(self) -> gr.Interface: ...


class WebApplication(Application):
    def __init__(self, *, config: Optional[WebApplicationConfig] = None) -> None:
        self._config = config or WebApplicationConfig()
        self._parsed_tasks: List[_WebTask] = []

    def register(self) -> Callable[[Task_T], Task_T]:
        def decorator(func: Task_T):
            self._parsed_tasks.append(_WebTask.parse_by_task(func))
            return func

        return decorator

    def __call__(self):
        interface = gr.TabbedInterface(
            [task.to_interface() for task in self._parsed_tasks],
            tab_names=[task.name for task in self._parsed_tasks],
        )
        interface.launch(
            server_name=self._config.listen_addr, server_port=self._config.port
        )
