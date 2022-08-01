from inspect import signature
from typing import Annotated, Any

import numpy as np
from numpy.typing import NDArray
import pandas as pd
import pytest
from design_by_contract import contract, ContractViolationError, UnresolvedSymbol

# pylint: skip-file
class TestNumpy:
    def test_matmult_correct(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda a, m, n: (m, n) == a.shape],
            b: Annotated[NDArray[np.floating[Any]], lambda b, n, o: (n, o) == b.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))

    def test_matmult_correct_shortcut(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda x, m, n: (m, n) == x.shape],
            b: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))

    def test_matmult_violated_in_return(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda x, m, n: (m, n) == x.shape],
            b: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, m, n: x.shape == (m, n)]:
            return a @ b

        with pytest.raises(ContractViolationError) as exc_info:
            spam(np.zeros((3, 2)), np.zeros((2, 4)))

        assert str(exc_info.value) == ("Contract violated for argument: `return`")

    def test_matmult_violated_in_argument(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda x, m, n: (m, n) == x.shape],
            b: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, m, n: x.shape == (m, n)]:
            return a @ b

        with pytest.raises(ContractViolationError) as exc_info:
            spam(np.zeros((3, 2)), np.zeros((3, 4)))

        assert str(exc_info.value) == ("Contract violated for argument: `b`")

    def test_matmult_unresolved(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda x, m, n: (m, n) == x.shape and m > 2],
            b: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        with pytest.raises(TypeError) as exc_info:
            spam(np.zeros((3, 2)), np.zeros((2, 4)))

        assert str(exc_info.value) == ("'>' not supported between instances of 'UnresolvedSymbol' and 'int'")

    def test_matmult_multi(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda x, m, n: (m, n) == x.shape, lambda x: x.shape[1] == 2],
            b: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))

    def test_matmult_mixed(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda x, m, n: (m, n) == x.shape and x.shape[1] == 2],
            b: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))

    def test_matmult_mixed_2(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda x, n: (3, n) == x.shape],
            b: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, o: x.shape == (3, o)]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))

    def test_matmult_mixed_violated(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda x, n: (4, n) == x.shape],
            b: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, o: x.shape == (3, o)]:
            return a @ b

        # Here we would expect a contract violation
        # However, n==shape[1] will not be evaluated so the unresolved
        # error is raised first

        with pytest.raises(ContractViolationError) as exc_info:
            spam(np.zeros((3, 2)), np.zeros((2, 4)))

        assert str(exc_info.value) == ("Contract violated for argument: `a`")

    def test_vstack(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda x, m, o: (m, o) == x.shape],
            b: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, m, n, o: x.shape == (m + n, o)]:
            print(np.vstack((a, b)).shape)
            return np.vstack((a, b))

        spam(np.zeros((3, 2)), np.zeros((4, 2)))


class TestGeneral:
    def test_docstring(self) -> None:
        @contract
        def spam(
            a: NDArray[np.floating[Any]], b: Annotated[NDArray[np.floating[Any]], lambda b, m: b.shape == (m, 3)]
        ) -> None:
            """A spam function"""
            pass

        assert spam.__doc__ == "A spam function"

    def test_signature(self) -> None:
        @contract
        def spam(
            a: NDArray[np.floating[Any]], b: Annotated[NDArray[np.floating[Any]], lambda b, m: b.shape == (m, 3)]
        ) -> None:
            pass

        assert (
            "(a: numpy.ndarray[typing.Any, numpy.dtype[numpy.floating[typing.Any]]], "
            "b: typing.Annotated[numpy.ndarray[typing.Any, numpy.dtype[numpy.floating[typing.Any]]],"
            in str(signature(spam))
        )

    def test_reserved(self) -> None:
        @contract(reserved="y")
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda y, m, n: (m, n) == y.shape],
            b: Annotated[NDArray[np.floating[Any]], lambda y, n, o: (n, o) == y.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda y, m, o: y.shape == (m, o)]:

            return a @ b

    def test_match(self) -> None:
        a, b = UnresolvedSymbol("a"), UnresolvedSymbol("b")
        a == 2
        b == a
        assert a.value == b.value

    def test_match_fail(self) -> None:
        a, b = UnresolvedSymbol("a"), UnresolvedSymbol("b")
        a == 2
        b == 1
        with pytest.raises(ContractViolationError) as exc_info:
            a == b

    def test_match_symmetry(self) -> None:
        a, b = UnresolvedSymbol("a"), UnresolvedSymbol("b")
        a == 2
        assert a.value == 2

        b = UnresolvedSymbol("a")
        2 == b
        assert b.value == 2

    def test_match_fail2(self) -> None:
        a = UnresolvedSymbol("a")
        a == 2

        with pytest.raises(ContractViolationError) as exc_info:
            a == 3

        with pytest.raises(ContractViolationError) as exc_info:
            3 == a

        a == 2
        2 == a

    def test_matching(self) -> None:
        a = UnresolvedSymbol("a")
        b = UnresolvedSymbol("b")

        with pytest.raises(ContractViolationError) as exc_info:
            a == b

        assert str(exc_info.value) == ("Symbols `a` and `b` undefined")

    def test_decorator_non_kw(self) -> None:

        with pytest.raises(TypeError) as exc_info:

            @contract("y")  # type: ignore
            def spam(
                a: Annotated[NDArray[np.floating[Any]], lambda y, m, n: (m, n) == y.shape],
                b: Annotated[NDArray[np.floating[Any]], lambda y, n, o: (n, o) == y.shape],
            ) -> Annotated[NDArray[np.floating[Any]], lambda y, m, o: y.shape == (m, o)]:

                return a @ b

        assert str(exc_info.value) == "Not a callable. Did you use a non-keyword argument?"

    def test_decorator_empty_paranthesis(self) -> None:
        @contract()
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda x, m, n: (m, n) == x.shape],
            b: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        with pytest.raises(ContractViolationError) as exc_info:
            spam(np.zeros((3, 2)), np.zeros((3, 4)))

        assert str(exc_info.value) == ("Contract violated for argument: `b`")

    def test_no_symbols(self) -> None:
        @contract
        def spam(
            a: Annotated[NDArray[np.floating[Any]], lambda a, b: a.shape[1] == b.shape[0]],
            b: NDArray[np.floating[Any]],
        ) -> Annotated[NDArray[np.floating[Any]], lambda x, a, b: x.shape == (a.shape[0], b.shape[1])]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))


class TestPandas:
    def test_pandas_correct(self) -> None:
        a = pd.DataFrame(np.random.randint(0, 2, size=(10, 3)), columns=list("ABC"))
        b = pd.DataFrame(np.random.randint(0, 3, size=(10, 3)), columns=list("BCD"))

        @contract
        def spam(
            a: Annotated[pd.DataFrame, lambda x, c: c == {"C", "B"}, lambda x, c: c.issubset(x.columns)],
            b: Annotated[pd.DataFrame, lambda x, c: c <= set(x.columns)],
        ) -> Annotated[pd.DataFrame, lambda x, c: c <= set(x.columns)]:
            return pd.merge(a, b, on=["B", "C"])

        spam(a, b)

    def test_pandas_violated_argument(self) -> None:
        a = pd.DataFrame(np.random.randint(0, 2, size=(10, 3)), columns=list("ABC"))
        b = pd.DataFrame(np.random.randint(0, 3, size=(10, 3)), columns=list("CDE"))

        @contract
        def spam(
            a: Annotated[pd.DataFrame, lambda x, c: c == {"C", "B"}, lambda x, c: c.issubset(x.columns)],
            b: Annotated[pd.DataFrame, lambda x, c: c <= set(x.columns)],
        ) -> Annotated[pd.DataFrame, lambda x, c: c <= set(x.columns)]:
            return pd.merge(a, b, on=["B", "C"])

        with pytest.raises(ContractViolationError) as exc_info:
            spam(a, b)

        assert str(exc_info.value) == ("Contract violated for argument: `b`")
