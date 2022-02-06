import pytest

# pylint: disable-all

from design_by_contract import Delayed, LogicError, ContractViolationError, TenaryReturn, resolve

class TestVariables:
    def test_simple_good(self):
        m = Delayed("m")

        # always return True
        m[-1] == 2
        m[-2] > 2
        m == [1, 2, 3, 2]

        assert m.DBC_check() == TenaryReturn.VALID

    def test_simple_bad(self):

        m = Delayed("m")
        m[-1] == 2
        m[-2] > 2
        m == [1, 2, 3, 1]

        assert m.DBC_check(False) == TenaryReturn.INVALID

        with pytest.raises(ContractViolationError) as exc_info:
            m.DBC_check()
            print(exc_info)
        print(exc_info.value)
        # Note that each each will increase the values in a delayed variable
        assert str(exc_info.value) == ("Ambiguity in variable `m.__getitem__((-1,))`: [2, 1, 1]")

        m = Delayed("m")
        m[-1] == 2
        m[-2] > 2
        m == [1, 2, 1, 2]

        with pytest.raises(ContractViolationError) as exc_info:
            m.DBC_check()
            print(exc_info)

        print(exc_info.value)
        assert str(exc_info.value) == ("Violation `m.__getitem__((-2,)).__gt__((2,))`")

    def test_sets(self):

        m = Delayed("m")
        m == {1, 2, 3}
        m < {1, 2, 3, 4}
        m > {1, 2}
        m - {1} == {2, 3}
        {1, 2, 3, 4, 5} - m == {4, 5}

        m | {5} > {1, 2, 3}
        {4} | m == {1, 2, 3, 4}

        assert m.DBC_check() == TenaryReturn.VALID
        assert m.DBC_values[0] == {1, 2, 3}

        {1, 2} == m

        with pytest.raises(ContractViolationError) as exc_info:
            m.DBC_check()
            print(exc_info)

        print(exc_info.value)
        assert str(exc_info.value) == ("Ambiguity in variable `m`: [{1, 2, 3}, {1, 2}]")

    def test_multi(self):
        m = Delayed("m")
        n = Delayed("n")

        m == n  # tricky because n == 2 is a terminal
        m == True

        assert (
            m.DBC_check() == TenaryReturn.UNRESOLVED
        )  # should raise something? not implemented? .. But should not be hard. Need to allow additional values in a terminal .. but they must be bool?

        m = Delayed("m")
        n = Delayed("n")

        m == n  # tricky because n == 2 is a terminal
        m == 2
        n == 3

        assert (
            m.DBC_check(raise_errors=False) == TenaryReturn.INVALID
        )  # should raise something? not implemented? .. But should not be hard. Need to allow additional values in a terminal .. but they must be bool?

        m = Delayed("m")
        n = Delayed("n")
        m == n  # tricky because n == 2 is a terminal
        m == 2
        n == 2

        assert (
            m.DBC_check() == TenaryReturn.VALID
        )  # should raise something? not implemented? .. But should not be hard. Need to allow additional values in a terminal .. but they must be bool?

    def test_unresolved(self):

        m = Delayed("m")
        n = Delayed("n")

        m[0] == n[0]
        n[1] == m[1]
        m == [1, 2]
        n == [1, 3]

        with pytest.raises(ContractViolationError) as exc_info:
            resolve([m, n], raise_errors=True)

        print(exc_info.value)
        assert str(exc_info.value) == ("Ambiguity in variable `n.__getitem__((1,))`: [2, 3]")


