from __future__ import annotations
from abc import ABC
from decimal import Decimal
import gettext
import inspect
import logging
from pathlib import Path
import pathlib
from typing import (
    Annotated,
    Callable,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    cast,
    final,
)
import inquirer
import prompt_toolkit as pt
from prompt_toolkit import completion as ptc
import rich
from typing_extensions import Self

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from kirei.types import Task_T, Task, Application
from kirei._task import InputParameter


_ = gettext.gettext
_T = TypeVar("_T")
_console = rich.console.Console()

_USER_TYPE_HINT_MAPPING = {
    int: _("整数"),
    str: _("文本"),
    Decimal: _("小数"),
    Path: _("文件路径"),
}

_logger = logging.getLogger(__name__)


class CliTextInputParameter(Generic[_T]):
    def __init__(
        self,
        *,
        param: InputParameter,
        converter: Callable[[str], _T],
        user_type_hint: str,
    ):
        self._param = param
        self._converter = converter
        self._user_type_hint = user_type_hint

    @classmethod
    def parse(cls, param: InputParameter) -> Self:
        tp = param.original_tp
        if tp not in _USER_TYPE_HINT_MAPPING:
            raise TypeError(_("Unsupported task type: {}").format(tp))
        return cls(
            param=param,
            converter=tp,
            user_type_hint=_USER_TYPE_HINT_MAPPING[tp],
        )

    def _query_value_once(self) -> _T:
        completer = (
            ptc.PathCompleter() if self._param.original_tp is pathlib.Path else None
        )
        _logger.debug(f"using completer {completer}")
        res = pt.prompt(
            _("请输入第 {} 个参数，参数名称 {}, 参数类型: {} :").format(
                self._param.index, self._param.name, self._user_type_hint
            ),
            completer=completer,
        )
        res = self._converter(res)
        self._param.validate(res)
        return res

    def query_value(self) -> _T:
        while True:
            try:
                return self._query_value_once()
            except Exception as err:
                typer.secho(
                    _("参数不合法，请重新输入: {}").format(err), fg=typer.colors.YELLOW
                )


@final
class CliTask:
    def __init__(self, task: Task):
        self._task = task
        self._name = task.__name__
        sig = inspect.signature(task)
        self._params = [
            CliTextInputParameter.parse(InputParameter.parse(i, param))
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
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(_("正在执行任务 {}").format(self._name))
            try:
                res = self._task(*self._filled_param)
            except Exception as err:
                _console.print_exception(show_locals=True)
                typer.secho(_("任务 {} 执行失败").format(self._name))
                return
        typer.secho(_("任务 {} 执行完毕").format(self._name), fg=typer.colors.GREEN)
        typer.secho(_("执行结果为: {}").format(res))


class CliApplication(Application):
    def __init__(
        self,
        title: Optional[str] = None,
    ):
        self._name_task_mapping: Dict[str, CliTask] = {}
        self._title = title

    def register(self) -> Callable[[Task_T], Task_T]:
        def decorator(func: Task_T) -> Task_T:
            task_name = func.__name__
            if task_name in self._name_task_mapping:
                raise TypeError(_(f"Multiple task can not have same name: {task_name}"))
            self._name_task_mapping[task_name] = CliTask(func)
            return func

        return decorator

    def _loop(self) -> bool:
        return True

    def _main(self):
        exit_command = _("退出")
        while self._loop():
            task_name: str = inquirer.list_input(
                _("请选择你要执行的任务"),
                choices=list(self._name_task_mapping.keys()) + [exit_command],
            )
            if task_name == exit_command:
                return
            task = self._name_task_mapping[task_name]
            task.query_and_run()

    def __call__(self):
        typer.run(self._main)
