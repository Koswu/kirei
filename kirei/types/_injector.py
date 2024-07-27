from types import NotImplementedType
from typing import Callable, Dict, List, Type, TypeVar, Union, cast

from kirei.types._func_parser import ParamAnnotation

_T = TypeVar("_T")

ParamInjector = Callable[[ParamAnnotation[_T]], Union[_T, NotImplementedType]]


class ParamInjectorCollection:
    def __init__(self):
        self._injectors: Dict[Type, List[ParamInjector]] = {}

    def register(self, injector: ParamInjector[_T], tp: Type[_T]):
        self._injectors.setdefault(tp, []).append(injector)
        return self

    def __call__(
        self, annotation: ParamAnnotation[_T]
    ) -> Union[_T, NotImplementedType]:
        for injector in self._injectors.get(annotation.real_source_type, []):
            res = injector(annotation)
            if res is not NotImplemented:
                return cast(_T, res)
        return NotImplemented
