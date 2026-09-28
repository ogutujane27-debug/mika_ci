import sqlite3
con = sqlite3.connect(r'.\data\mika_competitive_intel.db')
con.row_factory = sqlite3.Row
rows = con.execute('SELECT competitor_id, competitor_name, platform, source_url, verification_status, active FROM social_sources ORDER BY competitor_name, platform').fetchall()
print('SOCIAL SOURCES')
print('=' * 100)
for r in rows:
    print(r['competitor_name'], '|', r['platform'], '|', r['verification_status'], '| active=', r['active'], '|', r['source_url'])
print('=' * 100)
print('Total sources:', len(rows))
con.close()
