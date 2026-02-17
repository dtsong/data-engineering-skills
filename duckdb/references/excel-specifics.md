## Contents

- [Installation](#installation)
- [Basic Excel Reading](#basic-excel-reading)
- [Sheet Selection](#sheet-selection)
- [Handling Merged Cells and Header Rows](#handling-merged-cells-and-header-rows)
- [Date Serial Number Conversion](#date-serial-number-conversion)
- [Multi-Sheet Workbooks](#multi-sheet-workbooks)
- [Python-Based Alternative](#python-based-alternative)
- [Limitations and Workarounds](#limitations-and-workarounds)

---

# Excel Specifics

> **Part of:** [duckdb](../SKILL.md)

## Installation

DuckDB reads Excel files via the spatial extension's `st_read()` function (uses GDAL under the hood).

```sql
INSTALL spatial;
LOAD spatial;
```

This installs on first run and loads the extension into the session.

## Basic Excel Reading

```sql
-- Read the first sheet (default)
SELECT * FROM st_read('data.xlsx');

-- Read with explicit layer (sheet name)
SELECT * FROM st_read('data.xlsx', layer = 'Sheet1');
```

### Inspect Available Sheets

```sql
-- List all sheets in the workbook
SELECT * FROM st_layers('data.xlsx');
```

Returns a table with layer names (sheet names) and geometry types (always `None` for Excel).

## Sheet Selection

```sql
-- By sheet name
SELECT * FROM st_read('workbook.xlsx', layer = 'Revenue');

-- By sheet index (0-based)
SELECT * FROM st_read('workbook.xlsx', layer_index = 0);
```

Use `st_layers()` first to discover sheet names when they are unknown.

## Handling Merged Cells and Header Rows

### Merged Cells

Excel merged cells fill only the top-left cell; others appear as NULL. After reading:

```sql
-- Forward-fill NULLs from merged cells (common in category columns)
WITH raw AS (
    SELECT *, rowid AS rn FROM st_read('report.xlsx')
)
SELECT
    -- Forward-fill: use last non-null value
    COALESCE(
        category,
        LAST_VALUE(category IGNORE NULLS) OVER (ORDER BY rn ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
    ) AS category
    , value_col
FROM raw;
```

### Header Rows

When the header is not on row 1 (e.g., title rows above the data):

```sql
-- Skip title rows: read as all-varchar, then filter and rename
WITH raw AS (
    SELECT * FROM st_read('report.xlsx', open_options = ['HEADERS=DISABLE'])
)
SELECT
    -- Row 3 is the actual header; data starts at row 4
    Field1 AS customer_id
    , Field2 AS customer_name
    , Field3 AS revenue
FROM raw
WHERE rowid >= 3;  -- skip title and header rows
```

### Data Start Row

When data does not start on row 1:

```sql
-- Use OFFSET with open_options
SELECT * FROM st_read(
    'report.xlsx',
    open_options = ['HEADERS=FORCE', 'FIELD_TYPES=AUTO']
);
```

## Date Serial Number Conversion

Excel stores dates as serial numbers (days since 1899-12-30). If dates load as integers:

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

### Detect Whether Conversion Is Needed

```sql
-- If dates appear as numbers in the 40000-50000 range, they are serial numbers
SELECT typeof(date_column), date_column
FROM st_read('data.xlsx')
LIMIT 5;
```

## Multi-Sheet Workbooks

### Read and Union All Sheets

```python
import duckdb

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")

# Get sheet names
sheets = con.execute("SELECT * FROM st_layers('workbook.xlsx')").fetchall()

# Union all sheets
for i, (sheet_name, *_) in enumerate(sheets):
    query = f"SELECT *, '{sheet_name}' AS sheet_name FROM st_read('workbook.xlsx', layer = '{sheet_name}')"
    if i == 0:
        con.execute(f"CREATE TABLE all_data AS {query}")
    else:
        con.execute(f"INSERT INTO all_data {query}")

con.execute("SELECT count(*), sheet_name FROM all_data GROUP BY sheet_name").show()
```

### Union by Name (Different Column Orders)

When sheets have the same columns in different orders:

```python
# Read each sheet into a named view, then UNION BY NAME
for sheet_name, *_ in sheets:
    con.execute(f"""
        CREATE OR REPLACE VIEW "{sheet_name}" AS
        SELECT * FROM st_read('workbook.xlsx', layer = '{sheet_name}')
    """)

# Union aligns by column name
con.execute("""
    SELECT * FROM Sheet1
    UNION ALL BY NAME
    SELECT * FROM Sheet2
""").show()
```

## Python-Based Alternative

When the spatial extension is unavailable or Excel files are complex:

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

Advantages of Python approach: handles merged cells natively, better formula evaluation with `data_only=True`, access to cell formatting metadata.

## Limitations and Workarounds

| Limitation | Workaround |
|-----------|------------|
| `.xls` (old format) not supported by spatial | Convert to `.xlsx` or use Python `xlrd` |
| Formulas read as results only | Use `openpyxl` with `data_only=False` for formulas |
| Pivot tables not readable | Export pivot as values (paste special) first |
| Password-protected files | Remove protection first or use `msoffcrypto-tool` |
| Very large Excel (>100MB) | Convert to CSV/Parquet first; Excel is not a data format |
| Named ranges | Not accessible via `st_read`; use `openpyxl` |
| Charts/images | Ignored (correctly); data only |
