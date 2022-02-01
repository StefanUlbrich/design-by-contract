from typing import List, Optional, Callable, Any
from dataclasses import field, dataclass
from functools import partialmethod
import logging


logger = logging.getLogger(__name__)


def blueprint(self, *args, **kwargs):
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


class LogicError(Exception):
    """Thrown when there is a logic error."""


class ContractViolationError(Exception):
    """Thrown when conditions are not met."""


@dataclass
class Delayed:

    DBC_name: str
    DBC_term: Optional[Callable[[], bool]] = None
    DBC_terminal: bool = False

    DBC_values: List[Any] = field(default_factory=list)
    DBC_children: List["Delayed"] = field(default_factory=list)

    # prefix to avoid naming problems. Leading underscores collide with __getattribute__
    def DBC_check(self, raise_errors=True) -> bool:

        # FIXME  we need to handle the delays in the values

        if self.DBC_term is not None:  # only for the root
            self.DBC_values.append(self.DBC_term())
        elif len(self.DBC_values) == 0:
            raise LogicError(f"Variable not set `{self.DBC_name}`")

        logger.debug("%s, %s, %s", self.DBC_name, self.DBC_values, len(self.DBC_children))

        if not all(i == self.DBC_values[0] for i in self.DBC_values):
            if raise_errors:
                raise ContractViolationError(f"Ambiguity in variable `{self.DBC_name}`: {self.DBC_values}")
            return False

        if len(self.DBC_children) > 0:

            if self.DBC_terminal:
                raise LogicError("Non terminals are not allowed")  # for now

            return all(i.DBC_check(raise_errors) for i in self.DBC_children)

        if not self.DBC_values[0]:  # we are in a terminal
            if raise_errors:
                raise ContractViolationError(f"Violation `{self.DBC_name}`")
            return False
        return True

    def __eq__(self, other):

        self.DBC_values.append(other)
        # Alwyas return True
        return True


for chaining_builtin in ["__call__", "__getitem__", "__add__", "__sub__", "__rsub__", "__radd__", "__or__", "__ror__"]:
    # https://stackoverflow.com/a/2694991
    print(chaining_builtin)
    setattr(
        Delayed,
        chaining_builtin,
        partialmethod(blueprint, attribute=chaining_builtin, terminal=False),
    )

# Comment out for debugging when recursion errors occur
setattr(
    Delayed,
    "__getattr__",
    partialmethod(blueprint, attribute="__getattr__", other="__getattribute__", terminal=False),
)

for terminating_builtin in ["__lt__", "__gt__", "__le__", "__ge__"]:
    logger.debug(terminating_builtin)
    setattr(
        Delayed,
        terminating_builtin,
        partialmethod(blueprint, attribute=terminating_builtin, terminal=True),
    )
