# Welcome to `design-by-contract`

A minimalistic decorator for the [design by contract pattern](https://en.wikipedia.org/wiki/Design_by_contract)
written in a just little more than 100 lines of modern Python 3.10 code (not counting documentation and logging).

Contracts are useful to impose restrictions and constraints on function arguments in a way that

* reduces boilerplate for argument validation in the function body
  (no more if blocks that raise value errors),
* are exposed in the function signature, that is, they serve as a means of documentation
  that is always up-to-date,
* allow relations between arguments.

Install with

```sh
pip install design-by-contract
```

**Warning**

This project started as a weekend project to learn recent additions to the language (`typing.Annotated` and `typing.ParamSpec`, the [walrus operator](https://www.python.org/dev/peps/pep-0572/), [pattern matching](https://www.python.org/dev/peps/pep-0636/) and others). This means also that this package and its documentation should be considered as **work in progress**.
You probably shouldn't use it in production yet! But if you do, let me know how it went. Please leave a star if you like this project!

## Application

The decorator has been mainly designed with [numpy arrays](https://numpy.org) and [pandas DataFrames](https://pandas.pydata.org/)
in mind but can be universally applied.
Contracts are defined as lambda functions that are attached to the function arguments via the
[new Annotated type](https://www.python.org/dev/peps/pep-0593/) that allows adding additional information
to the arguments' and return value's type hint. Arguments are inserted into the lambda via
[dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) and working with
symbols to increase readability is supported.

Let's look at an example for for matrix multiplication!

```python
from typing import Annotated
import numpy as np
from design_by_contract import contract

@contract
def spam(
    first: Annotated[np.ndarray, lambda first, m, n: (m, n) == first.shape], # symbols m and n represent the shape of `a`
    second: Annotated[np.ndarray, lambda second, n, o: (n, o) == second.shape], # `b` number of columns matches the number of rows of `a`
) -> Annotated[np.ndarray, lambda x, m, o: x.shape == (m, o)]: # `x` holds the return value. The shape of `x` must equal `x` times `o`
    """Matrix multiplication"""
    return a @ b
```

Contracts are lamdbas with one argument named like the annotated argument. Alternatively, `x` can be used as a shortcut which means
that you cannot use `x` as a function argument unless you choose another reserved (using the `reserved` argument `contractor` decorator).

```python
@contract(reserved='y')
def spam(
    first: Annotated[np.ndarray, lambda y, m, n: (m, n) == y.shape],
    second: Annotated[np.ndarray, lambda y, n, o: (n, o) == y.shape],
) -> Annotated[np.ndarray, lambda y, m, o: y.shape == (m, o)]:
    """Matrix multiplication"""
    return a @ b
```

Symbolic  calculus is supported to certain degree to make your life easier. The symbols `m`, `n` and `o` are defined in a way
that

$$ \text spam: R^{m \times x} \times R^{n\times o} \rightarrow R^{m\times o} $$

Note however, that this package does **not** intend to be a symbolic calculus package and therefore, there are some strong limitations.

Python does not allow for assignments (`=`) in a lambda expression and therefore,
the equality operator (`==`) is chosen to act a replacement. Unknown arguments are replaced under the hood by an instance of `UnresolvedSymbol`
that overload this operator. As a consequence, each symbol, therefore has to be first appear in an equality before it can be used *in a different* lambda expression!

The following example will raise an error for instance:

```Python
@contract
def spam(
    a: Annotated[np.ndarray, lambda x, m, n: (m, n) == x.shape and m > 2], # you cannot "assign" and use `m` in the same lambda
    #  Annotated[np.ndarray, lambda x, m, n: (m, n) == x.shape, lambda x, m:  m > 2] # this would work
    b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
) -> Annotated[np.ndarray, lambda x, m, o: x.shape == (m, o)]:
    return a @ b

spam(a, b) # raises: '>' not supported between instances of 'UnresolvedSymbol' and 'int'
```

This design decision is arguably unclean but allows for elegant contract expressions and a very clean and compact implementation.
Different approaches involving symbolic algebra packages like [sympy](https://www.sympy.org/en/index.html) or parsing a syntax trees were considered but turned out
to be too complex to implement. The next best alternative is using a domain-specific language (DLS) as done in  the excellent
[pycontracts](https://github.com/AndreaCensi/contracts) package, which
actually inspired this project. By using python, calculus in the contract can be arbitrarily
complex without the need for extending the DSL (i.e., including python functions):

```python
@contract
def spam(
    a: Annotated[np.ndarray, lambda x, m, o: (m, o) == x.shape],
    b: Annotated[np.ndarray, lambda x, n, o: (n, o) == x.shape],
) -> Annotated[np.ndarray, lambda x, m,n,o: x.shape == (m+n, o)]:
    print(np.vstack((a,b)).shape)
    return np.vstack((a,b))
spam(np.zeros((3, 2)), np.zeros(( 4, 2)))
```

The decorator is also quite handy for being used with pandas data frames:

```python
@contract
def spam(a: Annotated[pd.DataFrame,
                      lambda x, c: c == {'C','B'}, # `x` or the argument name must be passed to the lambda
                      lambda x, c: c.issubset(x.columns) # Remember, we need to use two lambdas here!
                     ],
         b: Annotated[pd.DataFrame,
                      lambda x, c: c <= set(x.columns) # equivalent to `issubset` but more elegant
                     ]
        ) -> Annotated[pd.DataFrame,
                       lambda x, c: c <= set(x.columns)]:
    """Matrix multiplication"""
    return pd.merge(a,b,on=['B','C'])

spam(a, b)
```

Note that evaluation is not optimized. In production, you might consider disabling evaluation by passing
`evaluate=False` as a parameter to the `contract` decorator.

## Features

* [x] Simple to used design by contract. Does not require you to learn a domain specific language necessary.
  * [x] Uses python language features only. Some of them recently introduced (i.e., in Python 3.10)
  * [x] Preconditions written as lambda functions
  * [x] Additional symbols can be used to achieve compact contracts
  * [x] [Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) based on argument names
  * [x] Pre- and Postconditions
* [x] Encourages static typing
  * [x] Does not break your type checking & code completion (tested with [mypy](https://mypy.readthedocs.io/en/stable/) and [visual studio code](https://code.visualstudio.com/))
  * [x] Uses annotations for defining conditions
  * [ ] Optional dynamic type checking
* [x] Preserves your docstrings (thanks to [`decorator`](https://github.com/micheles/decorator)).
      Plays well with [Sphinx](https://www.sphinx-doc.org/en/master/)
* [x] Small, clean (opinionated) code base
  * [x] Implementation in a single file with ~100 lines of code!
  * [x] Currently only one runtime dependency!
  * [x] Documentation using [sphinx](https://www.sphinx-doc.org/en/master/), [myst](https://myst-parser.readthedocs.io/en/latest/index.html) and [sphinx book](https://sphinx-book-theme.readthedocs.io/en/stable/)
  * [x] Tested with pytest
  * [x] Type annotations
  * [x] code formatted ([black](https://github.com/psf/black)), linted ([pylint](https://pylint.org/)). Linting with [mypy](http://www.mypy-lang.org/) does not support pattern matching yet.
* [ ] Speed. Well.. maybe. I haven't tested it yet.

## Why?

I had the idea a while ago when reading about `typing.Annotated` in the release notes of Python 3.9.
Eventually, it turned out to be a nice, small Weekend project and a welcomed
opportunity to experiment with novel features in Python 3.10.
In addition, it has been a good exercise to practice several aspects of modern and clean Python development and eventually
might serve as an example for new Python developers:

If you think it's cool, please leave a star. And who knows, it might actually be useful.

## Related (active) projects

It appears that the related (still active) projects have significantly larger code bases
(include parsers for a domain-specific language, automated testing, etc.) but also try to achieve
additional and wider goals (automated testing, pure functions, etc.). The main strength
of this project, in my opinion, lies in its compact codebase and intuitiveness of the
dependency injection.

* [PyContracts](https://github.com/AndreaCensi/contracts).
  Originally inspired this project. Although it requires a domain specific language, it supports implicitly defining variables for array shapes (see below). This package tries to achieve
  a similar goal in pure Python but it requires a formal definition of variables.

  ```python
  @contract
  @contract(a='list[ M ](type(x))',
            b='list[ N ](type(x))',
            returns='list[M+N](type(x))')
  def my_cat_equal(a, b):
      ''' Concatenate two lists together. '''
      return a + b
  ```

* [icontract](https://github.com/Parquery/icontract) and [deal](https://github.com/life4/deal):
  Rely on conditions defined as lambdas much like this Project. They don't use the `Annotated` syntax
  and their codebases are significantly larger.

## Contributions

Pull requests are welcome!

## Changelog

* v0.2 (2022-03-05): Simple symbolic support
* v0.1.1 (2022-01-30): Better documentation
* v0.1.0 (2022-01-29): Initial release

## License

MIT License, Copyright 2022 Stefan Ulbrich
