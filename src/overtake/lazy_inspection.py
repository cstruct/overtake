"""This file contains every computation done at the first call of the function."""

from collections import defaultdict
import inspect
from itertools import chain
import sys
from typing import Callable, List, Set, Tuple, get_origin

from typing_extensions import Unpack, get_overloads

from overtake.display_objects import get_fully_qualified_name


class OverloadsNotFoundError(Exception):
    pass


class LazyOverloadsInspection:
    def __init__(self, overtaken_function: Callable):
        self.original_signature = inspect.signature(overtaken_function)
        self.has_defaults = any(p for p in self.original_signature.parameters.values() if p.default != inspect._empty)
        self.implementations: List[Tuple[Callable, inspect.Signature]] = (
            find_implementations(overtaken_function)
        )
        self.arguments_to_check: Set[str] = _find_arguments_to_check(
            self.implementations
        )


def find_implementations(
    overtaken_function: Callable,
) -> List[Tuple[Callable, inspect.Signature]]:
    overloaded_implementations = list(get_overloads(overtaken_function))
    raise_if_no_implementations(overtaken_function, overloaded_implementations)

    result = []
    for overloaded_implementation in overloaded_implementations:
        result.append(
            (overloaded_implementation, inspect.signature(overloaded_implementation))
        )
    return result


def raise_if_no_implementations(
    overtaken_function: Callable, implementations: List[Callable]
) -> None:
    if implementations != []:
        return

    if sys.version_info < (3, 11):
        additional_help = (
            "Did you use 'from typing import overload'? If this is the case, use"
            " 'from typing_extensions import overload' instead. \nOvertake cannot"
            " find the @overload from typing before Python 3.11. When you upgrade to"
            " Python 3.11, you'll be able to use 'from typing import overload'."
        )
    else:
        additional_help = "Did you forget to use '@overload'?"
    raise OverloadsNotFoundError(
        "Overtake could not find the overloads for the function"
        f" '{get_fully_qualified_name(overtaken_function)}'. " + additional_help
    )


def _find_arguments_to_check(
    implementations: List[Tuple[Callable, inspect.Signature]],
) -> Set[str]:
    """We optimise by writing arguments that have types that are changing.

    In some special cases, there might be no types change at all,
    meaning the dispatching is decided by the number of arguments
    provided.
    """
    variadic_unpack_present = False
    all_arguments = set()
    pos_arg_names = defaultdict(set)
    pos_found_types = defaultdict(set)
    kw_found_types = defaultdict(set)
    for _, signature in implementations:
        for argument_pos, (argument_name, argument) in enumerate(
            signature.parameters.items()
        ):
            all_arguments.add(argument_name)
            if get_origin(argument.annotation) == Unpack or (
                isinstance(argument.annotation, str) and "Unpack" in argument.annotation
            ):
                # We don't know yet which arguments this unpack might conflict with so we check all
                variadic_unpack_present = True
            if (
                argument.kind
                in (argument.POSITIONAL_ONLY, argument.POSITIONAL_OR_KEYWORD)
                and argument.annotation not in pos_found_types[argument_pos]
            ):
                pos_arg_names[argument_pos].add(argument_name)
                pos_found_types[argument_pos].add(argument.annotation)

            if (
                argument.kind
                in (
                    argument.KEYWORD_ONLY,
                    argument.POSITIONAL_OR_KEYWORD,
                    argument.VAR_POSITIONAL,
                    argument.VAR_KEYWORD,
                )
                and argument.annotation not in pos_found_types[argument_pos]
            ):
                kw_found_types[argument_name].add(argument.annotation)
    if variadic_unpack_present:
        return all_arguments

    return set(
        chain(
            *(
                pos_arg_names[pos]
                for pos, types in pos_found_types.items()
                if len(types) > 1
            ),
            (name for name, types in kw_found_types.items() if len(types) > 1),
        )
    )
