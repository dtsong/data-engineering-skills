## Contents

- [Primary: Excel Extension (DuckDB >=1.2)](#primary-excel-extension-duckdb-12)
- [Sheet Selection](#sheet-selection)
- [Header Row Handling](#header-row-handling)
- [Date Serial Number Conversion](#date-serial-number-conversion)
- [Multi-Sheet Workbooks](#multi-sheet-workbooks)
- [Legacy: Spatial Extension Fallback](#legacy-spatial-extension-fallback)
- [Python-Based Alternative](#python-based-alternative)
- [Limitations and Workarounds](#limitations-and-workarounds)

---

# Excel Specifics

> **Part of:** [duckdb](../SKILL.md)

## Primary: Excel Extension (DuckDB >=1.2)

DuckDB 1.2+ provides native Excel reading via the `excel` extension. This is the recommended approach.

```sql
INSTALL excel;
LOAD excel;

-- Read the first sheet (default)
SELECT * FROM read_xlsx('data.xlsx');

-- Read a specific sheet
SELECT * FROM read_xlsx('data.xlsx', sheet='Revenue');
```

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `sheet` | Sheet name to read | First sheet |
| `header` | Whether first row is header | `true` |
| `skip` | Number of rows to skip before reading | `0` |
| `all_varchar` | Read all columns as VARCHAR | `false` |

## Sheet Selection

```sql
-- By sheet name
SELECT * FROM read_xlsx('workbook.xlsx', sheet='Revenue');

-- Read all data from default (first) sheet
SELECT * FROM read_xlsx('workbook.xlsx');
```

To discover sheet names, use the spatial extension's `st_layers()` or read with Python openpyxl.

## Header Row Handling

```sql
-- Skip title rows above the actual header
SELECT * FROM read_xlsx('report.xlsx', skip=2);

-- Read without headers (columns named column0, column1, ...)
SELECT * FROM read_xlsx('report.xlsx', header=false);

-- All columns as VARCHAR for manual type casting
SELECT * FROM read_xlsx('report.xlsx', all_varchar=true);
```

## Date Serial Number Conversion

Excel stores dates as serial numbers (days since 1899-12-30). The excel extension handles most date columns automatically. If dates load as integers:

```sql
-- Convert Excel serial number to date
SELECT
    date '1899-12-30' + INTERVAL (excel_date_col) DAY AS actual_date
FROM raw_excel;
```

### Datetime Serial Numbers

When the serial number includes a decimal (time component):

```sql
SELECT
    date '1899-12-30'
    + INTERVAL (floor(excel_datetime_col)) DAY
    + INTERVAL (cast((excel_datetime_col - floor(excel_datetime_col)) * 86400 AS INTEGER)) SECOND
    AS actual_datetime
FROM raw_excel;
```

## Multi-Sheet Workbooks

```python
import duckdb

con = duckdb.connect()
con.execute("INSTALL excel; LOAD excel;")

# Read specific sheets and union
sheets = ['Q1', 'Q2', 'Q3', 'Q4']
for i, sheet in enumerate(sheets):
    query = f"SELECT *, '{sheet}' AS quarter FROM read_xlsx('workbook.xlsx', sheet='{sheet}')"
    if i == 0:
        con.execute(f"CREATE TABLE all_data AS {query}")
    else:
        con.execute(f"INSERT INTO all_data {query}")

con.execute("SELECT count(*), quarter FROM all_data GROUP BY quarter").show()
```

## Legacy: Spatial Extension Fallback

For DuckDB versions before 1.2, use the spatial extension's `st_read()` function:

```sql
INSTALL spatial;
LOAD spatial;

SELECT * FROM st_read('data.xlsx');
SELECT * FROM st_read('data.xlsx', layer='Sheet1');

-- List all sheets
SELECT * FROM st_layers('data.xlsx');
```

The spatial extension uses GDAL under the hood. It supports sheet selection via `layer` parameter, sheet listing via `st_layers()`, and `open_options` for header control. See DuckDB documentation for `st_read()` parameters.

Prefer `read_xlsx()` when available — it is faster, has simpler syntax, and does not require the full spatial/GDAL dependency.

## Python-Based Alternative

When Excel files are complex (heavy merged cells, formulas, named ranges):

```bash
pip install openpyxl duckdb
```

```python
import duckdb
import openpyxl

wb = openpyxl.load_workbook('complex_report.xlsx', data_only=True)
ws = wb['Revenue']

# Extract rows as list of dicts
headers = [cell.value for cell in ws[1]]
rows = [{headers[i]: cell.value for i, cell in enumerate(row)} for row in ws.iter_rows(min_row=2)]

# Load into DuckDB
con = duckdb.connect()
import pandas as pd
df = pd.DataFrame(rows)
con.execute("CREATE TABLE revenue AS SELECT * FROM df")
con.execute("SELECT * FROM revenue LIMIT 5").show()
```

Advantages: handles merged cells natively, better formula evaluation with `data_only=True`, access to cell formatting metadata.

## Limitations and Workarounds

| Limitation | Workaround |
|-----------|------------|
| `.xls` (old format) not supported | Convert to `.xlsx` or use Python `xlrd` |
| Formulas read as results only | Use `openpyxl` with `data_only=False` for formulas |
| Pivot tables not readable | Export pivot as values (paste special) first |
| Password-protected files | Remove protection first or use `msoffcrypto-tool` |
| Very large Excel (>100MB) | Convert to CSV/Parquet first; Excel is not a data format |
| Named ranges | Not accessible via `read_xlsx`; use `openpyxl` |
| Charts/images | Ignored (correctly); data only |
