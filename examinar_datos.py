#!/usr/bin/env python3
"""
Script para examinar los datos existentes en la base de datos SQLite y archivo Excel
"""

import sqlite3
import pandas as pd
import os

def examinar_base_datos():
    """Examina la estructura y contenido de la base de datos SQLite"""
    print("=== EXAMINANDO BASE DE DATOS SQLite ===")
    
    if not os.path.exists('taller.db'):
        print("❌ Archivo taller.db no encontrado")
        return
    
    try:
        conn = sqlite3.connect('taller.db')
        cursor = conn.cursor()
        
        # Obtener todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = cursor.fetchall()
        
        if not tablas:
            print("📋 Base de datos vacía - no hay tablas")
        else:
            print(f"📋 Tablas encontradas: {len(tablas)}")
            for tabla in tablas:
                print(f"  - {tabla[0]}")
                
                # Obtener esquema de cada tabla
                cursor.execute(f"PRAGMA table_info({tabla[0]});")
                columnas = cursor.fetchall()
                print("    Columnas:")
                for col in columnas:
                    print(f"      {col[1]} ({col[2]})")
                
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM {tabla[0]};")
                count = cursor.fetchone()[0]
                print(f"    Registros: {count}")
                
                # Mostrar algunos registros de ejemplo
                if count > 0:
                    cursor.execute(f"SELECT * FROM {tabla[0]} LIMIT 3;")
                    registros = cursor.fetchall()
                    print("    Ejemplos:")
                    for reg in registros:
                        print(f"      {reg}")
                print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error al examinar base de datos: {e}")

def examinar_excel():
    """Examina el contenido del archivo Excel"""
    print("=== EXAMINANDO ARCHIVO EXCEL ===")
    
    if not os.path.exists('Equipos.xlsx'):
        print("❌ Archivo Equipos.xlsx no encontrado")
        return
    
    try:
        # Leer el archivo Excel
        df = pd.read_excel('Equipos.xlsx')
        
        print(f"📊 Archivo Excel encontrado")
        print(f"   Filas: {len(df)}")
        print(f"   Columnas: {len(df.columns)}")
        print(f"   Columnas disponibles: {list(df.columns)}")
        print()
        
        # Mostrar información sobre cada columna
        print("📋 Información de columnas:")
        for col in df.columns:
            valores_no_nulos = df[col].notna().sum()
            print(f"   {col}: {valores_no_nulos} valores no nulos")
        print()
        
        # Mostrar las primeras filas
        print("📝 Primeras 5 filas:")
        print(df.head().to_string())
        print()
        
        # Estadísticas básicas
        print("📈 Estadísticas:")
        print(f"   Total de filas con datos: {len(df.dropna(how='all'))}")
        
        # Verificar columnas esperadas
        columnas_esperadas = ['Nombre', 'nombre', 'Marca', 'marca', 'Modelo', 'modelo', 'Numero_Serie', 'numero_serie']
        columnas_encontradas = []
        for col_esperada in columnas_esperadas:
            if col_esperada in df.columns:
                columnas_encontradas.append(col_esperada)
        
        print(f"   Columnas reconocidas: {columnas_encontradas}")
        
    except Exception as e:
        print(f"❌ Error al examinar archivo Excel: {e}")

def main():
    """Función principal"""
    print("🔍 EXAMINADOR DE DATOS DEL TALLER")
    print("=" * 50)
    print()
    
    examinar_base_datos()
    print()
    examinar_excel()
    
    print()
    print("✅ Examen completado")
    print("💡 Tip: Ejecuta 'python app.py' para iniciar la aplicación web")

if __name__ == "__main__":
    main()
