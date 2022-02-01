import pytest

from design_by_contract import Delayed, LogicError, ContractViolationError

class TestVariables:
    def test_simple_good(self):
        m = Delayed('m')

        # always return True
        assert m[-1]==2
        assert m[-2]>2
        assert m==[1,2,3,2]


        assert m.DBC_check()


    def test_simple_bad(self):

        m = Delayed('m')
        assert m[-1]==2
        assert m[-2]>2
        assert m==[1,2,3,1]

        assert not m.DBC_check(False)

        with pytest.raises(ContractViolationError) as exc_info:
            m.DBC_check()
            print(exc_info)

        assert str(exc_info.value) == ("Ambiguity in variable `m.__getitem__((-1,))`: [2, 1, 1]")

        m = Delayed('m')
        assert m[-1]==2
        assert m[-2]>2
        assert m==[1,2,1,2]

        with pytest.raises(ContractViolationError) as exc_info:
            m.DBC_check()
            print(exc_info)

        print(exc_info.value)
        assert str(exc_info.value) == ("Violation `m.__getitem__((-2,)).__gt__((2,))`")


    def test_sets(self):

        m = Delayed('m')
        assert m == {1,2,3}
        assert m < {1,2,3,4}
        assert m > {1,2}
        assert m - {1} == {2,3}
        assert {1,2,3,4,5} - m == {4,5}

        assert m | {5} > {1,2,3}
        assert {4} | m == {1,2,3,4}

        assert m.DBC_check()
        assert m.DBC_values[0] == {1,2,3}

        assert {1,2} == m

        with pytest.raises(ContractViolationError) as exc_info:
            m.DBC_check()
            print(exc_info)

        print(exc_info.value)
        assert str(exc_info.value) == ("Ambiguity in variable `m`: [{1, 2, 3}, {1, 2}]")


