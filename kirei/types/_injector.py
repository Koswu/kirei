from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
import tempfile
from types import NotImplementedType
from typing import Callable, Dict, List, Type, TypeVar, Union, cast

from kirei.types._param_annotation import ParamAnnotation

_T = TypeVar("_T")

ParamInjector = Callable[[ParamAnnotation[_T]], Union[_T, NotImplementedType]]


class ParamInjectorCollection:
    def __init__(self, injectors: Dict[Type, List[ParamInjector]]):
        self._injectors: Dict[Type, List[ParamInjector]] = injectors

    def __call__(
        self, annotation: ParamAnnotation[_T]
    ) -> Union[_T, NotImplementedType]:
        for injector in self._injectors.get(annotation.real_source_type, []):
            res = injector(annotation)
            if res is not NotImplemented:
                return cast(_T, res)
        return NotImplemented


class ContextInjectorCollection(AbstractContextManager[ParamInjector]):
    def __init__(self):
        self._injectors: Dict[Type, List[ParamInjector]] = {}
        self._context_injectors: Dict[
            Type, List[AbstractContextManager[ParamInjector]]
        ] = {}
        self._in_context = False

    def __enter__(self):
        assert not self._in_context
        self._in_context = True
        injectors: Dict[Type, List[ParamInjector]] = self._injectors.copy()
        for tp, inner_injectors in self._context_injectors.items():
            for injector in inner_injectors:
                injectors.setdefault(tp, []).append(injector.__enter__())
        return ParamInjectorCollection(injectors)

    def __exit__(self, exc_type, exc_value, traceback):
        for injectors in self._context_injectors.values():
            for injector in injectors:
                injector.__exit__(exc_type, exc_value, traceback)
        self._in_context = False
        return False

    def register_context_injector(
        self, injector: AbstractContextManager[ParamInjector], tp: Type[_T]
    ):
        self._context_injectors.setdefault(tp, []).append(injector)
        return self

    def register(self, injector: ParamInjector[_T], tp: Type[_T]):
        self._injectors.setdefault(tp, []).append(injector)
        return self


@contextmanager
def _temp_dir_injector():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def get_default_context_collection():
    return ContextInjectorCollection().register_context_injector(
        _temp_dir_injector, Path
    )
