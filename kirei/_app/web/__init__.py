from ast import Call
import gettext
import logging
from pathlib import Path
from types import NotImplementedType
from typing import Callable, List, Optional, Union, cast

from pydantic import BaseModel, ConfigDict
from kirei._app.web._component import (
    InputComponentGeneratorCollection,
    get_default_input_generator_collection,
    get_default_output_generator_collection,
)
from kirei.types import Application, Task_T, Task
import gradio as gr

from kirei.types.annotated import get_default_validator_provider
from kirei.types import FuncParam, FuncParser, ParsedFunc
from kirei.types.function import get_default_context_collection


class WebApplicationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    external_accessible: bool = False
    port: int = 8080

    @property
    def listen_addr(self):
        return "0.0.0.0" if self.external_accessible else "127.0.0.1"


_ = gettext.gettext
_logger = logging.getLogger(__name__)
_context_collection = get_default_context_collection()
_validator_provider = get_default_validator_provider()
_func_parser = FuncParser(_context_collection, _validator_provider)
_input_component_generator = get_default_input_generator_collection()
_output_component_generator = get_default_output_generator_collection()

_GrComponent = gr.components.Component


def _generate_interface(parsed_func: ParsedFunc) -> gr.Interface:
    metadata = parsed_func.get_metadata()

    input_components: List[_GrComponent] = []
    for param in metadata.non_injected_params:
        component = _input_component_generator(param)
        input_components.append(component)

    def _func(*args):
        with parsed_func.enter_session() as session:
            for param, arg in zip(session.meta_data.non_injected_params, args):
                param.fill(arg)
            res = session()
            # HACK: gradio 不支持 pathlib.Path 类型，需要转换为 str
            if isinstance(res, Path):
                res = str(res)
            return res

    output_components = [_output_component_generator(metadata.return_type_annotation)]

    return gr.Interface(
        _func,
        list(input_components),
        outputs=list(output_components),
        title=metadata.name,
    )


class WebApplication(Application):
    def __init__(self, *, config: Optional[WebApplicationConfig] = None) -> None:
        self._config = config or WebApplicationConfig()
        self._parsed_func: List[ParsedFunc] = []

    def register(
        self, override_name: Optional[str] = None
    ) -> Callable[[Task_T], Task_T]:
        def decorator(func: Task_T):
            self._parsed_func.append(
                _func_parser.parse(func, override_name=override_name)
            )
            return func

        return decorator

    def __call__(self):
        interface = gr.TabbedInterface(
            [_generate_interface(task) for task in self._parsed_func],
            [task.get_metadata().name for task in self._parsed_func],
        )
        interface.launch(
            server_name=self._config.listen_addr, server_port=self._config.port
        )
