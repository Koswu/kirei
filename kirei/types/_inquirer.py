from typing import Any, Callable, Dict, List, Type, TypeVar

from kirei.types._func_parser import FuncParam, ParamAnnotation

_T = TypeVar("_T")


_TypeParamInquirer = Callable[[FuncParam], Any]


class ParamInquirerCollection:
    def __init__(self):
        self._inquirers: Dict[Type, _TypeParamInquirer] = {}

    def register(self, inquirer: _TypeParamInquirer, tp: Type[_T]):
        self._inquirers[tp] = inquirer
        return self

    def register_multi(self, inquirer: _TypeParamInquirer, tps: List[Type[_T]]):
        for tp in tps:
            self._inquirers[tp] = inquirer
        return self

    def __call__(self, param: FuncParam) -> Any:
        if param.real_source_type not in self._inquirers:
            raise TypeError(f"Unsupported input type {param.real_source_type}")
        res = self._inquirers[param.real_source_type](param)
        if res is NotImplemented:
            raise TypeError(f"Unsupported input type {param.real_source_type}")
        return res
