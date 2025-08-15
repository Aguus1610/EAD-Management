#!/usr/bin/env python3
"""
Script de prueba para verificar que la aplicación Flask funciona correctamente
"""

def test_imports():
    """Probar todos los imports críticos"""
    print("🧪 Probando imports críticos...")
    
    try:
        import pandas as pd
        print(f"✅ pandas: {pd.__version__}")
    except Exception as e:
        print(f"❌ pandas: {e}")
        return False
    
    try:
        import numpy as np
        print(f"✅ numpy: {np.__version__}")
    except Exception as e:
        print(f"❌ numpy: {e}")
        return False
    
    try:
        import flask
        print(f"✅ flask: {flask.__version__}")
    except Exception as e:
        print(f"❌ flask: {e}")
        return False
    
    try:
        import sqlite3
        print("✅ sqlite3: integrado")
    except Exception as e:
        print(f"❌ sqlite3: {e}")
        return False
    
    return True

def test_app_syntax():
    """Probar sintaxis del archivo app.py"""
    print("\n🔍 Probando sintaxis de app.py...")
    
    try:
        import app
        print("✅ Sintaxis de app.py correcta")
        return True
    except Exception as e:
        print(f"❌ Error en app.py: {e}")
        return False

def test_database():
    """Probar conexión a la base de datos"""
    print("\n🗄️ Probando base de datos...")
    
    try:
        import sqlite3
        conn = sqlite3.connect('taller.db')
        
        # Verificar tabla principal
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        if cursor.fetchone():
            print("✅ Base de datos y tabla usuarios OK")
        else:
            print("❌ Tabla usuarios no encontrada")
            return False
        
        # Verificar nuevas tablas
        tablas_nuevas = [
            'configuracion_app',
            'temas_personalizados', 
            'dispositivos_iot',
            'lecturas_iot',
            'apis_externas'
        ]
        
        for tabla in tablas_nuevas:
            cursor = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla}'")
            if cursor.fetchone():
                print(f"✅ Tabla {tabla} OK")
            else:
                print(f"❌ Tabla {tabla} no encontrada")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en base de datos: {e}")
        return False

def main():
    """Ejecutar todas las pruebas"""
    print("🚀 PRUEBAS DE FUNCIONALIDAD DE LA APLICACIÓN")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Sintaxis App", test_app_syntax),
        ("Base de Datos", test_database)
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE PRUEBAS:")
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! La aplicación está lista.")
        print("🌐 Puedes ejecutar: python app.py")
        print("🔗 Y abrir: http://localhost:5000")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa los errores arriba.")
    
    return all_passed

if __name__ == "__main__":
    main()
