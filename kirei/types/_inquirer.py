from types import NotImplementedType
from typing import Any, Callable, Dict, List, Type, TypeVar, Union

from kirei.types._param_annotation import ParamAnnotation
from kirei.types._func_parser import FuncParam

_T = TypeVar("_T")


_TypeParamInquirer = Callable[[FuncParam], Union[Any, NotImplementedType]]


class ParamInquirerCollection:
    def __init__(self):
        self._inquirers: Dict[Type, List[_TypeParamInquirer]] = {}

    def register(self, inquirer: _TypeParamInquirer, tp: Type[_T]):
        self._inquirers.setdefault(tp, []).append(inquirer)
        return self

    def register_multi(self, inquirer: _TypeParamInquirer, tps: List[Type[_T]]):
        for tp in tps:
            self._inquirers.setdefault(tp, []).append(inquirer)
        return self

    def __call__(self, param: FuncParam) -> Any:
        for inquirer in self._inquirers.get(param.real_source_type, []):
            res = inquirer(param)
            if res is not NotImplemented:
                return res
        raise TypeError(f"Unsupported input type {param.real_source_type}")
