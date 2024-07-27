from typing_extensions import Annotated
from kirei.types.annotated._validator import (
    ValidatorProvider as ValidatorProvider,
    AfterValidator as AfterValidator,
    AnyValidator as AnyValidator,
    ValidatorChain as ValidatorChain,
    TypeValidatorProvider as TypeValidatorProvider,
)
from kirei.types.annotated.basic_types import PathType, Path


def _validate_path_type(path_type: PathType, path: Path):
    if path_type.type == "user_input_file" and not path.is_file():
        raise ValueError(f"{path} is not a file")
    return path


def get_default_validator_provider() -> ValidatorProvider:
    provider = ValidatorProvider().push_after_partial_validator(
        Path, PathType, _validate_path_type
    )
    return provider
