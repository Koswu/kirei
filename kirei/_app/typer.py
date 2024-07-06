from typing import Callable
from kirei._types import Application, Task


class TyperApplication(Application):
    def register[Task_T: Task](self) -> Callable[[Task_T], Task_T]:
        ...
