from __future__ import annotations
from decimal import Decimal
import gettext
import inspect
import sys
from typing import (
    Annotated,
    Callable,
    Dict,
    Generic,
    NoReturn,
    Optional,
    Type,
    TypeVar,
    final,
)
from typing_extensions import Self
import typing_extensions

import inquirer
import typer
from kirei._types import Application, Task_T, Task


_ = gettext.gettext
_T = TypeVar("_T")

_USER_TYPE_HINT_MAPPING = {
    int: _("整数"),
    str: _("文本"),
    Decimal: _("小数"),
}


def _get_original_tp(tp: Type) -> Type:
    if typing_extensions.get_origin(tp) is Annotated:
        return typing_extensions.get_args(tp)[0]
    return tp


class TextInputParameter(Generic[_T]):
    def __init__(
        self,
        *,
        index: int,
        name: str,
        converter: Callable[[str], _T],
        user_type_hint: str,
    ):
        self._index = index
        self._name = name
        self._converter = converter
        self._user_type_hint = user_type_hint

    @classmethod
    def parse(cls, index: int, param: inspect.Parameter) -> Self:
        name = param.name
        tp = _get_original_tp(param.annotation)
        if tp not in _USER_TYPE_HINT_MAPPING:
            raise TypeError(_("Unsupported task type: {}").format(tp))
        return cls(
            index=index,
            name=name,
            converter=tp,
            user_type_hint=_USER_TYPE_HINT_MAPPING[tp],
        )

    def query_value(self) -> _T:
        while True:
            res: str = inquirer.text(
                _("请输入第 {} 个参数，参数名称 {}, 参数类型: {}").format(
                    self._index, self._name
                )
            )
            try:
                return self._converter(res)
            except Exception as err:
                typer.secho(
                    _("参数不合法，请重新输入: {}").format(err), fg=typer.colors.YELLOW
                )
                typer.prompt(_("请按 Enter 继续..."))


@final
class ParsedTask:
    def __init__(self, task: Task):
        self._task = task
        self._name = task.__name__
        sig = inspect.signature(task)
        self._params = [
            TextInputParameter.parse(i, param)
            for i, param in enumerate(sig.parameters.values(), 1)
        ]
        self._filled_param = []

    @property
    def name(self):
        return self._name

    def query_and_run(self):
        for param in self._params:
            self._filled_param.append(param.query_value())
        typer.secho(_("开始执行任务 {}").format(self._name), fg=typer.colors.GREEN)
        res = self._task(*self._filled_param)
        typer.secho(_("任务 {} 执行完毕").format(self._name), fg=typer.colors.GREEN)
        typer.secho(_("执行结果为: {}").format(res))
        typer.prompt(_("请按 Enter 继续..."))


def _exit_task():
    sys.exit(0)


class CliApplication(Application):
    def __init__(
        self,
        title: Optional[str] = None,
    ):
        self._exit_task_name = _("退出")
        self._name_task_mapping: Dict[str, ParsedTask] = {
            _("退出"): ParsedTask(_exit_task)
        }
        self._title = title

    def register(self) -> Callable[[Task_T], Task_T]:
        def decorator(func: Task_T) -> Task_T:
            task_name = func.__name__
            if task_name in self._name_task_mapping:
                raise TypeError(_(f"Multiple task can not have same name: {task_name}"))
            self._name_task_mapping[task_name] = ParsedTask(func)
            return func

        return decorator

    def _loop(self) -> bool:
        return True

    def _main(self):
        while self._loop():
            task_name: str = inquirer.list_input(
                _("请选择你要执行的任务"),
                choices=list(self._name_task_mapping.keys()) + [_("退出")],
            )
            task = self._name_task_mapping[task_name]
            task.query_and_run()

    def __call__(self) -> NoReturn:
        typer.run(self._main)
        sys.exit(0)
