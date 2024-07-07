from dataclasses import dataclass
import inspect
from typing import Annotated, Any, Callable, Generic, List, Type
from typing_extensions import Self, TypeVar
import pydantic
import typing_extensions
from kirei.types import Task
from kirei.types.validate import PostValidator

_T = TypeVar("_T")


def _get_original_tp(tp: Type) -> Type:
    if typing_extensions.get_origin(tp) is Annotated:
        res = typing_extensions.get_args(tp)[0]
    else:
        res = tp
    if res is inspect.Parameter.empty:
        res = str
    return res


@dataclass(frozen=True)
class InputParameter(Generic[_T]):
    index: pydantic.PositiveInt
    name: str
    original_tp: Type[_T]
    other_annotations: List[Any]
    _validators: List[PostValidator[_T]]

    @classmethod
    def parse(cls, index: int, param: inspect.Parameter) -> Self:
        tp = _get_original_tp(param.annotation)
        other_annotations = list(typing_extensions.get_args(param.annotation))[1:]
        validators = [
            annotation
            for annotation in other_annotations
            if isinstance(annotation, PostValidator)
        ]
        return cls(
            index=index,
            name=param.name,
            original_tp=tp,
            other_annotations=list(typing_extensions.get_args(param.annotation))[1:],
            _validators=validators,
        )

    def validate(self, value: _T):
        """
        :raise ValueError
        """
        for validator in self._validators:
            validator(value)


@dataclass(frozen=True)
class OutputParameter:
    original_tp: Type
    other_annotations: List[Any]

    @classmethod
    def parse(cls, annotation: Type) -> Self:
        tp = _get_original_tp(annotation)
        return cls(
            original_tp=tp,
            other_annotations=list(typing_extensions.get_args(annotation))[1:],
        )


@dataclass(frozen=True)
class ParsedTask:
    origin_task: Task
    input_params: List[InputParameter]
    output_param: OutputParameter

    @classmethod
    def parse(cls, task: Task) -> Self:
        sig = inspect.signature(task)
        return cls(
            origin_task=task,
            input_params=[
                InputParameter.parse(i, param)
                for i, param in enumerate(sig.parameters.values(), 1)
            ],
            output_param=OutputParameter.parse(sig.return_annotation),
        )
