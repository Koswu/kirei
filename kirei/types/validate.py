import gettext
import pathlib
from typing import Callable, Generic
from typing_extensions import TypeVar

_T = TypeVar("_T")


class PostValidator(Generic[_T]):
    def __init__(self, func: Callable[[_T], None]):
        self._func = func

    def __call__(self, value: _T):
        self._func(value)
