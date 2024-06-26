import sys
from textwrap import dedent
from typing import Iterable, List, Sequence

from overtake import CompatibleOverloadNotFoundError, OverloadsNotFoundError, overtake
from overtake.runtime_type_checkers.umbrella import AVAILABLE_TYPE_CHECKERS
import pytest
import typing_extensions


@pytest.mark.parametrize("runtime_type_checker", ["basic", "beartype", "pydantic"])
def test_one_argument(runtime_type_checker: AVAILABLE_TYPE_CHECKERS):
    @typing_extensions.overload
    def my_function(my_var: int) -> int:
        return my_var + 1

    @typing_extensions.overload
    def my_function(my_var: str) -> str:
        return my_var + "dododo"

    @overtake(runtime_type_checker=runtime_type_checker)
    def my_function(my_var) -> int | str: ...

    assert my_function("5153") == "5153dododo"
    assert my_function(3) == 4


@pytest.mark.parametrize("runtime_type_checker", ["beartype", "pydantic"])
def test_one_argument_sequence(runtime_type_checker: AVAILABLE_TYPE_CHECKERS):
    @typing_extensions.overload
    def my_function(my_var: Sequence[int]) -> int:
        return my_var[0]

    @typing_extensions.overload
    def my_function(my_var: Sequence[str]) -> str:
        return my_var[0]

    @overtake(runtime_type_checker=runtime_type_checker)
    def my_function(my_var) -> int | str: ...

    assert my_function(["5153"]) == "5153"
    assert my_function([3]) == 3


@pytest.mark.parametrize("runtime_type_checker", ["beartype", "pydantic"])
def test_one_argument_iterable(runtime_type_checker: AVAILABLE_TYPE_CHECKERS):
    @typing_extensions.overload
    def my_function(my_var: Iterable[int]) -> int:
        return next(iter(my_var))

    @typing_extensions.overload
    def my_function(my_var: Iterable[str]) -> str:
        return next(iter(my_var))

    @overtake(runtime_type_checker=runtime_type_checker)
    def my_function(my_var) -> int | str: ...

    assert my_function(["5153"]) == "5153"
    assert my_function([3]) == 3


@pytest.mark.parametrize("runtime_type_checker", ["basic", "beartype", "pydantic"])
def test_multiple_arguments(runtime_type_checker: AVAILABLE_TYPE_CHECKERS):
    @typing_extensions.overload
    def my_function(unchanged_var: List[str], my_var: int) -> int:
        return my_var + 1

    @typing_extensions.overload
    def my_function(unchanged_var: List[str], my_var: str) -> str:
        return my_var + "dododo"

    @overtake(runtime_type_checker=runtime_type_checker)
    def my_function(unchanged_var, my_var) -> int | str: ...

    assert my_function([], "5153") == "5153dododo"
    assert my_function([], 3) == 4


@pytest.mark.parametrize("runtime_type_checker", ["basic", "beartype", "pydantic"])
def test_keyword_arguments(runtime_type_checker: AVAILABLE_TYPE_CHECKERS):
    @typing_extensions.overload
    def my_function(unchanged_var: List[str], my_var: int) -> int:
        return my_var + 1

    @typing_extensions.overload
    def my_function(unchanged_var: List[str], my_var: str) -> str:
        return my_var + "dododo"

    @overtake(runtime_type_checker=runtime_type_checker)
    def my_function(unchanged_var, my_var) -> int | str: ...

    assert my_function(my_var="5153", unchanged_var=[]) == "5153dododo"
    assert my_function(my_var=3, unchanged_var=[]) == 4


@pytest.mark.parametrize("runtime_type_checker", ["basic", "beartype", "pydantic"])
def test_variable_number_of_arguments(runtime_type_checker: AVAILABLE_TYPE_CHECKERS):
    @typing_extensions.overload
    def my_function(my_var: int) -> int:
        return my_var + 1

    @typing_extensions.overload
    def my_function(my_var: str, my_second: float = 4.1) -> str:
        return my_var + " new chars"

    @overtake(runtime_type_checker=runtime_type_checker)
    def my_function(my_var, my_second) -> int | str: ...

    assert my_function("base", my_second=5.2) == "base new chars"
    assert my_function(3) == 4


@pytest.mark.parametrize("runtime_type_checker", ["basic", "beartype", "pydantic"])
def test_variable_number_of_arguments_same_types(
    runtime_type_checker: AVAILABLE_TYPE_CHECKERS,
):
    @typing_extensions.overload
    def my_function(my_var: int) -> int:
        return my_var

    @typing_extensions.overload
    def my_function(my_var: int, my_second: float) -> float:
        return my_var + my_second

    @overtake(runtime_type_checker=runtime_type_checker)
    def my_function(my_var, my_second) -> int | float: ...

    assert isinstance(my_function(3), int)
    assert isinstance(my_function(3, 2.5), float)


@pytest.mark.skipif(
    sys.version_info < (3, 11), reason="typing.overload available in 3.11"
)
@pytest.mark.parametrize("runtime_type_checker", ["basic", "beartype", "pydantic"])
def test_regular_typing_overload(runtime_type_checker: AVAILABLE_TYPE_CHECKERS):
    from typing import overload

    @overload
    def my_function(my_var: int) -> int:
        return my_var + 1

    @overload
    def my_function(my_var: str) -> str:
        return my_var + "dododo"

    @overtake(runtime_type_checker=runtime_type_checker)
    def my_function(my_var) -> int | str: ...

    assert my_function("5153") == "5153dododo"
    assert my_function(3) == 4


@pytest.mark.skipif(
    sys.version_info >= (3, 11), reason="typing.overloads supported after 3.11"
)
@pytest.mark.parametrize("runtime_type_checker", ["basic", "beartype", "pydantic"])
def test_regular_typing_overload_with_old_python_versions(
    runtime_type_checker: AVAILABLE_TYPE_CHECKERS,
):
    from typing import overload

    @overload
    def my_function(my_var: int) -> int:
        return my_var + 1

    @overload
    def my_function(my_var: str) -> str:
        return my_var + "dododo"

    @overtake(runtime_type_checker=runtime_type_checker)
    def my_function(my_var) -> int | str: ...

    with pytest.raises(OverloadsNotFoundError) as err:
        my_function("dodo")
    assert (
        str(err.value) == "Overtake could not find the overloads for the function"
        " 'simple_use_cases_test.test_regular_typing_overload_with_old_python_versions.<locals>.my_function'."
        " Did you use 'from typing import overload'? If this is the case, use 'from"
        " typing_extensions import overload' instead. \nOvertake cannot find the"
        " @overload from typing before Python 3.11. When you upgrade to Python 3.11,"
        " you'll be able to use 'from typing import overload'."
    )


@pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="We want to make sure we don't give wrong hints about the error",
)
@pytest.mark.parametrize("runtime_type_checker", ["basic", "beartype", "pydantic"])
def test_forgotten_overload(runtime_type_checker: AVAILABLE_TYPE_CHECKERS):
    def my_function(my_var: int) -> int:  # type: ignore
        return my_var + 1

    def my_function(my_var: str) -> str:  # type: ignore
        return my_var + "dododo"

    @overtake(runtime_type_checker="beartype")
    def my_function(my_var) -> int: ...

    with pytest.raises(OverloadsNotFoundError) as err:
        my_function("dodo")
    assert (
        str(err.value) == "Overtake could not find the overloads for the function"
        " 'simple_use_cases_test.test_forgotten_overload.<locals>.my_function'."
        " Did you forget to use '@overload'?"
    )


def test_no_compatible_overload_found():
    from typing_extensions import overload

    @overload
    def my_function(my_var: int) -> int:
        return my_var

    @overload
    def my_function(my_var: int, second_var: float) -> int:
        return my_var

    @overload
    def my_function(my_var: str, second_var: float) -> str:
        return my_var

    @overtake(runtime_type_checker="beartype")
    def my_function(my_var, second_var) -> int | str: ...

    with pytest.raises(CompatibleOverloadNotFoundError) as err:
        result = my_function(438.15, 48.5)  # type: ignore
        typing_extensions.assert_never(result)
    assert (
        str(err.value)
        == dedent(
            """
            No compatible overload found for function 'simple_use_cases_test.test_no_compatible_overload_found.<locals>.my_function', here is why:
            Incompatible with '(my_var: int) -> int' because too many positional arguments
            Incompatible with '(my_var: int, second_var: float) -> int' because There is a type hint mismatch for argument my_var: Die_if_unbearable() value 438.15 violates type hint <class 'int'>, as float 438.15 not instance of int.
            Incompatible with '(my_var: str, second_var: float) -> str' because There is a type hint mismatch for argument my_var: Die_if_unbearable() value 438.15 violates type hint <class 'str'>, as float 438.15 not instance of str.
            """
        ).strip()
    )


@pytest.mark.parametrize("runtime_type_checker", ["basic", "beartype", "pydantic"])
def test_force_single_argument(runtime_type_checker: AVAILABLE_TYPE_CHECKERS):
    from typing_extensions import overload

    @overload
    def find_user_balance(*, name: str) -> int:
        return 40

    @overload
    def find_user_balance(*, user_id: int) -> int:
        return 50

    @overtake(runtime_type_checker=runtime_type_checker)
    def find_user_balance(*, user_id=None, name=None) -> int: ...

    assert find_user_balance(name="Julie") == 40
    assert find_user_balance(user_id=14) == 50


@pytest.mark.parametrize("runtime_type_checker", ["basic", "beartype", "pydantic"])
def test_positional_argument_different_type_and_name(
    runtime_type_checker: AVAILABLE_TYPE_CHECKERS,
):
    from typing_extensions import overload

    @overload
    def find_user_balance(name: str, /) -> int:
        return 40

    @overload
    def find_user_balance(user_id: int, /) -> int:
        return 50

    @overtake(runtime_type_checker=runtime_type_checker)
    def find_user_balance(name_or_id: str | int, /) -> int: ...

    assert find_user_balance("Julie") == 40
    assert find_user_balance(14) == 50
