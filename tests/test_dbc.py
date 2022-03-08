from inspect import signature
from typing import Annotated

import numpy as np
import pandas as pd
import pytest
from design_by_contract import contract, ContractViolationError, ContractLogicError, UnresolvedSymbol

# pylint: skip-file
class TestNumpy:
    def test_matmult_correct(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda a, m, n: (m, n) == a.shape],
            b: Annotated[np.ndarray, lambda b, n, o: (n, o) == b.shape],
        ) -> Annotated[np.ndarray, lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))

    def test_matmult_correct_shortcut(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda x, m, n: (m, n) == x.shape],
            b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[np.ndarray, lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))

    def test_matmult_violated_in_return(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda x, m, n: (m, n) == x.shape],
            b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[np.ndarray, lambda x, m, n: x.shape == (m, n)]:
            return a @ b

        with pytest.raises(ContractViolationError) as exc_info:
            spam(np.zeros((3, 2)), np.zeros((2, 4)))

        assert str(exc_info.value) == ("Contract violated for argument: `return`")

    def test_matmult_violated_in_argument(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda x, m, n: (m, n) == x.shape],
            b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[np.ndarray, lambda x, m, n: x.shape == (m, n)]:
            return a @ b

        with pytest.raises(ContractViolationError) as exc_info:
            spam(np.zeros((3, 2)), np.zeros((3, 4)))

        assert str(exc_info.value) == ("Contract violated for argument: `b`")

    def test_matmult_unresolved(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda x, m, n: (m, n) == x.shape and m > 2],
            b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[np.ndarray, lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        with pytest.raises(TypeError) as exc_info:
            spam(np.zeros((3, 2)), np.zeros((2, 4)))

        assert str(exc_info.value) == ("'>' not supported between instances of 'UnresolvedSymbol' and 'int'")

    def test_matmult_multi(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda x, m, n: (m, n) == x.shape, lambda x: x.shape[1] == 2],
            b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[np.ndarray, lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))

    def test_matmult_mixed(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda x, m, n: (m, n) == x.shape and x.shape[1] == 2],
            b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[np.ndarray, lambda x, m, o: x.shape == (m, o)]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))

    def test_matmult_mixed_2(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda x, n: (3, n) == x.shape],
            b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[np.ndarray, lambda x, o: x.shape == (3, o)]:
            return a @ b

        spam(np.zeros((3, 2)), np.zeros((2, 4)))

    def test_matmult_mixed_violated(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda x, n: (4, n) == x.shape],
            b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[np.ndarray, lambda x, o: x.shape == (3, o)]:
            return a @ b

        # Here we would expect a contract violation
        # However, n==shape[1] will not be evaluated so the unresolved
        # error is raised first

        with pytest.raises(ContractViolationError) as exc_info:
            spam(np.zeros((3, 2)), np.zeros((2, 4)))

        assert str(exc_info.value) == ("Contract violated for argument: `a`")

    def test_vstack(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda x, m, o: (m, o) == x.shape],
            b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
        ) -> Annotated[np.ndarray, lambda x, m, n, o: x.shape == (m + n, o)]:
            print(np.vstack((a, b)).shape)
            return np.vstack((a, b))

        spam(np.zeros((3, 2)), np.zeros((4, 2)))


class TestGeneral:
    def test_docstring(self):
        @contract
        def spam(a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]):
            """A spam function"""
            pass

        assert spam.__doc__ == "A spam function"

    def test_signature(self):
        @contract
        def spam(a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]):
            pass

        assert "(a: numpy.ndarray, b: typing.Annotated[numpy.ndarray," in str(signature(spam))

    def test_reserved(self):
        @contract(reserved="y")
        def spam(
            a: Annotated[np.ndarray, lambda y, m, n: (m, n) == y.shape],
            b: Annotated[np.ndarray, lambda y, n, o: (n, o) == y.shape],
        ) -> Annotated[np.ndarray, lambda y, m, o: y.shape == (m, o)]:

            return a @ b

    def test_match(self):
        a, b = UnresolvedSymbol("a"), UnresolvedSymbol("b")
        a == 2
        b == a
        assert a.value == b.value

    def test_match_fail(self):
        a, b = UnresolvedSymbol("a"), UnresolvedSymbol("b")
        a == 2
        b == 1
        with pytest.raises(ContractViolationError) as exc_info:
            a == b

    def test_match_symmetry(self):
        a, b = UnresolvedSymbol("a"), UnresolvedSymbol("b")
        a == 2
        assert a.value == 2

        b = UnresolvedSymbol("a")
        2 == b
        assert b.value == 2

    def test_match_fail2(self):
        a = UnresolvedSymbol("a")
        a == 2

        with pytest.raises(ContractViolationError) as exc_info:
            a == 3

        with pytest.raises(ContractViolationError) as exc_info:
            3 == a

        a == 2
        2 == a


class TestPandas:
    def test_pandas_correct(self):
        a = pd.DataFrame(np.random.randint(0, 2, size=(10, 3)), columns=list("ABC"))
        b = pd.DataFrame(np.random.randint(0, 3, size=(10, 3)), columns=list("BCD"))

        @contract
        def spam(
            a: Annotated[pd.DataFrame, lambda x, c: c == {"C", "B"}, lambda x, c: c.issubset(x.columns)],
            b: Annotated[pd.DataFrame, lambda x, c: c <= set(x.columns)],
        ) -> Annotated[pd.DataFrame, lambda x, c: c <= set(x.columns)]:
            return pd.merge(a, b, on=["B", "C"])

        spam(a, b)

    def test_pandas_violated_argument(self):
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
