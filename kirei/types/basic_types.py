import pathlib
from typing import Literal
import pydantic
from pydantic import StringConstraints as StringConstraints
import decimal


Str = str
Float = float
Decimal = decimal.Decimal
Path = pathlib.Path
Int = int


class PathType(pydantic.BaseModel):
    type: Literal["temp_dir", "user_input_file", "out_file"]
