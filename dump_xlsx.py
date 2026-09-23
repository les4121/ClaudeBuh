import sys, openpyxl
wb = openpyxl.load_workbook(sys.argv[1], data_only=True)
for ws in wb.worksheets:
    print(f"### SHEET: {ws.title}  dims={ws.dimensions}  max_row={ws.max_row} max_col={ws.max_column}")
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        if all(c is None or str(c).strip() == "" for c in row):
            continue
        cells = [("" if c is None else str(c)) for c in row]
        print(f"{i:4} | " + " | ".join(cells))
        if i > 80 and len(sys.argv) < 3:
            print("... (обрезано на 80 строк, передай 3-й аргумент чтобы показать всё)")
            break
