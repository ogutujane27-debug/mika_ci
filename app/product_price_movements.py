from pathlib import Path
import sys

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from database import connect


def normalize_text(value):
    if not value:
        return ''
    return ' '.join(str(value).strip().upper().split())


def pct_change(previous, current):
    if previous in (None, 0):
        return None
    return round((current - previous) / previous * 100, 2)

def load_price_observations(con):
    return con.execute('SELECT p.observation_id, p.product_name, p.model, p.price_kes, p.observed_date, f.brand, f.category, f.competitor_id FROM price_observations p JOIN findings f ON f.finding_id = p.finding_id WHERE p.price_kes IS NOT NULL ORDER BY p.observed_date, p.observation_id').fetchall()


def build_identities(rows):
    identities = {}

    for row in rows:
        model = normalize_text(row['model'])
        product_name = normalize_text(row['product_name'])
        brand = normalize_text(row['brand'])

        if not model or not product_name or not brand:
            continue

        key = (row['competitor_id'], brand, model, product_name)
        identities.setdefault(key, []).append(row)

    return identities

def detect_movements(identities):
    movements = []
    ambiguous = []

    for key, observations in identities.items():
        dates = {}

        for row in observations:
            dates.setdefault(row['observed_date'], []).append(row)

        if any(len(items) > 1 for items in dates.values()):
            ambiguous.append(key)

        daily = []

        for observed_date, items in dates.items():
            selected = max(items, key=lambda r: r['observation_id'])
            daily.append(selected)

        daily.sort(key=lambda r: r['observed_date'])

        for previous, current in zip(daily, daily[1:]):
            if previous['price_kes'] == current['price_kes']:
                continue

            change = current['price_kes'] - previous['price_kes']
            percentage = pct_change(previous['price_kes'], current['price_kes'])

            movements.append({
                'brand': current['brand'],
                'model': current['model'],
                'product_name': current['product_name'],
                'category': current['category'],
                'previous_price': previous['price_kes'],
                'current_price': current['price_kes'],
                'change': change,
                'percentage': percentage,
                'previous_date': previous['observed_date'],
                'current_date': current['observed_date'],
            })

    movements.sort(key=lambda item: abs(item['percentage'] or 0), reverse=True)

    return movements, ambiguous


def main():
    con = connect()

    print('=' * 80)
    print('MIKA CI - PHASE 2D PRICE MOVEMENT DETECTOR')
    print('=' * 80)
    print('Database writes: DISABLED')

    rows = load_price_observations(con)
    identities = build_identities(rows)
    movements, ambiguous = detect_movements(identities)
    print('Price observations analysed: {}'.format(len(rows)))
    print('Identities analysed: {}'.format(len(identities)))
    print('Movement candidates: {}'.format(len(movements)))
    print('Ambiguous same-day identity cases: {}'.format(len(ambiguous)))

    for index, item in enumerate(movements, 1):
        print('{} . {} | {}'.format(index, item['brand'], item['model']))
        print('   Product: {}'.format(item['product_name']))
        print('   Category: {}'.format(item['category']))
        print('   Previous price: KSh {:,.2f} ({})'.format(item['previous_price'], item['previous_date']))
        print('   Current price:  KSh {:,.2f} ({})'.format(item['current_price'], item['current_date']))
        print('   Change: {:+,.2f} KSh ({:+.2f}%)'.format(item['change'], item['percentage']))
        print('   Status: PRICE MOVEMENT CANDIDATE')
        print('   Confidence: HIGH')
        print()
    con.close()


if __name__ == '__main__':
    main()
