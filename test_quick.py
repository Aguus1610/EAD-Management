#!/usr/bin/env python3
# Test rápido de dependencias y errores

print("=== TESTING DEPENDENCIAS ===")
try:
    import bleach
    print("✅ bleach OK")
except Exception as e:
    print(f"❌ bleach ERROR: {e}")

try:
    import pandas
    print("✅ pandas OK")
except Exception as e:
    print(f"❌ pandas ERROR: {e}")

try:
    import xlsxwriter
    print("✅ xlsxwriter OK")
except Exception as e:
    print(f"❌ xlsxwriter ERROR: {e}")

try:
    import reportlab
    print("✅ reportlab OK")
except Exception as e:
    print(f"❌ reportlab ERROR: {e}")

print("\n=== TESTING IMPORTS APP ===")
try:
    from app import app
    print("✅ app import OK")
except Exception as e:
    print(f"❌ app import ERROR: {e}")

print("\n=== TESTING DB CONNECTION ===")
try:
    from app import get_db_connection
    conn = get_db_connection()
    conn.close()
    print("✅ DB connection OK")
except Exception as e:
    print(f"❌ DB connection ERROR: {e}")

print("\n=== TESTING FLASK INIT ===")
try:
    from app import app
    with app.test_client() as client:
        response = client.get('/login')
        print(f"✅ Flask test OK - Status: {response.status_code}")
except Exception as e:
    print(f"❌ Flask test ERROR: {e}")

