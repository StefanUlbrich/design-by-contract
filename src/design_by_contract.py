import logging
from inspect import get_annotations, getfullargspec
from typing import Annotated, Callable, Dict, TypeVar, ParamSpec, Optional

from decorator import decorator

logger = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar("R")


def _contract(
    func: Callable[P, R],
    definitions: Optional[Dict[str, Callable[..., bool]]] = None,
    *args,
    **kw,
) -> R:
    """The actual decorator for implementing design by contract.

    Use :func:`contract` a factory that generates the actual decorator.
    """

    annotations = get_annotations(func)

    # Resolved function arguments passed to func
    argv = {k: v for k, v in zip(annotations.keys(), args)}

    injectables = {}

    # Definitions are variables extracted from the arguments
    # They rules are given to the `contract`` factory
    if definitions is not None:
        for var, definition in definitions.items():
            # FIXME mypy error
            if not isinstance(definition, Callable): # type: ignore
                raise ValueError(f"Expected callable for dependency `{var}`")

            definition_args = getfullargspec(definition).args
            # Only argument names that appear in the decorated function are allowed
            unresolved = set(definition_args) - set(annotations.keys())
            if unresolved:
                raise ValueError(f"Unkown argument names `{unresolved}`")

            # inject arguments into definition function
            injectables[var] = definition(*[argv[i] for i in definition_args])

    # together with the arguments, definitions form the injectables
    injectables |= argv

    logger.debug("injectables: %s", injectables)

    for arg_name, annotation in annotations.items():
        # Filter for typing.Annotation objects with extra annotations
        if hasattr(annotation, "__metadata__"):
            for meta in annotation.__metadata__:
                # Only consider lambdas/callables
                if isinstance(meta, Callable): # type: ignore
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
    return result


def contract(**definitions) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Factory that generates the decorator.

    Necessary to support arbitrary keyword arguments to the decorator.
    See `documentation <https://github.com/micheles/decorator/blob/master/docs/documentation.md#decorator-factories>`_"""

    def caller(func: Callable[P, R], *args, **kw) -> R:
        return _contract(func, definitions, *args, **kw)

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
