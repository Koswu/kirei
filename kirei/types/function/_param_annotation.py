import inspect
from typing import (
    Annotated,
    Any,
    Generic,
    Optional,
    Sequence,
    Type,
    TypeVar,
    get_args,
    get_origin,
)

_T = TypeVar("_T")
_InfoT = TypeVar("_InfoT")


class ParamAnnotation(Generic[_T]):
    def __init__(self, tp: Type[_T]):
        assert tp is not inspect.Parameter.empty
        self._tp = tp

    @property
    def iter_annotated_params(self) -> Sequence[Any]:
        origin = get_origin(self._tp)
        if not origin:
            return []
        elif origin is Annotated:
            return get_args(self._tp)[1:]
        else:
            raise NotImplementedError(f"Unsupported origin {origin}")

    @property
    def real_source_type(self) -> Type[_T]:
        origin = get_origin(self._tp)
        if origin is None:
            return self._tp
        elif origin is Annotated:
            return get_args(self._tp)[0]
        else:
            raise NotImplementedError(f"Unsupported origin {origin}")

    def get_tp_info(self, info_t: Type[_InfoT]) -> Optional[_InfoT]:
        for annotation in self.iter_annotated_params:
            if isinstance(annotation, info_t):
                return annotation
        return None
