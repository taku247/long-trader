#!/usr/bin/env python3
from web_dashboard.app import WebDashboard

app = WebDashboard()
routes = sorted([rule.rule for rule in app.app.url_map.iter_rules() if rule.endpoint != 'static'])
print(f'Total routes: {len(routes)}')
print('Last 10 routes:')
for route in routes[-10:]:
    print(f'  {route}')

# Check where routes stop being added
print('\nChecking for /api/symbol/add:')
for rule in app.app.url_map.iter_rules():
    if 'symbol/add' in rule.rule:
        print(f'Found: {rule.rule}')