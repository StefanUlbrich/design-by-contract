from typing import List, Optional, Callable, Any, Sequence
from dataclasses import field, dataclass
from functools import partialmethod
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class LogicError(Exception):
    """Thrown when there is a logic error."""


class ContractViolationError(Exception):
    """Thrown when conditions are not met."""


class TenaryReturn(Enum):
    """Return type when checking conditions"""
    VALID = 1
    INVALID = 2
    UNRESOLVED = 3


@dataclass
class Delayed:
    """class"""
    #pylint: disable=invalid-name

    DBC_name: str
    DBC_term: Optional[Callable[[], bool]] = None
    DBC_terminal: bool = False

    DBC_values: List[Any] = field(default_factory=list)
    DBC_children: List["Delayed"] = field(default_factory=list)

    # prefix to avoid naming problems. Leading underscores collide with __getattribute__
    def DBC_check(self, raise_errors=True) -> TenaryReturn:
        """bla"""
        logger.debug("%s, %s, %s", self.DBC_name, self.DBC_values, len(self.DBC_children))

        # FIXME  we need to handle the delays in the values
        if any(len(i.DBC_values) == 0 for i in self.DBC_values if isinstance(i, Delayed)):
            # XXX catch cyclic self-reference

            logger.debug(
                "Unresolved: %s",
                [i.DBC_name for i in self.DBC_values if isinstance(i, Delayed) and len(i.DBC_values) == 0],
            )

            return TenaryReturn.UNRESOLVED

        if self.DBC_term is not None:  # only for the root
            self.DBC_values.append(self.DBC_term())
        elif len(self.DBC_values) == 0:
            raise LogicError(f"Variable not set `{self.DBC_name}`")

        logger.debug("%s, %s, %s", self.DBC_name, self.DBC_values, len(self.DBC_children))

        # XXX Not sure what happens if one of the values is a Delayed
        # FIXME Not what one would expect the == creates a new object .. this evaluates to true

        # if not all(i == self.DBC_values[0] for i in self.DBC_values):
        values = [i.DBC_values[0] if isinstance(i, Delayed) else i for i in self.DBC_values]
        if not all(i == values[0] for i in values):
            if raise_errors:
                raise ContractViolationError(f"Ambiguity in variable `{self.DBC_name}`: {values}")
            return TenaryReturn.INVALID

        if len(self.DBC_children) > 0:

            if self.DBC_terminal:
                raise LogicError("Please dont compare teminals! `{self.DBC_name}`: {self.DBC_values}")  # for now

            returns = [i.DBC_check(raise_errors) for i in self.DBC_children]
            if all(i == TenaryReturn.VALID for i in returns):
                return TenaryReturn.VALID
            elif any(i == TenaryReturn.UNRESOLVED for i in returns):
                return TenaryReturn.UNRESOLVED
            return TenaryReturn.INVALID

        if self.DBC_values[0] is False:  # we are in a terminal -> must be boolean.
            if raise_errors:
                raise ContractViolationError(f"Violation `{self.DBC_name}`")
            return TenaryReturn.INVALID
        return TenaryReturn.VALID

    def __eq__(self, other):

        self.DBC_values.append(other)
        # Alwyas return True
        # return self
        return True


# Add a little meta programming (code generation) to avoid code duplication: all `__*__` functions
# share the same code base


def blueprint(self, *args, **kwargs):
    """Blueprint for all delegated function calls"""
    # Necessary because some dunders have fix position arguments
    attribute = kwargs.pop("attribute")
    is_terminal = kwargs.pop("terminal") if "terminal" in kwargs.keys() else False
    other = kwargs.pop("other") if "other" in kwargs.keys() else attribute

    delayed = Delayed(
        f"{self.DBC_name}.{other}({args})",
        lambda: self.DBC_values[0].__getattribute__(other)(*args, **kwargs),
        is_terminal,
    )
    self.DBC_children.append(delayed)
    if is_terminal:
        return True
    return delayed


for chaining_builtin in [
    "__call__",
    "__getitem__",
    "__add__",
    "__sub__",
    "__rsub__",
    "__radd__",
    "__or__",
    "__ror__",
    "__and__",
    "__rand__",
]:
    # https://stackoverflow.com/a/2694991
    setattr(
        Delayed,
        chaining_builtin,
        partialmethod(blueprint, attribute=chaining_builtin, terminal=False),
    )

# Comment out for debugging when recursion errors occur and during debugging
setattr(
    Delayed,
    "__getattr__",
    partialmethod(blueprint, attribute="__getattr__", other="__getattribute__", terminal=False),
)

for terminating_builtin in ["__lt__", "__gt__", "__le__", "__ge__", "__ne__"]:
    setattr(
        Delayed,
        terminating_builtin,
        partialmethod(blueprint, attribute=terminating_builtin, terminal=True),
    )


def resolve(variables: Sequence[Delayed], raise_errors: bool) -> bool:
    """Resolves a set of delegated objects."""

    iterations = 0
    while (iterations := iterations + 1) < 100:
        check_results = [i.DBC_check(raise_errors=raise_errors) for i in variables]
        if all(i != TenaryReturn.UNRESOLVED for i in check_results):
            break

    if iterations >= 100:
        raise LogicError("colud not resolve all variables")  # todo spit out which
    return all(i == TenaryReturn.VALID for i in check_results)


if __name__ == "__main__":

    logging.basicConfig(format="%(name)s %(levelname)s [%(funcName)s:%(lineno)d] %(message)s")
    logger.setLevel(logging.DEBUG)

    # Add code for debugging here
    m = Delayed("m")
    n = Delayed("n")

    m[0] == n[0]
    n[1] == m[1]
    m == [1, 2]
    n == [1, 2]

    # n.DBC_check()
    print(resolve([m, n], raise_errors=True))
