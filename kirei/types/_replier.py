from typing import Any, Callable, Dict, List, Type, TypeVar, Union
from types import NotImplementedType

from kirei.types._func_parser import ParamAnnotation


_T = TypeVar("_T")
OutputReplier = Callable[[ParamAnnotation[_T], _T], Union[None, NotImplementedType]]


class ReplierCollection:
    def __init__(self):
        self._repliers: Dict[Type, OutputReplier] = {}

    def register(self, replier: OutputReplier, tp: Type):
        self._repliers[tp] = replier
        return self

    def register_multi(self, replier: OutputReplier, tps: List[Type]):
        for tp in tps:
            self._repliers[tp] = replier
        return self

    def __call__(self, annotation: ParamAnnotation, value: Any):
        replier = self._repliers.get(annotation.real_source_type)
        if not replier:
            raise TypeError(f"Unsupported output type {type(value)}")
        res = replier(annotation, value)
        if res is NotImplemented:
            raise TypeError(f"Unsupported output type {type(value)}")
        return None
