#!/usr/bin/env python3
import argparse
import os
import sys

import openpyxl


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\r", "").replace("_x000d_", "").strip()


def clean_op(name):
    return clean(name).replace("aten::", "", 1)


def find_columns(ws):
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

    return name_col, norm_col


def lookup_norm_name(op_name, xlsx_path):
    op_name = clean_op(op_name)

    if not op_name:
        raise SystemExit("operator name is empty")

    if not os.path.isfile(xlsx_path):
        raise SystemExit(f"file not found: {xlsx_path}")

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active

    name_col, norm_col = find_columns(ws)

    for row in ws.iter_rows(min_row=2):
        name = clean_op(row[name_col - 1].value)
        if name == op_name:
            norm_name = clean(row[norm_col - 1].value)
            if not norm_name:
                raise SystemExit(f"empty norm name for operator: {op_name}")
            return norm_name

    raise SystemExit(f"operator not found: {op_name}")


def main():
    parser = argparse.ArgumentParser(description="Query FlagGems operator norm name")
    parser.add_argument("operator", required=True, help="operator name, with or without aten:: prefix")
    parser.add_argument("--norm-xlsx", required=True, help="path to 规范名.xlsx")
    args = parser.parse_args()

    print(lookup_norm_name(args.operator, args.norm_xlsx))


if __name__ == "__main__":
    main()