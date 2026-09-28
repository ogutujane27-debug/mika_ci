from pathlib import Path

path = Path(r".\app\product_intelligence.py")
text = path.read_text(encoding="utf-8")

if "def print_price_movements():" in text:
    print("ALREADY INTEGRATED")
    raise SystemExit

marker = "\ndef main():\n"

if marker not in text:
    raise SystemExit("MAIN MARKER NOT FOUND")

function = '''
def print_price_movements():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    rows = price_movements.load_price_observations(con)
    identities = price_movements.build_identities(rows)
    movements, ambiguous = price_movements.detect_movements(identities)

    print()
    print("PRICE MOVEMENTS")
    print("-" * 80)
    print(f"Price observations analysed: {len(rows)}")
    print(f"Identities analysed: {len(identities)}")
    print(f"Movement candidates: {len(movements)}")
    print(f"Ambiguous same-day identity cases: {len(ambiguous)}")

    for index, item in enumerate(movements, 1):
        print()
        print(f"{index}. {item['brand']} | {item['model']}")
        print(f"   Product: {item['product_name']}")
        print(f"   Category: {item['category']}")
        print(f"   Previous: KSh {item['previous_price']:,.2f} ({item['previous_date']})")
        print(f"   Current:  KSh {item['current_price']:,.2f} ({item['current_date']})")
        print(f"   Change: {item['change']:+,.2f} KSh ({item['percentage']:+.2f}%)")
        print("   Status: PRICE MOVEMENT CANDIDATE")
        print("   Confidence: HIGH")

    con.close()


'''

path.write_text(text.replace(marker, "\n" + function + "def main():\n", 1), encoding="utf-8")
print("INTEGRATION WRITTEN")
