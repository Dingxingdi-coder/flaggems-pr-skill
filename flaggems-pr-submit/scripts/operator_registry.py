#!/usr/bin/env python3
"""FlagGems operator norm-name lookup.

No local path is assumed. Provide --norm-xlsx, or set FLAGGEMS_NORM_XLSX.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Iterable

import openpyxl


@dataclass(frozen=True)
class Columns:
    name: int
    norm: int


def clean(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", "").replace("_x000d_", "").strip()


def clean_op(name) -> str:
    return clean(name).replace("aten::", "", 1).strip()


def require_norm_xlsx(path: str | None) -> str:
    path = path or os.environ.get("FLAGGEMS_NORM_XLSX")
    if not path:
        raise SystemExit("missing --norm-xlsx or FLAGGEMS_NORM_XLSX")
    if not os.path.isfile(path):
        raise SystemExit(f"file not found: {path}")
    return path


def find_columns(ws) -> Columns:
    headers = [clean(cell.value) for cell in ws[1]]
    try:
        name_col = headers.index("算子名") + 1
    except ValueError:
        raise SystemExit("missing column: 算子名")
    norm_col = None
    for i, header in enumerate(headers, start=1):
        if header == "算子名（规范命名）" or "规范命名" in header:
            norm_col = i
            break
    if norm_col is None:
        raise SystemExit("missing column: 算子名（规范命名）")
    return Columns(name=name_col, norm=norm_col)


def iter_operator_rows(ws, cols: Columns) -> Iterable[tuple[str, str]]:
    for row in ws.iter_rows(min_row=2):
        yield clean_op(row[cols.name - 1].value), clean(row[cols.norm - 1].value)


def lookup_norm_name(op_name: str, xlsx_path: str | None = None) -> str:
    xlsx_path = require_norm_xlsx(xlsx_path)
    op_name = clean_op(op_name)
    if not op_name:
        raise SystemExit("operator name is empty")
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    cols = find_columns(ws)
    for name, norm in iter_operator_rows(ws, cols):
        if name == op_name or norm == op_name:
            if not norm:
                raise SystemExit(f"empty norm name for operator: {op_name}")
            return norm
    raise SystemExit(f"operator not found: {op_name}")


def _pop_option(argv: list[str], option: str) -> tuple[str | None, list[str]]:
    argv = list(argv)
    if option not in argv:
        return None, argv
    idx = argv.index(option)
    try:
        value = argv[idx + 1]
    except IndexError:
        raise SystemExit(f"{option} requires a value")
    del argv[idx:idx + 2]
    return value, argv


def usage() -> str:
    return (
        "usage:\n"
        "  operator_registry.py lookup <op> --norm-xlsx PATH\n"
        "  operator_registry.py <op> --norm-xlsx PATH\n"
        "FLAGGEMS_NORM_XLSX may replace --norm-xlsx."
    )


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print(usage())
        return
    norm_xlsx, argv = _pop_option(argv, "--norm-xlsx")
    if not argv:
        raise SystemExit(usage())
    if argv[0] == "lookup":
        if len(argv) != 2:
            raise SystemExit(usage())
        print(lookup_norm_name(argv[1], norm_xlsx))
        return
    if len(argv) == 1:
        print(lookup_norm_name(argv[0], norm_xlsx))
        return
    raise SystemExit(usage())


if __name__ == "__main__":
    main()
