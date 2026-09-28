from pathlib import Path

p = Path(r".\app\product_intelligence.py")
s = p.read_text(encoding="utf-8")

marker = '    print("AUDIT COMPLETE - NO DATABASE WRITES")'

if "    print_price_movements()\n\n" + marker in s:
    print("ALREADY UPDATED")
elif marker not in s:
    print("MARKER NOT FOUND")
else:
    s = s.replace(
        marker,
        '    print_price_movements()\n\n' + marker,
        1,
    )
    p.write_text(s, encoding="utf-8")
    print("MAIN UPDATED")
