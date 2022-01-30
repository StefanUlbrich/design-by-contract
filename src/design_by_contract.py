import logging
from inspect import get_annotations, getfullargspec
from typing import (
    Annotated,
    Callable,
    Dict,
    TypeVar,
    ParamSpec,
    Optional,
    Sequence,
    Any,
    Tuple,
    Set,
)
from decorator import decorator

logger = logging.getLogger(__name__)

_RESERVED = {"pre", "post"}

SHORTCUT_SYMBOL = "x"

P = ParamSpec("P")
R = TypeVar("R")


def _evaluate_condition(condition: Callable[..., bool], injectables: Dict[str, Any]) -> Tuple[Set[str], bool]:
    """Evaluate condition and return the set of unresolved identifiers and the result of the condition."""
    condition_args = getfullargspec(condition).args
    unresolved = set(condition_args) - set(injectables.keys())

    if len(unresolved) > 0:
        return unresolved, False

    return unresolved, condition(*[injectables[i] for i in condition_args])


def _contract(
    func: Callable[P, R],
    variables: Optional[Dict[str, Callable[..., bool]]] = None,
    pre: Optional[Sequence[Callable[..., bool]]] = None,
    post: Optional[Sequence[Callable[..., bool]]] = None,
    *args,
    **kw,
) -> R:
    """The actual decorator for implementing design by contract.

    Use :func:`contract` a factory that generates the actual decorator.
    """

    annotations = get_annotations(func)

    if len(_RESERVED.intersection(annotations.keys())) > 0:
        raise ValueError(
            f"Argument names are not allowed be `{_RESERVED}: {_RESERVED.intersection(annotations.keys())}`"
        )

    # Resolved function arguments passed to func
    argv = {k: v for k, v in zip(annotations.keys(), args)}

    injectables: Dict[str, Any] = {}

    # Definitions are variables extracted from the arguments
    # They rules are given to the `contract`` factory
    if variables is not None:
        for name, definition in variables.items():
            # FIXME mypy error
            if not isinstance(definition, Callable):  # type: ignore
                raise ValueError(f"Expected callable for dependency `{name}`")

            definition_args = getfullargspec(definition).args
            # Only argument names that appear in the decorated function are allowed
            unresolved = set(definition_args) - set(annotations.keys())
            if unresolved:
                raise ValueError(f"Unkown argument names `{unresolved}`")

            # inject arguments into definition function
            injectables[name] = definition(*[argv[i] for i in definition_args])

    # together with the arguments, definitions form the injectables
    injectables |= argv

    logger.debug("injectables: %s", injectables)

    for arg_name, annotation in annotations.items():
        # Filter for typing.Annotation objects with extra annotations
        if hasattr(annotation, "__metadata__"):
            for i, meta in enumerate(annotation.__metadata__):
                # Only consider lambdas/callables
                if isinstance(meta, Callable):  # type: ignore
                    meta_args = getfullargspec(meta).args
                    # Only if the original argument's name is among its argument names
                    if arg_name in meta_args:
                        unresolved, valid = _evaluate_condition(meta, injectables)
                        if len(unresolved) > 0:
                            raise ValueError(
                                f"Cannot inject `{unresolved}` for argument `{arg_name}`, {i+1}. condition"
                            )
                        if not valid:
                            raise ValueError(f"Contract violated for argument: `{arg_name}`, {i+1}. condition")

    if pre is not None:
        for i, condition in enumerate(pre):
            unresolved, valid = _evaluate_condition(condition, injectables)
            if len(unresolved) > 0:
                raise ValueError(f"Cannot inject `{unresolved}` for the `{i+1}`. global precoditions")
            if not valid:
                raise ValueError(f"Contract violated for argument for the `{i+1}`. global precoditions")

    result = func(*args, **kw)

    injectables[SHORTCUT_SYMBOL] = result

    if post is not None:
        for i, condition in enumerate(post):
            unresolved, valid = _evaluate_condition(condition, injectables)
            if len(unresolved) > 0:
                raise ValueError(f"Cannot inject `{unresolved}` for the `{i+1}`. postconditions")
            if not valid:
                raise ValueError(f"Contract violated for argument for the `{i+1}`. postconditions")

    return result


def contract(
    pre: Optional[Sequence[Callable[..., bool]]] = None,
    post: Optional[Sequence[Callable[..., bool]]] = None,
    **variables,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Factory that generates the decorator (necessary for decorator keywords args)"""

    def caller(func: Callable[P, R], *args, **kw) -> R:
        return _contract(func, variables, pre, post, *args, **kw)

    return decorator(caller)


if __name__ == "__main__":
    # Example
    import numpy as np

    logging.basicConfig(format=" %(asctime)s - %(levelname)s - %(message)s")
    logger.setLevel(logging.DEBUG)

    @contract(m=lambda a: a.shape[0])
    def spam(a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]) -> bool:
        return True

    spam(np.array([[4, 5, 6, 8]]), np.array([[1, 2, 3]]))

    # Correctly creates mypy error:
    # spam("asdf", 4)
