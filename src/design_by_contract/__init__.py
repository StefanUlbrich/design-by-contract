import logging
from dataclasses import dataclass
from functools import partial, wraps
from inspect import get_annotations, getfullargspec, signature
from typing import (
    Annotated,
    Any,
    Callable,
    Optional,
    ParamSpec,
    TypeVar,
    Union,
    overload,
)

logger = logging.getLogger(__name__)


class ContractViolationError(Exception):
    """Raised when a contract is violated"""


class ContractLogicError(Exception):
    """Raised when there is a syntactical error"""


@dataclass
class UnresolvedSymbol:
    """
    Placeholder for unknown symbols in contracts.

    Overrides the equality operator to behave like an
    assignment.
    """

    name: str
    value: Optional[Any] = None

    def __eq__(self, other: Any) -> Union["UnresolvedSymbol", bool]:  # type: ignore[override]
        match other:
            case UnresolvedSymbol(name=name, value=None):
                if self.value is None:
                    raise ContractViolationError(f"Symbols `{self.name}` and `{name}` undefined")
                other.value = self.value
            case UnresolvedSymbol(name=_, value=value) if self.value is None:
                self.value = value
            case UnresolvedSymbol(name=name, value=value) if value != self.value:
                raise ContractViolationError(
                    f"Symbols `{self.name}` and `{name}` do not match: `{self.value}` != `{value}`"
                )
            case self.value:
                return True
            case value if self.value is not None:
                raise ContractViolationError(
                    f"Symbols `{self.name}` and `{other}` do not match: `{self.value}` != `{other}`"
                )
            case value:
                self.value = value
        return self

    def __bool__(self) -> bool:
        return self.value is not None


P = ParamSpec("P")
R = TypeVar("R")


@overload
def contract(func: Callable[P, R]) -> Callable[P, R]:
    ...


@overload
def contract(*, reserved: str = "x", evaluate: bool = True) -> Callable[[Callable[P, R]], Callable[P, R]]:
    ...


def contract(
    func: Optional[Callable[P, R]] = None, *, reserved: str = "x", evaluate: bool = True
) -> Union[Callable[[Callable[P, R]], Callable[P, R]], Callable[P, R]]:
    """
    A decorator for enabling design by contract using :class:`typing.Annotated`.

    Define contract conditions as lambdas together with their type annotation.
    The decorator is overloaded so you can call it eigher with `@contract` or
    `@contract(...)` with our without arguments. Note that positional keywords
    are not allowed (i.e., you need to use keyword arguments)

    Parameters
    ----------
    reserved : str, optional
        This symbol gets always replaced by the current argument name, by default "x".
        This is a keyword only argument.
    evaluate : bool, optional
        If False, the contracts are not evaluated, by default True.
        This is a keyword only argument.
    """

    def wrapper(func: Callable[P, R], *args: Any, **kw: Any) -> R:
        """The actual logic"""

        if not evaluate:
            return func(*args, **kw)

        annotations = get_annotations(func)
        return_annotation = annotations.pop("return", None)

        if reserved in annotations.keys():
            raise ValueError(f"Argument cannot be the reserved identifier `{reserved}`")

        # Resolved function arguments passed to func
        injectables = dict(zip(annotations.keys(), args))
        logger.debug("injectables: %s", injectables)

        def evaluate_annotations(annotations: dict[str, Any]) -> None:
            nonlocal injectables
            for arg_name, annotation in annotations.items():

                # Filter for typing.Annotation objects with extra annotations
                if hasattr(annotation, "__metadata__"):
                    for meta in annotation.__metadata__:
                        # Only consider lambdas/callables
                        if callable(meta):
                            meta_args = getfullargspec(meta).args
                            # Only if the original argument's name is among its argument names
                            # TODO we shold remove that
                            if arg_name in meta_args or reserved in meta_args:

                                # the reserved identifier is a shortcut
                                injectables[reserved] = injectables[arg_name]
                                dependencies = set(injectables.keys()).intersection(meta_args)
                                logger.debug(
                                    "contract for `%s`, resolved: `%s`",
                                    arg_name,
                                    {i: injectables[i] for i in dependencies},
                                )

                                # Look for arguments that cannot be injected
                                if unresolved := set(meta_args) - set(injectables.keys()):

                                    symbols = {i: UnresolvedSymbol(i) for i in unresolved}

                                    logger.debug(
                                        "contract for `%s`, unresolved: `%s`, %s", arg_name, unresolved, symbols
                                    )

                                    if not meta(*[(symbols | injectables)[i] for i in meta_args]):
                                        raise ContractViolationError(f"Contract violated for argument: `{arg_name}`")

                                    if any([i.value is None for i in symbols.values()]):
                                        raise ContractLogicError(
                                            f"Not all symbols were resolved `{symbols}`",
                                        )

                                    injectables |= {k: v.value for k, v in symbols.items()}

                                else:

                                    # Evaluate contract by injecting values into the lambda
                                    if not meta(*(_args := [injectables[i] for i in meta_args])):
                                        raise ContractViolationError(f"Contract violated for argument: `{arg_name}`")

                                logger.debug("Contract fulfilled for argument `%s`", arg_name)

        evaluate_annotations(annotations)

        result = func(*args, **kw)

        if return_annotation is not None:
            injectables["return"] = result
            logger.debug(injectables)
            evaluate_annotations({"return": return_annotation})

        return result

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        return wraps(func)(partial(wrapper, func))

    if func is not None:
        if not callable(func):
            raise TypeError("Not a callable. Did you use a non-keyword argument?")
        return wraps(func)(partial(wrapper, func))

    return decorator
