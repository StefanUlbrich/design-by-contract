from inspect import signature
from typing import Annotated

import numpy as np
import pytest
from design_by_contract import contract, ContractViolationError, LogicError

array1 = np.array([[4, 5, 6, 8]])
array2 = np.array([[1, 2, 3]])


@pytest.fixture
def correct_spam():
    @contract
    def spam(
        a: Annotated[np.ndarray, lambda a, m, n: a.shape == (m, n)],
        b: Annotated[np.ndarray, lambda x, n, o: x.shape == (n, o)],
    ) -> Annotated[np.ndarray, lambda x, m,o: x.shape == (m, o)]:
        return a@b
    return spam

class TestDecorator:
    def test_multiplication(self, correct_spam):

        # c is not an argument

        correct_spam(np.ones((3,2)), np.ones((2,4)))

    def test_contract_violation(self, correct_spam):

        with pytest.raises(ContractViolationError) as exc_info:
            correct_spam(np.ones((3,2)), np.ones((4,2)))

        assert str(exc_info.value) == ("Ambiguity in variable `n`: [2, 4]")

    def test_wrong_return(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda a, m, n: a.shape == (m, n)],
            b: Annotated[np.ndarray, lambda x, n, o: x.shape == (n, o)],
        ) -> Annotated[np.ndarray, lambda x, m,n: x.shape == (m, n)]: #wrong!
            return a@b

        with pytest.raises(ContractViolationError) as exc_info:
            spam(np.ones((3,2)), np.ones((2,4)))

        assert str(exc_info.value) == ("Ambiguity in variable `n`: [2, 2, 4]")

    def test_unresolved(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda a, m, n: a.shape == (m, n)],
            b: Annotated[np.ndarray, lambda x, n, o, p: x.shape == (n, o) and o > p],
        ) -> Annotated[np.ndarray, lambda x, m,o: x.shape == (m, o)]:
            return a@b

        with pytest.raises(LogicError) as exc_info:
            spam(np.ones((3,2)), np.ones((2,4)))

        assert str(exc_info.value) == ("Variable not set `p`")

    def test_compare(self):
        @contract
        def spam(
            a: Annotated[np.ndarray, lambda a, m, n: a.shape == (m, n)],
            b: Annotated[np.ndarray, lambda x, m, n, o: x.shape == (n, o) and m < o],
        ) -> Annotated[np.ndarray, lambda x, m,o: x.shape == (m, o)]:
            return a@b

        spam(np.ones((3,2)), np.ones((2,4)))
