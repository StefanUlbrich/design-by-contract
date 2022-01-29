import logging
from inspect import get_annotations, getfullargspec
from typing import Annotated, Callable, Dict, TypeVar, ParamSpec

import numpy as np
from decorator import decorator

logger = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar('R')


def _contract(func: Callable[P, R], definitions: Dict[str, Callable[..., bool]]=None, *args, **kw) -> R:

    annotations = get_annotations(func)

    argv = {k: v for k, v in zip(annotations.keys(), args)}


    injectables = {}

    if definitions is not None:
        for var, anonym in definitions.items():
            if not isinstance(anonym, Callable):
                raise ValueError(f"Expected callable for dependency `{var}`")
            anonmy_args = getfullargspec(anonym).args
            unknown = set(anonmy_args) - set(annotations.keys())
            if unknown:
                raise ValueError(f"Unkown argument names `{unknown}`")

            # inject arguments
            injectables[var] = anonym(*[argv[i] for i in anonmy_args])


    injectables |= argv

    logger.debug("injectables: %s", injectables)

    for arg_name, annotation in annotations.items():
        if hasattr(annotation, "__metadata__"):
            for meta in annotation.__metadata__:
                if isinstance(meta, Callable):
                    meta_args = getfullargspec(meta).args
                    if arg_name in meta_args:
                        dependencies = set(injectables.keys()).intersection(meta_args)
                        logger.debug(
                            "contract for `%s`, dependencies: `%s`",
                            arg_name,
                            {i: injectables[i] for i in dependencies},
                        )

                        unknown = set(meta_args) - set(injectables.keys())
                        if len(unknown) > 0:
                            raise ValueError(
                                f"Cannot inject `{unknown}` for argument `{arg_name}`"
                            )
                        if not meta(*[injectables[i] for i in meta_args]):
                            raise ValueError(
                                f"Contract violated for argument: `{arg_name}`"
                            )
                        logger.debug("contract fullfilled for argument `%s`", arg_name)

    result = func(*args, **kw)
    return result


def contract(**definitions) -> Callable[[Callable[P, R]],Callable[P, R]]:

    def caller(f: Callable[P, R], *args, **kw) -> R:
        return _contract(f, definitions, *args, **kw)

    return decorator(caller)

if __name__=="__main__":

    import numpy as np

    logging.basicConfig(format=' %(asctime)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.DEBUG)

    @contract(m=lambda a: a.shape[0])
    def spam(a: np.ndarray, b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]) -> bool:
        return True

    spam(np.array([[4, 5, 6, 8]]), np.array([[1, 2, 3]]))

    spam("asdf", 4)


