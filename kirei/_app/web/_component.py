from decimal import Decimal
import pathlib
from types import NotImplementedType
from typing import Callable, Dict, List, Type, Union

import gradio as gr

from kirei.types.basic_types import PathType
from kirei.types.function import FuncParam
from kirei.types.function._param_annotation import ParamAnnotation

_GradioComponent = gr.components.Component

InputComponentGenerator = Callable[
    [FuncParam], Union[_GradioComponent, NotImplementedType]
]
OutputComponentGenerator = Callable[
    [ParamAnnotation], Union[_GradioComponent, NotImplementedType]
]


class InputComponentGeneratorCollection:
    def __init__(self) -> None:
        self._generators: List[InputComponentGenerator] = []

    def __call__(self, param: FuncParam) -> _GradioComponent:
        for generator in self._generators:
            res = generator(param)
            if res is not NotImplemented:
                return res
        raise TypeError(f"Unsupported input type {param}")

    def register(self, generator: InputComponentGenerator):
        self._generators.append(generator)
        return self


class OutputComponentGeneratorCollection:
    def __init__(self) -> None:
        self._generators: List[OutputComponentGenerator] = []

    def __call__(self, param: ParamAnnotation) -> _GradioComponent:
        for generator in self._generators:
            res = generator(param)
            if res is not NotImplemented:
                return res
        raise TypeError(f"Unsupported output type {param}")

    def register(self, generator: OutputComponentGenerator):
        self._generators.append(generator)
        return self


def _text_generator(param: FuncParam):
    if param.real_source_type in (int, str, float, Decimal):
        return gr.Textbox(label=param.name)
    return NotImplemented


def _component_generator(param: FuncParam):
    component = param.get_tp_info(_GradioComponent)
    if not component:
        return NotImplemented
    return component


def _file_generator(param: FuncParam):
    if param.real_source_type is not pathlib.Path:
        return NotImplemented
    pt = param.get_tp_info(PathType)
    if not pt:
        return NotImplemented
    elif pt.type != "user_input_file":
        return NotImplemented
    return gr.File(label=param.name)


def get_default_input_generator_collection() -> InputComponentGeneratorCollection:
    return (
        InputComponentGeneratorCollection()
        .register(_component_generator)
        .register(_text_generator)
        .register(_file_generator)
    )


def _annotation_component_generator(param: ParamAnnotation):
    component = param.get_tp_info(_GradioComponent)
    if not component:
        return NotImplemented
    return component


def _annotation_text_generator(param: ParamAnnotation):
    if param.real_source_type in (int, str, float, Decimal):
        return gr.Textbox("输出")
    return NotImplemented


def _annotation_file_generator(param: ParamAnnotation):
    if param.real_source_type is not pathlib.Path:
        return NotImplemented
    pt = param.get_tp_info(PathType)
    if not pt:
        return NotImplemented
    elif pt.type != "out_file":
        return NotImplemented
    return gr.File(label="输出")


def get_default_output_generator_collection() -> OutputComponentGeneratorCollection:
    return (
        OutputComponentGeneratorCollection()
        .register(_annotation_component_generator)
        .register(_annotation_file_generator)
        .register(_annotation_text_generator)
    )
