import logging
from inspect import get_annotations, getfullargspec
from typing import Annotated, Callable, Any, Sequence, TypeVar, ParamSpec
from decorator import decorator
from dill.source import getsource

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def make_iterable(x: Any) -> Sequence:
    """Check if argument is a sequence and if not, return wrapped in a list."""
    try:
        _ = iter(x)
        return x
    except TypeError:
        return [x]

@decorator
def contract(
    func: Callable[P, R],
    reserved: str = "x",
    evaluate: bool = True,
    *args,
    **kw,
) -> R:
    """The actual decorator for implementing design by contract.

    Use :func:`contract` a factory that generates the actual decorator.
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

                            logger.debug('Source code `%s`', getsource(meta))
                            # the reserved identifier is a shortcut
                            injectables[reserved] = injectables[arg_name]
                            dependencies = set(injectables.keys()).intersection(meta_args)
                            logger.debug(
                                "contract for `%s`, dependencies: `%s`",
                                arg_name,
                                {i: injectables[i] for i in dependencies},
                            )

                            # Look for arguments that cannot be injected
                            if unresolved := set(meta_args) - set(injectables.keys()):

                                placeholder = {i: None for i in unresolved} | injectables
                                result = make_iterable(meta(*[placeholder[i] for i in meta_args]))

                                if len(unresolved) != len(result):
                                    raise ValueError(f"Cannot inject `{unresolved}` for argument `{arg_name}`")

                                ordered_unresolved = [i for i in meta_args if i in unresolved ]

                                variables = dict(zip(ordered_unresolved, result))
                                injectables |= variables
                                logger.debug("Add injectables `%s`", variables)

                            else:

                                # Evaluate contract by injecting values into the lambda
                                if not meta(*[injectables[i] for i in meta_args]):
                                    raise ValueError(f"Contract violated for argument: `{arg_name}`")
                                logger.debug("contract fullfilled for argument `%s`", arg_name)

    evaluate_annotations(annotations)

    result = func(*args, **kw)

    logger.debug(return_annotation)
    if return_annotation is not None:
        injectables["return"] = result
        logger.debug(injectables)
        evaluate_annotations({"return": return_annotation})

    return result


if __name__ == "__main__":
    # Example
    import numpy as np

    logging.basicConfig(format="%(name)s %(levelname)s [%(funcName)s:%(lineno)d] %(message)s")
    logger.setLevel(logging.DEBUG)

    @contract
    def spam(
        a: Annotated[np.ndarray, lambda x, m, n: x.shape],
        b: Annotated[np.ndarray, lambda x, o, p: x.shape, lambda x,n,o: n==o],
    ) -> Annotated[np.ndarray, lambda x, m, p: x.shape == (m,p)]:
        return a @ b

    print(get_annotations(spam))
    spam(np.zeros((3, 2)), np.zeros((2, 4)))

