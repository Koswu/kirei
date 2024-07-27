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
    Optional,
    TypeVar,
)
import inquirer
import prompt_toolkit as pt
from prompt_toolkit import completion as ptc
import rich

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from kirei.types import Task_T, Application
from kirei.types import (
    FuncParam,
    FuncParser,
    ParsedFunc,
    FuncParser,
    ParamInquirerCollection,
    ReplierCollection,
)
from kirei.types.function._injector import get_default_context_collection
from kirei.types.function._param_annotation import ParamAnnotation
from kirei.types.basic_types import PathType


_ = gettext.gettext
_T = TypeVar("_T")
_console = rich.console.Console()


_logger = logging.getLogger(__name__)
_context_collection = get_default_context_collection()


def _anystr_inquirer(
    index: int, name: str, type_name: str, completer: Optional[ptc.Completer] = None
) -> str:
    return pt.prompt(
        _("请输入第 {} 个参数，参数名称 {}, 参数类型: {} :").format(
            index, name, type_name
        ),
        completer=completer,
    )


def _str_param_inquirer(param: FuncParam) -> str:
    _USER_TYPE_HINT_MAPPING = {
        int: _("整数"),
        str: _("文本"),
        Decimal: _("小数"),
    }
    return _anystr_inquirer(
        param.index,
        param.name,
        _USER_TYPE_HINT_MAPPING[param.real_source_type],
    )


def _user_file_inquirer(param: FuncParam) -> str:
    assert param.real_source_type is pathlib.Path
    pt = param.get_tp_info(PathType)
    if not pt:
        return NotImplemented
    elif pt.type != "user_input_file":
        return NotImplemented
    return _anystr_inquirer(
        param.index,
        param.name,
        _("文件(需要输入文件路径)"),
        completer=ptc.PathCompleter(),
    )


def _print_replier(param: ParamAnnotation, res: Any):
    typer.secho(_("执行结果为: {}").format(res))


def _file_replier(param: ParamAnnotation, res: pathlib.Path):
    path_type = param.get_tp_info(PathType)
    if not path_type:
        return NotImplemented
    if path_type.type != "out_file":
        return NotImplemented
    if not res.exists():
        raise ValueError(_("任务输出路径的文件不存在"))
    if not res.is_file():
        raise ValueError(_("任务输出路径不是一个有效的文件"))
    while True:
        out_path = pathlib.Path(
            pt.prompt(
                _("执行结果为文件，请输入要保存到的位置:"),
                completer=ptc.PathCompleter(only_directories=True),
            )
        )
        if out_path.is_dir() or out_path.parent.is_dir():
            break
        typer.secho(_("输入的路径不存在或不是一个有效的目录，请重新输入"))
    shutil.copy(res, out_path)
    typer.secho("文件已经成功保存到: {}".format(out_path))


_inquirer = (
    ParamInquirerCollection()
    .register_multi(_str_param_inquirer, [str, int, Decimal])
    .register(_user_file_inquirer, pathlib.Path)
)
_replier = (
    ReplierCollection()
    .register_multi(_print_replier, [str, int, Decimal])
    .register(_file_replier, pathlib.Path)
)


class CliApplication(Application):
    def __init__(
        self,
        title: Optional[str] = None,
    ):
        self._name_task_mapping: Dict[str, ParsedFunc] = {}
        self._title = title
        self._func_parser = FuncParser(_context_collection)
        self._is_running = True
        self.register(_("退出"))(lambda: self._exit())

    def _exit(self):
        self._is_running = False

    def register(
        self, override_task_name: Optional[str] = None
    ) -> Callable[[Task_T], Task_T]:
        def decorator(func: Task_T) -> Task_T:
            task_name = override_task_name or func.__name__
            if task_name in self._name_task_mapping:
                raise TypeError(_(f"Multiple task can not have same name: {task_name}"))
            self._name_task_mapping[task_name] = self._func_parser.parse(
                func, override_task_name
            )
            return func

        return decorator

    def _fill_param(self, param: FuncParam):
        while True:
            value = _inquirer(param)
            try:
                param.fill(value)
                return
            except Exception as err:
                typer.secho(_("参数校验失败：{}".format(err)), fg=typer.colors.RED)
                typer.secho("请重新输入", fg=typer.colors.YELLOW)

    def _show_task_result(self, annotation: ParamAnnotation, res: Any):
        try:
            _replier(annotation, res)
        except Exception as err:
            typer.secho(_("任务执行结果处理失败:{}".format(err)), fg=typer.colors.RED)

    def _execute_task(self, task: ParsedFunc):
        with task.enter_session() as session:
            for param in session.meta_data.non_injected_params:
                self._fill_param(param)
            typer.secho(
                _("开始执行任务 {}").format(session.meta_data.name),
                fg=typer.colors.GREEN,
            )
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                try:
                    progress.add_task(
                        _("正在执行任务 {}").format(session.meta_data.name)
                    )
                    res = session()
                except Exception as err:
                    typer.secho(
                        _("任务执行失败:以下是相关的错误信息"), fg=typer.colors.RED
                    )
                    _console.print_exception(show_locals=True)
                    typer.secho(_("任务执行失败"), fg=typer.colors.RED)
                    return
            typer.secho(_("任务执行完毕"), fg=typer.colors.GREEN)
            self._show_task_result(session.meta_data.return_type_annotation, res)

    def _main(self):
        while self._is_running:
            task_name: str = inquirer.list_input(
                _("请选择你要执行的任务"),
                choices=list(self._name_task_mapping.keys()),
            )
            task = self._name_task_mapping[task_name]
            self._execute_task(task)

    def __call__(self):
        typer.run(self._main)
