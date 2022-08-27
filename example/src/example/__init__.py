"""A module with examples for design by contract."""

from typing import Annotated, Any

import numpy as np
from jinja2 import Environment, PackageLoader
from numpy.typing import NDArray

from design_by_contract import contract

ENV = Environment(loader=PackageLoader("example"))


@contract(jinja=ENV)
def spam(
    first: Annotated[NDArray[np.floating[Any]], lambda x, m, o: (m, o) == x.shape],
    second: Annotated[NDArray[np.floating[Any]], lambda x, n, o: (n, o) == x.shape],
) -> Annotated[NDArray[np.floating[Any]], lambda x, m, n, o: x.shape == (m + n, o)]:
    """Stack two arrays

    **Contracts**
    {% import 'dbc.j2' as dbc %}{{ dbc.document(contract) | indent }}

    Parameters
    ----------
    first: NDarray
        The first array.

        {% for i in first %}:code:`{{ i }}`
        {% endfor %}
    second: NDarray
        The second array.

        {% for i in second %}:code:`{{ i }}`
        {% endfor %}

    Returns
    -------
    NdArray
        The stacked arrays.
    """
    return np.vstack((first, second))


