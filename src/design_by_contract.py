from dataclasses import dataclass
import logging
from inspect import get_annotations, getfullargspec
from typing import Annotated, Callable, Any, TypeVar, ParamSpec, Optional
from decorator import decorator

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

    def __eq__(self, other: Any) -> "UnresolvedSymbol":
        match other:
            case UnresolvedSymbol(None):
                if self.value is None:
                    raise ContractViolationError(f"Symbols `{self.name}` and `{other.name}` undefined")
                other.value = self.value
            case UnresolvedSymbol(_, value) if self.value is None:
                self.value = value
            case UnresolvedSymbol(name, value) if value != self.value:
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


P, R = ParamSpec("P"), TypeVar("R")


@decorator
def contract(
    func: Callable[P, R],
    reserved: str = "x",
    evaluate: bool = True,
    *args,
    **kw,
) -> R:
    """
    A decorator for enabling design by contract using :class:`typing.Annotated`.

    Define contract conditions as lambdas together with their type annotation.

    Parameters
    ----------
    reserved : str, optional
        This symbol gets always replaced by the current argument name, by default "x"
    evaluate : bool, optional
        If False, the contracts are not evaluated, by default True
    """

    if not evaluate:
        return func(*args, **kw)

    annotations = get_annotations(func)
    return_annotation = annotations.pop("return") if "return" in annotations else None

    if reserved in annotations.keys():
        raise ValueError(f"Argument cannot be the reserved identifier `{reserved}`")

    # Resolved function arguments passed to func
    injectables = {k: v for k, v in zip(annotations.keys(), args)}
    logger.debug("injectables: %s", injectables)

    def evaluate_annotations(annotations: dict[str, Any]) -> None:
        nonlocal injectables
        for arg_name, annotation in annotations.items():

            # Filter for typing.Annotation objects with extra annotations
            if hasattr(annotation, "__metadata__"):
                for meta in annotation.__metadata__:
                    # Only consider lambdas/callables
                    if isinstance(meta, Callable):  # type: ignore
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

                                logger.debug("contract for `%s`, unresolved: `%s`, %s", arg_name, unresolved, symbols)

                                if not meta(*[(symbols | injectables)[i] for i in meta_args]):
                                    raise ContractViolationError(f"Contract violated for argument: `{arg_name}`")

                                if any([i.value is None for i in symbols.values()]):
                                    raise ContractLogicError(f"Not all symbols were resolved `{symbols}`", )

                                injectables |= {k: v.value for k, v in symbols.items()}

                            else:

                                # Evaluate contract by injecting values into the lambda
                                if not meta(*(_args := [injectables[i] for i in meta_args])):
                                    raise ContractViolationError(f"Contract violated for argument: `{arg_name}`")

                            logger.debug("Contract fullfilled for argument `%s`", arg_name)

    evaluate_annotations(annotations)

    result = func(*args, **kw)

    if return_annotation is not None:
        injectables["return"] = result
        logger.debug(injectables)
        evaluate_annotations({"return": return_annotation})

    return result


if __name__ == "__main__":
    # pylint: disable=invalid-name, missing-function-docstring
    # Example
    import numpy as np

    logging.basicConfig(format="%(name)s %(levelname)s [%(funcName)s:%(lineno)d] %(message)s")
    logger.setLevel(logging.DEBUG)

    @contract
    def spam(
        a: Annotated[np.ndarray, lambda x, m, n: (m, n) == x.shape],
        b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
    ) -> Annotated[np.ndarray, lambda x, m, o: x.shape == (m, o)]:
        return a @ b

    spam(np.zeros((3, 2)), np.zeros((2, 4)))
