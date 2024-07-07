from __future__ import annotations
from decimal import Decimal
import gettext
import logging
import pathlib
import shutil
from typing import (
    Any,
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
from kirei.types import Task_T, Application, UserInputFilePath, UserOutputFilePath
from kirei._task import InputParameter, ParsedTask, OutputParameter
from kirei.types.validate import PostValidator


_ = gettext.gettext
_T = TypeVar("_T")
_console = rich.console.Console()

_USER_TYPE_HINT_MAPPING = {
    int: _("整数"),
    str: _("文本"),
    Decimal: _("小数"),
    UserInputFilePath: _("文件路径"),
}

_logger = logging.getLogger(__name__)


def _user_input_path_validator(path: pathlib.Path):
    if not path.exists():
        raise ValueError(_("找不到路径"))
    elif not path.is_file():
        raise ValueError(_("路径不是一个有效的文件"))


_EXTRA_VALIDATOR: Dict[Any, Callable[[Any], None]] = {
    UserInputFilePath: _user_input_path_validator
}
_CONVERTER_OVERRIDE = {UserInputFilePath: lambda x: UserInputFilePath(pathlib.Path(x))}


class CliInputParameter(Generic[_T]):
    def __init__(
        self,
        *,
        param: InputParameter,
        user_type_hint: str,
    ):
        self._param = param
        self._user_type_hint = user_type_hint

    @property
    def _converter(self):
        def convert(val: str) -> _T:
            _logger.debug(self._param.original_tp)
            override_converter = _CONVERTER_OVERRIDE.get(self._param.original_tp)
            if override_converter:
                res = cast(_T, override_converter(val))
            else:
                res = self._param.original_tp(val)
            _logger.debug(type(res))
            extra_validator = _EXTRA_VALIDATOR.get(res)
            if extra_validator:
                extra_validator(res)
            for annotation in self._param.other_annotations:
                if isinstance(annotation, PostValidator):
                    annotation(res)
            return res

        return convert

    @classmethod
    def parse(cls, param: InputParameter) -> Self:
        tp = param.original_tp
        if tp not in _USER_TYPE_HINT_MAPPING:
            raise TypeError(_("Unsupported task type: {}").format(tp))
        return cls(
            param=param,
            user_type_hint=_USER_TYPE_HINT_MAPPING[tp],
        )

    def _query_value_once(self) -> _T:
        completer = (
            ptc.PathCompleter()
            if self._param.original_tp is UserInputFilePath
            else None
        )
        _logger.debug(f"using completer {completer}")
        res = pt.prompt(
            _("请输入第 {} 个参数，参数名称 {}, 参数类型: {} :").format(
                self._param.index, self._param.name, self._user_type_hint
            ),
            completer=completer,
        )
        res = self._converter(res)
        validator = _EXTRA_VALIDATOR.get(self._param.original_tp)
        if validator:
            validator(res)
        return res

    def query_value(self) -> _T:
        while True:
            try:
                return self._query_value_once()
            except Exception as err:
                # _console.print_exception(show_locals=True)
                typer.secho(
                    _("参数不合法，请重新输入: {}").format(err), fg=typer.colors.YELLOW
                )


class CliOutputParameter(Generic[_T]):
    def __init__(self, param: OutputParameter[_T]):
        self._param = param

    def _check_is_path(self, filename: str):
        path = pathlib.Path(filename)

    def _query_path(self):
        completer = ptc.PathCompleter()
        while True:
            res = pt.prompt(_("请输入要保存执行结果的位置: "), completer=completer)
            path = pathlib.Path(res)
            if path.exists() and path.is_dir():
                return path
            typer.secho(
                _("输入的路径不存在或不是一个有效的目录，请重新输入"),
                fg=typer.colors.YELLOW,
            )

    def show_to_user(self, value: _T):
        _logger.debug(self._param.original_tp)
        if self._param.original_tp is not UserOutputFilePath:
            typer.secho(_("执行结果为: {}").format(value))
            return
        out_path = self._query_path()
        assert isinstance(value, pathlib.Path)
        path = value
        if not path.exists() or not path.is_file():
            raise ValueError(_("任务输出路径的文件不存在或不是一个有效的文件"))
        shutil.copy(path, out_path)
        typer.echo("保存成功")


@final
class CliTask:
    def __init__(self, task: ParsedTask):
        self._task = task
        self._input_params = [
            CliInputParameter.parse(param) for param in self._task.input_params
        ]
        self._output_param = CliOutputParameter(task.output_param)
        self._filled_param = []

    def _query_param(self):
        self._filled_param = []
        for param in self._input_params:
            self._filled_param.append(param.query_value())

    def query_and_run(self):
        self._query_param()
        assert len(self._filled_param) == len(self._input_params)
        typer.secho(_("开始执行任务 {}").format(self._task.name), fg=typer.colors.GREEN)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(_("正在执行任务 {}").format(self._task.name))
            try:
                res = self._task.origin_task(*self._filled_param)
            except Exception as err:
                _console.print_exception(show_locals=True)
                typer.secho(
                    _("任务 {} 执行失败").format(self._task.name), fg=typer.colors.RED
                )
                return
        try:
            self._output_param.show_to_user(res)
        except Exception as err:
            typer.secho(
                _("任务 {} 结果导出失败").format(self._task.name), fg=typer.colors.RED
            )
            _console.print_exception(show_locals=True)
            return
        typer.secho(
            _("任务 {} 执行完毕").format(self._task.name), fg=typer.colors.GREEN
        )


class CliApplication(Application):
    def __init__(
        self,
        title: Optional[str] = None,
    ):
        self._name_task_mapping: Dict[str, CliTask] = {}
        self._title = title
        self._exit_command = _("退出")

    def register(self) -> Callable[[Task_T], Task_T]:
        def decorator(func: Task_T) -> Task_T:
            task_name = func.__name__
            assert task_name != self._exit_command
            if task_name in self._name_task_mapping:
                raise TypeError(_(f"Multiple task can not have same name: {task_name}"))
            self._name_task_mapping[task_name] = CliTask(ParsedTask.parse(func))
            return func

        return decorator

    def _loop(self) -> bool:
        return True

    def _main(self):
        while self._loop():
            task_name: str = inquirer.list_input(
                _("请选择你要执行的任务"),
                choices=list(self._name_task_mapping.keys()) + [self._exit_command],
            )
            if task_name == self._exit_command:
                return
            task = self._name_task_mapping[task_name]
            task.query_and_run()

    def __call__(self):
        typer.run(self._main)
