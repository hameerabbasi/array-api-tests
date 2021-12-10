from hypothesis import given
from hypothesis import strategies as st

from array_api_tests.algos import broadcast_shapes
from array_api_tests.test_manipulation_functions import assert_equals as assert_equals_
from array_api_tests.test_statistical_functions import (
    assert_equals,
    assert_keepdimable_shape,
    axes_ndindex,
    normalise_axis,
)
from array_api_tests.typing import DataType

from . import _array_module as xp
from . import array_helpers as ah
from . import dtype_helpers as dh
from . import hypothesis_helpers as hh
from . import pytest_helpers as ph
from . import xps


def assert_default_index(func_name: str, dtype: DataType, repr_name="out.dtype"):
    f_dtype = dh.dtype_to_name[dtype]
    msg = (
        f"{repr_name}={f_dtype}, should be the default index dtype, "
        f"which is either int32 or int64 [{func_name}()]"
    )
    assert dtype in (xp.int32, xp.int64), msg


@given(
    x=xps.arrays(
        dtype=xps.numeric_dtypes(),
        shape=hh.shapes(min_side=1),
        elements={"allow_nan": False},
    ),
    data=st.data(),
)
def test_argmax(x, data):
    kw = data.draw(
        hh.kwargs(
            axis=st.none() | st.integers(-x.ndim, max(x.ndim - 1, 0)),
            keepdims=st.booleans(),
        ),
        label="kw",
    )

    out = xp.argmax(x, **kw)

    assert_default_index("argmax", out.dtype)
    axes = normalise_axis(kw.get("axis", None), x.ndim)
    assert_keepdimable_shape(
        "argmax", out.shape, x.shape, axes, kw.get("keepdims", False), **kw
    )
    scalar_type = dh.get_scalar_type(x.dtype)
    for indices, out_idx in zip(axes_ndindex(x.shape, axes), ah.ndindex(out.shape)):
        max_i = int(out[out_idx])
        elements = []
        for idx in indices:
            s = scalar_type(x[idx])
            elements.append(s)
        expected = max(range(len(elements)), key=elements.__getitem__)
        assert_equals("argmax", int, out_idx, max_i, expected)


@given(
    x=xps.arrays(
        dtype=xps.numeric_dtypes(),
        shape=hh.shapes(min_side=1),
        elements={"allow_nan": False},
    ),
    data=st.data(),
)
def test_argmin(x, data):
    kw = data.draw(
        hh.kwargs(
            axis=st.none() | st.integers(-x.ndim, max(x.ndim - 1, 0)),
            keepdims=st.booleans(),
        ),
        label="kw",
    )

    out = xp.argmin(x, **kw)

    assert_default_index("argmin", out.dtype)
    axes = normalise_axis(kw.get("axis", None), x.ndim)
    assert_keepdimable_shape(
        "argmin", out.shape, x.shape, axes, kw.get("keepdims", False), **kw
    )
    scalar_type = dh.get_scalar_type(x.dtype)
    for indices, out_idx in zip(axes_ndindex(x.shape, axes), ah.ndindex(out.shape)):
        min_i = int(out[out_idx])
        elements = []
        for idx in indices:
            s = scalar_type(x[idx])
            elements.append(s)
        expected = min(range(len(elements)), key=elements.__getitem__)
        assert_equals("argmin", int, out_idx, min_i, expected)


# TODO: skip if opted out
@given(xps.arrays(dtype=xps.scalar_dtypes(), shape=hh.shapes(min_side=1)))
def test_nonzero(x):
    out = xp.nonzero(x)
    if x.ndim == 0:
        assert len(out) == 1, f"{len(out)=}, but should be 1 for 0-dimensional arrays"
    else:
        assert len(out) == x.ndim, f"{len(out)=}, but should be {x.ndim=}"
    size = out[0].size
    for i in range(len(out)):
        assert out[i].ndim == 1, f"out[{i}].ndim={x.ndim}, but should be 1"
        assert (
            out[i].size == size
        ), f"out[{i}].size={x.size}, but should be out[0].size={size}"
        assert_default_index("nonzero", out[i].dtype, repr_name=f"out[{i}].dtype")
    indices = []
    if x.dtype == xp.bool:
        for idx in ah.ndindex(x.shape):
            if x[idx]:
                indices.append(idx)
    else:
        for idx in ah.ndindex(x.shape):
            if x[idx] != 0:
                indices.append(idx)
    if x.ndim == 0:
        assert out[0].size == len(
            indices
        ), f"{out[0].size=}, but should be {len(indices)}"
    else:
        for i in range(size):
            idx = tuple(int(x[i]) for x in out)
            f_idx = f"Extrapolated index (x[{i}] for x in out)={idx}"
            f_element = f"x[{idx}]={x[idx]}"
            assert idx in indices, f"{f_idx} results in {f_element}, a zero element"
            assert (
                idx == indices[i]
            ), f"{f_idx} is in the wrong position, should be {indices.index(idx)}"


@given(
    shapes=hh.mutually_broadcastable_shapes(3),
    dtypes=hh.mutually_promotable_dtypes(),
    data=st.data(),
)
def test_where(shapes, dtypes, data):
    cond = data.draw(xps.arrays(dtype=xp.bool, shape=shapes[0]), label="condition")
    x1 = data.draw(xps.arrays(dtype=dtypes[0], shape=shapes[1]), label="x1")
    x2 = data.draw(xps.arrays(dtype=dtypes[1], shape=shapes[2]), label="x2")

    out = xp.where(cond, x1, x2)

    shape = broadcast_shapes(*shapes)
    ph.assert_shape("where", out.shape, shape)
    # TODO: generate indices without broadcasting arrays
    _cond = xp.broadcast_to(cond, shape)
    _x1 = xp.broadcast_to(x1, shape)
    _x2 = xp.broadcast_to(x2, shape)
    for idx in ah.ndindex(shape):
        if _cond[idx]:
            assert_equals_("where", f"_x1[{idx}]", _x1[idx], f"out[{idx}]", out[idx])
        else:
            assert_equals_("where", f"_x2[{idx}]", _x2[idx], f"out[{idx}]", out[idx])
