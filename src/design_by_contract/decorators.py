import logging
from inspect import get_annotations, getfullargspec
from typing import Annotated, Callable, Any, TypeVar, ParamSpec
from decorator import decorator

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


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
        for arg_name, annotation in annotations.items():

            # Filter for typing.Annotation objects with extra annotations
            if hasattr(annotation, "__metadata__"):
                for meta in annotation.__metadata__:
                    # Only consider lambdas/callables
                    if isinstance(meta, Callable):  # type: ignore
                        meta_args = getfullargspec(meta).args
                        # Only if the original argument's name is among its argument names
                        if arg_name in meta_args or reserved in meta_args:
                            # the reserved identifier is a shortcut
                            injectables[reserved] = injectables[arg_name]
                            dependencies = set(injectables.keys()).intersection(meta_args)
                            logger.debug(
                                "contract for `%s`, dependencies: `%s`",
                                arg_name,
                                {i: injectables[i] for i in dependencies},
                            )

                            # Look for arguments that cannot be injected
                            unresolved = set(meta_args) - set(injectables.keys())
                            if len(unresolved) > 0:
                                raise ValueError(f"Cannot inject `{unresolved}` for argument `{arg_name}`")
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
        a: np.ndarray, b: Annotated[np.ndarray, lambda a, b: a.shape[1] == b.shape[0]]
    ) -> Annotated[np.ndarray, lambda x, a: x.shape[0] == a.shape[0], lambda x, b: x.shape[1] == b.shape[1]]:
        return a @ b

    print(get_annotations(spam))
    spam(np.zeros((3, 2)), np.zeros((2, 4)))

    # Correctly creates mypy error:
    # spam("asdf", 4)


# def contract(
#     pre: Optional[Sequence[Callable[..., bool]]] = None,
#     post: Optional[Callable[..., bool]] = None,
#     **variables,
# ) -> Callable[[Callable[P, R]], Callable[P, R]]:
#     """Factory that generates the decorator (necessary for decorator keywords args)"""

#     def caller(func: Callable[P, R], *args, **kw) -> R:
#         return _contract(func, variables, pre, post, *args, **kw)

#     return decorator(caller)
