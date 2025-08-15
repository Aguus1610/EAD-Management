#!/usr/bin/env python3
# Test específico de rutas

from app import app
import traceback

def test_route(route_path, method='GET'):
    try:
        with app.test_client() as client:
            if method == 'GET':
                response = client.get(route_path)
            elif method == 'POST':
                response = client.post(route_path)
            
            if response.status_code == 200:
                print(f"✅ {route_path} - OK ({response.status_code})")
            elif response.status_code == 302:
                print(f"🔄 {route_path} - Redirect ({response.status_code})")
            elif response.status_code == 500:
                print(f"❌ {route_path} - SERVER ERROR ({response.status_code})")
                # Obtener el error del response
                error_data = response.get_data(as_text=True)
                if "Internal Server Error" in error_data:
                    print(f"   Error interno del servidor")
            else:
                print(f"⚠️  {route_path} - Status {response.status_code}")
                
    except Exception as e:
        print(f"❌ {route_path} - EXCEPTION: {str(e)}")
        print(f"   {traceback.format_exc()}")

print("=== TESTING RUTAS PRINCIPALES ===")

# Rutas básicas
routes_to_test = [
    '/login',
    '/',
    '/equipos', 
    '/clientes',
    '/mantenimientos',
    '/repuestos',
    '/reportes',
    '/gestion_categorias',
    '/configuracion',
    '/usuarios',
    '/auditoria',
    '/ml',
    '/iot',
    '/apis',
    '/automatizacion'
]

for route in routes_to_test:
    test_route(route)

print("\n=== TESTING APIS ===")

api_routes = [
    '/api/stats',
    '/api/dashboard/metricas', 
    '/api/categorias',
    '/api/estadisticas_categorias'
]

for route in api_routes:
    test_route(route)

