import inspect
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
    def original_signature(self) -> inspect.Signature:
        return self.inspection_results.original_signature

    @property
    def arguments_to_check(self) -> Set[str]:
        return self.inspection_results.arguments_to_check

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        incompatibilities = []
        for overloaded_implementation, signature in self.implementations:
            try:
                bound_arguments = self.bind_with_defaults(args, kwargs, signature)
                incompatibility = self.find_incompatibility(bound_arguments, signature)
            except TypeError as e:
                incompatibility = IncompatibilityBind(e)

            if incompatibility is None:
                return overloaded_implementation(
                    *bound_arguments.args, **bound_arguments.kwargs
                )
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
        bound_arguments: inspect.BoundArguments,
        signature: inspect.Signature,
    ) -> Union[IncompatibilityReason, None]:
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

    def bind_with_defaults(
        self,
        args: Tuple[object, ...],
        kwargs: Dict[str, object],
        signature: inspect.Signature,
    ) -> inspect.BoundArguments:
        bound_arguments = signature.bind(*args, **kwargs)

        argument_defaults_to_apply = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.default == Ellipsis
        ]
        try:
            bound_default_arguments = self.original_signature.bind_partial(
                *args, **kwargs
            )
            bound_default_arguments.apply_defaults()
        except TypeError:
            return bound_arguments

        args_with_defaults = args
        kwargs_with_defaults = kwargs
        for parameter in argument_defaults_to_apply:
            if (
                parameter.name in bound_arguments.arguments
                or parameter.name not in bound_default_arguments.arguments
            ):
                continue

            parameter_value = bound_default_arguments.arguments[parameter.name]
            if parameter.kind in (
                parameter.KEYWORD_ONLY,
                parameter.POSITIONAL_OR_KEYWORD,
                parameter.VAR_KEYWORD,
            ):
                kwargs_with_defaults = kwargs_with_defaults | {
                    parameter.name: parameter_value
                }
            else:
                args_with_defaults = (*args, parameter_value)

        bound_arguments = signature.bind(*args_with_defaults, **kwargs_with_defaults)
        bound_arguments.apply_defaults()
        return bound_arguments
