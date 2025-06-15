#!/usr/bin/env python3
from web_dashboard.app import WebDashboard
import traceback

try:
    app = WebDashboard()
    print('Dashboard created successfully')
    
    # Check which route registration fails
    route_count = 0
    routes = []
    for rule in app.app.url_map.iter_rules():
        if rule.endpoint != 'static':
            route_count += 1
            routes.append(rule.rule)
    
    print(f'Total routes registered: {route_count}')
    
    # Check for critical missing routes
    missing_routes = []
    required_routes = [
        '/api/strategy-results/<symbol>',
        '/api/symbol/add',
        '/api/execution/<execution_id>/status',
        '/api/executions'
    ]
    
    for required in required_routes:
        found = False
        for route in routes:
            if route.replace('<symbol>', 'TEST').replace('<execution_id>', 'TEST') == required.replace('<symbol>', 'TEST').replace('<execution_id>', 'TEST'):
                found = True
                break
        if not found:
            missing_routes.append(required)
    
    if missing_routes:
        print(f'Missing critical routes: {missing_routes}')
        
        # Find where route registration stops
        last_registered = routes[-5:] if len(routes) >= 5 else routes
        print(f'Last registered routes: {last_registered}')
    else:
        print('All critical routes are registered')
    
except Exception as e:
    print(f'Error creating dashboard: {e}')
    traceback.print_exc()