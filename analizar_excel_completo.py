#!/usr/bin/env python3
"""
Script mejorado para analizar completamente el archivo Excel
y entender toda la estructura de datos
"""

import pandas as pd
import os

def analizar_excel_completo():
    """Analiza el archivo Excel completo incluyendo todas las hojas"""
    print("🔍 ANÁLISIS COMPLETO DEL ARCHIVO EXCEL")
    print("=" * 60)
    
    if not os.path.exists('Equipos.xlsx'):
        print("❌ Archivo Equipos.xlsx no encontrado")
        return
    
    try:
        # Leer el archivo Excel con todas las hojas
        excel_file = pd.ExcelFile('Equipos.xlsx')
        
        print(f"📊 Archivo Excel encontrado")
        print(f"📋 Hojas disponibles: {excel_file.sheet_names}")
        print(f"📈 Total de hojas: {len(excel_file.sheet_names)}")
        print()
        
        # Analizar cada hoja por separado
        for i, sheet_name in enumerate(excel_file.sheet_names):
            print(f"🔸 HOJA {i+1}: '{sheet_name}'")
            print("-" * 40)
            
            try:
                # Leer la hoja específica
                df = pd.read_excel('Equipos.xlsx', sheet_name=sheet_name)
                
                print(f"   📏 Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
                print(f"   📋 Columnas: {list(df.columns)}")
                
                # Mostrar información de cada columna
                print("   📊 Información por columna:")
                for col in df.columns:
                    valores_no_nulos = df[col].notna().sum()
                    print(f"      - {col}: {valores_no_nulos} valores no nulos")
                
                # Mostrar primeras filas no vacías
                df_limpio = df.dropna(how='all')
                if len(df_limpio) > 0:
                    print("   📝 Primeras filas con datos:")
                    for idx, row in df_limpio.head(3).iterrows():
                        print(f"      Fila {idx}: {row.tolist()}")
                else:
                    print("   ⚠️  Hoja sin datos válidos")
                
                # Buscar patrones de datos
                print("   🔍 Análisis de contenido:")
                
                # Buscar posibles nombres de equipos
                equipos_posibles = set()
                for col in df.columns:
                    for val in df[col].dropna():
                        val_str = str(val).strip()
                        if (len(val_str) > 5 and 
                            any(palabra in val_str.upper() for palabra in ['GRÚA', 'HIDRO', 'COMPRESOR', 'TALADRO', 'SOLDADORA', 'MÁQUINA'])):
                            equipos_posibles.add(val_str)
                
                if equipos_posibles:
                    print(f"      🔧 Posibles equipos encontrados: {list(equipos_posibles)[:3]}...")
                
                # Buscar fechas
                fechas_encontradas = 0
                for col in df.columns:
                    for val in df[col].dropna():
                        val_str = str(val)
                        if any(separador in val_str for separador in ['/', '-']) and any(char.isdigit() for char in val_str):
                            fechas_encontradas += 1
                            break
                
                if fechas_encontradas > 0:
                    print(f"      📅 Columnas con fechas: {fechas_encontradas}")
                
                print()
                
            except Exception as e:
                print(f"   ❌ Error al leer hoja '{sheet_name}': {e}")
                print()
        
        # Análisis global
        print("🌐 RESUMEN GLOBAL")
        print("-" * 40)
        print(f"✅ Hojas procesadas: {len(excel_file.sheet_names)}")
        
        # Sugerencias para importación
        print("\n💡 SUGERENCIAS PARA IMPORTACIÓN:")
        print("1. La aplicación actual solo lee la primera hoja")
        print("2. Cada hoja podría corresponder a un cliente diferente")
        print("3. Necesitamos modificar la importación para procesar todas las hojas")
        print("4. Deberíamos agregar gestión de clientes a la aplicación")
        
    except Exception as e:
        print(f"❌ Error al analizar archivo Excel: {e}")

def sugerir_estructura_clientes():
    """Sugiere cómo estructurar la gestión de clientes"""
    print("\n🏢 PROPUESTA: GESTIÓN DE CLIENTES")
    print("=" * 50)
    print("📋 Estructura sugerida:")
    print("   - Tabla CLIENTES: id, nombre, telefono, email, direccion")
    print("   - Relación: EQUIPOS pertenecen a CLIENTES")
    print("   - Importación: Cada hoja Excel = Un cliente")
    print("   - Mantenimientos: Vinculados a equipos de clientes específicos")

if __name__ == "__main__":
    analizar_excel_completo()
    sugerir_estructura_clientes()
