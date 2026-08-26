#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_blue_scc_fisheries_benchmark.py"
SPEC = importlib.util.spec_from_file_location("blue_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_minimal_xlsx(path: Path) -> None:
    workbook = '''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Upper panel" sheetId="1" r:id="rId1"/></sheets></workbook>'''
    rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/></Relationships>'''
    rows = [
        ["t", "scc", "oc_capital", "valuation"],
        [2020, 48.281363, "Total", "Total"],
        [2020, 0.057040, "Fisheries", "Market value"],
        [2020, 22.040509, "Fisheries", "Non-market use value"],
    ]
    xml_rows = []
    for row_number, row in enumerate(rows, 1):
        cells = []
        for column, value in enumerate(row):
            reference = f"{chr(65 + column)}{row_number}"
            if isinstance(value, str):
                cells.append(f'<c r="{reference}" t="inlineStr"><is><t>{value}</t></is></c>')
            else:
                cells.append(f'<c r="{reference}"><v>{value}</v></c>')
        xml_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    sheet = f'''<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(xml_rows)}</sheetData></worksheet>'''
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        xlsx = root / "figure.xlsx"
        write_minimal_xlsx(xlsx)
        rows = MODULE.xlsx_sheet_rows(xlsx, "Upper panel")
        assert rows[0] == ["t", "scc", "oc_capital", "valuation"]
        summary = MODULE.figure_summary(xlsx, "Upper panel", 2020)
        assert math.isclose(summary["fisheries_total_scc_usd_per_tco2"], 22.097549)
        assert math.isclose(
            summary["fisheries_share_of_total_blue_scc"],
            22.097549 / 48.281363,
        )

        coefficients = root / "coefficients.csv"
        coefficients.write_text(
            "country_iso3,GDP_FractionChange_perC\nAAA,-0.2\nBBB,0.1\nCCC,0\n",
            encoding="utf-8",
        )
        audit = MODULE.coefficient_summary(coefficients)
        assert audit["rows"] == 3
        assert audit["negative_coefficients"] == 1
        assert audit["positive_coefficients"] == 1
        assert audit["zero_coefficients"] == 1

        coefficients.write_text(
            "country_iso3,GDP_FractionChange_perC\nAAA,-0.2\nAAA,0.1\n",
            encoding="utf-8",
        )
        try:
            MODULE.coefficient_summary(coefficients)
        except ValueError as error:
            assert "duplicated" in str(error)
        else:
            raise AssertionError("duplicate countries must fail closed")

    print("Blue-SCC fisheries benchmark audit tests passed")


if __name__ == "__main__":
    main()
