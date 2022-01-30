import logging
from inspect import get_annotations, getfullargspec
from typing import Annotated, Callable, Dict, TypeVar, ParamSpec, Optional, Sequence
from decorator import decorator

logger = logging.getLogger(__name__)

_RESERVED = {"pre", "post"}
P = ParamSpec("P")
R = TypeVar("R")


def _contract(
    func: Callable[P, R],
    variables: Optional[Dict[str, Callable[..., bool]]] = None,
    pre: Optional[Sequence[Callable[..., bool]]] = None,
    post: Optional[Callable[..., bool]] = None,
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

    injectables = {}

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
            for meta in annotation.__metadata__:
                # Only consider lambdas/callables
                if isinstance(meta, Callable):  # type: ignore
                    meta_args = getfullargspec(meta).args
                    # Only if the original argument's name is among its argument names
                    if arg_name in meta_args:
                        dependencies = set(injectables.keys()).intersection(meta_args)
                        logger.debug(
                            "contract for `%s`, dependencies: `%s`",
                            arg_name,
                            {i: injectables[i] for i in dependencies},
                        )

                        # Look for arguments that cannot be injected
                        unresolved = set(meta_args) - set(injectables.keys())
                        if len(unresolved) > 0:
                            raise ValueError(
                                f"Cannot inject `{unresolved}` for argument `{arg_name}`"
                            )
                        # Evaluate contract by injecting values into the lambda
                        if not meta(*[injectables[i] for i in meta_args]):
                            raise ValueError(
                                f"Contract violated for argument: `{arg_name}`"
                            )
                        logger.debug("contract fullfilled for argument `%s`", arg_name)

    result = func(*args, **kw)

    if pre is not None or post is not None:
        raise NotImplementedError("Checking return values not yet supported")

    return result


def contract(
    pre: Optional[Sequence[Callable[..., bool]]] = None,
    post: Optional[Callable[..., bool]] = None,
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
    def spam(
        a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]
    ) -> bool:
        return True

    spam(np.array([[4, 5, 6, 8]]), np.array([[1, 2, 3]]))

    # Correctly creates mypy error:
    # spam("asdf", 4)
