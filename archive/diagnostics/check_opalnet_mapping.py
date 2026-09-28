from pathlib import Path

APP = Path("app")

print("=" * 80)
print("MIKA CI - OPALNET MAPPING DIAGNOSTIC")
print("=" * 80)

for path in sorted(APP.glob("*.py")):

    text = path.read_text(encoding="utf-8", errors="ignore")

    lines = text.splitlines()

    matches = []

    for number, line in enumerate(lines, start=1):

        lower = line.lower()

        if (
            "unknown competitor brand" in lower
            or "opalnet" in lower
            or "competitor_id" in lower
            or "competitor_id(" in lower
        ):
            matches.append((number, line.strip()))

    if matches:

        print("\n" + "-" * 80)
        print(path)
        print("-" * 80)

        for number, line in matches:
            print(f"{number}: {line}")

print("\n" + "=" * 80)
print("OPALNET MAPPING DIAGNOSTIC COMPLETE")
print("=" * 80)