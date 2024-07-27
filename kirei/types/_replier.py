from collections import defaultdict
from typing import Any, Callable, Dict, List, Type, TypeVar, Union
from types import NoneType, NotImplementedType

from kirei.types._param_annotation import ParamAnnotation


_T = TypeVar("_T")
OutputReplier = Callable[[ParamAnnotation[_T], _T], Union[None, NotImplementedType]]


class ReplierCollection:
    def __init__(self):
        self._repliers: Dict[Type, List[OutputReplier]] = {
            NoneType: [lambda x, y: None]
        }

    def register(self, replier: OutputReplier, tp: Type):
        self._repliers.setdefault(tp, []).append(replier)
        return self

    def register_multi(self, replier: OutputReplier, tps: List[Type]):
        for tp in tps:
            self._repliers.setdefault(tp, []).append(replier)
        return self

    def __call__(self, annotation: ParamAnnotation, value: Any):
        repliers = self._repliers.get(annotation.real_source_type, [])
        for replier in repliers:
            res = replier(annotation, value)
            if res is not NotImplemented:
                return None
        raise TypeError(f"Unsupported output type {type(value)}")
