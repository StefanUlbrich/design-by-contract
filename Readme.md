# Welcome to `design-by-contract`

Handy decorator to define contracts with
[dependency injection](https://en.wikipedia.org/wiki/Dependency_injection)
in Python 3.10 and above
without the need of a domain specific language. It helps following the
[design by contract](https://en.wikipedia.org/wiki/Design_by_contract)
paradigm.

This package and more importantly, this documentation, are still **work in progress**.
Don't use it in production yet!

## Usage

The decorator in this package uses
[dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) make the definition of
contracts as simple and natural as possible. Unlike the excellent
[pycontracts](https://github.com/AndreaCensi/contracts) package,
no domain specific language is required. Their definition requires Lambda expressions
which argument names match either the decorated function's arguments or injectable variables.
This way of defining contracts is very powerful and easy to use.

### Installation

The package is available (or will be shortly) on
[pypi](https://pypi.org/project/design-by-contract/). Install it with

```sh
pip install design-by-contract
```

To build the package from sources, you need [Poetry](https://python-poetry.org/).

Design-by-contract depends only on the [decorator](https://github.com/micheles/decorator)
package at runtime!

### Quick example

Consider a function that accepts two
[numpy arrays](https://numpy.org/doc/stable/reference/generated/numpy.array.html) as
parameters but requires that both
have exactly the same numbers of rows. With this package, this can be achieved by the following
code.


```python
from typing import Annotated
from design_by_contract import contract

@contract(m=lambda a: a.shape[0])
def spam(
    a: np.ndarray,
    b: Annotated[np.ndarray, lambda b, m: b.shape == (m, 3)]
) -> None: pass

array1 = np.array([[4, 5, 6, 8]])
array2 = np.array([[1, 2, 3]])

spam(array1, array2) # or
spam(a=array1,b=array2) # or
spam(b=array2,a=array1)
```

The decorator is initialized with a variable `m` that is defined to hold the number of rows of `a`, the first
argument of `spam`. This is achieved by passing a `m` as a keyword with a lambda expression that takes a single
argument `a`. The lambda's argument(s) have to match argument names of `spam`. The contract will then pass
the value of the argument to the lambda expression when `spam` is eventually evaluated.

The arguments of `spam` can be annotated by using `typing.Annotated`. `Annotated` first accepts the type of
the argument and any following lambda expression that contains the same argument name (in this case, `b`) will
be interpreted as a contract. It must return a boolean value!
All the expressions arguments must have the same name as either an argument of `spam`
or a variable defined in the decorator initialization (i.e., `a`,`b` or `m`). Again, the respective values
are injected by the decorator when the function is evaluated.

### Features

* Full type checking support ([mypy](https://mypy.readthedocs.io/en/stable/) and [visual studio code](https://code.visualstudio.com/))
* No domain specific language necessary
* Contracts are written as Lambda functions
* [Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) is used to make arguments and variables available in the contracts.
* Implementation in a single file with less than 100 lines!
* Only one runtime dependency!
* Leveraging logging facilities


### What's missing

Currently, contracts for return types (i.e., post conditions) cannot be specified.
The dependency `returns` is reserved already
but using it throws a `NotImplementedError` for now. Implementation, however, is straight forward
(I am accepting pull requests). Documentation can certainly be improved.

In the future, run-time type checking can be easily integrated.

## Why?

I had the idea a while ago when reading the release notes of Python 3.9. It turned out to be a
nice, small Saturday afternoon project and a good opportunity to experiment with features in Python 3.10.
In addition, it has been a good exercise for several aspects of modern Python development and might
serve as an example for new Python developers:

* Recent python features: [`typing.Annotation`](https://docs.python.org/3/library/typing.html#typing.Annotated) (3.9),
  [`typing.ParamSpec`](https://docs.python.org/3/library/typing.html#typing.ParamSpec) (3.10)
  and [`typing.get_annotations()`](get_annotations)  (3.10)
* Clean decorator design with the [decorator](https://github.com/micheles/decorator) package
* Project management with [Poetry](https://python-poetry.org/)
* GitHub Actions (TBD)
* Clean code (opinionated), type annotations and unit tests ([pytest](https://docs.pytest.org/en/6.2.x/))

If you think it's cool, please leave a star. And who knows, it might actually be useful.

## Contributions

Pull requests are welcome!
## License

MIT License, Copyright 2022 Stefan Ulbrich


