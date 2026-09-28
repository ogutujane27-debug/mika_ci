import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"

sys.path.insert(0, str(APP_DIR))

from database import connect
from samsutech_collector import extract_model

con = connect()

rows = con.execute("""
SELECT DISTINCT product_name, model
FROM price_observations
WHERE observed_date = '2026-09-19'
  AND (
      model IN ('TEFAL', 'SCL', 'CLIPSOMINUT')
      OR product_name LIKE '%TEFAL%'
      OR product_name LIKE '%SCL%'
      OR product_name LIKE '%CLIPSOMINUT%'
  )
ORDER BY observation_id
""").fetchall()

print("=== CURRENT MODEL EXTRACTION TEST ===")

for r in rows:
    print(
        "DB MODEL:", r["model"],
        "| EXTRACTED:", extract_model(r["product_name"], None),
        "| PRODUCT:", r["product_name"]
    )

con.close()
