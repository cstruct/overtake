from functools import reduce
import inspect
from itertools import chain
import operator
import typing
from typing import Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar, Union

from typing_extensions import ParamSpec, Unpack

from overtake.incompatibility_reasons import (
    FullIncompatibilityReason,
    IncompatibilityBind,
    IncompatibilityOverload,
    IncompatibilityReason,
)
from overtake.lazy_inspection import LazyOverloadsInspection
from overtake.runtime_type_checkers.umbrella import AVAILABLE_TYPE_CHECKERS, check_type


class CompatibleOverloadNotFoundError(Exception):
    pass


T = TypeVar("T")
P = ParamSpec("P")


class OvertakenFunctionRegistry(Generic[P, T]):
    def __init__(
        self,
        overtaken_function: Callable[P, T],
        runtime_type_checker: AVAILABLE_TYPE_CHECKERS,
    ):
        self.overtaken_function = overtaken_function
        self._lazy_inspection: Optional[LazyOverloadsInspection] = None
        self.runtime_type_checker: AVAILABLE_TYPE_CHECKERS = runtime_type_checker

    @property
    def inspection_results(self) -> LazyOverloadsInspection:
        if self._lazy_inspection is None:
            self._lazy_inspection = LazyOverloadsInspection(self.overtaken_function)
        return self._lazy_inspection

    @property
    def implementations(self) -> List[Tuple[Callable, inspect.Signature]]:
        return self.inspection_results.implementations

    @property
    def has_defaults(self) -> bool:
        return self.inspection_results.has_defaults

    @property
    def original_signature(self) -> inspect.Signature:
        return self.inspection_results.original_signature

    @property
    def arguments_to_check(self) -> Set[str]:
        return self.inspection_results.arguments_to_check

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        incompatibilities = []
        for overloaded_implementation, signature in self.implementations:
            incompatibility = self.find_incompatibility(args, kwargs, signature)
            if incompatibility is None:
                return overloaded_implementation(*args, **kwargs)
            else:
                incompatibilities.append(
                    IncompatibilityOverload(signature, incompatibility)
                )
        else:
            self.raise_full_incompatibility(incompatibilities)

    def raise_full_incompatibility(
        self, incompatibilities: List[IncompatibilityOverload]
    ) -> typing.NoReturn:
        error_message = str(
            FullIncompatibilityReason(self.overtaken_function, incompatibilities)
        )
        raise CompatibleOverloadNotFoundError(error_message)

    def find_incompatibility(
        self,
        args: Tuple[object, ...],
        kwargs: Dict[str, object],
        signature: inspect.Signature,
    ) -> Union[IncompatibilityReason, None]:
        if self.has_defaults:
            args, kwargs = self.apply_defaults(args, kwargs, signature)
        try:
            bound_arguments = signature.bind(*args, **kwargs)
        except TypeError as e:
            return IncompatibilityBind(e)

        for argument_name in self.arguments_to_check:
            if argument_name not in bound_arguments.arguments:
                continue
            argument_value = bound_arguments.arguments[argument_name]
            type_hint = signature.parameters[argument_name].annotation
            parameter = signature.parameters[argument_name]
            if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
                if typing.get_origin(type_hint) == Unpack:
                    unpacked = typing.get_args(type_hint)[0]
                    if typing.get_origin(unpacked) == tuple:
                        type_hint = unpacked
                    else:
                        type_hint = tuple[unpacked, ...]
                else:
                    type_hint = tuple[type_hint, ...]
            elif parameter.kind == inspect.Parameter.VAR_KEYWORD:
                if typing.get_origin(type_hint) == Unpack:
                    type_hint = typing.get_args(type_hint)[0]
                else:
                    type_hint = Dict[str, type_hint]  # type: ignore

            if type_hint == inspect.Parameter.empty:
                continue

            incompatibility_reason = check_type(
                argument_value, type_hint, argument_name, self.runtime_type_checker
            )
            if incompatibility_reason is None:
                continue
            else:
                return incompatibility_reason

        return None

    def apply_defaults(self, args: Tuple[object, ...], kwargs: Dict[str, object], signature: inspect.Signature) -> tuple[Tuple[object, ...], Dict[str, object]]:
        try:
            bound_arguments = self.original_signature.bind_partial(*args, **kwargs)
            bound_arguments.apply_defaults()
            args_with_defaults = tuple(chain(*(
                bound_arguments.arguments[name] if parameter.kind is parameter.VAR_POSITIONAL else [bound_arguments.arguments[name]]
                for name, parameter
                in bound_arguments.signature.parameters.items()
                if name in bound_arguments.arguments
                and (parameter.kind in (parameter.POSITIONAL_ONLY, parameter.VAR_POSITIONAL)
                    or (parameter.kind is parameter.POSITIONAL_OR_KEYWORD and name in signature.parameters))
            )))
            kwargs_with_defaults = reduce(operator.ior, (
                bound_arguments.arguments[name] if parameter.kind is parameter.VAR_KEYWORD else {name: bound_arguments.arguments[name]}
                for name, parameter
                in bound_arguments.signature.parameters.items()
                if name in bound_arguments.arguments
                and (
                    parameter.kind in (parameter.KEYWORD_ONLY, parameter.VAR_KEYWORD)
                    or (parameter.kind is parameter.POSITIONAL_OR_KEYWORD and name not in signature.parameters))
            ), {})
            return args_with_defaults, kwargs_with_defaults
        except TypeError:
            return args, kwargs
