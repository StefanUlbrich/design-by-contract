# Welcome to `design-by-contract`

Handy decorator to define contracts with
[dependency injection](https://en.wikipedia.org/wiki/Dependency_injection)
in Python 3.10 and above
without the need of a domain specific language. It helps following the
[design by contract](https://en.wikipedia.org/wiki/Design_by_contract)
paradigm.

Contracts are useful to impose restrictions and constraints on function arguments in a way that

* reduces boilerplate for argument validation in the function body
  (no more if blocks that raise value errors),
* are exposed in the function signature, that is, they serve as a means of documentation
  that is always up-to-date,
* allow relations between arguments.

Possible use cases are asserting mutual columns in
[data frames](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html),
limiting the value range or checking data types in its columns, checking the dimensions
of arrays and tensors, and much more. Note that validation can only occur at runtime!

The first version has been developed in a single afternoon and therefore, this package and more
importantly, this documentation, are still **work in progress**.
You probably shouldn't use it in production yet! But if you do, let me know how it went.

Please leave a star if you like this project!


### Features

* [x] Simple to used design by contract. Does not require you to learn a domain specific language necessary.
  * [x] Uses python language features only. Some of them recently introduced (i.e., in Python 3.10)
  * [x] Preconditions written as lambda functions
  * [x] Scope variables can be defined to simplify definition of conditions
  * [x] [Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) based on argument names
  * [ ] Postconditions (planned)
* [x] Encourages static typing
  * [x] Does not break your type checking & code completion (tested with [mypy](https://mypy.readthedocs.io/en/stable/) and [visual studio code](https://code.visualstudio.com/))
  * [x] Uses annotations for defining conditions
  * [ ] Optional dynamic type checking (planned)
* [x] Preserves your docstrings (thanks to [`decorator`](https://github.com/micheles/decorator)).
      Plays well with [Sphinx](https://www.sphinx-doc.org/en/master/)
  * [ ] Method to insert contracts to docstrings (planned). Probably using Jinja templates.
* [x] Small, clean (opinionated) code base
  * [x] Implementation in a single file with ~100 lines of code!
  * [x] Currently only one runtime dependency!
* [ ] Speed. Well.. maybe it is fast, I haven't tested it yet

## Usage

### Installation

The package is available (or will be shortly) on
[pypi](https://pypi.org/project/design-by-contract/). Install it with

```sh
pip install design-by-contract
```

To build the package from sources, you need [Poetry](https://python-poetry.org/).

Design-by-contract depends only on the [decorator](https://github.com/micheles/decorator)
package at runtime!

### Dependency injection

The decorator in this package uses
[dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) make the definition of
contracts as simple and natural as possible. That means that identifiers used in *conditions* and
must match either argument or *contract variable* names.

### Conditions

Unlike the excellent
[pycontracts](https://github.com/AndreaCensi/contracts) package,
no domain specific language is required. Their definition requires Lambda expressions instead
which arguments are filled by dependency injection.
This way of defining contracts is very powerful and easy to use.

Conditions are defined as lambdas so imagine
a function `spam(a: List[int],b: List[str])`, a condition that enforces the same length of both
arguments looks like:

```python
lambda a, b: len(a) == len(b)
```

Note that the arguments to the lambda have to match the arguments of `spam` in order to be injected.
If they cannot be resolved, then a `ValueError` will be raised.

Conditions are associated with arguments. Therefore, they have to be specified
together with the type annotations. Since Python 3.10, this is supported with
`typing.Annotated`:

```python
@contract
def spam(
    a: List[int],
    b: Annotated[List[str], lambda a, b: len(a) == len(b)]
)
```

**Important:** The argument that is annotated has to appear in the lambda arguments in
order to be recognized as a condition! Also, conditions should return a boolean value.

Currently, it is not possible to define conditions in the decorator itself. The `pre` and
`post` identifiers are reserved for this purpose but are not supported yet.

### Contract variables

To organize contracts and increase readability, contract variables that can be used in the
conditions are supported. In above example, the contract variables `m` could be assigned to
`len(a)` and then be used in the conditions. Contract variables are defined as
keyword arguments to the `contract` decorator:

```python
@contract(
    m=lambda a: len(a),
)
def spam(
    a: Annotated[List[int], lambda a, m: m <= 5], # needs to contain the argument even if unused!
    b: Annotated[List[str], lambda b, m: m == len(b)]
)
```

### Complete working example

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

spam(array1, array2) # or (arguments are resolved correctly)
spam(a=array1,b=array2) # or
spam(b=array2,a=array1) # but not
spam(a=array2,b=array1) # raises ValueError
```

Here, the decorator is initialized with a contract variable definition of `m` . It holds the number
of rows of the array `a`, the first argument of `spam`.
This is achieved by passing a `m` as a keyword argument with a lambda expression that takes a single
argument named `a`. The lambda's argument(s) have to match argument names of `spam`. The contract decorator
will then inject the value of the argument `a` into the lambda expression when `spam` is eventually evaluated.

The arguments of `spam` can be annotated by using `typing.Annotated` if there is a condition for them.
`Annotated` first requires a type definition. Any following lambda expression that contains the
same argument name (in this case, `b`) is interpreted as a contract. The lambdas should return a boolean value!
Note that there can be multiple conditions in the same annotation.

All the expressions arguments must have the same name as either an argument of `spam`
or a contract variable (i.e., `a`,`b` or `m`). Again, the respective values are injected by the decorator when the function is evaluated.

## What's missing?

Currently, contracts for return types (i.e., post conditions) cannot be specified.
The identifier `post` is reserved already but using it throws a `NotImplementedError` for now.
Implementation, however, is straight forward
(I am accepting pull requests). Documentation can certainly be improved.

In the future, optional run-time type checking might be worth considering.

## Why?

I had the idea a while ago when reading about `typing.Annotated` in the release notes of Python 3.9.
Eventually, it turned out to be a nice, small Saturday afternoon project and a welcomed
opportunity to experiment with novel features in Python 3.10.
In addition, it has been a good exercise to practice several aspects of modern Python development and eventually
might serve as an example for new Python developers:

* [x] Recent python features: [`typing.Annotation`](https://docs.python.org/3/library/typing.html#typing.Annotated) (3.9),
  [`typing.ParamSpec`](https://docs.python.org/3/library/typing.html#typing.ParamSpec) (3.10)
  and [`typing.get_annotations()`](get_annotations)  (3.10)
* [x] Clean decorator design with the [decorator](https://github.com/micheles/decorator) package
* [x] Project management with [Poetry](https://python-poetry.org/)
* [x] Clean code (opinionated), commented code, type annotations and unit tests ([pytest](https://docs.pytest.org/en/6.2.x/)). Open for criticism.
* [x] Leveraging logging facilities
* [x] Sensible exceptions
* [x] Good documentation (ok, only half a check)
* [ ] GitHub Actions
* [ ] Sphinx documentation

If you think it's cool, please leave a star. And who knows, it might actually be useful.

## Related (active) projects.

It appears that the related (still active) projects have significantly larger code bases
(include parsers for a domain-specific language, automated testing, etc.) but also try to achieve
additional and wider goals (automated testing, pure functions, etc.). The main strength
of this project, in my opinion, lies in its compact codebase and intuitiveness of the
dependency injection.

* [PyContracts](https://github.com/AndreaCensi/contracts).
  Originally inspired this project. Although it requires a domain specific language, it supports implicitly defining variables for array shapes (see below). This package tries to achieve
  a similar goal in pure Python but it requires a formal definition of variables.

  ```ptyhon
  @contract
  @contract(a='list[ M ](type(x))',
            b='list[ N ](type(x))',
            returns='list[M+N](type(x))')
  def my_cat_equal(a, b):
      ''' Concatenate two lists together. '''
      return a + b
  ```

* [icontract](https://github.com/Parquery/icontract) and [deal](https://github.com/life4/deal):
  Rely on conditions defined as lambdas much like this Project. However, their codebase is less
  lean and the lack of variable definitions make it appear less intuitive to use.

## Contributions

Pull requests are welcome!

## Changelog

* v0.2 (TBP): add Postconditions
* v0.1.1 (2022-01-30): Better documentation
* v0.1.0 (2022-01-29): Initial release

## License

MIT License, Copyright 2022 Stefan Ulbrich


