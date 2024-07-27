from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
)
from typing_extensions import Annotated, TypeVar, get_args, get_origin


_TargetT = TypeVar("_TargetT")
_InfoT = TypeVar("_InfoT")

AfterValidator = Callable[[_TargetT], _TargetT]
PreValidator = Callable[[Any], _TargetT]
AnyValidator = Union[AfterValidator[_TargetT], PreValidator[_TargetT]]
AnyValidatorGenerator = Callable[[_InfoT], AnyValidator[_TargetT]]
ValidatorType = Literal["after", "pre"]
PartialPreValidator = Callable[[_InfoT, Any], _TargetT]
PartialAfterValidator = Callable[[_InfoT, _TargetT], _TargetT]


class ValidatorChain(Sequence[AnyValidator[_TargetT]]):
    def __init__(self, chain: Sequence[AnyValidator[_TargetT]]):
        if not chain:
            raise ValueError("chain must not be empty")
        self._chain = list(chain)

    def __len__(self) -> int:
        return len(self._chain)

    def __iter__(self) -> Iterator[AnyValidator[_TargetT]]:
        return iter(self._chain)

    def __call__(self, data: Any) -> _TargetT:
        res = data
        for validator in self._chain:
            res = validator(res)
        return res

    def lpush(self, validator: PreValidator[_TargetT]):
        self._chain.insert(0, validator)
        return self

    def rpush(self, validator: AfterValidator[_TargetT]):
        self._chain.append(validator)
        return self


class TypeValidatorProvider(Generic[_TargetT]):
    def __init__(self, initial_validator: PreValidator[_TargetT]):
        self._initial_validator = initial_validator
        self._validator_generator_mapping: Dict[
            Type, Dict[ValidatorType, AnyValidatorGenerator]
        ] = {}

    def register_validator_generator(
        self,
        info_tp: Type[_InfoT],
        generator: AnyValidatorGenerator[_InfoT, _TargetT],
        validator_type: ValidatorType,
    ):
        current_generator = self._validator_generator_mapping.setdefault(
            info_tp, {}
        ).get(validator_type)
        assert not current_generator
        self._validator_generator_mapping[info_tp][validator_type] = generator
        return self

    def get_info_validator(
        self, info: Any, type: ValidatorType
    ) -> Optional[AnyValidator[_TargetT]]:
        assert type in ["pre", "after"]
        generator = self._validator_generator_mapping.get(info.__class__, {}).get(type)
        if generator is None:
            return None
        return generator(info)

    def get_validator(self, *infos: Any):
        validator_chain = ValidatorChain([self._initial_validator])
        for info in infos:
            for validator_type in ["pre", "after"]:
                validator_type = cast(ValidatorType, validator_type)
                validator = self.get_info_validator(info, validator_type)
                if validator:
                    if validator_type == "pre":
                        validator_chain = validator_chain.lpush(validator)
                    else:
                        validator_chain = validator_chain.rpush(validator)
        return validator_chain


class ValidatorProvider:
    def __init__(self):
        self._tp_to_validator_provider: Dict[Type, TypeValidatorProvider] = {}

    def push_pre_partial_validator(
        self,
        tp: Type[_TargetT],
        info_tp: Type[_InfoT],
        validator: PartialPreValidator[_InfoT, _TargetT],
    ):
        def generator(info: _InfoT) -> PreValidator[_TargetT]:
            return lambda data: validator(info, data)

        self._get_validator_provider(tp).register_validator_generator(
            info_tp, generator, "pre"
        )
        return self

    def push_after_partial_validator(
        self,
        tp: Type[_TargetT],
        info_tp: Type[_InfoT],
        validator: PartialAfterValidator[_InfoT, _TargetT],
    ):
        def generator(info: _InfoT) -> AfterValidator[_TargetT]:
            return lambda data: validator(info, data)

        self._get_validator_provider(tp).register_validator_generator(
            info_tp, generator, "after"
        )
        return self

    def reset_validator(self, tp: Type[_TargetT], validator: PreValidator[_TargetT]):
        self._tp_to_validator_provider[tp] = TypeValidatorProvider(validator)
        return self

    def _get_validator_provider(self, tp: Type[_TargetT]) -> TypeValidatorProvider:
        return self._tp_to_validator_provider.setdefault(tp, TypeValidatorProvider(tp))

    def _get_constraints(self, t: Type[_TargetT]) -> List[Any]:
        origin = get_origin(t)
        if origin is None:
            return []
        elif origin is Annotated:
            return list(get_args(t))[1:]
        else:
            raise NotImplementedError(f"Unsupported origin type: {t}")

    def _get_real_type(self, t: Type[_TargetT]) -> Type[_TargetT]:
        origin = get_origin(t)
        if origin is None:
            return t
        elif origin is Annotated:
            return get_args(t)[0]
        else:
            raise NotImplementedError(f"Unsupported origin type: {t}")

    def get_validator(self, t: Type[_TargetT]) -> Callable[[Any], _TargetT]:
        real_type = self._get_real_type(t)
        constraints = self._get_constraints(t)
        return self._get_validator_provider(real_type).get_validator(*constraints)
