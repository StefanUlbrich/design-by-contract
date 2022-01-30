from inspect import signature
from typing import Annotated

import numpy as np
import pytest
from design_by_contract import contract

array1 = np.array([[4, 5, 6, 8]])
array2 = np.array([[1, 2, 3]])


def test_unkown_argument():

    # c is not an argument
    @contract(m=lambda c: c.shape[0])
    def spam(a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]):
        pass

    with pytest.raises(ValueError) as exc_info:
        spam(b=array2, a=array1)

    assert str(exc_info.value) == ("Unkown argument names `{'c'}`")


def test_unresolved_injection():

    # n cannot be resolved
    @contract(m=lambda a: a.shape[0])
    def spam(
        a: np.ndarray, b: Annotated[np.ndarray, lambda b, m, n: b.shape == (m, n)]
    ):
        pass

    with pytest.raises(ValueError) as exc_info:
        spam(b=array2, a=array1)
        print(exc_info)

    assert str(exc_info.value) == ("Cannot inject `{'n'}` for argument `b`")


def test_noncallable():
    @contract(m=1)
    def spam(
        a: np.ndarray, b: Annotated[np.ndarray, lambda b, m, n: b.shape == (m, n)]
    ):
        pass

    with pytest.raises(ValueError) as exc_info:
        spam(b=array2, a=array1)

    assert str(exc_info.value) == ("Expected callable for dependency `m`")


def test_contract_violation():
    @contract(m=lambda a: a.shape[0])
    def spam(a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]):
        pass

    # contract violation
    with pytest.raises(ValueError) as exc_info:
        spam(a=array2, b=array1)
    assert str(exc_info.value) == ("Contract violated for argument: `b`")


def test_correct_usage():
    @contract(m=lambda a: a.shape[0])
    def spam(a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]):
        pass

    # independence of order and kw args
    spam(array1, array2)
    spam(a=array1, b=array2)
    spam(b=array2, a=array1)

    # without variables, only argument injection
    @contract()
    def eggs(
        a: np.ndarray, b: Annotated[np.ndarray, lambda b, a: b.shape[0] == a.shape[0]]
    ):
        pass

    eggs(b=array2, a=array1)


def test_docstring():
    @contract(m=lambda a: a.shape[0])
    def spam(a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]):
        """A spam function"""
        pass

    assert spam.__doc__ == "A spam function"


def test_signature():
    @contract(m=lambda a: a.shape[0])
    def spam(a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]):
        pass

    assert "(a: numpy.ndarray, b: typing.Annotated[numpy.ndarray," in str(
        signature(spam)
    )


def test_return():
    @contract(m=lambda a: a.shape[0], post=lambda: None)
    def spam(a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]):
        pass

    with pytest.raises(NotImplementedError) as exc_info:
        spam(b=array2, a=array1)
    assert str(exc_info.value) == ("Checking return values not yet supported")


def test_multiple_contracts():
    @contract(m=lambda a: a.shape[0])
    def spam(
        a: np.ndarray,
        b: Annotated[
            np.ndarray, lambda b, m: b.shape[0] == m, lambda b: b.shape[1] == 3
        ],
    ):
        pass

    spam(b=array2, a=array1)

    # make sure both conditions are evaluated:

    @contract(m=lambda a: a.shape[0])
    def spam2(
        a: np.ndarray,
        b: Annotated[
            np.ndarray, lambda b, m: b.shape[0] == m, lambda b: b.shape[1] == 2
        ],
    ):
        pass

    with pytest.raises(ValueError) as exc_info:
        spam2(a=array2, b=array1)
    assert str(exc_info.value) == ("Contract violated for argument: `b`")