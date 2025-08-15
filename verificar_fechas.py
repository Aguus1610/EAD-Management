#!/usr/bin/env python3
"""
Script para verificar que las fechas se están importando correctamente
"""

import sqlite3
import pandas as pd
from datetime import datetime

def verificar_fechas_base_datos():
    """Verifica las fechas en la base de datos"""
    print("🔍 VERIFICANDO FECHAS EN LA BASE DE DATOS")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('taller.db')
        conn.row_factory = sqlite3.Row
        
        # Verificar mantenimientos con fechas
        mantenimientos = conn.execute('''
            SELECT m.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
            FROM mantenimientos m
            JOIN equipos e ON m.equipo_id = e.id
            JOIN clientes c ON e.cliente_id = c.id
            ORDER BY c.nombre, m.fecha_mantenimiento DESC
            LIMIT 20
        ''').fetchall()
        
        if not mantenimientos:
            print("❌ No hay mantenimientos en la base de datos")
            return
        
        print(f"📊 Encontrados {len(mantenimientos)} mantenimientos (mostrando últimos 20)")
        print()
        
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        fechas_hoy = 0
        fechas_validas = 0
        
        for mant in mantenimientos:
            fecha = mant['fecha_mantenimiento']
            descripcion = mant['descripcion'][:60] + "..." if len(mant['descripcion']) > 60 else mant['descripcion']
            
            if fecha == fecha_actual:
                fechas_hoy += 1
                print(f"⚠️  {mant['cliente_nombre']} - {mant['equipo_nombre']}")
                print(f"    📅 Fecha: {fecha} (HOY - posible error)")
                print(f"    📝 {descripcion}")
            else:
                fechas_validas += 1
                print(f"✅ {mant['cliente_nombre']} - {mant['equipo_nombre']}")
                print(f"    📅 Fecha: {fecha}")
                print(f"    📝 {descripcion}")
            print()
        
        print("📈 RESUMEN:")
        print(f"   ✅ Fechas válidas (no hoy): {fechas_validas}")
        print(f"   ⚠️  Fechas de hoy (posibles errores): {fechas_hoy}")
        
        if fechas_hoy > fechas_validas:
            print("   🚨 PROBLEMA: Muchas fechas son de hoy, revisar importación")
        else:
            print("   ✅ CORRECTO: La mayoría de fechas son históricas")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def verificar_fechas_excel():
    """Verifica las fechas en el Excel original"""
    print("\n🔍 VERIFICANDO FECHAS EN EXCEL ORIGINAL")
    print("=" * 50)
    
    try:
        excel_file = pd.ExcelFile('Equipos.xlsx')
        
        for sheet_name in excel_file.sheet_names[:3]:  # Solo primeras 3 hojas
            print(f"\n🔸 HOJA: {sheet_name}")
            
            df = pd.read_excel('Equipos.xlsx', sheet_name=sheet_name)
            
            if df.empty:
                print("   ⚠️ Hoja vacía")
                continue
            
            # Analizar columna de fechas (columna 1)
            col_fecha = 1
            fechas_encontradas = []
            
            for index, row in df.iterrows():
                if index < 2:  # Saltar encabezados
                    continue
                    
                fecha_valor = row.iloc[col_fecha] if col_fecha < len(row) else None
                equipo_valor = row.iloc[0] if 0 < len(row) else None
                
                if pd.notna(fecha_valor):
                    if isinstance(fecha_valor, pd.Timestamp) or hasattr(fecha_valor, 'strftime'):
                        fecha_str = fecha_valor.strftime('%Y-%m-%d')
                        fechas_encontradas.append({
                            'fila': index,
                            'fecha': fecha_str,
                            'equipo': str(equipo_valor) if pd.notna(equipo_valor) else 'CONTINUACIÓN'
                        })
            
            print(f"   📅 Fechas encontradas: {len(fechas_encontradas)}")
            for fecha_info in fechas_encontradas[:5]:  # Mostrar primeras 5
                print(f"      Fila {fecha_info['fila']}: {fecha_info['fecha']} - {fecha_info['equipo']}")
            
            if len(fechas_encontradas) > 5:
                print(f"      ... y {len(fechas_encontradas) - 5} más")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("📊 VERIFICACIÓN DE FECHAS DE MANTENIMIENTOS")
    print("=" * 60)
    
    verificar_fechas_excel()
    verificar_fechas_base_datos()
    
    print("\n💡 RECOMENDACIONES:")
    print("1. Si muchas fechas son de 'hoy', hay que reimportar el Excel")
    print("2. Las fechas válidas deben ser históricas (2023, 2024)")
    print("3. Usar 'Reiniciar App' y volver a importar si es necesario")

if __name__ == "__main__":
    main()
