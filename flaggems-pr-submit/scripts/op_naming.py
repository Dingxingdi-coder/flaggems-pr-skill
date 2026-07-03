"""Operator naming helpers shared by PR submission scripts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OperatorNames:
    """Names used by different FlagGems surfaces for one operator."""

    op: str
    module: str
    op_id: str
    config_entries: tuple = ()
    yaml_for: tuple = ()
    yaml_description: str = ""
    strip_test_marks: tuple = ()


SPECIAL_OPS = {
    "max_pool2d_with_indices_backward": OperatorNames(
        op="max_pool2d_with_indices_backward",
        module="max_pool2d_with_indices",
        op_id="max_pool2d_with_indices_backward",
        config_entries=(
            (
                "max_pool2d_with_indices_backward",
                "max_pool2d_with_indices_backward",
            ),
        ),
        yaml_for=("max_pool2d_with_indices_backward",),
        yaml_description="The backward version of `max_pool2d_with_indices()`.",
    ),
    "matmul_layer_norm": OperatorNames(
        op="matmul_layer_norm",
        module="Matmul_Layer_Norm",
        op_id="matmul_layernorm",
        config_entries=(("matmul_layernorm", "matmul_layernorm"),),
        yaml_for=("matmul_layernorm",),
        yaml_description="Fused matmul and layer normalization operation.",
    ),
    "__and__": OperatorNames(
        op="__and__",
        module="_and_",
        op_id="and_op",
        config_entries=(
            ("__and__.Scalar", "__and___scalar"),
            ("__and__.Tensor", "__and__"),
        ),
        yaml_for=("__and__.Scalar", "__and__.Tensor"),
        yaml_description="Computes the bitwise AND operation through the tensor dunder method.",
        strip_test_marks=("inplace",),
    ),
}


def resolve_op(op_name):
    """Return the module filename stem and public test/benchmark id for op_name."""
    if op_name in SPECIAL_OPS:
        return SPECIAL_OPS[op_name]
    return OperatorNames(op=op_name, module=op_name, op_id=op_name.lstrip("_"))


def is_special_op(op_name):
    return op_name in SPECIAL_OPS
