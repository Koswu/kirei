from __future__ import annotations
from contextlib import contextmanager
import inspect
import logging
from typing import (
    Any,
    Callable,
    Generic,
    Iterator,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    cast,
)
from typing_extensions import ParamSpec

from kirei.types._param_annotation import ParamAnnotation
from kirei.types._injector import (
    ContextInjectorCollection,
    ParamInjector,
    ParamInjectorCollection,
)
from kirei.types.annotated import get_default_validator_provider
from kirei.types.annotated._validator import (
    AnyValidator,
    ValidatorProvider,
)

_T = TypeVar("_T")
_InfoT = TypeVar("_InfoT")
_logger = logging.getLogger(__name__)


class FuncParam(Generic[_T]):
    def __init__(
        self, index: int, name: str, tp: Type[_T], validator: AnyValidator[_T]
    ) -> None:
        self._index = index
        self._is_filled = False
        self._filled_value = None
        self._name = name
        self._tp = ParamAnnotation(tp)
        self._validator = validator

    def __repr__(self) -> str:
        return super().__repr__() + f"({self._name})"

    @property
    def index(self):
        return self._index

    @property
    def is_filled(self):
        return self._is_filled

    @property
    def name(self):
        return self._name

    @property
    def iter_annotated_params(self) -> Sequence[Any]:
        return self._tp.iter_annotated_params

    @property
    def real_source_type(self) -> Type[_T]:
        return self._tp.real_source_type

    def get_tp_info(self, info_t: Type[_InfoT]) -> Optional[_InfoT]:
        return self._tp.get_tp_info(info_t)

    def reindex(self, value: int):
        self._index = value
        return self

    def get_value(self) -> _T:
        if not self._is_filled:
            raise ValueError(f"Param {self._name} is not filled")
        return cast(_T, self._filled_value)

    def fill(self, value: Any):
        assert not self._is_filled
        self._is_filled = True
        self._filled_value = self._validator(value)
        return self

    def maybe_fill_with_injector(self, injector: ParamInjector[_T]):
        assert not self._is_filled
        val = injector(self._tp)
        if val is NotImplemented:
            return self
        self.fill(val)
        return self


_P = ParamSpec("_P")
_T = TypeVar("_T")


class TaskSession(Generic[_P, _T]):
    def __init__(
        self,
        injector_collection: ParamInjectorCollection,
        func: Callable[_P, _T],
        validator_provider: ValidatorProvider,
        task_name: str,
        params: List[FuncParam],
    ):
        self._injector_collection = injector_collection
        self._func = func
        self._validator_provider = validator_provider
        self._task_name = task_name
        self._params = [
            param.maybe_fill_with_injector(self._injector_collection)
            for param in params
        ]

    @property
    def name(self):
        return self._task_name

    @property
    def non_filled_params(self) -> Iterator[FuncParam]:
        index = 1
        for param in self._params:
            if not param.is_filled:
                yield param.reindex(index)
                index += 1

    @property
    def return_type_annotation(self):
        annotation = inspect.signature(self._func).return_annotation
        if annotation is inspect.Parameter.empty:
            return ParamAnnotation(str)
        return ParamAnnotation(annotation)

    def __call__(self) -> _T:
        res = self._func(*[param.get_value() for param in self._func_params])  # type: ignore
        return res


class ParsedFunc(Generic[_P, _T]):
    def __init__(
        self,
        injector_collection: ContextInjectorCollection,
        func: Callable[_P, _T],
        validator_provider: ValidatorProvider,
        override_name: Optional[str] = None,
    ):
        self._injector_collection = injector_collection
        self._func = func
        self._validator_provider = validator_provider
        self._name = override_name or func.__name__

    @contextmanager
    def enter_session(self):
        with self._injector_collection as injector:
            yield TaskSession(
                injector,
                self._func,
                self._validator_provider,
                self._name,
                list(self._get_func_params()),
            )

    def _get_func_params(self) -> Iterator[FuncParam]:
        sig: inspect.Signature = inspect.signature(self._func)
        index = 1
        for param in sig.parameters.values():
            tp = param.annotation
            if tp is inspect.Parameter.empty:
                tp = str  # fallback to str
            validator_chain = self._validator_provider.get_validator(tp)
            yield FuncParam(index, param.name, tp, validator_chain)
            index += 1


class FuncParser:
    def __init__(
        self,
        injector_collection: ContextInjectorCollection,
        validator_provider: Optional[ValidatorProvider] = None,
    ):
        self._injector_collection = injector_collection
        self._validator_provider = (
            validator_provider or get_default_validator_provider()
        )

    def parse(self, func: Callable, override_name: Optional[str] = None) -> ParsedFunc:
        return ParsedFunc(
            self._injector_collection, func, self._validator_provider, override_name
        )
