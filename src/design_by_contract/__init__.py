import logging
from dataclasses import dataclass
from functools import partial, wraps
from inspect import get_annotations, getfullargspec, getsource, signature
from pickle import TRUE
from typing import Any, Callable, Dict, Optional, ParamSpec, TypeVar, Union, overload

try:
    import ast
    from textwrap import dedent

    import asttokens
    from jinja2 import Template, Environment

    __HAS_JINJA2__ = True
    # print(__HAS_JINJA2__)
except ImportError:
    __HAS_JINJA2__ = False
    # print(__HAS_JINJA2__)

    # Todo does: `Environment` = Any work?
    class Environment:  # type: ignore
        """Placeholer class if jinja is not found"""


logger = logging.getLogger(__name__)

logger.info("Using templates: %s", __HAS_JINJA2__)


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


def get_predicate_src(func: Callable[P, R], jinja: Optional[Environment]) -> Dict[str, list[str]]:
    """Extract the source code of the predicates."""
    if not __HAS_JINJA2__:
        return {}

    src = dedent(getsource(func))
    atok = asttokens.ASTTokens(src, parse=True)

    func_def = atok.tree.body[0]

    if not isinstance(func_def, ast.FunctionDef):
        raise TypeError("Not a function")

    sources = {
        i.arg: [
            src[j.first_token.startpos : j.last_token.endpos]  #  type: ignore
            for j in i.annotation.slice.elts  #  type: ignore
            if isinstance(j, ast.Lambda)
        ]
        for i in func_def.args.args
        if isinstance(i.annotation, ast.Subscript) and i.annotation.value.id == "Annotated"  #  type: ignore
    }

    if func_def.returns:
        if isinstance(func_def.returns, ast.Subscript) and (func_def.returns.value.id == "Annotated"):  #  type: ignore
            sources["return"] = [
                src[i.first_token.startpos : i.last_token.endpos]  #  type: ignore
                for i in func_def.returns.slice.elts  #  type: ignore
                if isinstance(i, ast.Lambda)
            ]
    else:
        sources["return"] = []
    # FIXME missing returns

    # print(jinja, func.__doc__)
    if jinja is not None and func.__doc__ is not None:
        print(sources)
        func.__doc__ = jinja.from_string(func.__doc__).render(sources | {"contract": sources})

    return sources


@overload
def contract(func: Callable[P, R]) -> Callable[P, R]:
    ...


@overload
def contract(
    *, reserved: str = "x", evaluate: bool = True, jinja: Optional[Environment] = None  # , inject: bool = False
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    ...


def contract(
    func: Optional[Callable[P, R]] = None,
    *,
    reserved: str = "x",
    evaluate: bool = True,  # inject: bool = False,
    jinja: Optional[Environment] = None,
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

    if func is not None:
        if not callable(func):
            raise TypeError("Not a callable. Did you use a non-keyword argument?")
        return wraps(func)(partial(wrapper, func))

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        get_predicate_src(func, jinja)
        return wraps(func)(partial(wrapper, func))

    return decorator


if __name__ == "__main__":
    # Example
    from numpy.typing import NDArray
    import numpy as np
    from typing import Annotated
    from jinja2 import Environment

    logging.basicConfig(format="%(name)s %(levelname)s [%(funcName)s:%(lineno)d] %(message)s")
    logger.setLevel(logging.DEBUG)

    env = Environment()

    @contract(jinja=env)
    def spam(
        a: Annotated[NDArray[np.floating[Any]], lambda a, m, n: (m, n) == a.shape],
        b: Annotated[NDArray[np.floating[Any]], lambda b, n, o: (n, o) == b.shape, lambda b, n, o: (n, o) == b.shape],
    ) -> Annotated[NDArray[np.floating[Any]], lambda x, m, o: x.shape == (m, o)]:
        """
        Test function

        Parameters
        ----------

        a
            {% for i in a %}
            :code:`{{ i }}`{% endfor %}

        b
            {% for i in b %}
            :code:`{{ i }}`{% endfor %}

        """
        return a @ b

    logger.debug("Docstring: %s\n%s", spam.__doc__, str(signature(spam)))
    # spam(np.zeros((3, 2)), np.zeros((2, 4)))
