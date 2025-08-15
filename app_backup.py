#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Gestión de Taller
============================

Sistema completo para la gestión de talleres de mantenimiento de equipos.
Incluye gestión de clientes, equipos, mantenimientos, repuestos y reportes.

Autor: Sistema Automatizado
Versión: 2.0
Fecha: 2024
"""

import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from datetime import datetime
import logging
from motor_reconocimiento import crear_motor_reconocimiento

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('taller.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_desarrollo_cambiar_en_produccion')

# Configuración de la aplicación
app.config.update(
    DATABASE='taller.db',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB máximo para archivos
    UPLOAD_FOLDER='uploads',
    DEBUG=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
)

# Configuración de la base de datos
DATABASE = app.config['DATABASE']

# Constantes de la aplicación
ESTADOS_EQUIPO = ['Activo', 'Inactivo', 'Mantenimiento', 'Fuera de Servicio']
TIPOS_MANTENIMIENTO = ['Preventivo', 'Correctivo', 'Emergencia', 'Inspección', 'Reparación']
ESTADOS_MANTENIMIENTO = ['Pendiente', 'En Progreso', 'Completado', 'Cancelado']

def procesar_hoja_excel(df, cliente_id, conn, sheet_name):
    """
    Procesa una hoja específica del Excel para un cliente.
    
    Esta función analiza una hoja de Excel que contiene información de equipos y mantenimientos,
    extrae los datos y los importa a la base de datos asociándolos al cliente especificado.
    
    Args:
        df (pandas.DataFrame): DataFrame con los datos de la hoja Excel
        cliente_id (int): ID del cliente al que pertenecen los equipos
        conn (sqlite3.Connection): Conexión activa a la base de datos
        sheet_name (str): Nombre de la hoja Excel que se está procesando
        
    Returns:
        tuple: (equipos_importados, mantenimientos_importados) cantidad de registros creados
        
    Note:
        La función busca automáticamente las columnas por nombre (EQUIPOS, FECHA, REPUESTOS, MANO DE OBRA)
        o usa posiciones por defecto si no las encuentra. Maneja correctamente las fechas y agrupa
        los mantenimientos por equipo y fecha.
    """
    equipos_importados = 0
    mantenimientos_importados = 0
    
    # Buscar las columnas correctas por nombre
    columnas_excel = df.columns.tolist()
    print(f"  📋 Columnas encontradas: {columnas_excel}")
    
    # Intentar encontrar las columnas por nombre
    col_equipos = None
    col_fecha = None
    col_repuestos = None
    col_mano_obra = None
    
    for i, col in enumerate(columnas_excel):
        col_str = str(col).upper() if pd.notna(col) else ""
        if 'EQUIPO' in col_str:
            col_equipos = i
        elif 'FECHA' in col_str:
            col_fecha = i
        elif 'REPUESTO' in col_str:
            col_repuestos = i
        elif 'MANO' in col_str and 'OBRA' in col_str:
            col_mano_obra = i
    
    # Si no encontramos por nombre, usar posiciones por defecto
    if col_equipos is None:
        col_equipos = 0
    if col_fecha is None:
        col_fecha = 1
    if col_repuestos is None:
        col_repuestos = 2
    if col_mano_obra is None:
        col_mano_obra = 3
    
    print(f"  🔍 Usando columnas - Equipos: {col_equipos}, Fecha: {col_fecha}, Repuestos: {col_repuestos}, Mano de Obra: {col_mano_obra}")
    
    equipo_actual_id = None
    fecha_actual_mantenimiento = None  # Variable para mantener la fecha del mantenimiento actual
    
    for index, row in df.iterrows():
        # Obtener datos de las columnas identificadas
        equipo_nombre = str(row.iloc[col_equipos]) if col_equipos < len(row) and pd.notna(row.iloc[col_equipos]) else None
        fecha_valor = row.iloc[col_fecha] if col_fecha < len(row) and pd.notna(row.iloc[col_fecha]) else None
        repuestos = str(row.iloc[col_repuestos]) if col_repuestos < len(row) and pd.notna(row.iloc[col_repuestos]) else None
        mano_obra = str(row.iloc[col_mano_obra]) if col_mano_obra < len(row) and pd.notna(row.iloc[col_mano_obra]) else None
        
        # Limpiar y validar datos de texto
        if equipo_nombre:
            equipo_nombre = equipo_nombre.strip()
        if repuestos:
            repuestos = repuestos.strip()
        if mano_obra:
            mano_obra = mano_obra.strip()
        
        # Procesar fecha (puede ser datetime o string)
        # SIEMPRE capturar fecha si está presente, incluso en filas de continuación
        fecha_procesada = None
        if fecha_valor is not None:
            try:
                if isinstance(fecha_valor, pd.Timestamp) or hasattr(fecha_valor, 'strftime'):
                    # Ya es un objeto datetime
                    fecha_procesada = fecha_valor.strftime('%Y-%m-%d')
                    fecha_actual_mantenimiento = fecha_procesada  # Actualizar fecha actual
                    print(f"    📅 Nueva fecha de mantenimiento: {fecha_procesada}")
                else:
                    # Es string, intentar convertir
                    fecha_str = str(fecha_valor).strip()
                    if fecha_str not in ['nan', '', 'FECHA']:
                        if '/' in fecha_str:
                            fecha_obj = pd.to_datetime(fecha_str, dayfirst=True)
                        elif '-' in fecha_str:
                            fecha_obj = pd.to_datetime(fecha_str)
                        else:
                            fecha_obj = pd.to_datetime(fecha_str)
                        
                        fecha_procesada = fecha_obj.strftime('%Y-%m-%d')
                        fecha_actual_mantenimiento = fecha_procesada  # Actualizar fecha actual
                        print(f"    📅 Nueva fecha de mantenimiento: {fecha_procesada}")
            except Exception as e:
                print(f"    ⚠️ Error procesando fecha '{fecha_valor}': {e}")
                # No cambiar fecha_actual_mantenimiento, mantener la anterior
        
        # Si hay nombre de equipo válido, crear/encontrar el equipo
        if (equipo_nombre and 
            equipo_nombre not in ['nan', 'EQUIPO', 'EQUIPOS'] and
            len(equipo_nombre) > 2):
            
            # Verificar si el equipo ya existe para este cliente
            equipo_existente = conn.execute(
                'SELECT id FROM equipos WHERE nombre = ? AND cliente_id = ?', 
                (equipo_nombre, cliente_id)
            ).fetchone()
            
            if not equipo_existente:
                # Crear nuevo equipo
                cursor = conn.execute('''
                    INSERT INTO equipos (cliente_id, nombre, estado)
                    VALUES (?, ?, ?)
                ''', (cliente_id, equipo_nombre, 'Activo'))
                equipo_actual_id = cursor.lastrowid
                equipos_importados += 1
                print(f"    ➕ Equipo creado: {equipo_nombre} (ID: {equipo_actual_id})")
            else:
                equipo_actual_id = equipo_existente[0]
                print(f"    ✅ Equipo existente: {equipo_nombre} (ID: {equipo_actual_id})")
        
        # Si hay información de mantenimiento y tenemos un equipo actual
        if equipo_actual_id and ((repuestos and repuestos not in ['nan', '', 'REPUESTOS']) or 
                                (mano_obra and mano_obra not in ['nan', '', 'MANO DE OBRA'])):
            
            descripcion_partes = []
            
            if repuestos and repuestos not in ['nan', '', 'REPUESTOS']:
                descripcion_partes.append(f"Repuestos: {repuestos}")
            
            if mano_obra and mano_obra not in ['nan', '', 'MANO DE OBRA']:
                descripcion_partes.append(f"Trabajo realizado: {mano_obra}")
            
            if descripcion_partes:
                descripcion = " | ".join(descripcion_partes)
                
                # Usar la fecha actual del mantenimiento o fecha por defecto
                fecha_mantenimiento = fecha_actual_mantenimiento
                if not fecha_mantenimiento:
                    from datetime import datetime
                    fecha_mantenimiento = datetime.now().strftime('%Y-%m-%d')
                    print(f"    ⚠️ Usando fecha actual como fallback: {fecha_mantenimiento}")
                
                # Estrategia mejorada para mantenimientos:
                # 1. Si hay equipo nuevo O cambió la fecha -> Nuevo mantenimiento
                # 2. Si NO hay equipo Y es la misma fecha -> Actualizar el último mantenimiento
                
                crear_nuevo_mantenimiento = True
                
                if not equipo_nombre:  # Es una fila de continuación (sin equipo)
                    # Buscar el último mantenimiento del equipo actual
                    mantenimiento_existente = conn.execute('''
                        SELECT id, descripcion, fecha_mantenimiento FROM mantenimientos 
                        WHERE equipo_id = ? 
                        ORDER BY id DESC LIMIT 1
                    ''', (equipo_actual_id,)).fetchone()
                    
                    if (mantenimiento_existente and 
                        mantenimiento_existente['fecha_mantenimiento'] == fecha_mantenimiento):
                        # Es continuación del mismo mantenimiento (misma fecha)
                        descripcion_actualizada = mantenimiento_existente['descripcion'] + " | " + descripcion
                        conn.execute('''
                            UPDATE mantenimientos 
                            SET descripcion = ?
                            WHERE id = ?
                        ''', (descripcion_actualizada, mantenimiento_existente['id']))
                        print(f"    🔄 Mantenimiento actualizado ({fecha_mantenimiento}): {descripcion[:50]}...")
                        crear_nuevo_mantenimiento = False
                
                if crear_nuevo_mantenimiento:
                    # Crear nuevo mantenimiento
                    conn.execute('''
                        INSERT INTO mantenimientos 
                        (equipo_id, tipo_mantenimiento, fecha_mantenimiento, descripcion)
                        VALUES (?, ?, ?, ?)
                    ''', (equipo_actual_id, 'Correctivo', fecha_mantenimiento, descripcion))
                    mantenimientos_importados += 1
                    print(f"    ✅ Nuevo mantenimiento ({fecha_mantenimiento}): {descripcion[:50]}...")
    
    print(f"  📊 Hoja '{sheet_name}': {equipos_importados} equipos, {mantenimientos_importados} mantenimientos")
    return equipos_importados, mantenimientos_importados

def get_db_connection():
    """
    Crea y devuelve una conexión a la base de datos SQLite.
    
    Configura la conexión para devolver resultados como diccionarios (Row objects)
    lo que permite acceder a las columnas por nombre además de por índice.
    
    Returns:
        sqlite3.Connection: Conexión configurada a la base de datos
        
    Note:
        Utiliza sqlite3.Row como row_factory para facilitar el acceso a los datos
        por nombre de columna en los templates y funciones.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    conn = get_db_connection()
    
    # Crear tabla de clientes si no existe
    conn.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            telefono TEXT,
            email TEXT,
            direccion TEXT,
            observaciones TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crear tabla de equipos si no existe (ahora con cliente_id)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            nombre TEXT NOT NULL,
            marca TEXT,
            modelo TEXT,
            numero_serie TEXT,
            fecha_compra DATE,
            estado TEXT DEFAULT 'Activo',
            ubicacion TEXT,
            observaciones TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')
    
    # Crear tabla de mantenimientos si no existe
    conn.execute('''
        CREATE TABLE IF NOT EXISTS mantenimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER,
            tipo_mantenimiento TEXT NOT NULL,
            fecha_mantenimiento DATE NOT NULL,
            descripcion TEXT,
            costo REAL,
            tecnico TEXT,
            estado TEXT DEFAULT 'Pendiente',
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (equipo_id) REFERENCES equipos (id)
        )
    ''')
    
    # Crear tabla de repuestos si no existe
    conn.execute('''
        CREATE TABLE IF NOT EXISTS repuestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            codigo TEXT UNIQUE,
            descripcion TEXT,
            stock_actual INTEGER DEFAULT 0,
            stock_minimo INTEGER DEFAULT 0,
            precio_unitario REAL,
            proveedor TEXT,
            ubicacion TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crear tabla de movimientos de repuestos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS movimientos_repuestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repuesto_id INTEGER,
            mantenimiento_id INTEGER,
            tipo_movimiento TEXT NOT NULL, -- 'entrada', 'salida', 'ajuste'
            cantidad INTEGER NOT NULL,
            motivo TEXT,
            fecha_movimiento DATE DEFAULT CURRENT_DATE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (repuesto_id) REFERENCES repuestos (id),
            FOREIGN KEY (mantenimiento_id) REFERENCES mantenimientos (id)
        )
    ''')
    
    # Agregar columna cliente_id a equipos existentes si no existe
    try:
        conn.execute('ALTER TABLE equipos ADD COLUMN cliente_id INTEGER REFERENCES clientes(id)')
    except:
        pass  # La columna ya existe
    
    # Agregar columna estado a mantenimientos existentes si no existe
    try:
        conn.execute('ALTER TABLE mantenimientos ADD COLUMN estado TEXT DEFAULT "Pendiente"')
    except:
        pass  # La columna ya existe
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Página principal que muestra el resumen del taller"""
    conn = get_db_connection()
    
    # Obtener estadísticas
    total_equipos = conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0]
    equipos_activos = conn.execute('SELECT COUNT(*) FROM equipos WHERE estado = "Activo"').fetchone()[0]
    total_mantenimientos = conn.execute('SELECT COUNT(*) FROM mantenimientos').fetchone()[0]
    total_clientes = conn.execute('SELECT COUNT(*) FROM clientes').fetchone()[0]
    
    # Últimos equipos agregados con información del cliente
    equipos_recientes = conn.execute('''
        SELECT e.*, c.nombre as cliente_nombre 
        FROM equipos e
        LEFT JOIN clientes c ON e.cliente_id = c.id
        ORDER BY e.fecha_creacion DESC 
        LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template('index.html', 
                         total_equipos=total_equipos,
                         equipos_activos=equipos_activos,
                         total_mantenimientos=total_mantenimientos,
                         total_clientes=total_clientes,
                         equipos_recientes=equipos_recientes)

@app.route('/equipos')
def equipos():
    """Página para ver todos los equipos con búsqueda y filtros"""
    conn = get_db_connection()
    
    # Obtener parámetros de búsqueda
    busqueda = request.args.get('busqueda', '').strip()
    cliente_id = request.args.get('cliente_id', '')
    estado = request.args.get('estado', '')
    
    # Construir consulta base
    query = '''
        SELECT e.*, c.nombre as cliente_nombre 
        FROM equipos e
        LEFT JOIN clientes c ON e.cliente_id = c.id
        WHERE 1=1
    '''
    params = []
    
    # Agregar filtros
    if busqueda:
        query += ''' AND (
            e.nombre LIKE ? OR 
            e.marca LIKE ? OR 
            e.modelo LIKE ? OR 
            e.numero_serie LIKE ? OR
            c.nombre LIKE ?
        )'''
        busqueda_param = f'%{busqueda}%'
        params.extend([busqueda_param] * 5)
    
    if cliente_id:
        query += ' AND e.cliente_id = ?'
        params.append(cliente_id)
    
    if estado:
        query += ' AND e.estado = ?'
        params.append(estado)
    
    query += ' ORDER BY c.nombre, e.nombre'
    
    equipos = conn.execute(query, params).fetchall()
    
    # Obtener clientes para el filtro
    clientes = conn.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    
    # Obtener estados únicos
    estados = conn.execute('SELECT DISTINCT estado FROM equipos WHERE estado IS NOT NULL ORDER BY estado').fetchall()
    
    conn.close()
    return render_template('equipos.html', 
                         equipos=equipos, 
                         clientes=clientes, 
                         estados=estados,
                         busqueda=busqueda,
                         cliente_id_filtro=cliente_id,
                         estado_filtro=estado)

@app.route('/equipos/nuevo', methods=['GET', 'POST'])
def nuevo_equipo():
    """Página para agregar un nuevo equipo"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        nombre = request.form['nombre']
        marca = request.form['marca']
        modelo = request.form['modelo']
        numero_serie = request.form['numero_serie']
        fecha_compra = request.form['fecha_compra']
        estado = request.form['estado']
        ubicacion = request.form['ubicacion']
        observaciones = request.form['observaciones']
        
        try:
            conn.execute('''
                INSERT INTO equipos (cliente_id, nombre, marca, modelo, numero_serie, fecha_compra, estado, ubicacion, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (cliente_id, nombre, marca, modelo, numero_serie, fecha_compra, estado, ubicacion, observaciones))
            conn.commit()
            
            # Obtener nombre del cliente para el mensaje
            cliente = conn.execute('SELECT nombre FROM clientes WHERE id = ?', (cliente_id,)).fetchone()
            cliente_nombre = cliente['nombre'] if cliente else 'Cliente'
            
            flash(f'Equipo "{nombre}" agregado exitosamente para {cliente_nombre}!', 'success')
            return redirect(url_for('equipos'))
            
        except Exception as e:
            flash(f'Error al agregar equipo: {str(e)}', 'error')
        finally:
            conn.close()
    
    # GET: Mostrar formulario con lista de clientes
    clientes = conn.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    conn.close()
    
    return render_template('nuevo_equipo.html', clientes=clientes)

@app.route('/equipos/<int:id>/eliminar', methods=['POST'])
def eliminar_equipo(id):
    """Eliminar un equipo"""
    conn = get_db_connection()
    
    try:
        # Verificar que el equipo existe y obtener información
        equipo = conn.execute('''
            SELECT e.*, c.nombre as cliente_nombre 
            FROM equipos e 
            JOIN clientes c ON e.cliente_id = c.id 
            WHERE e.id = ?
        ''', (id,)).fetchone()
        
        if not equipo:
            flash('Equipo no encontrado', 'error')
            return redirect(url_for('equipos'))
        
        # Verificar si tiene mantenimientos asociados
        mantenimientos = conn.execute('SELECT COUNT(*) as count FROM mantenimientos WHERE equipo_id = ?', (id,)).fetchone()
        
        if mantenimientos['count'] > 0:
            flash(f'No se puede eliminar el equipo "{equipo["nombre"]}" porque tiene {mantenimientos["count"]} mantenimiento(s) asociado(s). Elimina primero los mantenimientos.', 'error')
            return redirect(url_for('equipos'))
        
        # Eliminar equipo
        conn.execute('DELETE FROM equipos WHERE id = ?', (id,))
        conn.commit()
        
        flash(f'Equipo "{equipo["nombre"]}" de {equipo["cliente_nombre"]} eliminado exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al eliminar equipo: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('equipos'))

@app.route('/equipos/<int:id>/editar', methods=['GET', 'POST'])
def editar_equipo(id):
    """Página para editar un equipo existente"""
    conn = get_db_connection()
    equipo = conn.execute('SELECT * FROM equipos WHERE id = ?', (id,)).fetchone()
    
    if not equipo:
        flash('Equipo no encontrado', 'error')
        return redirect(url_for('equipos'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        marca = request.form['marca']
        modelo = request.form['modelo']
        numero_serie = request.form['numero_serie']
        fecha_compra = request.form['fecha_compra']
        estado = request.form['estado']
        ubicacion = request.form['ubicacion']
        observaciones = request.form['observaciones']
        
        conn.execute('''
            UPDATE equipos 
            SET nombre=?, marca=?, modelo=?, numero_serie=?, fecha_compra=?, estado=?, ubicacion=?, observaciones=?
            WHERE id=?
        ''', (nombre, marca, modelo, numero_serie, fecha_compra, estado, ubicacion, observaciones, id))
        conn.commit()
        conn.close()
        
        flash('Equipo actualizado exitosamente!', 'success')
        return redirect(url_for('equipos'))
    
    conn.close()
    return render_template('editar_equipo.html', equipo=equipo)

@app.route('/importar_excel', methods=['GET', 'POST'])
def importar_excel():
    """Página para importar datos desde Excel"""
    if request.method == 'POST':
        try:
            # Leer todas las hojas del archivo Excel
            excel_file = pd.ExcelFile('Equipos.xlsx')
            
            conn = get_db_connection()
            equipos_importados = 0
            mantenimientos_importados = 0
            clientes_importados = 0
            
            print(f"📊 Procesando {len(excel_file.sheet_names)} hojas del Excel...")
            
            # Procesar cada hoja como un cliente diferente
            for sheet_name in excel_file.sheet_names:
                if sheet_name in ['Hoja5', 'Sheet1']:  # Omitir hojas vacías o genéricas
                    continue
                    
                print(f"\n🔸 Procesando hoja: '{sheet_name}'")
                
                # Leer la hoja específica
                df = pd.read_excel('Equipos.xlsx', sheet_name=sheet_name)
                
                if df.empty:
                    print(f"  ⚠️ Hoja '{sheet_name}' está vacía, omitiendo...")
                    continue
                
                # Crear o encontrar cliente
                cliente_nombre = sheet_name.strip()
                cliente_existente = conn.execute(
                    'SELECT id FROM clientes WHERE nombre = ?', (cliente_nombre,)
                ).fetchone()
                
                if not cliente_existente:
                    cursor = conn.execute('''
                        INSERT INTO clientes (nombre)
                        VALUES (?)
                    ''', (cliente_nombre,))
                    cliente_id = cursor.lastrowid
                    clientes_importados += 1
                    print(f"  ✅ Cliente creado: {cliente_nombre} (ID: {cliente_id})")
                else:
                    cliente_id = cliente_existente[0]
                    print(f"  ✅ Cliente existente: {cliente_nombre} (ID: {cliente_id})")
                
                # Procesar equipos y mantenimientos de esta hoja
                equipos_hoja, mantenimientos_hoja = procesar_hoja_excel(df, cliente_id, conn, sheet_name)
                equipos_importados += equipos_hoja
                mantenimientos_importados += mantenimientos_hoja
            
            conn.commit()
            conn.close()
            
            mensaje = f'Importación exitosa! {clientes_importados} clientes, {equipos_importados} equipos y {mantenimientos_importados} mantenimientos importados.'
            flash(mensaje, 'success')
            return redirect(url_for('equipos'))
            
        except Exception as e:
            flash(f'Error al importar el archivo: {str(e)}', 'error')
    
    return render_template('importar_excel.html')

@app.route('/mantenimientos')
def mantenimientos():
    """Página para ver todos los mantenimientos"""
    conn = get_db_connection()
    mantenimientos = conn.execute('''
        SELECT m.*, e.nombre as equipo_nombre 
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        ORDER BY m.fecha_mantenimiento DESC
    ''').fetchall()
    conn.close()
    return render_template('mantenimientos.html', mantenimientos=mantenimientos)

@app.route('/clientes')
def clientes():
    """Página para ver todos los clientes"""
    conn = get_db_connection()
    clientes = conn.execute('''
        SELECT c.*, 
               COUNT(DISTINCT e.id) as total_equipos,
               COUNT(DISTINCT m.id) as total_mantenimientos
        FROM clientes c
        LEFT JOIN equipos e ON c.id = e.cliente_id
        LEFT JOIN mantenimientos m ON e.id = m.equipo_id
        GROUP BY c.id
        ORDER BY c.nombre
    ''').fetchall()
    conn.close()
    return render_template('clientes.html', clientes=clientes)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    """Página para agregar un nuevo cliente"""
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        direccion = request.form['direccion']
        observaciones = request.form['observaciones']
        
        conn = get_db_connection()
        try:
            # Insertar cliente
            cursor = conn.execute('''
                INSERT INTO clientes (nombre, telefono, email, direccion, observaciones)
                VALUES (?, ?, ?, ?, ?)
            ''', (nombre, telefono, email, direccion, observaciones))
            cliente_id = cursor.lastrowid
            
            # Procesar equipos si existen
            equipos_agregados = 0
            form_data = request.form.to_dict()
            
            # Buscar equipos en el formulario
            equipos_indices = set()
            for key in form_data.keys():
                if key.startswith('equipos[') and '][nombre]' in key:
                    # Extraer índice del equipo
                    indice = key.split('[')[1].split(']')[0]
                    equipos_indices.add(indice)
            
            # Insertar cada equipo
            for indice in equipos_indices:
                equipo_nombre = form_data.get(f'equipos[{indice}][nombre]', '').strip()
                if equipo_nombre:  # Solo procesar si tiene nombre
                    equipo_marca = form_data.get(f'equipos[{indice}][marca]', '')
                    equipo_modelo = form_data.get(f'equipos[{indice}][modelo]', '')
                    equipo_numero_serie = form_data.get(f'equipos[{indice}][numero_serie]', '')
                    equipo_estado = form_data.get(f'equipos[{indice}][estado]', 'Activo')
                    equipo_ubicacion = form_data.get(f'equipos[{indice}][ubicacion]', '')
                    equipo_observaciones = form_data.get(f'equipos[{indice}][observaciones]', '')
                    
                    conn.execute('''
                        INSERT INTO equipos (cliente_id, nombre, marca, modelo, numero_serie, estado, ubicacion, observaciones)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (cliente_id, equipo_nombre, equipo_marca, equipo_modelo, 
                          equipo_numero_serie, equipo_estado, equipo_ubicacion, equipo_observaciones))
                    
                    equipos_agregados += 1
            
            conn.commit()
            
            # Mensaje de confirmación
            if equipos_agregados > 0:
                flash(f'Cliente "{nombre}" creado exitosamente con {equipos_agregados} equipo(s)!', 'success')
            else:
                flash(f'Cliente "{nombre}" creado exitosamente!', 'success')
            
            return redirect(url_for('clientes'))
            
        except sqlite3.IntegrityError:
            flash('Ya existe un cliente con ese nombre', 'error')
        except Exception as e:
            flash(f'Error al crear cliente: {str(e)}', 'error')
        finally:
            conn.close()
    
    return render_template('nuevo_cliente.html')

@app.route('/clientes/<int:id>/eliminar', methods=['POST'])
def eliminar_cliente(id):
    """Eliminar un cliente"""
    conn = get_db_connection()
    
    try:
        # Verificar que el cliente existe
        cliente = conn.execute('SELECT * FROM clientes WHERE id = ?', (id,)).fetchone()
        if not cliente:
            flash('Cliente no encontrado', 'error')
            return redirect(url_for('clientes'))
        
        # Verificar si tiene equipos asociados
        equipos = conn.execute('SELECT COUNT(*) as count FROM equipos WHERE cliente_id = ?', (id,)).fetchone()
        
        if equipos['count'] > 0:
            flash(f'No se puede eliminar el cliente "{cliente["nombre"]}" porque tiene {equipos["count"]} equipo(s) asociado(s). Elimina primero los equipos.', 'error')
            return redirect(url_for('clientes'))
        
        # Eliminar cliente
        conn.execute('DELETE FROM clientes WHERE id = ?', (id,))
        conn.commit()
        
        flash(f'Cliente "{cliente["nombre"]}" eliminado exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al eliminar cliente: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('clientes'))

@app.route('/clientes/<int:id>')
def ver_cliente(id):
    """Página para ver detalles de un cliente específico"""
    conn = get_db_connection()
    cliente = conn.execute('SELECT * FROM clientes WHERE id = ?', (id,)).fetchone()
    
    if not cliente:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('clientes'))
    
    # Obtener equipos del cliente
    equipos = conn.execute('''
        SELECT * FROM equipos WHERE cliente_id = ? ORDER BY nombre
    ''', (id,)).fetchall()
    
    # Obtener mantenimientos del cliente
    mantenimientos = conn.execute('''
        SELECT m.*, e.nombre as equipo_nombre 
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        WHERE e.cliente_id = ?
        ORDER BY m.fecha_mantenimiento DESC
        LIMIT 10
    ''', (id,)).fetchall()
    
    conn.close()
    return render_template('ver_cliente.html', cliente=cliente, equipos=equipos, mantenimientos=mantenimientos)

@app.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
def editar_cliente(id):
    """Página para editar un cliente existente"""
    conn = get_db_connection()
    cliente = conn.execute('SELECT * FROM clientes WHERE id = ?', (id,)).fetchone()
    
    if not cliente:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('clientes'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        direccion = request.form['direccion']
        observaciones = request.form['observaciones']
        
        try:
            conn.execute('''
                UPDATE clientes 
                SET nombre=?, telefono=?, email=?, direccion=?, observaciones=?
                WHERE id=?
            ''', (nombre, telefono, email, direccion, observaciones, id))
            conn.commit()
            conn.close()
            
            flash('Cliente actualizado exitosamente!', 'success')
            return redirect(url_for('ver_cliente', id=id))
        except sqlite3.IntegrityError:
            flash('Ya existe un cliente con ese nombre', 'error')
    
    conn.close()
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/reiniciar_app', methods=['GET', 'POST'])
def reiniciar_app():
    """Página para reiniciar la aplicación y limpiar todos los datos"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            
            # Contar registros antes de borrar
            equipos_count = conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0]
            mantenimientos_count = conn.execute('SELECT COUNT(*) FROM mantenimientos').fetchone()[0]
            
            # Limpiar todas las tablas de equipos y mantenimientos
            conn.execute('DELETE FROM mantenimientos')
            conn.execute('DELETE FROM equipos')
            
            # Reiniciar los auto-increment
            conn.execute('DELETE FROM sqlite_sequence WHERE name="equipos"')
            conn.execute('DELETE FROM sqlite_sequence WHERE name="mantenimientos"')
            
            conn.commit()
            conn.close()
            
            flash(f'Aplicación reiniciada exitosamente! Se eliminaron {equipos_count} equipos y {mantenimientos_count} mantenimientos.', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f'Error al reiniciar la aplicación: {str(e)}', 'error')
    
    # Obtener estadísticas actuales
    conn = get_db_connection()
    total_equipos = conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0]
    total_mantenimientos = conn.execute('SELECT COUNT(*) FROM mantenimientos').fetchone()[0]
    conn.close()
    
    return render_template('reiniciar_app.html', 
                         total_equipos=total_equipos,
                         total_mantenimientos=total_mantenimientos)

@app.route('/mantenimientos/nuevo', methods=['GET', 'POST'])
def nuevo_mantenimiento():
    """Página para agregar un nuevo mantenimiento"""
    conn = get_db_connection()
    equipos = conn.execute('SELECT id, nombre FROM equipos WHERE estado = "Activo" ORDER BY nombre').fetchall()
    
    if request.method == 'POST':
        equipo_id = request.form['equipo_id']
        tipo_mantenimiento = request.form['tipo_mantenimiento']
        fecha_mantenimiento = request.form['fecha_mantenimiento']
        descripcion = request.form['descripcion']
        costo = request.form['costo'] or None
        tecnico = request.form['tecnico']
        
        conn.execute('''
            INSERT INTO mantenimientos (equipo_id, tipo_mantenimiento, fecha_mantenimiento, descripcion, costo, tecnico)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (equipo_id, tipo_mantenimiento, fecha_mantenimiento, descripcion, costo, tecnico))
        conn.commit()
        conn.close()
        
        flash('Mantenimiento registrado exitosamente!', 'success')
        return redirect(url_for('mantenimientos'))
    
    conn.close()
    return render_template('nuevo_mantenimiento.html', equipos=equipos)

@app.route('/reportes')
def reportes():
    """Página de reportes y estadísticas avanzadas con filtros"""
    # Obtener parámetros de filtro de la URL
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    periodo = request.args.get('periodo', 'mes')  # 'dia', 'semana', 'mes', 'año'
    cliente_id = request.args.get('cliente_id', '')
    
    conn = get_db_connection()
    
    # Construir condiciones WHERE para filtros
    where_conditions = []
    params = []
    
    if fecha_inicio:
        where_conditions.append("m.fecha_mantenimiento >= ?")
        params.append(fecha_inicio)
    
    if fecha_fin:
        where_conditions.append("m.fecha_mantenimiento <= ?")
        params.append(fecha_fin)
    
    if cliente_id:
        where_conditions.append("c.id = ?")
        params.append(cliente_id)
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Estadísticas generales (algunas filtradas, otras generales)
    stats = {
        'total_clientes': conn.execute('SELECT COUNT(*) FROM clientes').fetchone()[0],
        'total_equipos': conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0],
        'equipos_activos': conn.execute('SELECT COUNT(*) FROM equipos WHERE estado = "Activo"').fetchone()[0],
    }
    
    # Total de mantenimientos (filtrado)
    query_total = f'''
        SELECT COUNT(*) 
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN clientes c ON e.cliente_id = c.id
        {where_clause}
    '''
    stats['total_mantenimientos'] = conn.execute(query_total, params).fetchone()[0]
    
    # Mantenimientos del mes actual (no filtrado para comparación)
    stats['mantenimientos_mes'] = conn.execute('''
        SELECT COUNT(*) FROM mantenimientos 
        WHERE fecha_mantenimiento >= date('now', 'start of month')
    ''').fetchone()[0]
    
    # Determinar formato de agrupación según el período
    if periodo == 'dia':
        format_periodo = '%Y-%m-%d'
        limite = 30
        titulo_periodo = 'Días'
    elif periodo == 'semana':
        format_periodo = '%Y-W%W'
        limite = 26
        titulo_periodo = 'Semanas'
    elif periodo == 'año':
        format_periodo = '%Y'
        limite = 10
        titulo_periodo = 'Años'
    else:  # mes por defecto
        format_periodo = '%Y-%m'
        limite = 12
        titulo_periodo = 'Meses'
    
    # Mantenimientos por período (filtrado)
    query_periodo = f'''
        SELECT 
            strftime('{format_periodo}', m.fecha_mantenimiento) as periodo,
            COUNT(*) as total
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN clientes c ON e.cliente_id = c.id
        {where_clause}
        GROUP BY strftime('{format_periodo}', m.fecha_mantenimiento)
        ORDER BY periodo DESC
        LIMIT {limite}
    '''
    mantenimientos_por_periodo = conn.execute(query_periodo, params).fetchall()
    
    # Equipos por cliente con mantenimientos en el período
    if where_conditions:
        equipos_query = f'''
            SELECT c.nombre, COUNT(DISTINCT e.id) as total_equipos,
                   COUNT(m.id) as mantenimientos_periodo
            FROM clientes c
            LEFT JOIN equipos e ON c.id = e.cliente_id
            LEFT JOIN mantenimientos m ON e.id = m.equipo_id
            {where_clause}
            GROUP BY c.id, c.nombre
            HAVING COUNT(m.id) > 0
            ORDER BY mantenimientos_periodo DESC, total_equipos DESC
            LIMIT 10
        '''
        equipos_por_cliente = conn.execute(equipos_query, params).fetchall()
    else:
        equipos_por_cliente = conn.execute('''
            SELECT c.nombre, COUNT(e.id) as total_equipos,
                   COUNT(m.id) as mantenimientos_periodo
            FROM clientes c
            LEFT JOIN equipos e ON c.id = e.cliente_id
            LEFT JOIN mantenimientos m ON e.id = m.equipo_id
            GROUP BY c.id, c.nombre
            ORDER BY total_equipos DESC
            LIMIT 10
        ''').fetchall()
    
    # Tipos de mantenimiento (filtrados)
    query_tipos = f'''
        SELECT m.tipo_mantenimiento, COUNT(*) as total
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN clientes c ON e.cliente_id = c.id
        {where_clause}
        GROUP BY m.tipo_mantenimiento
        ORDER BY total DESC
    '''
    tipos_mantenimiento = conn.execute(query_tipos, params).fetchall()
    
    # Estados de equipos (general, no filtrado)
    estados_equipos = conn.execute('''
        SELECT estado, COUNT(*) as total
        FROM equipos
        GROUP BY estado
        ORDER BY total DESC
    ''').fetchall()
    
    # Análisis de actividad por día de la semana (filtrado)
    query_actividad_semana = f'''
        SELECT 
            CASE strftime('%w', m.fecha_mantenimiento)
                WHEN '0' THEN 'Domingo'
                WHEN '1' THEN 'Lunes'
                WHEN '2' THEN 'Martes'
                WHEN '3' THEN 'Miércoles'
                WHEN '4' THEN 'Jueves'
                WHEN '5' THEN 'Viernes'
                WHEN '6' THEN 'Sábado'
            END as dia_semana,
            COUNT(*) as total
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN clientes c ON e.cliente_id = c.id
        {where_clause}
        GROUP BY strftime('%w', m.fecha_mantenimiento)
        ORDER BY strftime('%w', m.fecha_mantenimiento)
    '''
    actividad_por_dia = conn.execute(query_actividad_semana, params).fetchall()
    
    # Clientes más activos (filtrados)
    query_clientes_activos = f'''
        SELECT c.nombre, COUNT(m.id) as total_mantenimientos,
               COUNT(DISTINCT e.id) as equipos
        FROM clientes c
        LEFT JOIN equipos e ON c.id = e.cliente_id
        LEFT JOIN mantenimientos m ON e.id = m.equipo_id
        {where_clause}
        GROUP BY c.id, c.nombre
        HAVING COUNT(m.id) > 0
        ORDER BY total_mantenimientos DESC
        LIMIT 10
    '''
    clientes_activos = conn.execute(query_clientes_activos, params).fetchall()
    
    # Mantenimientos recientes (filtrados)
    query_recientes = f'''
        SELECT m.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN clientes c ON e.cliente_id = c.id
        {where_clause}
        ORDER BY m.fecha_mantenimiento DESC
        LIMIT 15
    '''
    mantenimientos_recientes = conn.execute(query_recientes, params).fetchall()
    
    # Lista de clientes para el filtro
    clientes_lista = conn.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    
    conn.close()
    
    # Determinar el template a usar según la ruta
    template_name = 'reportes_avanzados.html' if 'avanzados' in request.endpoint else 'reportes.html'
    
    return render_template(template_name,
                         stats=stats,
                         equipos_por_cliente=equipos_por_cliente,
                         mantenimientos_por_periodo=mantenimientos_por_periodo,
                         tipos_mantenimiento=tipos_mantenimiento,
                         estados_equipos=estados_equipos,
                         clientes_activos=clientes_activos,
                         mantenimientos_recientes=mantenimientos_recientes,
                         actividad_por_dia=actividad_por_dia,
                         clientes_lista=clientes_lista,
                         # Parámetros de filtro y configuración
                         fecha_inicio=fecha_inicio,
                         fecha_fin=fecha_fin,
                         periodo=periodo,
                         cliente_id=cliente_id,
                         titulo_periodo=titulo_periodo)

@app.route('/reportes/avanzados')
def reportes_avanzados():
    """Página de reportes avanzados con filtros dinámicos"""
    # Reutilizar la misma lógica que reportes() pero con template diferente
    return reportes()

@app.route('/api/stats')
def api_stats():
    """API endpoint para obtener estadísticas en tiempo real"""
    conn = get_db_connection()
    equipos = conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0]
    mantenimientos = conn.execute('SELECT COUNT(*) FROM mantenimientos').fetchone()[0]
    conn.close()
    
    return jsonify({
        'equipos': equipos,
        'mantenimientos': mantenimientos
    })

@app.route('/repuestos')
def repuestos():
    """Página para ver todos los repuestos"""
    conn = get_db_connection()
    repuestos = conn.execute('''
        SELECT * FROM repuestos 
        ORDER BY nombre
    ''').fetchall()
    
    # Calcular alertas de stock bajo
    alertas_stock = conn.execute('''
        SELECT * FROM repuestos 
        WHERE stock_actual <= stock_minimo AND stock_minimo > 0
        ORDER BY (stock_actual - stock_minimo) ASC
    ''').fetchall()
    
    # Calcular valor total del inventario (cantidad × precio)
    valor_total_inventario = 0
    for repuesto in repuestos:
        if repuesto['precio_unitario'] and repuesto['stock_actual']:
            valor_total_inventario += repuesto['stock_actual'] * repuesto['precio_unitario']
    
    conn.close()
    return render_template('repuestos.html', 
                         repuestos=repuestos, 
                         alertas_stock=alertas_stock,
                         valor_total_inventario=valor_total_inventario)

@app.route('/repuestos/nuevo', methods=['GET', 'POST'])
def nuevo_repuesto():
    """Página para agregar un nuevo repuesto"""
    if request.method == 'POST':
        nombre = request.form['nombre']
        codigo = request.form['codigo'] or None
        descripcion = request.form['descripcion']
        stock_actual = int(request.form['stock_actual']) if request.form['stock_actual'] else 0
        stock_minimo = int(request.form['stock_minimo']) if request.form['stock_minimo'] else 0
        precio_unitario = float(request.form['precio_unitario']) if request.form['precio_unitario'] else None
        proveedor = request.form['proveedor']
        ubicacion = request.form['ubicacion']
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO repuestos (nombre, codigo, descripcion, stock_actual, stock_minimo, precio_unitario, proveedor, ubicacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, codigo, descripcion, stock_actual, stock_minimo, precio_unitario, proveedor, ubicacion))
            conn.commit()
            conn.close()
            
            flash('Repuesto agregado exitosamente!', 'success')
            return redirect(url_for('repuestos'))
        except sqlite3.IntegrityError:
            flash('Ya existe un repuesto con ese código', 'error')
            conn.close()
    
    return render_template('nuevo_repuesto.html')

@app.route('/repuestos/<int:id>/editar', methods=['GET', 'POST'])
def editar_repuesto(id):
    """Página para editar un repuesto existente"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        codigo = request.form['codigo'] or None
        descripcion = request.form['descripcion']
        stock_actual = int(request.form['stock_actual']) if request.form['stock_actual'] else 0
        stock_minimo = int(request.form['stock_minimo']) if request.form['stock_minimo'] else 0
        precio_unitario = float(request.form['precio_unitario']) if request.form['precio_unitario'] else None
        proveedor = request.form['proveedor']
        ubicacion = request.form['ubicacion']
        
        try:
            conn.execute('''
                UPDATE repuestos 
                SET nombre = ?, codigo = ?, descripcion = ?, stock_actual = ?, 
                    stock_minimo = ?, precio_unitario = ?, proveedor = ?, ubicacion = ?
                WHERE id = ?
            ''', (nombre, codigo, descripcion, stock_actual, stock_minimo, precio_unitario, proveedor, ubicacion, id))
            conn.commit()
            conn.close()
            flash('Repuesto actualizado exitosamente!', 'success')
            return redirect(url_for('repuestos'))
        except sqlite3.IntegrityError:
            flash('Ya existe un repuesto con ese código', 'error')
            conn.close()
    
    # GET - mostrar formulario de edición
    repuesto = conn.execute('SELECT * FROM repuestos WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if not repuesto:
        flash('Repuesto no encontrado', 'error')
        return redirect(url_for('repuestos'))
    
    return render_template('editar_repuesto.html', repuesto=repuesto)

@app.route('/repuestos/<int:id>/ajustar_stock', methods=['POST'])
def ajustar_stock(id):
    """Ruta para ajustar rápidamente el stock de un repuesto"""
    nuevo_stock = int(request.form.get('nuevo_stock', 0))
    motivo = request.form.get('motivo', 'Ajuste manual')
    
    conn = get_db_connection()
    try:
        # Obtener stock actual
        repuesto = conn.execute('SELECT stock_actual, nombre FROM repuestos WHERE id = ?', (id,)).fetchone()
        if not repuesto:
            flash('Repuesto no encontrado', 'error')
            return redirect(url_for('repuestos'))
        
        stock_anterior = repuesto['stock_actual']
        diferencia = nuevo_stock - stock_anterior
        
        # Actualizar stock
        conn.execute('UPDATE repuestos SET stock_actual = ? WHERE id = ?', (nuevo_stock, id))
        
        # Registrar movimiento
        tipo_movimiento = 'entrada' if diferencia > 0 else 'salida' if diferencia < 0 else 'ajuste'
        conn.execute('''
            INSERT INTO movimientos_repuestos (repuesto_id, tipo_movimiento, cantidad, motivo)
            VALUES (?, ?, ?, ?)
        ''', (id, tipo_movimiento, abs(diferencia), motivo))
        
        conn.commit()
        flash(f'Stock actualizado: {repuesto["nombre"]} ({stock_anterior} → {nuevo_stock})', 'success')
    except Exception as e:
        flash(f'Error al ajustar stock: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('repuestos'))

@app.route('/repuestos/<int:id>/eliminar', methods=['POST'])
def eliminar_repuesto(id):
    """Eliminar un repuesto"""
    conn = get_db_connection()
    
    try:
        # Verificar que el repuesto existe
        repuesto = conn.execute('SELECT * FROM repuestos WHERE id = ?', (id,)).fetchone()
        if not repuesto:
            flash('Repuesto no encontrado', 'error')
            return redirect(url_for('repuestos'))
        
        # Verificar si tiene movimientos asociados
        movimientos = conn.execute('SELECT COUNT(*) as count FROM movimientos_repuestos WHERE repuesto_id = ?', (id,)).fetchone()
        
        if movimientos['count'] > 0:
            flash(f'No se puede eliminar el repuesto "{repuesto["nombre"]}" porque tiene {movimientos["count"]} movimiento(s) de stock asociado(s). Los repuestos con historial no pueden eliminarse por trazabilidad.', 'error')
            return redirect(url_for('repuestos'))
        
        # Verificar si tiene stock actual
        if repuesto['stock_actual'] > 0:
            flash(f'No se puede eliminar el repuesto "{repuesto["nombre"]}" porque tiene stock actual de {repuesto["stock_actual"]} unidades. Ajusta el stock a 0 primero.', 'error')
            return redirect(url_for('repuestos'))
        
        # Eliminar repuesto
        conn.execute('DELETE FROM repuestos WHERE id = ?', (id,))
        conn.commit()
        
        flash(f'Repuesto "{repuesto["nombre"]}" eliminado exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al eliminar repuesto: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('repuestos'))

@app.route('/informes/repuestos')
def informe_repuestos():
    """Informe de análisis de repuestos utilizados con filtros avanzados"""
    # Obtener parámetros de filtro
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    cliente_id = request.args.get('cliente_id', '')
    mostrar_detalles = request.args.get('detalles', '0') == '1'
    
    conn = get_db_connection()
    
    # Construir condiciones WHERE para filtros
    where_conditions = []
    params = []
    
    if fecha_inicio:
        where_conditions.append("m.fecha_mantenimiento >= ?")
        params.append(fecha_inicio)
    
    if fecha_fin:
        where_conditions.append("m.fecha_mantenimiento <= ?")
        params.append(fecha_fin)
    
    if cliente_id:
        where_conditions.append("c.id = ?")
        params.append(cliente_id)
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    if where_clause:
        where_clause += " AND m.descripcion IS NOT NULL"
    else:
        where_clause = "WHERE m.descripcion IS NOT NULL"
    
    # Extraer repuestos de las descripciones de mantenimientos
    query = f'''
        SELECT m.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN clientes c ON e.cliente_id = c.id
        {where_clause}
        ORDER BY m.fecha_mantenimiento DESC
    '''
    mantenimientos = conn.execute(query, params).fetchall()
    
    # Análisis inteligente de repuestos mencionados
    repuestos_mencionados = {}
    palabras_clave_repuestos = [
        'filtro', 'aceite', 'kit', 'reparacion', 'reparación', 'cilindro', 'manguera', 
        'valvula', 'válvula', 'bomba', 'motor', 'cable', 'tornillo', 'junta', 
        'sello', 'retén', 'bujes', 'buje', 'terminal', 'terminales', 'caño', 'caños',
        'hidráulico', 'hidraulico', 'neumático', 'neumatico', 'eléctrico', 'electrico',
        'mecánico', 'mecanico', 'grasa', 'lubricante', 'rodamiento', 'cojinete',
        'correa', 'cadena', 'piñón', 'engranaje', 'resorte', 'muelle', 'batería',
        'bateria', 'foco', 'bombilla', 'lámpara', 'interruptor', 'relé', 'rele',
        'tubo', 'tuerca', 'perno', 'arandela', 'empaque', 'gasket', 'compresor',
        'radiador', 'ventilador', 'alternador', 'starter', 'arranque'
    ]
    
    # Análisis por período (mensual)
    repuestos_por_mes = {}
    
    trabajos_mano_obra = {}
    palabras_clave_trabajo = [
        'reparar', 'reparación', 'desarmar', 'armar', 'montar', 'desmontar',
        'instalar', 'instalación', 'reemplazar', 'cambiar', 'ajustar', 'calibrar',
        'limpiar', 'service', 'mantenimiento', 'revisar', 'revisión', 'soldar',
        'pintar', 'lubricar', 'alinear', 'regular', 'construir', 'fabricar'
    ]
    
    for mantenimiento in mantenimientos:
        descripcion = mantenimiento['descripcion'].lower() if mantenimiento['descripcion'] else ""
        mes = mantenimiento['fecha_mantenimiento'][:7]  # YYYY-MM
        
        # Buscar menciones de repuestos
        for palabra in palabras_clave_repuestos:
            if palabra in descripcion:
                # Análisis general
                if palabra not in repuestos_mencionados:
                    repuestos_mencionados[palabra] = {
                        'frecuencia': 0,
                        'clientes': set(),
                        'equipos': set(),
                        'fechas': [],
                        'mantenimientos': []
                    }
                
                repuestos_mencionados[palabra]['frecuencia'] += 1
                repuestos_mencionados[palabra]['clientes'].add(mantenimiento['cliente_nombre'])
                repuestos_mencionados[palabra]['equipos'].add(mantenimiento['equipo_nombre'])
                repuestos_mencionados[palabra]['fechas'].append(mantenimiento['fecha_mantenimiento'])
                
                if mostrar_detalles:
                    desc_corta = mantenimiento['descripcion'][:100] + '...' if len(mantenimiento['descripcion']) > 100 else mantenimiento['descripcion']
                    repuestos_mencionados[palabra]['mantenimientos'].append({
                        'id': mantenimiento['id'],
                        'fecha': mantenimiento['fecha_mantenimiento'],
                        'cliente': mantenimiento['cliente_nombre'],
                        'equipo': mantenimiento['equipo_nombre'],
                        'descripcion': desc_corta
                    })
                
                # Análisis por mes
                if mes not in repuestos_por_mes:
                    repuestos_por_mes[mes] = {}
                if palabra not in repuestos_por_mes[mes]:
                    repuestos_por_mes[mes][palabra] = 0
                repuestos_por_mes[mes][palabra] += 1
        
        # Buscar trabajos de mano de obra
        for palabra in palabras_clave_trabajo:
            if palabra in descripcion:
                if palabra not in trabajos_mano_obra:
                    trabajos_mano_obra[palabra] = {
                        'count': 0,
                        'clientes': set(),
                        'equipos': set(),
                        'fechas': []
                    }
                trabajos_mano_obra[palabra]['count'] += 1
                trabajos_mano_obra[palabra]['clientes'].add(mantenimiento['cliente_nombre'])
                trabajos_mano_obra[palabra]['equipos'].add(mantenimiento['equipo_nombre'])
                trabajos_mano_obra[palabra]['fechas'].append(mantenimiento['fecha_mantenimiento'])
    
    # Convertir sets a listas para el template
    for repuesto in repuestos_mencionados.values():
        repuesto['clientes'] = list(repuesto['clientes'])
        repuesto['equipos'] = list(repuesto['equipos'])
        repuesto['fechas'] = sorted(repuesto['fechas'], reverse=True)
        repuesto['clientes_count'] = len(repuesto['clientes'])
        repuesto['equipos_count'] = len(repuesto['equipos'])
    
    for trabajo in trabajos_mano_obra.values():
        trabajo['clientes'] = list(trabajo['clientes'])
        trabajo['equipos'] = list(trabajo['equipos'])
        trabajo['fechas'] = sorted(trabajo['fechas'], reverse=True)
    
    # Ordenar por frecuencia
    repuestos_mencionados = dict(sorted(repuestos_mencionados.items(), 
                                      key=lambda x: x[1]['frecuencia'], reverse=True))
    
    # Análisis por cliente
    repuestos_por_cliente = {}
    trabajos_por_cliente = {}
    
    for mant in mantenimientos:
        cliente = mant['cliente_nombre']
        if cliente not in repuestos_por_cliente:
            repuestos_por_cliente[cliente] = {'total': 0, 'tipos': set()}
            trabajos_por_cliente[cliente] = {'total': 0, 'tipos': set()}
        
        descripcion = mant['descripcion'].lower() if mant['descripcion'] else ""
        
        for palabra in palabras_clave_repuestos:
            if palabra in descripcion:
                repuestos_por_cliente[cliente]['total'] += 1
                repuestos_por_cliente[cliente]['tipos'].add(palabra)
        
        for palabra in palabras_clave_trabajo:
            if palabra in descripcion:
                trabajos_por_cliente[cliente]['total'] += 1
                trabajos_por_cliente[cliente]['tipos'].add(palabra)
    
    # Convertir sets a números
    for cliente_data in repuestos_por_cliente.values():
        cliente_data['tipos_count'] = len(cliente_data['tipos'])
        cliente_data['tipos'] = list(cliente_data['tipos'])
    
    for cliente_data in trabajos_por_cliente.values():
        cliente_data['tipos_count'] = len(cliente_data['tipos'])
        cliente_data['tipos'] = list(cliente_data['tipos'])
    
    # Repuestos más utilizados (top 10)
    top_repuestos = dict(list(repuestos_mencionados.items())[:10])
    
    # Preparar datos para gráfico por mes
    meses_ordenados = sorted(repuestos_por_mes.keys())
    
    # Lista de clientes para filtro
    clientes_lista = conn.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    
    # Estadísticas generales
    stats = {
        'total_mantenimientos': len(mantenimientos),
        'repuestos_diferentes': len(repuestos_mencionados),
        'clientes_afectados': len(set(m['cliente_nombre'] for m in mantenimientos)),
        'equipos_con_repuestos': len(set(m['equipo_nombre'] for m in mantenimientos))
    }
    
    conn.close()
    
    # Adaptar estructura de datos para la plantilla simple
    repuestos_ordenados = []
    for repuesto, data in repuestos_mencionados.items():
        repuestos_ordenados.append((repuesto, {
            'count': data['frecuencia'],
            'clientes': list(data['clientes']),
            'equipos': list(data['equipos'])
        }))
    
    trabajos_ordenados = []
    for trabajo, data in trabajos_mano_obra.items():
        trabajos_ordenados.append((trabajo, {
            'count': data['count'],
            'clientes': list(data['clientes']),
            'equipos': list(data['equipos'])
        }))
    
    return render_template('informe_repuestos.html',
                         total_mantenimientos=len(mantenimientos),
                         repuestos_ordenados=repuestos_ordenados,
                         trabajos_ordenados=trabajos_ordenados,
                         repuestos_por_cliente=repuestos_por_cliente,
                         trabajos_por_cliente=trabajos_por_cliente)

@app.route('/informes/mano_obra')
def informe_mano_obra():
    """Informe detallado de mano de obra por cliente y tipo con filtros"""
    # Obtener parámetros de filtro
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    cliente_id = request.args.get('cliente_id', '')
    mostrar_detalles = request.args.get('detalles', '0') == '1'
    
    conn = get_db_connection()
    
    # Construir condiciones WHERE para filtros
    where_conditions = []
    params = []
    
    if fecha_inicio:
        where_conditions.append("m.fecha_mantenimiento >= ?")
        params.append(fecha_inicio)
    
    if fecha_fin:
        where_conditions.append("m.fecha_mantenimiento <= ?")
        params.append(fecha_fin)
    
    if cliente_id:
        where_conditions.append("c.id = ?")
        params.append(cliente_id)
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    if where_clause:
        where_clause += " AND m.descripcion IS NOT NULL"
    else:
        where_clause = "WHERE m.descripcion IS NOT NULL"
    
    # Obtener mantenimientos con análisis de complejidad (con filtros)
    query = f'''
        SELECT m.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN clientes c ON e.cliente_id = c.id
        {where_clause}
        ORDER BY m.fecha_mantenimiento DESC
    '''
    mantenimientos = conn.execute(query, params).fetchall()
    
    # Análisis de complejidad de trabajos
    trabajos_complejos = ['desarmar', 'reparación', 'construccion', 'fabricar', 'soldar']
    trabajos_medios = ['instalar', 'reemplazar', 'ajustar', 'calibrar', 'alinear']
    trabajos_simples = ['limpiar', 'lubricar', 'revisar', 'service']
    
    analisis_por_cliente = {}
    
    for mant in mantenimientos:
        cliente = mant['cliente_nombre']
        if cliente not in analisis_por_cliente:
            analisis_por_cliente[cliente] = {
                'total_trabajos': 0,
                'complejos': 0,
                'medios': 0,
                'simples': 0,
                'equipos_atendidos': set(),
                'tipos_trabajo': {},
                'trabajos_detalle': []
            }
        
        descripcion = mant['descripcion'].lower() if mant['descripcion'] else ""
        complejidad = 'simple'
        
        # Determinar complejidad
        if any(palabra in descripcion for palabra in trabajos_complejos):
            complejidad = 'complejo'
            analisis_por_cliente[cliente]['complejos'] += 1
        elif any(palabra in descripcion for palabra in trabajos_medios):
            complejidad = 'medio'
            analisis_por_cliente[cliente]['medios'] += 1
        else:
            analisis_por_cliente[cliente]['simples'] += 1
        
        analisis_por_cliente[cliente]['total_trabajos'] += 1
        analisis_por_cliente[cliente]['equipos_atendidos'].add(mant['equipo_nombre'])
        
        # Categorizar tipo de trabajo
        if 'hidraulic' in descripcion or 'cilindro' in descripcion:
            tipo = 'Hidráulico'
        elif 'electr' in descripcion or 'motor' in descripcion:
            tipo = 'Eléctrico'
        elif 'mecan' in descripcion or 'engranaje' in descripcion:
            tipo = 'Mecánico'
        elif 'service' in descripcion or 'mantenimiento' in descripcion:
            tipo = 'Mantenimiento'
        else:
            tipo = 'General'
        
        if tipo not in analisis_por_cliente[cliente]['tipos_trabajo']:
            analisis_por_cliente[cliente]['tipos_trabajo'][tipo] = 0
        analisis_por_cliente[cliente]['tipos_trabajo'][tipo] += 1
        
        # Agregar detalle del trabajo (solo si se requieren detalles)
        if mostrar_detalles:
            analisis_por_cliente[cliente]['trabajos_detalle'].append({
                'fecha': mant['fecha_mantenimiento'],
                'equipo': mant['equipo_nombre'],
                'descripcion': mant['descripcion'][:100] + '...' if len(mant['descripcion']) > 100 else mant['descripcion'],
                'complejidad': complejidad,
                'tipo': tipo
            })
    
    # Convertir sets y ordenar
    for cliente_data in analisis_por_cliente.values():
        cliente_data['equipos_count'] = len(cliente_data['equipos_atendidos'])
        cliente_data['equipos_atendidos'] = list(cliente_data['equipos_atendidos'])
        if mostrar_detalles and 'trabajos_detalle' in cliente_data:
            cliente_data['trabajos_detalle'] = sorted(cliente_data['trabajos_detalle'], 
                                                    key=lambda x: x['fecha'], reverse=True)[:5]  # Últimos 5
    
    # Estadísticas globales
    total_trabajos = sum(data['total_trabajos'] for data in analisis_por_cliente.values())
    total_complejos = sum(data['complejos'] for data in analisis_por_cliente.values())
    total_medios = sum(data['medios'] for data in analisis_por_cliente.values())
    total_simples = sum(data['simples'] for data in analisis_por_cliente.values())
    
    # Análisis global de tipos de trabajo
    tipos_trabajo = {}
    for cliente_data in analisis_por_cliente.values():
        for tipo, cantidad in cliente_data['tipos_trabajo'].items():
            if tipo not in tipos_trabajo:
                tipos_trabajo[tipo] = 0
            tipos_trabajo[tipo] += cantidad
    
    # Lista de clientes para filtro
    clientes_lista = conn.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    
    stats = {
        'total_mantenimientos': len(mantenimientos),
        'total_trabajos': total_trabajos,
        'complejos': total_complejos,
        'medios': total_medios,
        'simples': total_simples,
        'total_complejos': total_complejos,  # Para el gráfico
        'total_medios': total_medios,        # Para el gráfico
        'total_simples': total_simples,      # Para el gráfico
        'porcentaje_complejos': round((total_complejos / total_trabajos * 100) if total_trabajos > 0 else 0, 1),
        'porcentaje_medios': round((total_medios / total_trabajos * 100) if total_trabajos > 0 else 0, 1),
        'porcentaje_simples': round((total_simples / total_trabajos * 100) if total_trabajos > 0 else 0, 1)
    }
    
    conn.close()
    
    return render_template('informe_mano_obra.html',
                         analisis_por_cliente=analisis_por_cliente,
                         estadisticas_globales=stats)

@app.route('/mantenimientos/<int:id>/editar', methods=['GET', 'POST'])
def editar_mantenimiento(id):
    """Editar un mantenimiento existente"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            equipo_id = request.form['equipo_id']
            fecha_mantenimiento = request.form['fecha_mantenimiento']
            tipo_mantenimiento = request.form['tipo_mantenimiento']
            descripcion = request.form['descripcion']
            estado = request.form['estado']
            
            # Actualizar mantenimiento
            conn.execute('''
                UPDATE mantenimientos 
                SET equipo_id = ?, fecha_mantenimiento = ?, tipo_mantenimiento = ?, 
                    descripcion = ?, estado = ?
                WHERE id = ?
            ''', (equipo_id, fecha_mantenimiento, tipo_mantenimiento, descripcion, estado, id))
            
            conn.commit()
            flash('Mantenimiento actualizado exitosamente', 'success')
            return redirect(url_for('mantenimientos'))
            
        except Exception as e:
            flash(f'Error al actualizar mantenimiento: {str(e)}', 'error')
    
    # GET: Mostrar formulario de edición
    mantenimiento = conn.execute('''
        SELECT m.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN clientes c ON e.cliente_id = c.id
        WHERE m.id = ?
    ''', (id,)).fetchone()
    
    if not mantenimiento:
        flash('Mantenimiento no encontrado', 'error')
        return redirect(url_for('mantenimientos'))
    
    # Obtener lista de equipos para el select
    equipos = conn.execute('''
        SELECT e.*, c.nombre as cliente_nombre 
        FROM equipos e 
        JOIN clientes c ON e.cliente_id = c.id 
        ORDER BY c.nombre, e.nombre
    ''').fetchall()
    
    conn.close()
    
    return render_template('editar_mantenimiento.html', 
                         mantenimiento=mantenimiento, 
                         equipos=equipos)

@app.route('/mantenimientos/<int:id>/eliminar', methods=['POST'])
def eliminar_mantenimiento(id):
    """Eliminar un mantenimiento"""
    conn = get_db_connection()
    
    try:
        # Verificar que el mantenimiento existe
        mantenimiento = conn.execute('SELECT * FROM mantenimientos WHERE id = ?', (id,)).fetchone()
        if not mantenimiento:
            flash('Mantenimiento no encontrado', 'error')
            return redirect(url_for('mantenimientos'))
        
        # Eliminar mantenimiento
        conn.execute('DELETE FROM mantenimientos WHERE id = ?', (id,))
        conn.commit()
        
        flash('Mantenimiento eliminado exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al eliminar mantenimiento: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('mantenimientos'))

@app.route('/api/reportes/charts')
def api_reportes_charts():
    """API endpoint para datos de gráficos"""
    conn = get_db_connection()
    
    # Datos para gráfico de mantenimientos por mes
    mantenimientos_chart = conn.execute('''
        SELECT 
            strftime('%Y-%m', fecha_mantenimiento) as mes,
            COUNT(*) as total
        FROM mantenimientos
        WHERE fecha_mantenimiento >= date('now', '-6 months')
        GROUP BY strftime('%Y-%m', fecha_mantenimiento)
        ORDER BY mes ASC
    ''').fetchall()
    
    # Datos para gráfico de equipos por estado
    estados_chart = conn.execute('''
        SELECT estado, COUNT(*) as total
        FROM equipos
        GROUP BY estado
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'mantenimientos_por_mes': [dict(row) for row in mantenimientos_chart],
        'equipos_por_estado': [dict(row) for row in estados_chart]
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
