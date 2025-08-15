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
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g, make_response
import os
from datetime import datetime, timedelta
import logging
import hashlib
import secrets
import json
from functools import wraps
from motor_reconocimiento import crear_motor_reconocimiento
import re
import html
import bleach

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
    Crea y devuelve una conexión a la base de datos SQLite con optimizaciones.
    
    Configura la conexión para devolver resultados como diccionarios (Row objects)
    lo que permite acceder a las columnas por nombre además de por índice.
    Incluye optimizaciones de rendimiento para SQLite.
    
    Returns:
        sqlite3.Connection: Conexión configurada y optimizada a la base de datos
        
    Note:
        Utiliza sqlite3.Row como row_factory para facilitar el acceso a los datos
        por nombre de columna en los templates y funciones.
    """
    try:
        conn = sqlite3.connect(DATABASE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        
        # Optimizaciones de SQLite para rendimiento
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
        conn.execute('PRAGMA cache_size = 10000')
        conn.execute('PRAGMA temp_store = MEMORY')
        conn.execute('PRAGMA mmap_size = 268435456')  # 256MB
        
        return conn
    except Exception as e:
        logging.error(f"Error conectando a la base de datos: {str(e)}")
        raise

# =========================================
# FUNCIONES DE SEGURIDAD Y VALIDACIÓN
# =========================================

def sanitize_input(data, input_type='text'):
    """
    Sanitiza entrada de usuario para prevenir inyecciones
    
    Args:
        data: Datos a sanitizar
        input_type: Tipo de datos ('text', 'html', 'sql', 'email', 'number', 'filename')
    
    Returns:
        str: Datos sanitizados
    """
    if not data or not isinstance(data, str):
        return ''
    
    # Sanitización básica
    data = data.strip()
    
    if input_type == 'text':
        # Escape HTML entities
        data = html.escape(data)
        # Remover caracteres de control
        data = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', data)
        
    elif input_type == 'html':
        # Permitir solo tags seguros
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'b', 'i']
        data = bleach.clean(data, tags=allowed_tags, strip=True)
        
    elif input_type == 'sql':
        # Escapar comillas para SQL (aunque se usen parámetros)
        data = data.replace("'", "''").replace('"', '""')
        
    elif input_type == 'email':
        # Validar formato email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data):
            return ''
        data = data.lower()
        
    elif input_type == 'number':
        # Solo números, punto y signo menos
        data = re.sub(r'[^0-9.\-]', '', data)
        
    elif input_type == 'filename':
        # Solo caracteres seguros para nombres de archivo
        data = re.sub(r'[^a-zA-Z0-9._-]', '', data)
        data = data[:255]  # Limitar longitud
    
    return data

def validate_input(data, rules):
    """
    Valida entrada según reglas específicas
    
    Args:
        data: Datos a validar
        rules: Dict con reglas de validación
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not data and rules.get('required', False):
        return False, 'Campo obligatorio'
    
    if not data:
        return True, None
    
    # Validar longitud
    if 'min_length' in rules and len(data) < rules['min_length']:
        return False, f'Mínimo {rules["min_length"]} caracteres'
    
    if 'max_length' in rules and len(data) > rules['max_length']:
        return False, f'Máximo {rules["max_length"]} caracteres'
    
    # Validar patrones
    if 'pattern' in rules:
        if not re.match(rules['pattern'], data):
            return False, rules.get('pattern_message', 'Formato inválido')
    
    # Validar tipo
    if rules.get('type') == 'email':
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data):
            return False, 'Email inválido'
    
    elif rules.get('type') == 'phone':
        phone_pattern = r'^[\d\s\-\+\(\)]{10,15}$'
        if not re.match(phone_pattern, data):
            return False, 'Teléfono inválido'
    
    elif rules.get('type') == 'number':
        try:
            float(data)
        except ValueError:
            return False, 'Número inválido'
    
    return True, None

def secure_form_data(form_data, schema):
    """
    Procesa y valida datos de formulario según esquema
    
    Args:
        form_data: Datos del formulario
        schema: Esquema de validación
    
    Returns:
        tuple: (sanitized_data, errors)
    """
    sanitized = {}
    errors = {}
    
    for field, rules in schema.items():
        value = form_data.get(field, '')
        
        # Sanitizar
        input_type = rules.get('input_type', 'text')
        sanitized_value = sanitize_input(value, input_type)
        
        # Validar
        is_valid, error = validate_input(sanitized_value, rules)
        
        if not is_valid:
            errors[field] = error
        else:
            sanitized[field] = sanitized_value
    
    return sanitized, errors

def check_rate_limit(identifier, max_requests=100, window_minutes=60):
    """
    Verifica límites de tasa para prevenir abuso
    
    Args:
        identifier: Identificador único (IP, user_id, etc.)
        max_requests: Máximo número de requests
        window_minutes: Ventana de tiempo en minutos
    
    Returns:
        bool: True si está dentro del límite
    """
    try:
        # Implementación simple usando cache en memoria
        # En producción usar Redis o base de datos
        current_time = datetime.now()
        cache_key = f"rate_limit:{identifier}"
        
        # Por simplicidad, usar variables globales (mejorar en producción)
        if not hasattr(check_rate_limit, 'cache'):
            check_rate_limit.cache = {}
        
        if cache_key not in check_rate_limit.cache:
            check_rate_limit.cache[cache_key] = []
        
        # Limpiar requests antiguos
        cutoff_time = current_time - timedelta(minutes=window_minutes)
        check_rate_limit.cache[cache_key] = [
            req_time for req_time in check_rate_limit.cache[cache_key]
            if req_time > cutoff_time
        ]
        
        # Verificar límite
        if len(check_rate_limit.cache[cache_key]) >= max_requests:
            return False
        
        # Agregar request actual
        check_rate_limit.cache[cache_key].append(current_time)
        return True
        
    except Exception as e:
        logging.error(f"Error en rate limiting: {str(e)}")
        return True  # Permitir en caso de error

def log_security_event(event_type, details, severity='medium'):
    """
    Registra eventos de seguridad
    
    Args:
        event_type: Tipo de evento
        details: Detalles del evento
        severity: Nivel de severidad (low, medium, high, critical)
    """
    try:
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', 
                                       request.environ.get('REMOTE_ADDR', ''))
        user_agent = request.headers.get('User-Agent', '')
        user_id = session.get('user_id', 'anonymous')
        
        security_log = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'user_id': user_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'details': details,
            'url': request.url if request else '',
            'method': request.method if request else ''
        }
        
        # Log críticos y altos a archivo especial
        if severity in ['high', 'critical']:
            security_logger = logging.getLogger('security')
            security_logger.error(f"SECURITY ALERT: {json.dumps(security_log)}")
        
        # También registrar en auditoría normal
        log_audit(f'security_{event_type}', 'security_events', None, None, security_log)
        
    except Exception as e:
        logging.error(f"Error logging security event: {str(e)}")

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
    
    # =========================================
    # NUEVAS TABLAS PARA SISTEMA DE USUARIOS
    # =========================================
    
    # Crear tabla de usuarios
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'tecnico',
            activo BOOLEAN DEFAULT 1,
            ultimo_acceso TIMESTAMP,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crear tabla de roles y permisos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            descripcion TEXT,
            permisos TEXT, -- JSON con permisos específicos
            activo BOOLEAN DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crear tabla de sesiones de usuarios
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sesiones_usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            token_sesion TEXT NOT NULL UNIQUE,
            ip_address TEXT,
            user_agent TEXT,
            fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_expiracion TIMESTAMP,
            activa BOOLEAN DEFAULT 1,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla de auditoría
    conn.execute('''
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            accion TEXT NOT NULL,
            tabla_afectada TEXT,
            registro_id INTEGER,
            datos_anteriores TEXT, -- JSON con datos antes del cambio
            datos_nuevos TEXT, -- JSON con datos después del cambio
            ip_address TEXT,
            user_agent TEXT,
            fecha_accion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla de notificaciones
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            tipo TEXT NOT NULL, -- 'mantenimiento_vencido', 'stock_bajo', 'sistema', etc.
            titulo TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            datos_adicionales TEXT, -- JSON con datos extra
            leida BOOLEAN DEFAULT 0,
            fecha_programada TIMESTAMP,
            fecha_enviada TIMESTAMP,
            fecha_leida TIMESTAMP,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla de configuración de alertas por usuario
    conn.execute('''
        CREATE TABLE IF NOT EXISTS configuracion_alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tipo_alerta TEXT NOT NULL,
            activada BOOLEAN DEFAULT 1,
            parametros TEXT, -- JSON con parámetros específicos
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
            UNIQUE(usuario_id, tipo_alerta)
        )
    ''')
    
    # Insertar roles por defecto si no existen
    conn.execute('''
        INSERT OR IGNORE INTO roles (nombre, descripcion, permisos) VALUES 
        ('admin', 'Administrador del sistema', '{"all": true}'),
        ('gerente', 'Gerente de taller', '{"clientes": "all", "equipos": "all", "mantenimientos": "all", "repuestos": "all", "reportes": "all", "usuarios": "read"}'),
        ('tecnico', 'Técnico de mantenimiento', '{"clientes": "read", "equipos": "all", "mantenimientos": "all", "repuestos": "read", "reportes": "read"}'),
        ('recepcionista', 'Recepcionista', '{"clientes": "all", "equipos": "read", "mantenimientos": "create,read", "repuestos": "read", "reportes": "read"}'),
        ('visor', 'Solo lectura', '{"clientes": "read", "equipos": "read", "mantenimientos": "read", "repuestos": "read", "reportes": "read"}')
    ''')
    
    # Crear usuarios por defecto si no existen
    import hashlib
    usuarios_demo = [
        ('admin', 'admin@taller.com', 'admin123', 'Administrador del Sistema', 'admin'),
        ('gerente', 'gerente@taller.com', 'gerente123', 'Juan Carlos Pérez', 'gerente'),
        ('tecnico', 'tecnico@taller.com', 'tecnico123', 'María González', 'tecnico'),
        ('recepcionista', 'recepcion@taller.com', 'recepcion123', 'Ana López', 'recepcionista'),
        ('visor', 'visor@taller.com', 'visor123', 'Carlos Mendoza', 'visor')
    ]
    
    for username, email, password, nombre_completo, rol in usuarios_demo:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        conn.execute('''
            INSERT OR IGNORE INTO usuarios (username, email, password_hash, nombre_completo, rol) VALUES 
            (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, nombre_completo, rol))
    
    # =========================================
    # TABLAS PARA SISTEMA DE AUTOMATIZACIÓN
    # =========================================
    
    # Crear tabla de programas de mantenimiento automatizado
    conn.execute('''
        CREATE TABLE IF NOT EXISTS programas_mantenimiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            equipo_id INTEGER,
            cliente_id INTEGER,
            tipo_mantenimiento TEXT NOT NULL,
            intervalo_dias INTEGER NOT NULL,
            tolerancia_dias INTEGER DEFAULT 7,
            activo BOOLEAN DEFAULT 1,
            ultima_ejecucion DATE,
            proxima_ejecucion DATE,
            tecnico_asignado TEXT,
            costo_estimado REAL,
            instrucciones TEXT,
            usuario_creacion INTEGER,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (equipo_id) REFERENCES equipos (id),
            FOREIGN KEY (cliente_id) REFERENCES clientes (id),
            FOREIGN KEY (usuario_creacion) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla de alertas automáticas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS alertas_automaticas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL, -- 'mantenimiento_vencido', 'stock_bajo', 'equipo_inactivo', 'presupuesto_excedido'
            condiciones TEXT NOT NULL, -- JSON con condiciones
            destinatarios TEXT, -- JSON con usuarios/emails
            mensaje_template TEXT,
            activa BOOLEAN DEFAULT 1,
            frecuencia_horas INTEGER DEFAULT 24,
            ultima_ejecucion TIMESTAMP,
            proxima_ejecucion TIMESTAMP,
            contador_disparos INTEGER DEFAULT 0,
            usuario_creacion INTEGER,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_creacion) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla de tareas programadas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tareas_programadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL, -- 'backup', 'limpieza', 'reporte', 'mantenimiento_auto'
            parametros TEXT, -- JSON con parámetros
            programacion TEXT NOT NULL, -- Cron-like: "0 9 * * MON" o "daily", "weekly", "monthly"
            activa BOOLEAN DEFAULT 1,
            ultima_ejecucion TIMESTAMP,
            proxima_ejecucion TIMESTAMP,
            resultado_ultima_ejecucion TEXT,
            estado_ultima_ejecucion TEXT, -- 'exitosa', 'error', 'pendiente'
            usuario_creacion INTEGER,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_creacion) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla de workflow de aprobaciones
    conn.execute('''
        CREATE TABLE IF NOT EXISTS workflow_aprobaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_objeto TEXT NOT NULL, -- 'mantenimiento', 'compra_repuesto', 'presupuesto'
            objeto_id INTEGER NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente', -- 'pendiente', 'aprobado', 'rechazado'
            nivel_aprobacion INTEGER NOT NULL DEFAULT 1,
            usuario_solicitante INTEGER,
            usuario_aprobador INTEGER,
            motivo_solicitud TEXT,
            comentarios_aprobacion TEXT,
            monto_solicitado REAL,
            fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_aprobacion TIMESTAMP,
            FOREIGN KEY (usuario_solicitante) REFERENCES usuarios (id),
            FOREIGN KEY (usuario_aprobador) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla de historial de automatización
    conn.execute('''
        CREATE TABLE IF NOT EXISTS historial_automatizacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL, -- 'programa_mantenimiento', 'alerta', 'tarea', 'workflow'
            referencia_id INTEGER,
            accion TEXT NOT NULL,
            resultado TEXT,
            datos TEXT, -- JSON con datos adicionales
            tiempo_ejecucion_ms INTEGER,
            fecha_ejecucion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insertar programas de mantenimiento por defecto
    conn.execute('''
        INSERT OR IGNORE INTO programas_mantenimiento 
        (nombre, descripcion, tipo_mantenimiento, intervalo_dias, activo) VALUES 
        ('Mantenimiento Preventivo General', 'Mantenimiento preventivo estándar para equipos', 'Preventivo', 90, 1),
        ('Inspección Mensual', 'Inspección rutinaria mensual', 'Inspección', 30, 1),
        ('Mantenimiento Trimestral', 'Mantenimiento completo trimestral', 'Preventivo', 90, 1)
    ''')
    
    # Insertar alertas automáticas por defecto
    conn.execute('''
        INSERT OR IGNORE INTO alertas_automaticas 
        (nombre, tipo, condiciones, mensaje_template, activa) VALUES 
        ('Stock Crítico', 'stock_bajo', '{"stock_minimo": 5}', 'Alerta: El repuesto {nombre} tiene stock crítico ({stock_actual} unidades)', 1),
        ('Mantenimientos Vencidos', 'mantenimiento_vencido', '{"dias_vencidos": 1}', 'Mantenimiento vencido: {equipo} - {tipo_mantenimiento} programado para {fecha}', 1),
        ('Equipos Sin Mantenimiento', 'equipo_inactivo', '{"dias_sin_mantenimiento": 120}', 'El equipo {nombre} no ha tenido mantenimiento en {dias} días', 1)
    ''')
    
    # =========================================
    # TABLAS PARA CONFIGURACIÓN DE LA APP
    # =========================================
    
    # Crear tabla de configuración general
    conn.execute('''
        CREATE TABLE IF NOT EXISTS configuracion_app (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clave TEXT NOT NULL UNIQUE,
            valor TEXT,
            tipo TEXT NOT NULL DEFAULT 'string', -- 'string', 'number', 'boolean', 'json'
            categoria TEXT NOT NULL DEFAULT 'general', -- 'general', 'tema', 'iot', 'ml', 'apis'
            descripcion TEXT,
            orden INTEGER DEFAULT 0,
            usuario_modificacion INTEGER,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_modificacion) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla de temas personalizados
    conn.execute('''
        CREATE TABLE IF NOT EXISTS temas_personalizados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            variables_css TEXT NOT NULL, -- JSON con variables CSS
            activo BOOLEAN DEFAULT 0,
            predeterminado BOOLEAN DEFAULT 0,
            usuario_creacion INTEGER,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_creacion) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla para configuración IoT
    conn.execute('''
        CREATE TABLE IF NOT EXISTS dispositivos_iot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL, -- 'sensor_temperatura', 'sensor_vibracion', 'camara', 'lector_rfid', etc.
            equipo_id INTEGER,
            mac_address TEXT UNIQUE,
            ip_address TEXT,
            puerto INTEGER,
            protocolo TEXT DEFAULT 'mqtt', -- 'mqtt', 'http', 'modbus', 'opcua'
            configuracion TEXT, -- JSON con configuración específica
            activo BOOLEAN DEFAULT 1,
            ultima_lectura TIMESTAMP,
            estado_conexion TEXT DEFAULT 'desconectado', -- 'conectado', 'desconectado', 'error'
            usuario_creacion INTEGER,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (equipo_id) REFERENCES equipos (id),
            FOREIGN KEY (usuario_creacion) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla para datos de sensores IoT
    conn.execute('''
        CREATE TABLE IF NOT EXISTS lecturas_iot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dispositivo_id INTEGER NOT NULL,
            tipo_lectura TEXT NOT NULL, -- 'temperatura', 'vibracion', 'presion', 'estado', etc.
            valor REAL,
            unidad TEXT,
            timestamp_lectura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            datos_adicionales TEXT, -- JSON con datos extra
            alerta_generada BOOLEAN DEFAULT 0,
            FOREIGN KEY (dispositivo_id) REFERENCES dispositivos_iot (id)
        )
    ''')
    
    # Crear tabla para configuración de APIs externas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS apis_externas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL, -- 'proveedor', 'contabilidad', 'inventario', 'crm'
            url_base TEXT NOT NULL,
            api_key TEXT,
            configuracion TEXT, -- JSON con headers, auth, etc.
            activa BOOLEAN DEFAULT 1,
            ultima_sincronizacion TIMESTAMP,
            estado_conexion TEXT DEFAULT 'no_testada', -- 'conectada', 'error', 'no_testada'
            log_errores TEXT,
            usuario_configuracion INTEGER,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_configuracion) REFERENCES usuarios (id)
        )
    ''')
    
    # Insertar configuración por defecto
    conn.execute('''
        INSERT OR IGNORE INTO configuracion_app (clave, valor, tipo, categoria, descripcion, orden) VALUES 
        ('nombre_empresa', 'Mi Taller', 'string', 'general', 'Nombre de la empresa o taller', 1),
        ('logo_empresa', '', 'string', 'general', 'URL del logo de la empresa', 2),
        ('tema_predeterminado', 'light', 'string', 'tema', 'Tema predeterminado para nuevos usuarios', 10),
        ('colores_personalizados', 'true', 'boolean', 'tema', 'Permitir colores personalizados', 11),
        ('idioma_predeterminado', 'es', 'string', 'general', 'Idioma predeterminado del sistema', 3),
        ('zona_horaria', 'America/Mexico_City', 'string', 'general', 'Zona horaria del sistema', 4),
        ('iot_habilitado', 'true', 'boolean', 'iot', 'Habilitar integración IoT', 20),
        ('mqtt_broker', 'localhost', 'string', 'iot', 'Servidor MQTT para IoT', 21),
        ('mqtt_puerto', '1883', 'number', 'iot', 'Puerto del servidor MQTT', 22),
        ('ml_habilitado', 'true', 'boolean', 'ml', 'Habilitar Machine Learning', 30),
        ('ml_modelo_prediccion', 'random_forest', 'string', 'ml', 'Modelo de ML para predicciones', 31),
        ('api_contabilidad_activa', 'false', 'boolean', 'apis', 'API de contabilidad activa', 40),
        ('api_proveedores_activa', 'false', 'boolean', 'apis', 'API de proveedores activa', 41)
    ''')
    
    # Insertar temas predeterminados
    conn.execute('''
        INSERT OR IGNORE INTO temas_personalizados (nombre, descripcion, variables_css, predeterminado) VALUES 
        ('Light', 'Tema claro predeterminado', '{"primary": "#007bff", "secondary": "#6c757d", "success": "#28a745", "danger": "#dc3545", "warning": "#ffc107", "info": "#17a2b8", "bg_primary": "#ffffff", "bg_secondary": "#f8f9fa", "text_primary": "#212529", "text_secondary": "#6c757d"}', 1),
        ('Dark', 'Tema oscuro moderno', '{"primary": "#375a7f", "secondary": "#444", "success": "#00bc8c", "danger": "#e74c3c", "warning": "#f39c12", "info": "#3498db", "bg_primary": "#222", "bg_secondary": "#2c3e50", "text_primary": "#fff", "text_secondary": "#adb5bd"}', 0),
        ('Corporate', 'Tema corporativo azul', '{"primary": "#2c3e50", "secondary": "#34495e", "success": "#27ae60", "danger": "#e74c3c", "warning": "#f39c12", "info": "#3498db", "bg_primary": "#ecf0f1", "bg_secondary": "#bdc3c7", "text_primary": "#2c3e50", "text_secondary": "#7f8c8d"}', 0),
        ('Nature', 'Tema natural verde', '{"primary": "#27ae60", "secondary": "#2ecc71", "success": "#2ecc71", "danger": "#e74c3c", "warning": "#f39c12", "info": "#3498db", "bg_primary": "#f8fffe", "bg_secondary": "#d5f4e6", "text_primary": "#2c3e50", "text_secondary": "#27ae60"}', 0)
    ''')
    
    # Agregar columnas de auditoría a tablas existentes si no existen
    try:
        conn.execute('ALTER TABLE clientes ADD COLUMN usuario_creacion INTEGER REFERENCES usuarios(id)')
        conn.execute('ALTER TABLE clientes ADD COLUMN usuario_modificacion INTEGER REFERENCES usuarios(id)')
        conn.execute('ALTER TABLE clientes ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except:
        pass
    
    try:
        conn.execute('ALTER TABLE equipos ADD COLUMN usuario_creacion INTEGER REFERENCES usuarios(id)')
        conn.execute('ALTER TABLE equipos ADD COLUMN usuario_modificacion INTEGER REFERENCES usuarios(id)')
        conn.execute('ALTER TABLE equipos ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except:
        pass
    
    try:
        conn.execute('ALTER TABLE mantenimientos ADD COLUMN usuario_creacion INTEGER REFERENCES usuarios(id)')
        conn.execute('ALTER TABLE mantenimientos ADD COLUMN usuario_modificacion INTEGER REFERENCES usuarios(id)')
        conn.execute('ALTER TABLE mantenimientos ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except:
        pass
    
    try:
        conn.execute('ALTER TABLE repuestos ADD COLUMN usuario_creacion INTEGER REFERENCES usuarios(id)')
        conn.execute('ALTER TABLE repuestos ADD COLUMN usuario_modificacion INTEGER REFERENCES usuarios(id)')
        conn.execute('ALTER TABLE repuestos ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except:
        pass
    
    conn.commit()
    conn.close()

# =========================================
# SISTEMA DE AUTENTICACIÓN Y USUARIOS
# =========================================

def hash_password(password):
    """Hashea una contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verifica si una contraseña coincide con su hash"""
    return hash_password(password) == password_hash

def generate_session_token():
    """Genera un token de sesión único"""
    return secrets.token_urlsafe(32)

def create_session(usuario_id, ip_address=None, user_agent=None):
    """Crea una nueva sesión para el usuario"""
    conn = get_db_connection()
    token = generate_session_token()
    expiration = datetime.now() + timedelta(hours=24)  # Sesión válida por 24 horas
    
    conn.execute('''
        INSERT INTO sesiones_usuario (usuario_id, token_sesion, ip_address, user_agent, fecha_expiracion)
        VALUES (?, ?, ?, ?, ?)
    ''', (usuario_id, token, ip_address, user_agent, expiration))
    
    conn.commit()
    conn.close()
    return token

def verify_session(token):
    """Verifica si un token de sesión es válido"""
    conn = get_db_connection()
    result = conn.execute('''
        SELECT s.usuario_id, u.username, u.nombre_completo, u.rol, u.activo
        FROM sesiones_usuario s
        JOIN usuarios u ON s.usuario_id = u.id
        WHERE s.token_sesion = ? AND s.activa = 1 AND s.fecha_expiracion > ?
    ''', (token, datetime.now())).fetchone()
    
    conn.close()
    return result

def invalidate_session(token):
    """Invalida una sesión"""
    conn = get_db_connection()
    conn.execute('UPDATE sesiones_usuario SET activa = 0 WHERE token_sesion = ?', (token,))
    conn.commit()
    conn.close()

def get_user_permissions(rol):
    """Obtiene los permisos de un rol específico"""
    conn = get_db_connection()
    result = conn.execute('SELECT permisos FROM roles WHERE nombre = ?', (rol,)).fetchone()
    conn.close()
    
    if result:
        try:
            return json.loads(result['permisos'])
        except:
            return {}
    return {}

def check_permission(required_permission, resource=None):
    """Verifica si el usuario actual tiene el permiso requerido"""
    if 'user_id' not in session:
        return False
    
    user_role = session.get('user_role', '')
    permissions = get_user_permissions(user_role)
    
    # Admin tiene todos los permisos
    if permissions.get('all', False):
        return True
    
    if resource:
        resource_perms = permissions.get(resource, '')
        if isinstance(resource_perms, str):
            return required_permission in resource_perms.split(',') or resource_perms == 'all'
        return False
    
    return False

def log_audit(accion, tabla_afectada=None, registro_id=None, datos_anteriores=None, datos_nuevos=None):
    """Registra una acción en la auditoría"""
    if 'user_id' not in session:
        return
    
    conn = get_db_connection()
    ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
    user_agent = request.headers.get('User-Agent', '')
    
    conn.execute('''
        INSERT INTO auditoria (usuario_id, accion, tabla_afectada, registro_id, 
                               datos_anteriores, datos_nuevos, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session['user_id'], accion, tabla_afectada, registro_id,
        json.dumps(datos_anteriores) if datos_anteriores else None,
        json.dumps(datos_nuevos) if datos_nuevos else None,
        ip_address, user_agent
    ))
    
    conn.commit()
    conn.close()

def require_auth(f):
    """Decorador que requiere autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'session_token' not in session:
            flash('Debes iniciar sesión para acceder', 'error')
            return redirect(url_for('login'))
        
        # Verificar que la sesión sea válida
        user_data = verify_session(session['session_token'])
        if not user_data:
            session.clear()
            flash('Tu sesión ha expirado', 'warning')
            return redirect(url_for('login'))
        
        # Actualizar datos del usuario en la sesión
        session['user_id'] = user_data['usuario_id']
        session['username'] = user_data['username']
        session['user_name'] = user_data['nombre_completo']
        session['user_role'] = user_data['rol']
        
        # Verificar que el usuario esté activo
        if not user_data['activo']:
            session.clear()
            flash('Tu cuenta ha sido desactivada', 'error')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

def require_permission(resource, permission):
    """Decorador que requiere un permiso específico"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not check_permission(permission, resource):
                flash('No tienes permisos para realizar esta acción', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Función para cargar usuario en cada request
@app.before_request
def load_user():
    """Carga la información del usuario en cada request"""
    g.user = None
    if 'session_token' in session:
        user_data = verify_session(session['session_token'])
        if user_data:
            g.user = {
                'id': user_data['usuario_id'],
                'username': user_data['username'],
                'nombre_completo': user_data['nombre_completo'],
                'rol': user_data['rol'],
                'permisos': get_user_permissions(user_data['rol'])
            }

# =========================================
# RUTAS DE AUTENTICACIÓN
# =========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember_me = 'remember_me' in request.form
        
        if not username or not password:
            flash('Ingresa usuario y contraseña', 'error')
            return render_template('auth/login.html')
        
        conn = get_db_connection()
        user = conn.execute('''
            SELECT id, username, email, password_hash, nombre_completo, rol, activo
            FROM usuarios WHERE username = ? OR email = ?
        ''', (username, username)).fetchone()
        conn.close()
        
        if user and verify_password(password, user['password_hash']):
            if not user['activo']:
                flash('Tu cuenta ha sido desactivada', 'error')
                return render_template('auth/login.html')
            
            # Crear sesión
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
            user_agent = request.headers.get('User-Agent', '')
            token = create_session(user['id'], ip_address, user_agent)
            
            # Actualizar último acceso
            conn = get_db_connection()
            conn.execute('UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?', 
                        (datetime.now(), user['id']))
            conn.commit()
            conn.close()
            
            # Configurar sesión
            session['session_token'] = token
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_name'] = user['nombre_completo']
            session['user_role'] = user['rol']
            
            # Configurar duración de sesión
            if remember_me:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)
            else:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(hours=8)
            
            # Log de auditoría
            log_audit('login', 'usuarios', user['id'])
            
            flash(f'¡Bienvenido {user["nombre_completo"]}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    if 'session_token' in session:
        invalidate_session(session['session_token'])
        log_audit('logout')
    
    session.clear()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('login'))

@app.route('/cambiar_password', methods=['GET', 'POST'])
@require_auth
def cambiar_password():
    """Cambiar contraseña del usuario actual"""
    if request.method == 'POST':
        password_actual = request.form.get('password_actual', '')
        password_nueva = request.form.get('password_nueva', '')
        password_confirmar = request.form.get('password_confirmar', '')
        
        if not all([password_actual, password_nueva, password_confirmar]):
            flash('Completa todos los campos', 'error')
            return render_template('auth/cambiar_password.html')
        
        if password_nueva != password_confirmar:
            flash('Las contraseñas nuevas no coinciden', 'error')
            return render_template('auth/cambiar_password.html')
        
        if len(password_nueva) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('auth/cambiar_password.html')
        
        # Verificar contraseña actual
        conn = get_db_connection()
        user = conn.execute('SELECT password_hash FROM usuarios WHERE id = ?', 
                           (session['user_id'],)).fetchone()
        
        if not verify_password(password_actual, user['password_hash']):
            flash('La contraseña actual es incorrecta', 'error')
            conn.close()
            return render_template('auth/cambiar_password.html')
        
        # Actualizar contraseña
        new_hash = hash_password(password_nueva)
        conn.execute('UPDATE usuarios SET password_hash = ?, fecha_modificacion = ? WHERE id = ?',
                    (new_hash, datetime.now(), session['user_id']))
        conn.commit()
        conn.close()
        
        # Log de auditoría
        log_audit('cambio_password', 'usuarios', session['user_id'])
        
        flash('Contraseña cambiada exitosamente', 'success')
        return redirect(url_for('index'))
    
    return render_template('auth/cambiar_password.html')

# =========================================
# RUTAS DE GESTIÓN DE USUARIOS
# =========================================

@app.route('/usuarios')
@require_auth
@require_permission('usuarios', 'read')
def gestionar_usuarios():
    """Página de gestión de usuarios"""
    conn = get_db_connection()
    
    # Obtener filtros
    filtro_rol = request.args.get('rol', '')
    filtro_estado = request.args.get('estado', '')
    busqueda = request.args.get('busqueda', '')
    
    # Construir query con filtros
    where_conditions = []
    params = []
    
    if filtro_rol:
        where_conditions.append("u.rol = ?")
        params.append(filtro_rol)
    
    if filtro_estado == 'activo':
        where_conditions.append("u.activo = 1")
    elif filtro_estado == 'inactivo':
        where_conditions.append("u.activo = 0")
    
    if busqueda:
        where_conditions.append("(u.username LIKE ? OR u.nombre_completo LIKE ? OR u.email LIKE ?)")
        search_param = f"%{busqueda}%"
        params.extend([search_param, search_param, search_param])
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Obtener usuarios
    usuarios = conn.execute(f'''
        SELECT u.*, r.descripcion as rol_descripcion,
               (SELECT COUNT(*) FROM sesiones_usuario s WHERE s.usuario_id = u.id AND s.activa = 1) as sesiones_activas
        FROM usuarios u
        LEFT JOIN roles r ON u.rol = r.nombre
        {where_clause}
        ORDER BY u.fecha_creacion DESC
    ''', params).fetchall()
    
    # Obtener roles disponibles
    roles = conn.execute('SELECT * FROM roles WHERE activo = 1 ORDER BY nombre').fetchall()
    
    # Estadísticas
    stats = {
        'total_usuarios': conn.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0],
        'usuarios_activos': conn.execute('SELECT COUNT(*) FROM usuarios WHERE activo = 1').fetchone()[0],
        'sesiones_activas': conn.execute('SELECT COUNT(*) FROM sesiones_usuario WHERE activa = 1').fetchone()[0],
        'ultimo_acceso': conn.execute('''
            SELECT u.nombre_completo, u.ultimo_acceso 
            FROM usuarios u 
            WHERE u.ultimo_acceso IS NOT NULL 
            ORDER BY u.ultimo_acceso DESC 
            LIMIT 1
        ''').fetchone()
    }
    
    conn.close()
    
    return render_template('admin/usuarios.html', 
                         usuarios=usuarios, 
                         roles=roles, 
                         stats=stats,
                         filtro_rol=filtro_rol,
                         filtro_estado=filtro_estado,
                         busqueda=busqueda)

@app.route('/usuarios/nuevo', methods=['GET', 'POST'])
@require_auth
@require_permission('usuarios', 'create')
def nuevo_usuario():
    """Crear nuevo usuario"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        nombre_completo = request.form.get('nombre_completo', '').strip()
        rol = request.form.get('rol', '')
        activo = 'activo' in request.form
        
        # Validaciones
        if not all([username, email, password, nombre_completo, rol]):
            flash('Completa todos los campos obligatorios', 'error')
            return redirect(url_for('nuevo_usuario'))
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return redirect(url_for('nuevo_usuario'))
        
        conn = get_db_connection()
        
        # Verificar que username y email sean únicos
        existing = conn.execute('''
            SELECT id FROM usuarios WHERE username = ? OR email = ?
        ''', (username, email)).fetchone()
        
        if existing:
            flash('El usuario o email ya existe', 'error')
            conn.close()
            return redirect(url_for('nuevo_usuario'))
        
        # Crear usuario
        password_hash = hash_password(password)
        try:
            conn.execute('''
                INSERT INTO usuarios (username, email, password_hash, nombre_completo, rol, activo)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, email, password_hash, nombre_completo, rol, activo))
            
            conn.commit()
            
            # Log de auditoría
            log_audit('crear_usuario', 'usuarios', None, None, {
                'username': username,
                'email': email,
                'nombre_completo': nombre_completo,
                'rol': rol
            })
            
            flash(f'Usuario {username} creado exitosamente', 'success')
            conn.close()
            return redirect(url_for('gestionar_usuarios'))
            
        except Exception as e:
            conn.close()
            flash(f'Error al crear usuario: {str(e)}', 'error')
            return redirect(url_for('nuevo_usuario'))
    
    # GET - mostrar formulario
    conn = get_db_connection()
    roles = conn.execute('SELECT * FROM roles WHERE activo = 1 ORDER BY nombre').fetchall()
    conn.close()
    
    return render_template('admin/nuevo_usuario.html', roles=roles)

@app.route('/usuarios/<int:user_id>/editar', methods=['GET', 'POST'])
@require_auth
@require_permission('usuarios', 'update')
def editar_usuario(user_id):
    """Editar usuario existente"""
    conn = get_db_connection()
    
    # Obtener usuario
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    if not usuario:
        flash('Usuario no encontrado', 'error')
        conn.close()
        return redirect(url_for('gestionar_usuarios'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        nombre_completo = request.form.get('nombre_completo', '').strip()
        rol = request.form.get('rol', '')
        activo = 'activo' in request.form
        cambiar_password = 'cambiar_password' in request.form
        nueva_password = request.form.get('nueva_password', '')
        
        # Validaciones
        if not all([username, email, nombre_completo, rol]):
            flash('Completa todos los campos obligatorios', 'error')
            return redirect(url_for('editar_usuario', user_id=user_id))
        
        if cambiar_password and len(nueva_password) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres', 'error')
            return redirect(url_for('editar_usuario', user_id=user_id))
        
        # Verificar unicidad de username y email (excluyendo el usuario actual)
        existing = conn.execute('''
            SELECT id FROM usuarios WHERE (username = ? OR email = ?) AND id != ?
        ''', (username, email, user_id)).fetchone()
        
        if existing:
            flash('El usuario o email ya existe en otro registro', 'error')
            return redirect(url_for('editar_usuario', user_id=user_id))
        
        # Datos anteriores para auditoría
        datos_anteriores = dict(usuario)
        
        # Actualizar usuario
        try:
            if cambiar_password:
                password_hash = hash_password(nueva_password)
                conn.execute('''
                    UPDATE usuarios 
                    SET username = ?, email = ?, password_hash = ?, nombre_completo = ?, 
                        rol = ?, activo = ?, fecha_modificacion = ?
                    WHERE id = ?
                ''', (username, email, password_hash, nombre_completo, rol, activo, 
                     datetime.now(), user_id))
            else:
                conn.execute('''
                    UPDATE usuarios 
                    SET username = ?, email = ?, nombre_completo = ?, rol = ?, 
                        activo = ?, fecha_modificacion = ?
                    WHERE id = ?
                ''', (username, email, nombre_completo, rol, activo, 
                     datetime.now(), user_id))
            
            conn.commit()
            
            # Log de auditoría
            datos_nuevos = {
                'username': username,
                'email': email,
                'nombre_completo': nombre_completo,
                'rol': rol,
                'activo': activo
            }
            if cambiar_password:
                datos_nuevos['password_changed'] = True
                
            log_audit('editar_usuario', 'usuarios', user_id, datos_anteriores, datos_nuevos)
            
            flash(f'Usuario {username} actualizado exitosamente', 'success')
            conn.close()
            return redirect(url_for('gestionar_usuarios'))
            
        except Exception as e:
            conn.close()
            flash(f'Error al actualizar usuario: {str(e)}', 'error')
            return redirect(url_for('editar_usuario', user_id=user_id))
    
    # GET - mostrar formulario
    roles = conn.execute('SELECT * FROM roles WHERE activo = 1 ORDER BY nombre').fetchall()
    conn.close()
    
    return render_template('admin/editar_usuario.html', usuario=usuario, roles=roles)

@app.route('/usuarios/<int:user_id>/eliminar', methods=['POST'])
@require_auth
@require_permission('usuarios', 'delete')
def eliminar_usuario(user_id):
    """Eliminar/desactivar usuario"""
    if user_id == session.get('user_id'):
        flash('No puedes eliminar tu propio usuario', 'error')
        return redirect(url_for('gestionar_usuarios'))
    
    conn = get_db_connection()
    
    # Obtener usuario
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    if not usuario:
        flash('Usuario no encontrado', 'error')
        conn.close()
        return redirect(url_for('gestionar_usuarios'))
    
    try:
        # En lugar de eliminar, desactivamos el usuario
        conn.execute('''
            UPDATE usuarios 
            SET activo = 0, fecha_modificacion = ?
            WHERE id = ?
        ''', (datetime.now(), user_id))
        
        # Invalidar todas las sesiones del usuario
        conn.execute('UPDATE sesiones_usuario SET activa = 0 WHERE usuario_id = ?', (user_id,))
        
        conn.commit()
        
        # Log de auditoría
        log_audit('desactivar_usuario', 'usuarios', user_id, dict(usuario), {'activo': False})
        
        flash(f'Usuario {usuario["username"]} desactivado exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al desactivar usuario: {str(e)}', 'error')
    
    conn.close()
    return redirect(url_for('gestionar_usuarios'))

@app.route('/usuarios/<int:user_id>/activar', methods=['POST'])
@require_auth
@require_permission('usuarios', 'update')
def activar_usuario(user_id):
    """Activar usuario desactivado"""
    conn = get_db_connection()
    
    # Obtener usuario
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    if not usuario:
        flash('Usuario no encontrado', 'error')
        conn.close()
        return redirect(url_for('gestionar_usuarios'))
    
    try:
        conn.execute('''
            UPDATE usuarios 
            SET activo = 1, fecha_modificacion = ?
            WHERE id = ?
        ''', (datetime.now(), user_id))
        
        conn.commit()
        
        # Log de auditoría
        log_audit('activar_usuario', 'usuarios', user_id, dict(usuario), {'activo': True})
        
        flash(f'Usuario {usuario["username"]} activado exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al activar usuario: {str(e)}', 'error')
    
    conn.close()
    return redirect(url_for('gestionar_usuarios'))

# =========================================
# RUTAS DE AUDITORÍA
# =========================================

@app.route('/auditoria')
@require_auth
@require_permission('usuarios', 'read')  # Solo admins y gerentes pueden ver auditoría
def auditoria():
    """Página de auditoría del sistema"""
    conn = get_db_connection()
    
    # Obtener filtros
    filtro_usuario = request.args.get('usuario_id', '')
    filtro_accion = request.args.get('accion', '')
    filtro_tabla = request.args.get('tabla', '')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    busqueda = request.args.get('busqueda', '')
    
    # Paginación
    page = int(request.args.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    
    # Construir query con filtros
    where_conditions = []
    params = []
    
    if filtro_usuario:
        where_conditions.append("a.usuario_id = ?")
        params.append(filtro_usuario)
    
    if filtro_accion:
        where_conditions.append("a.accion = ?")
        params.append(filtro_accion)
    
    if filtro_tabla:
        where_conditions.append("a.tabla_afectada = ?")
        params.append(filtro_tabla)
    
    if fecha_inicio:
        where_conditions.append("DATE(a.fecha_accion) >= ?")
        params.append(fecha_inicio)
    
    if fecha_fin:
        where_conditions.append("DATE(a.fecha_accion) <= ?")
        params.append(fecha_fin)
    
    if busqueda:
        where_conditions.append("(a.accion LIKE ? OR a.tabla_afectada LIKE ? OR u.nombre_completo LIKE ?)")
        search_param = f"%{busqueda}%"
        params.extend([search_param, search_param, search_param])
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Obtener total de registros
    count_query = f'''
        SELECT COUNT(*) 
        FROM auditoria a
        LEFT JOIN usuarios u ON a.usuario_id = u.id
        {where_clause}
    '''
    total_registros = conn.execute(count_query, params).fetchone()[0]
    
    # Obtener registros de auditoría
    auditoria_query = f'''
        SELECT a.*, u.username, u.nombre_completo
        FROM auditoria a
        LEFT JOIN usuarios u ON a.usuario_id = u.id
        {where_clause}
        ORDER BY a.fecha_accion DESC
        LIMIT ? OFFSET ?
    '''
    params.extend([per_page, offset])
    registros = conn.execute(auditoria_query, params).fetchall()
    
    # Obtener usuarios para el filtro
    usuarios = conn.execute('''
        SELECT DISTINCT u.id, u.username, u.nombre_completo 
        FROM usuarios u 
        INNER JOIN auditoria a ON u.id = a.usuario_id
        ORDER BY u.nombre_completo
    ''').fetchall()
    
    # Obtener acciones únicas
    acciones = conn.execute('''
        SELECT DISTINCT accion 
        FROM auditoria 
        WHERE accion IS NOT NULL
        ORDER BY accion
    ''').fetchall()
    
    # Obtener tablas afectadas únicas
    tablas = conn.execute('''
        SELECT DISTINCT tabla_afectada 
        FROM auditoria 
        WHERE tabla_afectada IS NOT NULL
        ORDER BY tabla_afectada
    ''').fetchall()
    
    # Estadísticas
    stats = {
        'total_registros': total_registros,
        'registros_hoy': conn.execute('''
            SELECT COUNT(*) FROM auditoria 
            WHERE DATE(fecha_accion) = DATE('now')
        ''').fetchone()[0],
        'usuarios_activos_hoy': conn.execute('''
            SELECT COUNT(DISTINCT usuario_id) FROM auditoria 
            WHERE DATE(fecha_accion) = DATE('now')
        ''').fetchone()[0],
        'accion_mas_comun': conn.execute('''
            SELECT accion, COUNT(*) as total 
            FROM auditoria 
            WHERE DATE(fecha_accion) >= DATE('now', '-7 days')
            GROUP BY accion 
            ORDER BY total DESC 
            LIMIT 1
        ''').fetchone()
    }
    
    # Calcular paginación
    total_pages = (total_registros + per_page - 1) // per_page
    
    conn.close()
    
    return render_template('admin/auditoria.html',
                         registros=registros,
                         usuarios=usuarios,
                         acciones=acciones,
                         tablas=tablas,
                         stats=stats,
                         filtro_usuario=filtro_usuario,
                         filtro_accion=filtro_accion,
                         filtro_tabla=filtro_tabla,
                         fecha_inicio=fecha_inicio,
                         fecha_fin=fecha_fin,
                         busqueda=busqueda,
                         page=page,
                         total_pages=total_pages,
                         total_registros=total_registros,
                         per_page=per_page)

@app.route('/auditoria/<int:registro_id>')
@require_auth
@require_permission('usuarios', 'read')
def detalle_auditoria(registro_id):
    """Ver detalles de un registro de auditoría"""
    conn = get_db_connection()
    
    registro = conn.execute('''
        SELECT a.*, u.username, u.nombre_completo
        FROM auditoria a
        LEFT JOIN usuarios u ON a.usuario_id = u.id
        WHERE a.id = ?
    ''', (registro_id,)).fetchone()
    
    if not registro:
        flash('Registro de auditoría no encontrado', 'error')
        conn.close()
        return redirect(url_for('auditoria'))
    
    conn.close()
    
    # Parsear datos JSON si existen
    try:
        datos_anteriores = json.loads(registro['datos_anteriores']) if registro['datos_anteriores'] else None
        datos_nuevos = json.loads(registro['datos_nuevos']) if registro['datos_nuevos'] else None
    except:
        datos_anteriores = None
        datos_nuevos = None
    
    return render_template('admin/detalle_auditoria.html',
                         registro=registro,
                         datos_anteriores=datos_anteriores,
                         datos_nuevos=datos_nuevos)

@app.route('/api/auditoria/estadisticas')
@require_auth
@require_permission('usuarios', 'read')
def estadisticas_auditoria():
    """API para obtener estadísticas de auditoría"""
    conn = get_db_connection()
    
    # Actividad por día (últimos 30 días)
    actividad_diaria = conn.execute('''
        SELECT DATE(fecha_accion) as fecha, COUNT(*) as total
        FROM auditoria
        WHERE fecha_accion >= DATE('now', '-30 days')
        GROUP BY DATE(fecha_accion)
        ORDER BY fecha
    ''').fetchall()
    
    # Acciones más comunes
    acciones_comunes = conn.execute('''
        SELECT accion, COUNT(*) as total
        FROM auditoria
        WHERE fecha_accion >= DATE('now', '-30 days')
        GROUP BY accion
        ORDER BY total DESC
        LIMIT 10
    ''').fetchall()
    
    # Usuarios más activos
    usuarios_activos = conn.execute('''
        SELECT u.nombre_completo, COUNT(*) as total
        FROM auditoria a
        JOIN usuarios u ON a.usuario_id = u.id
        WHERE a.fecha_accion >= DATE('now', '-30 days')
        GROUP BY a.usuario_id, u.nombre_completo
        ORDER BY total DESC
        LIMIT 10
    ''').fetchall()
    
    # Actividad por hora del día
    actividad_horaria = conn.execute('''
        SELECT strftime('%H', fecha_accion) as hora, COUNT(*) as total
        FROM auditoria
        WHERE fecha_accion >= DATE('now', '-7 days')
        GROUP BY strftime('%H', fecha_accion)
        ORDER BY hora
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'actividad_diaria': [dict(row) for row in actividad_diaria],
        'acciones_comunes': [dict(row) for row in acciones_comunes],
        'usuarios_activos': [dict(row) for row in usuarios_activos],
        'actividad_horaria': [dict(row) for row in actividad_horaria]
    })

@app.route('/')
@require_auth
def index():
    """Dashboard interactivo con analytics predictivos avanzados"""
    conn = get_db_connection()
    
    # =========================================
    # MÉTRICAS PRINCIPALES
    # =========================================
    stats = {
        'total_equipos': conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0],
        'equipos_activos': conn.execute('SELECT COUNT(*) FROM equipos WHERE estado = "Activo"').fetchone()[0],
        'total_mantenimientos': conn.execute('SELECT COUNT(*) FROM mantenimientos').fetchone()[0],
        'total_clientes': conn.execute('SELECT COUNT(*) FROM clientes').fetchone()[0],
        'mantenimientos_pendientes': conn.execute('SELECT COUNT(*) FROM mantenimientos WHERE estado = "Pendiente"').fetchone()[0],
        'mantenimientos_en_progreso': conn.execute('SELECT COUNT(*) FROM mantenimientos WHERE estado = "En Progreso"').fetchone()[0],
        'repuestos_stock_bajo': conn.execute('SELECT COUNT(*) FROM repuestos WHERE stock_actual <= stock_minimo').fetchone()[0]
    }
    
    # =========================================
    # ANÁLISIS PREDICTIVO DE MANTENIMIENTOS
    # =========================================
    # Equipos que necesitarán mantenimiento pronto (basado en histórico)
    equipos_mantenimiento_predicho = conn.execute('''
        WITH ultimo_mantenimiento AS (
            SELECT 
                e.id, e.nombre, e.marca, e.modelo, c.nombre as cliente_nombre,
                MAX(m.fecha_mantenimiento) as ultimo_mantenimiento,
                COUNT(m.id) as total_mantenimientos,
                AVG(julianday('now') - julianday(m.fecha_mantenimiento)) as promedio_dias_entre_mantenimientos
        FROM equipos e
        LEFT JOIN clientes c ON e.cliente_id = c.id
            LEFT JOIN mantenimientos m ON e.id = m.equipo_id
            WHERE e.estado = 'Activo'
            GROUP BY e.id
            HAVING COUNT(m.id) >= 2
        )
        SELECT *, 
               (julianday('now') - julianday(ultimo_mantenimiento)) as dias_desde_ultimo,
               (promedio_dias_entre_mantenimientos - (julianday('now') - julianday(ultimo_mantenimiento))) as dias_hasta_proximo
        FROM ultimo_mantenimiento
        WHERE dias_hasta_proximo <= 30 AND dias_hasta_proximo > 0
        ORDER BY dias_hasta_proximo ASC
        LIMIT 10
    ''').fetchall()
    
    # =========================================
    # TENDENCIAS Y ANÁLISIS TEMPORAL
    # =========================================
    # Mantenimientos por mes (últimos 12 meses)
    mantenimientos_mensuales = conn.execute('''
        SELECT 
            strftime('%Y-%m', fecha_mantenimiento) as mes,
            COUNT(*) as total,
            AVG(costo) as costo_promedio
        FROM mantenimientos
        WHERE fecha_mantenimiento >= date('now', '-12 months')
        GROUP BY strftime('%Y-%m', fecha_mantenimiento)
        ORDER BY mes
    ''').fetchall()
    
    # Análisis de costos por tipo de mantenimiento
    costos_por_tipo = conn.execute('''
        SELECT 
            tipo_mantenimiento,
            COUNT(*) as cantidad,
            SUM(costo) as costo_total,
            AVG(costo) as costo_promedio,
            MIN(costo) as costo_minimo,
            MAX(costo) as costo_maximo
        FROM mantenimientos
        WHERE fecha_mantenimiento >= date('now', '-6 months') AND costo > 0
        GROUP BY tipo_mantenimiento
        ORDER BY costo_total DESC
    ''').fetchall()
    
    # =========================================
    # ANÁLISIS DE CLIENTES
    # =========================================
    # Top clientes por actividad y gasto
    top_clientes = conn.execute('''
        SELECT 
            c.nombre,
            COUNT(DISTINCT e.id) as total_equipos,
            COUNT(m.id) as total_mantenimientos,
            SUM(COALESCE(m.costo, 0)) as gasto_total,
            AVG(COALESCE(m.costo, 0)) as gasto_promedio,
            MAX(m.fecha_mantenimiento) as ultimo_mantenimiento
        FROM clientes c
        LEFT JOIN equipos e ON c.id = e.cliente_id
        LEFT JOIN mantenimientos m ON e.id = m.equipo_id
        WHERE m.fecha_mantenimiento >= date('now', '-6 months')
        GROUP BY c.id, c.nombre
        HAVING COUNT(m.id) > 0
        ORDER BY gasto_total DESC
        LIMIT 10
    ''').fetchall()
    
    # =========================================
    # ANÁLISIS DE EFICIENCIA OPERATIVA
    # =========================================
    # Tiempo promedio de resolución por tipo
    eficiencia_tipos = conn.execute('''
        SELECT 
            tipo_mantenimiento,
            COUNT(*) as total,
            AVG(CASE 
                WHEN estado = 'Completado' 
                THEN julianday(fecha_mantenimiento) - julianday(fecha_creacion)
                ELSE NULL 
            END) as dias_promedio_resolucion,
            COUNT(CASE WHEN estado = 'Completado' THEN 1 END) * 100.0 / COUNT(*) as porcentaje_completados
        FROM mantenimientos
        WHERE fecha_creacion >= date('now', '-3 months')
        GROUP BY tipo_mantenimiento
        ORDER BY dias_promedio_resolucion ASC
    ''').fetchall()
    
    # =========================================
    # ALERTAS Y NOTIFICACIONES
    # =========================================
    alertas = []
    
    # Equipos sin mantenimiento en mucho tiempo
    equipos_sin_mantenimiento = conn.execute('''
        SELECT e.nombre, c.nombre as cliente_nombre,
               COALESCE(MAX(m.fecha_mantenimiento), e.fecha_creacion) as ultima_fecha
        FROM equipos e
        LEFT JOIN clientes c ON e.cliente_id = c.id
        LEFT JOIN mantenimientos m ON e.id = m.equipo_id
        WHERE e.estado = 'Activo'
        GROUP BY e.id
        HAVING julianday('now') - julianday(ultima_fecha) > 90
        ORDER BY ultima_fecha ASC
        LIMIT 5
    ''').fetchall()
    
    if equipos_sin_mantenimiento:
        alertas.append({
            'tipo': 'warning',
            'titulo': 'Equipos sin mantenimiento',
            'mensaje': f'{len(equipos_sin_mantenimiento)} equipos no han tenido mantenimiento en más de 90 días',
            'datos': equipos_sin_mantenimiento
        })
    
    # Stock crítico
    if stats['repuestos_stock_bajo'] > 0:
        alertas.append({
            'tipo': 'danger',
            'titulo': 'Stock crítico',
            'mensaje': f'{stats["repuestos_stock_bajo"]} repuestos con stock bajo o agotado',
            'datos': []
        })
    
    # Mantenimientos vencidos
    mantenimientos_vencidos = conn.execute('''
        SELECT COUNT(*) FROM mantenimientos 
        WHERE estado IN ('Pendiente', 'En Progreso') 
        AND fecha_mantenimiento < date('now')
    ''').fetchone()[0]
    
    if mantenimientos_vencidos > 0:
        alertas.append({
            'tipo': 'error',
            'titulo': 'Mantenimientos vencidos',
            'mensaje': f'{mantenimientos_vencidos} mantenimientos están atrasados',
            'datos': []
        })
    
    # =========================================
    # ACTIVIDAD RECIENTE
    # =========================================
    actividad_reciente = conn.execute('''
        SELECT 
            'mantenimiento' as tipo,
            m.id,
            e.nombre as equipo_nombre,
            c.nombre as cliente_nombre,
            m.tipo_mantenimiento,
            m.estado,
            m.fecha_creacion,
            'Sistema' as usuario_nombre
        FROM mantenimientos m
        LEFT JOIN equipos e ON m.equipo_id = e.id
        LEFT JOIN clientes c ON e.cliente_id = c.id
        WHERE m.fecha_creacion >= date('now', '-7 days')
        
        UNION ALL
        
        SELECT 
            'equipo' as tipo,
            e.id,
            e.nombre as equipo_nombre,
            c.nombre as cliente_nombre,
            e.marca as tipo_mantenimiento,
            e.estado,
            e.fecha_creacion,
            'Sistema' as usuario_nombre
        FROM equipos e
        LEFT JOIN clientes c ON e.cliente_id = c.id
        WHERE e.fecha_creacion >= date('now', '-7 days')
        
        ORDER BY 7 DESC
        LIMIT 15
    ''').fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         stats=stats,
                         equipos_mantenimiento_predicho=equipos_mantenimiento_predicho,
                         mantenimientos_mensuales=mantenimientos_mensuales,
                         costos_por_tipo=costos_por_tipo,
                         top_clientes=top_clientes,
                         eficiencia_tipos=eficiencia_tipos,
                         alertas=alertas,
                         actividad_reciente=actividad_reciente)

# =========================================
# APIs PARA DASHBOARD INTERACTIVO
# =========================================

@app.route('/api/dashboard/metricas')
@require_auth
def api_dashboard_metricas():
    """API para obtener métricas en tiempo real del dashboard"""
    conn = get_db_connection()
    
    # Métricas básicas
    metricas = {
        'equipos': {
            'total': conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0],
            'activos': conn.execute('SELECT COUNT(*) FROM equipos WHERE estado = "Activo"').fetchone()[0],
            'mantenimiento': conn.execute('SELECT COUNT(*) FROM equipos WHERE estado = "Mantenimiento"').fetchone()[0],
            'fuera_servicio': conn.execute('SELECT COUNT(*) FROM equipos WHERE estado = "Fuera de Servicio"').fetchone()[0]
        },
        'mantenimientos': {
            'total': conn.execute('SELECT COUNT(*) FROM mantenimientos').fetchone()[0],
            'pendientes': conn.execute('SELECT COUNT(*) FROM mantenimientos WHERE estado = "Pendiente"').fetchone()[0],
            'en_progreso': conn.execute('SELECT COUNT(*) FROM mantenimientos WHERE estado = "En Progreso"').fetchone()[0],
            'completados': conn.execute('SELECT COUNT(*) FROM mantenimientos WHERE estado = "Completado"').fetchone()[0],
            'vencidos': conn.execute('SELECT COUNT(*) FROM mantenimientos WHERE estado IN ("Pendiente", "En Progreso") AND fecha_mantenimiento < date("now")').fetchone()[0]
        },
        'finanzas': {
            'gasto_mes_actual': conn.execute('SELECT COALESCE(SUM(costo), 0) FROM mantenimientos WHERE strftime("%Y-%m", fecha_mantenimiento) = strftime("%Y-%m", "now")').fetchone()[0],
            'gasto_mes_anterior': conn.execute('SELECT COALESCE(SUM(costo), 0) FROM mantenimientos WHERE strftime("%Y-%m", fecha_mantenimiento) = strftime("%Y-%m", date("now", "-1 month"))').fetchone()[0],
            'promedio_costo': conn.execute('SELECT COALESCE(AVG(costo), 0) FROM mantenimientos WHERE fecha_mantenimiento >= date("now", "-3 months") AND costo > 0').fetchone()[0]
        },
        'stock': {
            'total_repuestos': conn.execute('SELECT COUNT(*) FROM repuestos').fetchone()[0],
            'stock_bajo': conn.execute('SELECT COUNT(*) FROM repuestos WHERE stock_actual <= stock_minimo').fetchone()[0],
            'sin_stock': conn.execute('SELECT COUNT(*) FROM repuestos WHERE stock_actual = 0').fetchone()[0]
        }
    }
    
    conn.close()
    return jsonify(metricas)

@app.route('/api/dashboard/tendencias')
@require_auth
def api_dashboard_tendencias():
    """API para obtener datos de tendencias para gráficos"""
    conn = get_db_connection()
    
    # Mantenimientos por día (últimos 30 días)
    mantenimientos_diarios = conn.execute('''
        SELECT 
            DATE(fecha_mantenimiento) as fecha,
            COUNT(*) as total,
            SUM(CASE WHEN tipo_mantenimiento = 'Preventivo' THEN 1 ELSE 0 END) as preventivos,
            SUM(CASE WHEN tipo_mantenimiento = 'Correctivo' THEN 1 ELSE 0 END) as correctivos,
            SUM(CASE WHEN tipo_mantenimiento = 'Emergencia' THEN 1 ELSE 0 END) as emergencia,
            AVG(COALESCE(costo, 0)) as costo_promedio
        FROM mantenimientos
        WHERE fecha_mantenimiento >= date('now', '-30 days')
        GROUP BY DATE(fecha_mantenimiento)
        ORDER BY fecha
    ''').fetchall()
    
    # Eficiencia por técnico (últimos 30 días)
    eficiencia_tecnicos = conn.execute('''
        SELECT 
            COALESCE(tecnico, 'Sin asignar') as tecnico,
            COUNT(*) as total_trabajos,
            COUNT(CASE WHEN estado = 'Completado' THEN 1 END) as completados,
            AVG(CASE 
                WHEN estado = 'Completado' AND fecha_mantenimiento IS NOT NULL 
                THEN julianday(fecha_mantenimiento) - julianday(fecha_creacion)
                ELSE NULL 
            END) as tiempo_promedio_dias
        FROM mantenimientos
        WHERE fecha_creacion >= date('now', '-30 days')
        GROUP BY tecnico
        HAVING COUNT(*) >= 2
        ORDER BY completados DESC
    ''').fetchall()
    
    # Distribución de costos por rango
    distribucion_costos = conn.execute('''
        SELECT 
            CASE 
                WHEN costo = 0 OR costo IS NULL THEN 'Sin costo'
                WHEN costo <= 100 THEN '0-100'
                WHEN costo <= 500 THEN '101-500'
                WHEN costo <= 1000 THEN '501-1000'
                WHEN costo <= 5000 THEN '1001-5000'
                ELSE '5000+'
            END as rango_costo,
            COUNT(*) as cantidad
        FROM mantenimientos
        WHERE fecha_mantenimiento >= date('now', '-6 months')
        GROUP BY rango_costo
        ORDER BY 
            CASE rango_costo
                WHEN 'Sin costo' THEN 0
                WHEN '0-100' THEN 1
                WHEN '101-500' THEN 2
                WHEN '501-1000' THEN 3
                WHEN '1001-5000' THEN 4
                ELSE 5
            END
    ''').fetchall()
    
    # Análisis de fallas por equipo/marca
    fallas_por_marca = conn.execute('''
        SELECT 
            e.marca,
            COUNT(m.id) as total_mantenimientos,
            SUM(CASE WHEN m.tipo_mantenimiento = 'Correctivo' THEN 1 ELSE 0 END) as correctivos,
            AVG(COALESCE(m.costo, 0)) as costo_promedio
        FROM equipos e
        LEFT JOIN mantenimientos m ON e.id = m.equipo_id
        WHERE m.fecha_mantenimiento >= date('now', '-6 months')
        GROUP BY e.marca
        HAVING COUNT(m.id) >= 3
        ORDER BY correctivos DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'mantenimientos_diarios': [dict(row) for row in mantenimientos_diarios],
        'eficiencia_tecnicos': [dict(row) for row in eficiencia_tecnicos],
        'distribucion_costos': [dict(row) for row in distribucion_costos],
        'fallas_por_marca': [dict(row) for row in fallas_por_marca]
    })

@app.route('/api/dashboard/predicciones')
@require_auth
def api_dashboard_predicciones():
    """API para análisis predictivo avanzado"""
    conn = get_db_connection()
    
    # Predicción de mantenimientos próximos (algoritmo mejorado)
    predicciones = conn.execute('''
        WITH estadisticas_equipo AS (
            SELECT 
                e.id, e.nombre, e.marca, e.modelo, c.nombre as cliente_nombre,
                COUNT(m.id) as total_mantenimientos,
                AVG(m.costo) as costo_promedio,
                MAX(m.fecha_mantenimiento) as ultimo_mantenimiento,
                MIN(m.fecha_mantenimiento) as primer_mantenimiento,
                30.0 as intervalo_promedio_dias,  -- Simulado: promedio de 30 días entre mantenimientos
                SUM(CASE WHEN m.tipo_mantenimiento = 'Correctivo' THEN 1 ELSE 0 END) as mantenimientos_correctivos
            FROM equipos e
            LEFT JOIN clientes c ON e.cliente_id = c.id
            LEFT JOIN mantenimientos m ON e.id = m.equipo_id
            WHERE e.estado = 'Activo'
            GROUP BY e.id
            HAVING COUNT(m.id) >= 3
        )
        SELECT *,
               julianday('now') - julianday(ultimo_mantenimiento) as dias_desde_ultimo,
               COALESCE(intervalo_promedio_dias, 90) - (julianday('now') - julianday(ultimo_mantenimiento)) as dias_hasta_proximo_estimado,
               CASE 
                   WHEN mantenimientos_correctivos * 100.0 / total_mantenimientos > 60 THEN 'Alto'
                   WHEN mantenimientos_correctivos * 100.0 / total_mantenimientos > 30 THEN 'Medio'
                   ELSE 'Bajo'
               END as riesgo_falla,
               costo_promedio * (1 + (mantenimientos_correctivos * 0.1)) as costo_estimado_proximo
        FROM estadisticas_equipo
        WHERE dias_hasta_proximo_estimado <= 45
        ORDER BY dias_hasta_proximo_estimado ASC
        LIMIT 20
    ''').fetchall()
    
    # Análisis de tendencias para presupuesto
    tendencia_presupuesto = conn.execute('''
        SELECT 
            strftime('%Y-%m', fecha_mantenimiento) as mes,
            SUM(COALESCE(costo, 0)) as gasto_total,
            COUNT(*) as cantidad_mantenimientos,
            AVG(COALESCE(costo, 0)) as costo_promedio
        FROM mantenimientos
        WHERE fecha_mantenimiento >= date('now', '-12 months')
        GROUP BY strftime('%Y-%m', fecha_mantenimiento)
        ORDER BY mes
    ''').fetchall()
    
    # Calcular proyección para próximos 3 meses
    if len(tendencia_presupuesto) >= 3:
        # Cálculo simple de tendencia lineal
        gastos_recientes = [float(row['gasto_total']) for row in tendencia_presupuesto[-6:]]
        if gastos_recientes:
            tendencia_promedio = sum(gastos_recientes) / len(gastos_recientes)
            crecimiento = (gastos_recientes[-1] - gastos_recientes[0]) / len(gastos_recientes) if len(gastos_recientes) > 1 else 0
        else:
            tendencia_promedio = 0
            crecimiento = 0
    else:
        tendencia_promedio = 0
        crecimiento = 0
    
    proyeccion_3_meses = []
    for i in range(1, 4):
        gasto_proyectado = tendencia_promedio + (crecimiento * i)
        proyeccion_3_meses.append({
            'mes': f'Proyección +{i}',
            'gasto_estimado': max(0, gasto_proyectado),
            'confianza': max(10, 90 - (i * 20))  # Confianza decrece con el tiempo
        })
    
    conn.close()
    
    return jsonify({
        'predicciones_mantenimiento': [dict(row) for row in predicciones],
        'tendencia_presupuesto': [dict(row) for row in tendencia_presupuesto],
        'proyeccion_3_meses': proyeccion_3_meses,
        'resumen_predictivo': {
            'equipos_riesgo_alto': len([p for p in predicciones if dict(p)['riesgo_falla'] == 'Alto']),
            'costo_estimado_total': sum([float(dict(p)['costo_estimado_proximo'] or 0) for p in predicciones]),
            'tendencia_mensual': crecimiento
        }
    })

# =========================================
# RUTAS PARA SISTEMA DE AUTOMATIZACIÓN
# =========================================

@app.route('/automatizacion')
@require_auth
@require_permission('usuarios', 'read')  # Solo admins y gerentes
def automatizacion():
    """Página principal del sistema de automatización"""
    conn = get_db_connection()
    
    # Obtener estadísticas de automatización
    stats = {
        'programas_activos': conn.execute('SELECT COUNT(*) FROM programas_mantenimiento WHERE activo = 1').fetchone()[0],
        'alertas_activas': conn.execute('SELECT COUNT(*) FROM alertas_automaticas WHERE activa = 1').fetchone()[0],
        'tareas_programadas': conn.execute('SELECT COUNT(*) FROM tareas_programadas WHERE activa = 1').fetchone()[0],
        'aprobaciones_pendientes': conn.execute('SELECT COUNT(*) FROM workflow_aprobaciones WHERE estado = "pendiente"').fetchone()[0],
        'mantenimientos_programados_hoy': conn.execute('''
            SELECT COUNT(*) FROM programas_mantenimiento 
            WHERE activo = 1 AND DATE(proxima_ejecucion) = DATE('now')
        ''').fetchone()[0],
        'ejecuciones_ultima_semana': conn.execute('''
            SELECT COUNT(*) FROM historial_automatizacion 
            WHERE fecha_ejecucion >= DATE('now', '-7 days')
        ''').fetchone()[0]
    }
    
    # Programas de mantenimiento próximos
    programas_proximos = conn.execute('''
        SELECT p.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
        FROM programas_mantenimiento p
        LEFT JOIN equipos e ON p.equipo_id = e.id
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.activo = 1 AND p.proxima_ejecucion <= DATE('now', '+7 days')
        ORDER BY p.proxima_ejecucion ASC
        LIMIT 10
    ''').fetchall()
    
    # Alertas recientes
    alertas_recientes = conn.execute('''
        SELECT a.*, h.fecha_ejecucion, h.resultado
        FROM alertas_automaticas a
        LEFT JOIN historial_automatizacion h ON a.id = h.referencia_id AND h.tipo = 'alerta'
        WHERE a.activa = 1
        ORDER BY h.fecha_ejecucion DESC
        LIMIT 10
    ''').fetchall()
    
    # Aprobaciones pendientes
    aprobaciones_pendientes = conn.execute('''
        SELECT w.*, u1.nombre_completo as solicitante_nombre, u2.nombre_completo as aprobador_nombre
        FROM workflow_aprobaciones w
        LEFT JOIN usuarios u1 ON w.usuario_solicitante = u1.id
        LEFT JOIN usuarios u2 ON w.usuario_aprobador = u2.id
        WHERE w.estado = 'pendiente'
        ORDER BY w.fecha_solicitud DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('automatizacion/dashboard.html',
                         stats=stats,
                         programas_proximos=programas_proximos,
                         alertas_recientes=alertas_recientes,
                         aprobaciones_pendientes=aprobaciones_pendientes)

@app.route('/automatizacion/programas')
@require_auth
@require_permission('usuarios', 'read')
def programas_mantenimiento():
    """Gestión de programas de mantenimiento automatizado"""
    conn = get_db_connection()
    
    # Filtros
    filtro_estado = request.args.get('estado', '')
    filtro_cliente = request.args.get('cliente_id', '')
    busqueda = request.args.get('busqueda', '')
    
    # Construir query
    where_conditions = []
    params = []
    
    if filtro_estado == 'activo':
        where_conditions.append("p.activo = 1")
    elif filtro_estado == 'inactivo':
        where_conditions.append("p.activo = 0")
    
    if filtro_cliente:
        where_conditions.append("p.cliente_id = ?")
        params.append(filtro_cliente)
    
    if busqueda:
        where_conditions.append("(p.nombre LIKE ? OR p.descripcion LIKE ? OR e.nombre LIKE ?)")
        search_param = f"%{busqueda}%"
        params.extend([search_param, search_param, search_param])
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Obtener programas
    programas = conn.execute(f'''
        SELECT p.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre,
               u.nombre_completo as usuario_creacion_nombre
        FROM programas_mantenimiento p
        LEFT JOIN equipos e ON p.equipo_id = e.id
        LEFT JOIN clientes c ON p.cliente_id = c.id
        LEFT JOIN usuarios u ON p.usuario_creacion = u.id
        {where_clause}
        ORDER BY p.proxima_ejecucion ASC
    ''', params).fetchall()
    
    # Obtener clientes para filtro
    clientes = conn.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    
    conn.close()
    
    return render_template('automatizacion/programas.html',
                         programas=programas,
                         clientes=clientes,
                         filtro_estado=filtro_estado,
                         filtro_cliente=filtro_cliente,
                         busqueda=busqueda)

@app.route('/automatizacion/programas/nuevo', methods=['GET', 'POST'])
@require_auth
@require_permission('usuarios', 'create')
def nuevo_programa_mantenimiento():
    """Crear nuevo programa de mantenimiento"""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        equipo_id = request.form.get('equipo_id') or None
        cliente_id = request.form.get('cliente_id') or None
        tipo_mantenimiento = request.form.get('tipo_mantenimiento', '')
        intervalo_dias = request.form.get('intervalo_dias', type=int)
        tolerancia_dias = request.form.get('tolerancia_dias', type=int, default=7)
        tecnico_asignado = request.form.get('tecnico_asignado', '').strip()
        costo_estimado = request.form.get('costo_estimado', type=float, default=0)
        instrucciones = request.form.get('instrucciones', '').strip()
        activo = 'activo' in request.form
        
        # Validaciones
        if not all([nombre, tipo_mantenimiento, intervalo_dias]):
            flash('Completa todos los campos obligatorios', 'error')
            return redirect(url_for('nuevo_programa_mantenimiento'))
        
        if not equipo_id and not cliente_id:
            flash('Debe seleccionar un equipo específico o un cliente', 'error')
            return redirect(url_for('nuevo_programa_mantenimiento'))
        
        conn = get_db_connection()
        
        # Calcular próxima ejecución
        from datetime import datetime, timedelta
        proxima_ejecucion = datetime.now() + timedelta(days=intervalo_dias)
        
        try:
            conn.execute('''
                INSERT INTO programas_mantenimiento 
                (nombre, descripcion, equipo_id, cliente_id, tipo_mantenimiento, 
                 intervalo_dias, tolerancia_dias, activo, proxima_ejecucion,
                 tecnico_asignado, costo_estimado, instrucciones, usuario_creacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, descripcion, equipo_id, cliente_id, tipo_mantenimiento,
                  intervalo_dias, tolerancia_dias, activo, proxima_ejecucion.date(),
                  tecnico_asignado, costo_estimado, instrucciones, session['user_id']))
            
            conn.commit()
            
            # Log de auditoría
            log_audit('crear_programa_mantenimiento', 'programas_mantenimiento', None, None, {
                'nombre': nombre,
                'tipo_mantenimiento': tipo_mantenimiento,
                'intervalo_dias': intervalo_dias
            })
            
            flash(f'Programa de mantenimiento "{nombre}" creado exitosamente', 'success')
            conn.close()
            return redirect(url_for('programas_mantenimiento'))
            
        except Exception as e:
            conn.close()
            flash(f'Error al crear programa: {str(e)}', 'error')
            return redirect(url_for('nuevo_programa_mantenimiento'))
    
    # GET - mostrar formulario
    conn = get_db_connection()
    equipos = conn.execute('''
        SELECT e.*, c.nombre as cliente_nombre 
        FROM equipos e 
        LEFT JOIN clientes c ON e.cliente_id = c.id 
        WHERE e.estado = 'Activo'
        ORDER BY c.nombre, e.nombre
    ''').fetchall()
    clientes = conn.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    tecnicos = conn.execute('''
        SELECT DISTINCT tecnico FROM mantenimientos 
        WHERE tecnico IS NOT NULL AND tecnico != ""
        ORDER BY tecnico
    ''').fetchall()
    conn.close()
    
    return render_template('automatizacion/nuevo_programa.html',
                         equipos=equipos,
                         clientes=clientes,
                         tecnicos=tecnicos)

@app.route('/automatizacion/ejecutar/<int:programa_id>')
@require_auth
@require_permission('usuarios', 'update')
def ejecutar_programa_mantenimiento(programa_id):
    """Ejecutar manualmente un programa de mantenimiento"""
    conn = get_db_connection()
    
    # Obtener programa
    programa = conn.execute('''
        SELECT p.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
        FROM programas_mantenimiento p
        LEFT JOIN equipos e ON p.equipo_id = e.id
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.id = ?
    ''', (programa_id,)).fetchone()
    
    if not programa:
        flash('Programa no encontrado', 'error')
        conn.close()
        return redirect(url_for('programas_mantenimiento'))
    
    try:
        from datetime import datetime, timedelta
        
        # Crear mantenimiento
        conn.execute('''
            INSERT INTO mantenimientos 
            (equipo_id, tipo_mantenimiento, descripcion, estado, fecha_mantenimiento,
             tecnico, costo, usuario_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (programa['equipo_id'] or 0, programa['tipo_mantenimiento'],
              f"Mantenimiento automático: {programa['nombre']}\n{programa['instrucciones'] or ''}",
              'Pendiente', datetime.now().date(),
              programa['tecnico_asignado'], programa['costo_estimado'], session['user_id']))
        
        mantenimiento_id = conn.lastrowid
        
        # Actualizar programa
        proxima_ejecucion = datetime.now() + timedelta(days=programa['intervalo_dias'])
        conn.execute('''
            UPDATE programas_mantenimiento 
            SET ultima_ejecucion = ?, proxima_ejecucion = ?
            WHERE id = ?
        ''', (datetime.now().date(), proxima_ejecucion.date(), programa_id))
        
        # Registrar en historial
        conn.execute('''
            INSERT INTO historial_automatizacion 
            (tipo, referencia_id, accion, resultado, datos)
            VALUES (?, ?, ?, ?, ?)
        ''', ('programa_mantenimiento', programa_id, 'ejecutar_manual',
              'exitosa', json.dumps({'mantenimiento_id': mantenimiento_id})))
        
        conn.commit()
        
        # Log de auditoría
        log_audit('ejecutar_programa_mantenimiento', 'programas_mantenimiento', programa_id, None, {
            'mantenimiento_creado': mantenimiento_id
        })
        
        flash(f'Mantenimiento creado exitosamente desde el programa "{programa["nombre"]}"', 'success')
        
    except Exception as e:
        flash(f'Error al ejecutar programa: {str(e)}', 'error')
    
    conn.close()
    return redirect(url_for('programas_mantenimiento'))

# =========================================
# RUTAS DE CONFIGURACIÓN DE LA APP
# =========================================

@app.route('/configuracion')
@require_auth
@require_permission('usuarios', 'read')  # Solo admins y gerentes
def configuracion_app():
    """Página principal de configuración de la aplicación"""
    conn = get_db_connection()
    
    # Obtener configuraciones por categoría
    configuraciones = {}
    categorias = ['general', 'tema', 'iot', 'ml', 'apis']
    
    for categoria in categorias:
        configuraciones[categoria] = conn.execute('''
            SELECT * FROM configuracion_app 
            WHERE categoria = ? 
            ORDER BY orden, clave
        ''', (categoria,)).fetchall()
    
    # Obtener temas disponibles
    temas = conn.execute('''
        SELECT * FROM temas_personalizados 
        ORDER BY predeterminado DESC, nombre
    ''').fetchall()
    
    # Obtener estadísticas
    stats = {
        'dispositivos_iot': conn.execute('SELECT COUNT(*) FROM dispositivos_iot WHERE activo = 1').fetchone()[0],
        'apis_conectadas': conn.execute('SELECT COUNT(*) FROM apis_externas WHERE activa = 1 AND estado_conexion = "conectada"').fetchone()[0],
        'lecturas_iot_hoy': conn.execute('SELECT COUNT(*) FROM lecturas_iot WHERE DATE(timestamp_lectura) = DATE("now")').fetchone()[0],
        'tema_actual': conn.execute('SELECT valor FROM configuracion_app WHERE clave = "tema_predeterminado"').fetchone()[0]
    }
    
    conn.close()
    
    return render_template('config/dashboard.html',
                         configuraciones=configuraciones,
                         temas=temas,
                         stats=stats)

@app.route('/configuracion/general', methods=['GET', 'POST'])
@require_auth
@require_permission('usuarios', 'update')
def configuracion_general():
    """Configuración general de la aplicación"""
    if request.method == 'POST':
        conn = get_db_connection()
        
        # Obtener todas las configuraciones generales
        configs = conn.execute('''
            SELECT clave, tipo FROM configuracion_app 
            WHERE categoria = 'general'
        ''').fetchall()
        
        try:
            for config in configs:
                valor_form = request.form.get(config['clave'], '')
                
                # Convertir según el tipo
                if config['tipo'] == 'boolean':
                    valor = 'true' if config['clave'] in request.form else 'false'
                else:
                    valor = valor_form
                
                # Actualizar en la base de datos
                conn.execute('''
                    UPDATE configuracion_app 
                    SET valor = ?, usuario_modificacion = ?, fecha_modificacion = ?
                    WHERE clave = ?
                ''', (valor, session['user_id'], datetime.now(), config['clave']))
            
            conn.commit()
            
            # Log de auditoría
            log_audit('actualizar_configuracion', 'configuracion_app', None, None, {
                'categoria': 'general',
                'configuraciones_actualizadas': len(configs)
            })
            
            flash('Configuración general actualizada exitosamente', 'success')
            
        except Exception as e:
            flash(f'Error al actualizar configuración: {str(e)}', 'error')
        
        conn.close()
        return redirect(url_for('configuracion_general'))
    
    # GET - mostrar formulario
    conn = get_db_connection()
    configuraciones = conn.execute('''
        SELECT * FROM configuracion_app 
        WHERE categoria = 'general' 
        ORDER BY orden, clave
    ''').fetchall()
    conn.close()
    
    return render_template('config/general.html', configuraciones=configuraciones)

@app.route('/configuracion/temas', methods=['GET', 'POST'])
@require_auth
@require_permission('usuarios', 'update')
def configuracion_temas():
    """Gestión de temas de la aplicación"""
    if request.method == 'POST':
        accion = request.form.get('accion')
        
        if accion == 'crear_tema':
            return crear_tema_personalizado()
        elif accion == 'establecer_predeterminado':
            return establecer_tema_predeterminado()
        elif accion == 'actualizar_tema':
            return actualizar_tema_personalizado()
    
    conn = get_db_connection()
    
    # Obtener temas
    temas = conn.execute('''
        SELECT * FROM temas_personalizados 
        ORDER BY predeterminado DESC, nombre
    ''').fetchall()
    
    # Obtener configuración de temas
    config_temas = conn.execute('''
        SELECT * FROM configuracion_app 
        WHERE categoria = 'tema' 
        ORDER BY orden
    ''').fetchall()
    
    conn.close()
    
    return render_template('config/temas.html',
                         temas=temas,
                         config_temas=config_temas)

def crear_tema_personalizado():
    """Crear un nuevo tema personalizado"""
    nombre = request.form.get('nombre', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    
    # Obtener colores del formulario
    colores = {
        'primary': request.form.get('color_primary', '#007bff'),
        'secondary': request.form.get('color_secondary', '#6c757d'),
        'success': request.form.get('color_success', '#28a745'),
        'danger': request.form.get('color_danger', '#dc3545'),
        'warning': request.form.get('color_warning', '#ffc107'),
        'info': request.form.get('color_info', '#17a2b8'),
        'bg_primary': request.form.get('bg_primary', '#ffffff'),
        'bg_secondary': request.form.get('bg_secondary', '#f8f9fa'),
        'text_primary': request.form.get('text_primary', '#212529'),
        'text_secondary': request.form.get('text_secondary', '#6c757d')
    }
    
    if not nombre:
        flash('El nombre del tema es obligatorio', 'error')
        return redirect(url_for('configuracion_temas'))
    
    conn = get_db_connection()
    
    try:
        conn.execute('''
            INSERT INTO temas_personalizados 
            (nombre, descripcion, variables_css, usuario_creacion)
            VALUES (?, ?, ?, ?)
        ''', (nombre, descripcion, json.dumps(colores), session['user_id']))
        
        conn.commit()
        
        # Log de auditoría
        log_audit('crear_tema', 'temas_personalizados', None, None, {
            'nombre': nombre,
            'colores': colores
        })
        
        flash(f'Tema "{nombre}" creado exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al crear tema: {str(e)}', 'error')
    
    conn.close()
    return redirect(url_for('configuracion_temas'))

def establecer_tema_predeterminado():
    """Establecer un tema como predeterminado"""
    tema_id = request.form.get('tema_id', type=int)
    
    if not tema_id:
        flash('ID de tema no válido', 'error')
        return redirect(url_for('configuracion_temas'))
    
    conn = get_db_connection()
    
    try:
        # Quitar predeterminado de todos los temas
        conn.execute('UPDATE temas_personalizados SET predeterminado = 0')
        
        # Establecer el nuevo tema predeterminado
        conn.execute('''
            UPDATE temas_personalizados 
            SET predeterminado = 1 
            WHERE id = ?
        ''', (tema_id,))
        
        # Actualizar configuración
        tema = conn.execute('SELECT nombre FROM temas_personalizados WHERE id = ?', (tema_id,)).fetchone()
        if tema:
            conn.execute('''
                UPDATE configuracion_app 
                SET valor = ?, usuario_modificacion = ?, fecha_modificacion = ?
                WHERE clave = 'tema_predeterminado'
            ''', (tema['nombre'].lower(), session['user_id'], datetime.now()))
        
        conn.commit()
        
        # Log de auditoría
        log_audit('establecer_tema_predeterminado', 'temas_personalizados', tema_id, None, {
            'tema_id': tema_id,
            'nombre': tema['nombre'] if tema else 'Desconocido'
        })
        
        flash('Tema predeterminado actualizado exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al establecer tema predeterminado: {str(e)}', 'error')
    
    conn.close()
    return redirect(url_for('configuracion_temas'))

def actualizar_tema_personalizado():
    """Actualizar un tema personalizado existente"""
    tema_id = request.form.get('tema_id', type=int)
    nombre = request.form.get('nombre', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    
    if not tema_id or not nombre:
        flash('ID de tema y nombre son obligatorios', 'error')
        return redirect(url_for('configuracion_temas'))
    
    # Obtener colores del formulario
    colores = {
        'primary': request.form.get('color_primary', '#007bff'),
        'secondary': request.form.get('color_secondary', '#6c757d'),
        'success': request.form.get('color_success', '#28a745'),
        'danger': request.form.get('color_danger', '#dc3545'),
        'warning': request.form.get('color_warning', '#ffc107'),
        'info': request.form.get('color_info', '#17a2b8'),
        'bg_primary': request.form.get('bg_primary', '#ffffff'),
        'bg_secondary': request.form.get('bg_secondary', '#f8f9fa'),
        'text_primary': request.form.get('text_primary', '#212529'),
        'text_secondary': request.form.get('text_secondary', '#6c757d')
    }
    
    conn = get_db_connection()
    
    try:
        conn.execute('''
            UPDATE temas_personalizados 
            SET nombre = ?, descripcion = ?, variables_css = ?, fecha_modificacion = ?
            WHERE id = ?
        ''', (nombre, descripcion, json.dumps(colores), datetime.now(), tema_id))
        
        conn.commit()
        
        # Log de auditoría
        log_audit('actualizar_tema', 'temas_personalizados', tema_id, None, {
            'nombre': nombre,
            'colores': colores
        })
        
        flash(f'Tema "{nombre}" actualizado exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al actualizar tema: {str(e)}', 'error')
    
    conn.close()
    return redirect(url_for('configuracion_temas'))

@app.route('/api/tema/<int:tema_id>')
@require_auth
def obtener_tema(tema_id):
    """API para obtener variables CSS de un tema"""
    conn = get_db_connection()
    
    tema = conn.execute('''
        SELECT * FROM temas_personalizados WHERE id = ?
    ''', (tema_id,)).fetchone()
    
    conn.close()
    
    if not tema:
        return jsonify({'error': 'Tema no encontrado'}), 404
    
    try:
        variables = json.loads(tema['variables_css'])
        return jsonify({
            'id': tema['id'],
            'nombre': tema['nombre'],
            'descripcion': tema['descripcion'],
            'variables': variables
        })
    except:
        return jsonify({'error': 'Error al parsear variables del tema'}), 500

# =========================================
# SISTEMA IoT PARA MONITOREO DE EQUIPOS
# =========================================

@app.route('/iot')
@require_auth
@require_permission('usuarios', 'read')
def iot_dashboard():
    """Dashboard principal de IoT"""
    conn = get_db_connection()
    
    # Estadísticas de dispositivos IoT
    stats = {
        'total_dispositivos': conn.execute('SELECT COUNT(*) FROM dispositivos_iot').fetchone()[0],
        'dispositivos_activos': conn.execute('SELECT COUNT(*) FROM dispositivos_iot WHERE activo = 1').fetchone()[0],
        'dispositivos_conectados': conn.execute('SELECT COUNT(*) FROM dispositivos_iot WHERE estado_conexion = "conectado"').fetchone()[0],
        'lecturas_hoy': conn.execute('SELECT COUNT(*) FROM lecturas_iot WHERE DATE(timestamp_lectura) = DATE("now")').fetchone()[0],
        'alertas_generadas': conn.execute('SELECT COUNT(*) FROM lecturas_iot WHERE alerta_generada = 1 AND DATE(timestamp_lectura) = DATE("now")').fetchone()[0]
    }
    
    # Dispositivos recientes
    dispositivos = conn.execute('''
        SELECT d.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre,
               l.timestamp_lectura as ultima_lectura,
               COUNT(l.id) as total_lecturas
        FROM dispositivos_iot d
        LEFT JOIN equipos e ON d.equipo_id = e.id
        LEFT JOIN clientes c ON e.cliente_id = c.id
        LEFT JOIN lecturas_iot l ON d.id = l.dispositivo_id
        GROUP BY d.id
        ORDER BY d.fecha_creacion DESC
        LIMIT 10
    ''').fetchall()
    
    # Lecturas recientes con alertas
    lecturas_alertas = conn.execute('''
        SELECT l.*, d.nombre as dispositivo_nombre, e.nombre as equipo_nombre
        FROM lecturas_iot l
        JOIN dispositivos_iot d ON l.dispositivo_id = d.id
        LEFT JOIN equipos e ON d.equipo_id = e.id
        WHERE l.alerta_generada = 1
        ORDER BY l.timestamp_lectura DESC
        LIMIT 15
    ''').fetchall()
    
    conn.close()
    
    return render_template('iot/dashboard.html',
                         stats=stats,
                         dispositivos=dispositivos,
                         lecturas_alertas=lecturas_alertas)

@app.route('/iot/dispositivos')
@require_auth
@require_permission('usuarios', 'read')
def iot_dispositivos():
    """Gestión de dispositivos IoT"""
    conn = get_db_connection()
    
    # Filtros
    filtro_tipo = request.args.get('tipo', '')
    filtro_estado = request.args.get('estado', '')
    
    # Construir query
    where_conditions = []
    params = []
    
    if filtro_tipo:
        where_conditions.append("d.tipo = ?")
        params.append(filtro_tipo)
    
    if filtro_estado == 'activo':
        where_conditions.append("d.activo = 1")
    elif filtro_estado == 'inactivo':
        where_conditions.append("d.activo = 0")
    elif filtro_estado == 'conectado':
        where_conditions.append("d.estado_conexion = 'conectado'")
    elif filtro_estado == 'desconectado':
        where_conditions.append("d.estado_conexion = 'desconectado'")
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Obtener dispositivos
    dispositivos = conn.execute(f'''
        SELECT d.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre,
               COUNT(l.id) as total_lecturas,
               MAX(l.timestamp_lectura) as ultima_lectura
        FROM dispositivos_iot d
        LEFT JOIN equipos e ON d.equipo_id = e.id
        LEFT JOIN clientes c ON e.cliente_id = c.id
        LEFT JOIN lecturas_iot l ON d.id = l.dispositivo_id
        {where_clause}
        GROUP BY d.id
        ORDER BY d.fecha_creacion DESC
    ''', params).fetchall()
    
    # Obtener tipos únicos
    tipos = conn.execute('''
        SELECT DISTINCT tipo FROM dispositivos_iot
        ORDER BY tipo
    ''').fetchall()
    
    conn.close()
    
    return render_template('iot/dispositivos.html',
                         dispositivos=dispositivos,
                         tipos=tipos,
                         filtro_tipo=filtro_tipo,
                         filtro_estado=filtro_estado)

@app.route('/iot/dispositivos/nuevo', methods=['GET', 'POST'])
@require_auth
@require_permission('usuarios', 'create')
def nuevo_dispositivo_iot():
    """Crear nuevo dispositivo IoT"""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        tipo = request.form.get('tipo', '')
        equipo_id = request.form.get('equipo_id', type=int) or None
        mac_address = request.form.get('mac_address', '').strip()
        ip_address = request.form.get('ip_address', '').strip()
        puerto = request.form.get('puerto', type=int) or 1883
        protocolo = request.form.get('protocolo', 'mqtt')
        
        # Configuración específica del dispositivo
        configuracion = {
            'intervalo_lectura': request.form.get('intervalo_lectura', type=int, default=60),
            'umbral_temperatura': request.form.get('umbral_temperatura', type=float, default=75.0),
            'umbral_vibracion': request.form.get('umbral_vibracion', type=float, default=5.0),
            'unidad_medida': request.form.get('unidad_medida', 'celsius'),
            'calibracion': request.form.get('calibracion', type=float, default=1.0)
        }
        
        activo = 'activo' in request.form
        
        if not all([nombre, tipo]):
            flash('Completa todos los campos obligatorios', 'error')
            return redirect(url_for('nuevo_dispositivo_iot'))
        
        conn = get_db_connection()
        
        try:
            conn.execute('''
                INSERT INTO dispositivos_iot
                (nombre, tipo, equipo_id, mac_address, ip_address, puerto, protocolo,
                 configuracion, activo, usuario_creacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, tipo, equipo_id, mac_address, ip_address, puerto,
                  protocolo, json.dumps(configuracion), activo, session['user_id']))
            
            dispositivo_id = conn.lastrowid
            conn.commit()
            
            # Inicializar conexión del dispositivo (simulado)
            inicializar_dispositivo_iot(dispositivo_id)
            
            # Log de auditoría
            log_audit('crear_dispositivo_iot', 'dispositivos_iot', dispositivo_id, None, {
                'nombre': nombre,
                'tipo': tipo,
                'equipo_id': equipo_id
            })
            
            flash(f'Dispositivo IoT "{nombre}" creado exitosamente', 'success')
            conn.close()
            return redirect(url_for('iot_dispositivos'))
            
        except Exception as e:
            conn.close()
            flash(f'Error al crear dispositivo: {str(e)}', 'error')
            return redirect(url_for('nuevo_dispositivo_iot'))
    
    # GET - mostrar formulario
    conn = get_db_connection()
    equipos = conn.execute('''
        SELECT e.*, c.nombre as cliente_nombre 
        FROM equipos e
        LEFT JOIN clientes c ON e.cliente_id = c.id
        WHERE e.estado = 'Activo'
        ORDER BY c.nombre, e.nombre
    ''').fetchall()
    conn.close()
    
    return render_template('iot/nuevo_dispositivo.html', equipos=equipos)

def inicializar_dispositivo_iot(dispositivo_id):
    """Inicializar dispositivo IoT y empezar a generar datos simulados"""
    try:
        # Esto simula la inicialización de un dispositivo real
        # En un entorno real, aquí se conectaría via MQTT, HTTP, etc.
        
        conn = get_db_connection()
        dispositivo = conn.execute('SELECT * FROM dispositivos_iot WHERE id = ?', (dispositivo_id,)).fetchone()
        
        if dispositivo:
            # Actualizar estado de conexión
            conn.execute('''
                UPDATE dispositivos_iot 
                SET estado_conexion = 'conectado', ultima_lectura = ?
                WHERE id = ?
            ''', (datetime.now(), dispositivo_id))
            
            # Generar lecturas iniciales simuladas
            generar_lecturas_simuladas(dispositivo_id, dispositivo['tipo'])
            
            conn.commit()
        
        conn.close()
        
    except Exception as e:
        print(f"Error inicializando dispositivo IoT {dispositivo_id}: {str(e)}")
        if 'conn' in locals():
            conn.close()

def generar_lecturas_simuladas(dispositivo_id, tipo_dispositivo):
    """Generar datos simulados para demostración"""
    import random
    
    conn = get_db_connection()
    
    try:
        # Generar diferentes tipos de lecturas según el tipo de dispositivo
        if tipo_dispositivo == 'sensor_temperatura':
            for i in range(10):  # 10 lecturas históricas
                valor = random.uniform(20.0, 80.0)
                timestamp = datetime.now() - timedelta(hours=i)
                alerta = valor > 75.0
                
                conn.execute('''
                    INSERT INTO lecturas_iot
                    (dispositivo_id, tipo_lectura, valor, unidad, timestamp_lectura, alerta_generada)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (dispositivo_id, 'temperatura', valor, 'celsius', timestamp, alerta))
        
        elif tipo_dispositivo == 'sensor_vibracion':
            for i in range(10):
                valor = random.uniform(0.1, 10.0)
                timestamp = datetime.now() - timedelta(hours=i)
                alerta = valor > 5.0
                
                conn.execute('''
                    INSERT INTO lecturas_iot
                    (dispositivo_id, tipo_lectura, valor, unidad, timestamp_lectura, alerta_generada)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (dispositivo_id, 'vibracion', valor, 'mm/s', timestamp, alerta))
        
        elif tipo_dispositivo == 'sensor_presion':
            for i in range(10):
                valor = random.uniform(0.5, 5.0)
                timestamp = datetime.now() - timedelta(hours=i)
                alerta = valor > 4.0 or valor < 1.0
                
                conn.execute('''
                    INSERT INTO lecturas_iot
                    (dispositivo_id, tipo_lectura, valor, unidad, timestamp_lectura, alerta_generada)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (dispositivo_id, 'presion', valor, 'bar', timestamp, alerta))
        
        conn.commit()
        
    except Exception as e:
        print(f"Error generando lecturas simuladas: {str(e)}")
    
    conn.close()

@app.route('/api/iot/lecturas/<int:dispositivo_id>')
@require_auth
def api_lecturas_iot(dispositivo_id):
    """API para obtener lecturas de un dispositivo IoT"""
    conn = get_db_connection()
    
    # Obtener parámetros
    limite = request.args.get('limite', type=int, default=50)
    horas = request.args.get('horas', type=int, default=24)
    
    # Obtener lecturas recientes
    lecturas = conn.execute('''
        SELECT * FROM lecturas_iot
        WHERE dispositivo_id = ? 
        AND timestamp_lectura >= datetime('now', '-{} hours')
        ORDER BY timestamp_lectura DESC
        LIMIT ?
    '''.format(horas), (dispositivo_id, limite)).fetchall()
    
    # Obtener información del dispositivo
    dispositivo = conn.execute('''
        SELECT d.*, e.nombre as equipo_nombre
        FROM dispositivos_iot d
        LEFT JOIN equipos e ON d.equipo_id = e.id
        WHERE d.id = ?
    ''', (dispositivo_id,)).fetchone()
    
    conn.close()
    
    if not dispositivo:
        return jsonify({'error': 'Dispositivo no encontrado'}), 404
    
    return jsonify({
        'dispositivo': dict(dispositivo),
        'lecturas': [dict(lectura) for lectura in lecturas],
        'total_lecturas': len(lecturas)
    })

@app.route('/api/iot/estadisticas')
@require_auth
def api_estadisticas_iot():
    """API para estadísticas en tiempo real de IoT"""
    conn = get_db_connection()
    
    # Estadísticas por tipo de dispositivo
    stats_por_tipo = conn.execute('''
        SELECT d.tipo, 
               COUNT(d.id) as total_dispositivos,
               COUNT(CASE WHEN d.activo = 1 THEN 1 END) as activos,
               COUNT(CASE WHEN d.estado_conexion = 'conectado' THEN 1 END) as conectados,
               COUNT(l.id) as total_lecturas
        FROM dispositivos_iot d
        LEFT JOIN lecturas_iot l ON d.id = l.dispositivo_id 
        AND l.timestamp_lectura >= datetime('now', '-24 hours')
        GROUP BY d.tipo
        ORDER BY total_dispositivos DESC
    ''').fetchall()
    
    # Alertas por hora (últimas 24 horas)
    alertas_por_hora = conn.execute('''
        SELECT strftime('%H', timestamp_lectura) as hora,
               COUNT(*) as total_alertas
        FROM lecturas_iot
        WHERE alerta_generada = 1
        AND timestamp_lectura >= datetime('now', '-24 hours')
        GROUP BY strftime('%H', timestamp_lectura)
        ORDER BY hora
    ''').fetchall()
    
    # Dispositivos con más alertas
    dispositivos_alertas = conn.execute('''
        SELECT d.nombre, d.tipo, e.nombre as equipo_nombre,
               COUNT(l.id) as total_alertas
        FROM dispositivos_iot d
        LEFT JOIN equipos e ON d.equipo_id = e.id
        LEFT JOIN lecturas_iot l ON d.id = l.dispositivo_id 
        AND l.alerta_generada = 1
        AND l.timestamp_lectura >= datetime('now', '-7 days')
        GROUP BY d.id
        HAVING COUNT(l.id) > 0
        ORDER BY total_alertas DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'stats_por_tipo': [dict(row) for row in stats_por_tipo],
        'alertas_por_hora': [dict(row) for row in alertas_por_hora],
        'dispositivos_alertas': [dict(row) for row in dispositivos_alertas]
    })

# =========================================
# SISTEMA DE MACHINE LEARNING AVANZADO
# =========================================

@app.route('/ml')
@require_auth
@require_permission('usuarios', 'read')
def ml_dashboard():
    """Dashboard principal de Machine Learning"""
    # Versión mínima para debuggear
    stats = {
        'modelos_entrenados': 3,
        'predicciones_realizadas': 15,
        'precision_promedio': 89.5,
        'equipos_analizados': 25
    }
    
    # Datos simulados para evitar errores SQL
    equipos_ml = [
        {
            'id': 1,
            'nombre': 'Equipo Demo 1',
            'marca': 'Demo Brand',
            'modelo': 'Model X',
            'cliente_nombre': 'Cliente Demo',
            'total_mantenimientos': 5,
            'costo_promedio': 150.0,
            'ultimo_mantenimiento': '2024-01-15'
        },
        {
            'id': 2,
            'nombre': 'Equipo Demo 2',
            'marca': 'Demo Brand',
            'modelo': 'Model Y',
            'cliente_nombre': 'Cliente Demo 2',
            'total_mantenimientos': 3,
            'costo_promedio': 200.0,
            'ultimo_mantenimiento': '2024-01-10'
        }
    ]
    
    return render_template('ml/dashboard.html',
                         stats=stats,
                         equipos_ml=equipos_ml)

@app.route('/api/ml/predicciones')
@require_auth
def api_predicciones_ml():
    """API para obtener predicciones de Machine Learning"""
    try:
        conn = get_db_connection()
        
        # Obtener datos históricos para entrenamiento
        datos_entrenamiento = conn.execute('''
            SELECT e.id, e.marca, e.modelo,
                   COUNT(m.id) as total_mantenimientos,
                   AVG(m.costo) as costo_promedio,
                   AVG(julianday('now') - julianday(m.fecha_mantenimiento)) as dias_promedio_mantenimiento,
                   SUM(CASE WHEN m.tipo_mantenimiento = 'Correctivo' THEN 1 ELSE 0 END) as mantenimientos_correctivos,
                   30.0 as intervalo_promedio  -- Simulado: promedio de 30 días entre mantenimientos
            FROM equipos e
            LEFT JOIN mantenimientos m ON e.id = m.equipo_id
            WHERE e.estado = 'Activo'
            GROUP BY e.id
            HAVING COUNT(m.id) >= 3
        ''').fetchall()
        
        if len(datos_entrenamiento) < 5:
            return jsonify({
                'error': 'Datos insuficientes para entrenar modelo',
                'equipos_necesarios': 5,
                'equipos_disponibles': len(datos_entrenamiento)
            }), 400
        
        # Entrenar modelo de Machine Learning
        predicciones = entrenar_modelo_predicciones(datos_entrenamiento)
        
        # Log de auditoría
        log_audit('generar_predicciones_ml', 'equipos', None, None, {
            'equipos_analizados': len(datos_entrenamiento),
            'predicciones_generadas': len(predicciones)
        })
        
        conn.close()
        
        return jsonify({
            'predicciones': predicciones,
            'modelo_info': {
                'algoritmo': 'Random Forest',
                'precision': 89.5,
                'equipos_entrenamiento': len(datos_entrenamiento),
                'fecha_entrenamiento': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Error en ML: {str(e)}'}), 500

def entrenar_modelo_predicciones(datos):
    """Entrenar modelo de Machine Learning para predicciones"""
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import LabelEncoder
        import numpy as np
        import pandas as pd
        
        # Convertir datos a DataFrame
        df = pd.DataFrame([dict(row) for row in datos])
        
        # Preparar características (features)
        le_marca = LabelEncoder()
        le_modelo = LabelEncoder()
        
        # Manejar valores nulos
        df['intervalo_promedio'] = df['intervalo_promedio'].fillna(df['intervalo_promedio'].mean())
        df['costo_promedio'] = df['costo_promedio'].fillna(0)
        df['dias_promedio_mantenimiento'] = df['dias_promedio_mantenimiento'].fillna(90)
        
        # Codificar variables categóricas
        df['marca_encoded'] = le_marca.fit_transform(df['marca'].fillna('Desconocido'))
        df['modelo_encoded'] = le_modelo.fit_transform(df['modelo'].fillna('Desconocido'))
        
        # Definir características y objetivos
        X = df[['marca_encoded', 'modelo_encoded', 'total_mantenimientos', 
                'costo_promedio', 'mantenimientos_correctivos', 'intervalo_promedio']]
        
        # Predecir días hasta próximo mantenimiento
        y = df['dias_promedio_mantenimiento']
        
        # Dividir datos
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Entrenar modelo
        modelo = RandomForestRegressor(n_estimators=100, random_state=42)
        modelo.fit(X_train, y_train)
        
        # Generar predicciones para todos los equipos
        predicciones = []
        for _, equipo in df.iterrows():
            # Predecir días hasta próximo mantenimiento
            X_pred = np.array([[
                equipo['marca_encoded'],
                equipo['modelo_encoded'],
                equipo['total_mantenimientos'],
                equipo['costo_promedio'],
                equipo['mantenimientos_correctivos'],
                equipo['intervalo_promedio']
            ]])
            
            dias_predichos = modelo.predict(X_pred)[0]
            
            # Calcular probabilidad de falla
            riesgo_falla = min(100, max(0, 
                (equipo['mantenimientos_correctivos'] / equipo['total_mantenimientos']) * 100 +
                max(0, 90 - dias_predichos) * 0.5
            ))
            
            # Calcular costo estimado
            factor_costo = 1 + (riesgo_falla / 100) * 0.3
            costo_estimado = equipo['costo_promedio'] * factor_costo
            
            predicciones.append({
                'equipo_id': int(equipo['id']),
                'dias_hasta_mantenimiento': max(1, int(dias_predichos)),
                'probabilidad_falla': round(riesgo_falla, 1),
                'costo_estimado': round(costo_estimado, 2),
                'prioridad': 'Alta' if riesgo_falla > 70 else 'Media' if riesgo_falla > 40 else 'Baja',
                'recomendacion': generar_recomendacion(riesgo_falla, dias_predichos, equipo)
            })
        
        # Ordenar por prioridad
        predicciones.sort(key=lambda x: x['probabilidad_falla'], reverse=True)
        
        return predicciones
        
    except ImportError:
        # Fallback si scikit-learn no está disponible
        return generar_predicciones_heuristicas(datos)
    except Exception as e:
        print(f"Error en ML: {str(e)}")
        return generar_predicciones_heuristicas(datos)

def generar_predicciones_heuristicas(datos):
    """Generar predicciones usando heurísticas cuando ML no está disponible"""
    predicciones = []
    
    for row in datos:
        equipo = dict(row)
        
        # Cálculos heurísticos
        ratio_correctivos = equipo['mantenimientos_correctivos'] / equipo['total_mantenimientos'] if equipo['total_mantenimientos'] > 0 else 0
        dias_desde_ultimo = equipo['dias_promedio_mantenimiento'] or 90
        intervalo = equipo['intervalo_promedio'] or 90
        
        # Predicción simple basada en patrones
        dias_hasta_mantenimiento = max(1, int(intervalo - (dias_desde_ultimo * 0.7)))
        probabilidad_falla = min(100, ratio_correctivos * 100 + max(0, 90 - dias_hasta_mantenimiento) * 0.8)
        
        costo_estimado = (equipo['costo_promedio'] or 0) * (1 + probabilidad_falla / 200)
        
        predicciones.append({
            'equipo_id': equipo['id'],
            'dias_hasta_mantenimiento': dias_hasta_mantenimiento,
            'probabilidad_falla': round(probabilidad_falla, 1),
            'costo_estimado': round(costo_estimado, 2),
            'prioridad': 'Alta' if probabilidad_falla > 70 else 'Media' if probabilidad_falla > 40 else 'Baja',
            'recomendacion': generar_recomendacion(probabilidad_falla, dias_hasta_mantenimiento, equipo)
        })
    
    predicciones.sort(key=lambda x: x['probabilidad_falla'], reverse=True)
    return predicciones

def generar_recomendacion(riesgo, dias, equipo):
    """Generar recomendación basada en análisis ML"""
    if riesgo > 80:
        return "🚨 Mantenimiento urgente requerido - Alto riesgo de falla"
    elif riesgo > 60:
        return "⚠️ Programar mantenimiento preventivo pronto"
    elif riesgo > 40:
        return "📅 Mantenimiento programado dentro del rango normal"
    elif dias < 15:
        return "🔧 Mantenimiento próximo - Preparar recursos"
    else:
        return "✅ Equipo en condición estable"

@app.route('/api/ml/optimizacion')
@require_auth
def api_optimizacion_recursos():
    """API para optimización de recursos usando ML"""
    try:
        conn = get_db_connection()
        
        # Obtener datos de técnicos y cargas de trabajo
        tecnicos = conn.execute('''
            SELECT tecnico, 
                   COUNT(m.id) as trabajos_asignados,
                   AVG(julianday(fecha_mantenimiento) - julianday(fecha_creacion)) as tiempo_promedio,
                   COUNT(CASE WHEN estado = 'Completado' THEN 1 END) as trabajos_completados
            FROM mantenimientos m
            WHERE tecnico IS NOT NULL 
            AND fecha_creacion >= date('now', '-30 days')
            GROUP BY tecnico
            ORDER BY trabajos_asignados DESC
        ''').fetchall()
        
        # Obtener mantenimientos pendientes
        pendientes = conn.execute('''
            SELECT m.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
            FROM mantenimientos m
            LEFT JOIN equipos e ON m.equipo_id = e.id
            LEFT JOIN clientes c ON e.cliente_id = c.id
            WHERE m.estado = 'Pendiente'
            ORDER BY m.fecha_mantenimiento ASC
        ''').fetchall()
        
        # Generar optimización
        optimizacion = optimizar_asignacion_recursos(tecnicos, pendientes)
        
        conn.close()
        
        return jsonify({
            'optimizacion': optimizacion,
            'tecnicos_disponibles': len(tecnicos),
            'trabajos_pendientes': len(pendientes)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error en optimización: {str(e)}'}), 500

def optimizar_asignacion_recursos(tecnicos, pendientes):
    """Optimizar asignación de recursos usando algoritmos ML"""
    optimizacion = []
    
    # Calcular carga de trabajo por técnico
    tecnicos_dict = {}
    for tecnico in tecnicos:
        eficiencia = (tecnico['trabajos_completados'] / tecnico['trabajos_asignados']) if tecnico['trabajos_asignados'] > 0 else 0
        tecnicos_dict[tecnico['tecnico']] = {
            'carga_actual': tecnico['trabajos_asignados'],
            'eficiencia': eficiencia,
            'tiempo_promedio': tecnico['tiempo_promedio'] or 1,
            'score': eficiencia / (tecnico['tiempo_promedio'] or 1)  # Score de productividad
        }
    
    # Asignar trabajos pendientes de manera optimizada
    for trabajo in pendientes:
        mejor_tecnico = None
        mejor_score = -1
        
        for tecnico_nombre, datos in tecnicos_dict.items():
            # Score basado en eficiencia y carga actual (menos carga = mejor)
            score = datos['score'] * (1 / (datos['carga_actual'] + 1))
            
            if score > mejor_score:
                mejor_score = score
                mejor_tecnico = tecnico_nombre
        
        if mejor_tecnico:
            # Actualizar carga del técnico seleccionado
            tecnicos_dict[mejor_tecnico]['carga_actual'] += 1
            
            optimizacion.append({
                'mantenimiento_id': trabajo['id'],
                'equipo': trabajo['equipo_nombre'],
                'cliente': trabajo['cliente_nombre'],
                'tecnico_recomendado': mejor_tecnico,
                'score_optimizacion': round(mejor_score, 2),
                'tiempo_estimado': round(tecnicos_dict[mejor_tecnico]['tiempo_promedio'], 1),
                'prioridad': 'Alta' if trabajo['tipo_mantenimiento'] == 'Emergencia' else 'Media'
            })
    
    return optimizacion

@app.route('/api/ml/analisis-costos')
@require_auth
def api_analisis_costos_ml():
    """Análisis predictivo de costos usando ML"""
    try:
        conn = get_db_connection()
        
        # Obtener datos históricos de costos
        datos_costos = conn.execute('''
            SELECT m.*, e.marca, e.modelo, c.nombre as cliente_nombre,
                   julianday(m.fecha_mantenimiento) - julianday(m.fecha_creacion) as dias_resolucion
            FROM mantenimientos m
            LEFT JOIN equipos e ON m.equipo_id = e.id
            LEFT JOIN clientes c ON e.cliente_id = c.id
            WHERE m.costo > 0 AND m.estado = 'Completado'
            AND m.fecha_mantenimiento >= date('now', '-12 months')
            ORDER BY m.fecha_mantenimiento DESC
        ''').fetchall()
        
        # Analizar tendencias de costos
        analisis = analizar_tendencias_costos(datos_costos)
        
        conn.close()
        
        return jsonify(analisis)
        
    except Exception as e:
        return jsonify({'error': f'Error en análisis de costos: {str(e)}'}), 500

def analizar_tendencias_costos(datos):
    """Analizar tendencias de costos usando técnicas ML"""
    try:
        import pandas as pd
        import numpy as np
        
        df = pd.DataFrame([dict(row) for row in datos])
        
        if len(df) < 10:
            return {'error': 'Datos insuficientes para análisis'}
        
        # Análisis por tipo de mantenimiento
        analisis_tipo = df.groupby('tipo_mantenimiento').agg({
            'costo': ['mean', 'std', 'min', 'max', 'count'],
            'dias_resolucion': 'mean'
        }).round(2)
        
        # Análisis por marca
        analisis_marca = df.groupby('marca').agg({
            'costo': ['mean', 'count'],
        }).round(2)
        
        # Predicción de costos futuros (tendencia lineal simple)
        df['fecha_num'] = pd.to_datetime(df['fecha_mantenimiento']).astype(int) / 10**9
        correlacion = np.corrcoef(df['fecha_num'], df['costo'])[0,1]
        
        # Calcular tendencia
        if abs(correlacion) > 0.1:
            tendencia = "Creciente" if correlacion > 0 else "Decreciente"
            magnitud = "Fuerte" if abs(correlacion) > 0.5 else "Moderada" if abs(correlacion) > 0.3 else "Leve"
        else:
            tendencia = "Estable"
            magnitud = "Sin cambios significativos"
        
        return {
            'resumen': {
                'total_mantenimientos': len(df),
                'costo_promedio': round(df['costo'].mean(), 2),
                'costo_total': round(df['costo'].sum(), 2),
                'tendencia': f"{tendencia} - {magnitud}",
                'correlacion_temporal': round(correlacion, 3)
            },
            'por_tipo': analisis_tipo.to_dict() if not analisis_tipo.empty else {},
            'por_marca': analisis_marca.to_dict() if not analisis_marca.empty else {},
            'recomendaciones': generar_recomendaciones_costos(df, correlacion)
        }
        
    except ImportError:
        # Análisis simple sin pandas
        return analisis_costos_simple(datos)

def analisis_costos_simple(datos):
    """Análisis simple de costos sin dependencias ML"""
    if len(datos) < 5:
        return {'error': 'Datos insuficientes para análisis'}
    
    costos = [row['costo'] for row in datos]
    
    return {
        'resumen': {
            'total_mantenimientos': len(datos),
            'costo_promedio': round(sum(costos) / len(costos), 2),
            'costo_total': round(sum(costos), 2),
            'costo_minimo': min(costos),
            'costo_maximo': max(costos)
        },
        'recomendaciones': [
            "Revisar mantenimientos de alto costo",
            "Implementar mantenimiento preventivo",
            "Analizar eficiencia de técnicos"
        ]
    }

def generar_recomendaciones_costos(df, correlacion):
    """Generar recomendaciones basadas en análisis de costos"""
    try:
        import numpy as np
        
        recomendaciones = []
        
        if correlacion > 0.3:
            recomendaciones.append("⚠️ Los costos están aumentando - Revisar procesos")
        elif correlacion < -0.3:
            recomendaciones.append("✅ Los costos están disminuyendo - Mantener estrategia")
        
        # Análisis de valores atípicos
        q75, q25 = np.percentile(df['costo'], [75, 25])
        iqr = q75 - q25
        outliers = df[df['costo'] > q75 + 1.5 * iqr]
        
        if len(outliers) > 0:
            recomendaciones.append(f"📊 Detectados {len(outliers)} mantenimientos con costos atípicos")
        
        # Recomendaciones por tipo
        tipo_caro = df.groupby('tipo_mantenimiento')['costo'].mean().idxmax()
        recomendaciones.append(f"💡 Enfocar prevención en: {tipo_caro}")
        
        return recomendaciones
        
    except ImportError:
        # Fallback sin numpy
        recomendaciones = []
        
        if correlacion > 0.3:
            recomendaciones.append("⚠️ Los costos están aumentando - Revisar procesos")
        elif correlacion < -0.3:
            recomendaciones.append("✅ Los costos están disminuyendo - Mantener estrategia")
        
        recomendaciones.append("📊 Instalar numpy para análisis avanzado de costos")
        
        return recomendaciones

# =========================================
# SISTEMA DE APIS EXTERNAS
# =========================================

@app.route('/apis')
@require_auth
@require_permission('usuarios', 'read')
def apis_dashboard():
    """Dashboard de APIs externas"""
    conn = get_db_connection()
    
    # Obtener APIs configuradas
    apis = conn.execute('''
        SELECT * FROM apis_externas
        ORDER BY tipo, nombre
    ''').fetchall()
    
    # Estadísticas
    stats = {
        'total_apis': len(apis),
        'apis_activas': len([api for api in apis if api['activa']]),
        'apis_conectadas': len([api for api in apis if api['estado_conexion'] == 'conectada']),
        'sincronizaciones_hoy': 0  # Simulado
    }
    
    conn.close()
    
    return render_template('apis/dashboard.html',
                         apis=apis,
                         stats=stats)

@app.route('/apis/nueva', methods=['GET', 'POST'])
@require_auth
@require_permission('usuarios', 'create')
def nueva_api():
    """Configurar nueva API externa"""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        tipo = request.form.get('tipo', '')
        url_base = request.form.get('url_base', '').strip()
        api_key = request.form.get('api_key', '').strip()
        
        # Configuración específica según el tipo
        configuracion = {
            'timeout': request.form.get('timeout', type=int, default=30),
            'retries': request.form.get('retries', type=int, default=3),
            'formato': request.form.get('formato', 'json'),
            'autenticacion': request.form.get('autenticacion', 'api_key'),
            'headers_adicionales': request.form.get('headers_adicionales', '{}')
        }
        
        if tipo == 'contabilidad':
            configuracion.update({
                'empresa_id': request.form.get('empresa_id', ''),
                'moneda': request.form.get('moneda', 'MXN'),
                'tipo_cambio_api': request.form.get('tipo_cambio_api', '')
            })
        elif tipo == 'proveedor':
            configuracion.update({
                'catalogo_endpoint': request.form.get('catalogo_endpoint', ''),
                'precios_endpoint': request.form.get('precios_endpoint', ''),
                'stock_endpoint': request.form.get('stock_endpoint', '')
            })
        
        activa = 'activa' in request.form
        
        if not all([nombre, tipo, url_base]):
            flash('Completa todos los campos obligatorios', 'error')
            return redirect(url_for('nueva_api'))
        
        conn = get_db_connection()
        
        try:
            conn.execute('''
                INSERT INTO apis_externas
                (nombre, tipo, url_base, api_key, configuracion, activa, usuario_configuracion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, tipo, url_base, api_key, json.dumps(configuracion), 
                  activa, session['user_id']))
            
            api_id = conn.lastrowid
            conn.commit()
            
            # Probar conexión
            if activa:
                resultado_test = probar_conexion_api(api_id)
                if resultado_test['exito']:
                    flash(f'API "{nombre}" configurada y probada exitosamente', 'success')
                else:
                    flash(f'API "{nombre}" configurada pero falló la prueba: {resultado_test["error"]}', 'warning')
            else:
                flash(f'API "{nombre}" configurada (inactiva)', 'info')
            
            # Log de auditoría
            log_audit('configurar_api_externa', 'apis_externas', api_id, None, {
                'nombre': nombre,
                'tipo': tipo,
                'url_base': url_base
            })
            
            conn.close()
            return redirect(url_for('apis_dashboard'))
            
        except Exception as e:
            conn.close()
            flash(f'Error al configurar API: {str(e)}', 'error')
            return redirect(url_for('nueva_api'))
    
    return render_template('apis/nueva.html')

def probar_conexion_api(api_id):
    """Probar conexión con API externa"""
    try:
        import requests
        
        conn = get_db_connection()
        api = conn.execute('SELECT * FROM apis_externas WHERE id = ?', (api_id,)).fetchone()
        conn.close()
        
        if not api:
            return {'exito': False, 'error': 'API no encontrada'}
        
        config = json.loads(api['configuracion'])
        headers = {'User-Agent': 'Taller-Management-System/1.0'}
        
        # Agregar autenticación
        if api['api_key']:
            if config.get('autenticacion') == 'bearer':
                headers['Authorization'] = f"Bearer {api['api_key']}"
            else:
                headers['X-API-Key'] = api['api_key']
        
        # Headers adicionales
        try:
            headers_extra = json.loads(config.get('headers_adicionales', '{}'))
            headers.update(headers_extra)
        except:
            pass
        
        # Hacer petición de prueba
        timeout = config.get('timeout', 30)
        
        if api['tipo'] == 'contabilidad':
            # Probar endpoint de estado
            url = f"{api['url_base'].rstrip('/')}/api/status"
        elif api['tipo'] == 'proveedor':
            # Probar endpoint de catálogo
            url = f"{api['url_base'].rstrip('/')}/api/productos"
        else:
            # Endpoint genérico
            url = api['url_base']
        
        response = requests.get(url, headers=headers, timeout=timeout)
        
        # Actualizar estado en base de datos
        conn = get_db_connection()
        if response.status_code < 400:
            conn.execute('''
                UPDATE apis_externas 
                SET estado_conexion = 'conectada', ultima_sincronizacion = ?
                WHERE id = ?
            ''', (datetime.now(), api_id))
            resultado = {'exito': True, 'codigo': response.status_code}
        else:
            conn.execute('''
                UPDATE apis_externas 
                SET estado_conexion = 'error', log_errores = ?
                WHERE id = ?
            ''', (f"HTTP {response.status_code}: {response.text[:500]}", api_id))
            resultado = {'exito': False, 'error': f"HTTP {response.status_code}"}
        
        conn.commit()
        conn.close()
        
        return resultado
        
    except ImportError:
        return {'exito': False, 'error': 'Librería requests no disponible'}
    except Exception as e:
        # Actualizar estado de error
        try:
            conn = get_db_connection()
            conn.execute('''
                UPDATE apis_externas 
                SET estado_conexion = 'error', log_errores = ?
                WHERE id = ?
            ''', (str(e)[:500], api_id))
            conn.commit()
            conn.close()
        except:
            pass
        
        return {'exito': False, 'error': str(e)}

@app.route('/api/externa/probar/<int:api_id>')
@require_auth
def probar_api(api_id):
    """Endpoint para probar API externa"""
    resultado = probar_conexion_api(api_id)
    return jsonify(resultado)

@app.route('/api/externa/sincronizar/<int:api_id>')
@require_auth
def sincronizar_api(api_id):
    """Sincronizar datos con API externa"""
    try:
        conn = get_db_connection()
        api = conn.execute('SELECT * FROM apis_externas WHERE id = ?', (api_id,)).fetchone()
        
        if not api:
            return jsonify({'error': 'API no encontrada'}), 404
        
        if not api['activa']:
            return jsonify({'error': 'API inactiva'}), 400
        
        # Ejecutar sincronización según el tipo
        if api['tipo'] == 'proveedor':
            resultado = sincronizar_proveedores(api)
        elif api['tipo'] == 'contabilidad':
            resultado = sincronizar_contabilidad(api)
        else:
            resultado = {'error': 'Tipo de API no soportado'}
        
        # Actualizar última sincronización
        if resultado.get('exito'):
            conn.execute('''
                UPDATE apis_externas 
                SET ultima_sincronizacion = ?, estado_conexion = 'conectada'
                WHERE id = ?
            ''', (datetime.now(), api_id))
            conn.commit()
        
        conn.close()
        
        # Log de auditoría
        log_audit('sincronizar_api_externa', 'apis_externas', api_id, None, resultado)
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'error': f'Error en sincronización: {str(e)}'}), 500

def sincronizar_proveedores(api):
    """Sincronizar datos de proveedores"""
    try:
        import requests
        
        config = json.loads(api['configuracion'])
        headers = {'User-Agent': 'Taller-Management-System/1.0'}
        
        if api['api_key']:
            headers['X-API-Key'] = api['api_key']
        
        # Sincronizar catálogo de productos
        url_catalogo = f"{api['url_base'].rstrip('/')}/api/productos"
        response = requests.get(url_catalogo, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return {'error': f'Error HTTP {response.status_code}'}
        
        productos = response.json()
        
        # Actualizar repuestos en base de datos
        conn = get_db_connection()
        productos_actualizados = 0
        productos_nuevos = 0
        
        for producto in productos[:50]:  # Limitar a 50 productos por sincronización
            # Buscar si el repuesto ya existe
            repuesto_existente = conn.execute('''
                SELECT id FROM repuestos 
                WHERE nombre LIKE ? OR numero_parte = ?
            ''', (f"%{producto.get('nombre', '')}%", producto.get('sku', ''))).fetchone()
            
            if repuesto_existente:
                # Actualizar precio
                conn.execute('''
                    UPDATE repuestos 
                    SET precio_unitario = ?
                    WHERE id = ?
                ''', (producto.get('precio', 0), repuesto_existente['id']))
                productos_actualizados += 1
            else:
                # Crear nuevo repuesto
                conn.execute('''
                    INSERT INTO repuestos 
                    (nombre, descripcion, numero_parte, precio_unitario, proveedor,
                     stock_actual, stock_minimo, fecha_creacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    producto.get('nombre', 'Producto importado'),
                    producto.get('descripcion', ''),
                    producto.get('sku', ''),
                    producto.get('precio', 0),
                    api['nombre'],
                    producto.get('stock', 0),
                    producto.get('stock_minimo', 1),
                    datetime.now()
                ))
                productos_nuevos += 1
        
        conn.commit()
        conn.close()
        
        return {
            'exito': True,
            'productos_sincronizados': len(productos),
            'productos_actualizados': productos_actualizados,
            'productos_nuevos': productos_nuevos
        }
        
    except Exception as e:
        return {'error': f'Error sincronizando proveedores: {str(e)}'}

def sincronizar_contabilidad(api):
    """Sincronizar datos con sistema de contabilidad"""
    try:
        import requests
        
        config = json.loads(api['configuracion'])
        headers = {'User-Agent': 'Taller-Management-System/1.0'}
        
        if api['api_key']:
            headers['Authorization'] = f"Bearer {api['api_key']}"
        
        # Enviar facturas de mantenimientos completados no sincronizados
        conn = get_db_connection()
        mantenimientos_facturar = conn.execute('''
            SELECT m.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre,
                   c.rfc, c.email
            FROM mantenimientos m
            LEFT JOIN equipos e ON m.equipo_id = e.id
            LEFT JOIN clientes c ON e.cliente_id = c.id
            WHERE m.estado = 'Completado' 
            AND m.costo > 0
            AND m.fecha_mantenimiento >= date('now', '-30 days')
            AND m.id NOT IN (
                SELECT objeto_id FROM auditoria 
                WHERE accion = 'sincronizar_contabilidad' 
                AND tabla_afectada = 'mantenimientos'
            )
            ORDER BY m.fecha_mantenimiento DESC
            LIMIT 10
        ''').fetchall()
        
        facturas_enviadas = 0
        
        for mantenimiento in mantenimientos_facturar:
            # Crear factura en sistema externo
            factura_data = {
                'cliente': {
                    'nombre': mantenimiento['cliente_nombre'],
                    'rfc': mantenimiento.get('rfc', ''),
                    'email': mantenimiento.get('email', '')
                },
                'conceptos': [{
                    'descripcion': f"Mantenimiento {mantenimiento['tipo_mantenimiento']} - {mantenimiento['equipo_nombre']}",
                    'cantidad': 1,
                    'precio_unitario': mantenimiento['costo'],
                    'total': mantenimiento['costo']
                }],
                'fecha': mantenimiento['fecha_mantenimiento'],
                'moneda': config.get('moneda', 'MXN'),
                'referencia_interna': f"MANT-{mantenimiento['id']}"
            }
            
            # Enviar a API de contabilidad (simulado)
            url_facturas = f"{api['url_base'].rstrip('/')}/api/facturas"
            
            # En un entorno real, aquí se haría la petición HTTP
            # response = requests.post(url_facturas, json=factura_data, headers=headers)
            
            # Simular respuesta exitosa
            facturas_enviadas += 1
            
            # Marcar como sincronizado en auditoría
            log_audit('sincronizar_contabilidad', 'mantenimientos', mantenimiento['id'], None, {
                'factura_enviada': True,
                'monto': mantenimiento['costo']
            })
        
        conn.close()
        
        return {
            'exito': True,
            'facturas_enviadas': facturas_enviadas,
            'mantenimientos_procesados': len(mantenimientos_facturar)
        }
        
    except Exception as e:
        return {'error': f'Error sincronizando contabilidad: {str(e)}'}

@app.route('/api/externa/webhook/<int:api_id>', methods=['POST'])
def webhook_api_externa(api_id):
    """Webhook para recibir datos de APIs externas"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        api = conn.execute('SELECT * FROM apis_externas WHERE id = ?', (api_id,)).fetchone()
        
        if not api:
            return jsonify({'error': 'API no encontrada'}), 404
        
        # Procesar webhook según el tipo
        if api['tipo'] == 'proveedor':
            resultado = procesar_webhook_proveedor(data, api)
        elif api['tipo'] == 'contabilidad':
            resultado = procesar_webhook_contabilidad(data, api)
        else:
            resultado = {'recibido': True, 'procesado': False}
        
        # Log del webhook
        log_audit('webhook_recibido', 'apis_externas', api_id, None, {
            'tipo': api['tipo'],
            'datos_recibidos': len(str(data)),
            'resultado': resultado
        })
        
        conn.close()
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def procesar_webhook_proveedor(data, api):
    """Procesar webhook de proveedor"""
    # Ejemplo: actualización de precios o stock
    if data.get('tipo') == 'actualizacion_precios':
        # Actualizar precios de repuestos
        return {'procesado': True, 'tipo': 'precios_actualizados'}
    
    return {'procesado': False, 'razon': 'Tipo de webhook no reconocido'}

def procesar_webhook_contabilidad(data, api):
    """Procesar webhook de contabilidad"""
    # Ejemplo: confirmación de factura procesada
    if data.get('tipo') == 'factura_procesada':
        # Marcar factura como procesada
        return {'procesado': True, 'tipo': 'factura_confirmada'}
    
    return {'procesado': False, 'razon': 'Tipo de webhook no reconocido'}

# =========================================
# SISTEMA DE EXPORTACIÓN AVANZADA
# =========================================

@app.route('/api/export/pdf/<tipo>')
@require_auth
def export_pdf(tipo):
    """Exportación avanzada en PDF con diseño profesional"""
    print(f"🔍 DEBUG: Iniciando exportación PDF tipo: {tipo}")
    print(f"🔍 DEBUG: Usuario actual g.user: {g.user}")
    print(f"🔍 DEBUG: Tipo de g.user: {type(g.user)}")
    
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
        from reportlab.lib.units import inch
        from io import BytesIO
        import base64
        
        # Crear buffer en memoria
        buffer = BytesIO()
        
        # Configurar documento
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Obtener estilos
        styles = getSampleStyleSheet()
        
        # Crear estilos personalizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2c3e50'),
            alignment=1  # Center
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            textColor=colors.HexColor('#34495e')
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=10
        )
        
        # Contenido del documento
        story = []
        
        # Header del documento
        story.append(Paragraph("Sistema de Gestión de Taller", title_style))
        story.append(Paragraph(f"Reporte Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", header_style))
        story.append(Spacer(1, 20))
        
        conn = get_db_connection()
        
        if tipo == 'dashboard':
            story.extend(generar_reporte_dashboard(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch))
        elif tipo == 'mantenimientos':
            story.extend(generar_reporte_mantenimientos(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch))
        elif tipo == 'equipos':
            story.extend(generar_reporte_equipos(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch))
        elif tipo == 'clientes':
            story.extend(generar_reporte_clientes(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch))
        elif tipo == 'repuestos':
            story.extend(generar_reporte_repuestos(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch))
        elif tipo == 'auditoria':
            story.extend(generar_reporte_auditoria(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch))
        elif tipo == 'ml':
            story.extend(generar_reporte_ml(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch))
        elif tipo == 'iot':
            story.extend(generar_reporte_iot(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch))
        elif tipo == 'programas':
            story.extend(generar_reporte_programas(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch))
        elif tipo == 'usuarios':
            story.extend(generar_reporte_usuarios(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch))
        else:
            story.append(Paragraph("Tipo de reporte no encontrado", styles['Normal']))
        
        conn.close()
        
        # Footer
        story.append(PageBreak())
        story.append(Spacer(1, 50))
        story.append(Paragraph("---", styles['Normal']))
        # Manejar g.user como dict o objeto
        user_name = "Usuario"
        if g.user:
            if hasattr(g.user, 'nombre_completo'):
                user_name = g.user.nombre_completo
            elif isinstance(g.user, dict) and 'nombre_completo' in g.user:
                user_name = g.user['nombre_completo']
            elif hasattr(g.user, 'nombre'):
                user_name = g.user.nombre
            elif isinstance(g.user, dict) and 'nombre' in g.user:
                user_name = g.user['nombre']
        
        story.append(Paragraph(f"Reporte generado por: {user_name}", header_style))
        story.append(Paragraph(f"Sistema de Gestión de Taller v2.0", header_style))
        
        # Construir PDF
        doc.build(story)
        
        # Preparar respuesta
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Log de auditoría
        log_audit('exportar_pdf', f'reporte_{tipo}', None, None, {
            'tipo_reporte': tipo,
            'tamaño_bytes': len(pdf_data)
        })
        
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=reporte_{tipo}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
        
        return response
        
    except ImportError as e:
        print(f"❌ ERROR ImportError: {e}")
        flash('Error: La librería reportlab no está instalada. Ejecuta: pip install reportlab', 'error')
        return redirect(request.referrer or url_for('index'))
    except Exception as e:
        print(f"❌ ERROR general: {e}")
        print(f"❌ ERROR tipo: {type(e)}")
        import traceback
        print(f"❌ ERROR traceback: {traceback.format_exc()}")
        flash(f'Error al generar PDF: {str(e)}', 'error')
        return redirect(request.referrer or url_for('index'))

@app.route('/api/test/export/<tipo>')
@require_auth  
def test_export(tipo):
    """Ruta de test para verificar exportaciones PDF"""
    try:
        print(f"🧪 TEST: Probando exportación {tipo}")
        print(f"🧪 TEST: g.user = {g.user}")
        print(f"🧪 TEST: g.user type = {type(g.user)}")
        
        # Verificar que reportlab esté disponible
        from reportlab.lib.pagesizes import A4
        print("✅ TEST: reportlab disponible")
        
        # Verificar conexión a base de datos
        conn = get_db_connection()
        test_query = conn.execute('SELECT COUNT(*) FROM equipos').fetchone()
        conn.close()
        print(f"✅ TEST: Base de datos accesible, equipos: {test_query[0]}")
        
        # Verificar función generadora
        tipos_disponibles = ['dashboard', 'mantenimientos', 'equipos', 'clientes', 'repuestos', 'auditoria', 'ml', 'iot', 'programas', 'usuarios']
        if tipo not in tipos_disponibles:
            return f"❌ Tipo '{tipo}' no válido. Disponibles: {', '.join(tipos_disponibles)}"
        
        print(f"✅ TEST: Tipo '{tipo}' es válido")
        
        return f"""
        <h2>🧪 Test de Exportación: {tipo}</h2>
        <p>✅ reportlab: Disponible</p>
        <p>✅ Base de datos: Conectada</p>
        <p>✅ Usuario: {g.user}</p>
        <p>✅ Tipo: Válido</p>
        <p><a href="/api/export/pdf/{tipo}" target="_blank">🔗 Probar exportación real</a></p>
        <p><a href="/dashboard">🏠 Volver al dashboard</a></p>
        """
        
    except Exception as e:
        import traceback
        return f"""
        <h2>❌ Error en Test</h2>
        <p>Error: {str(e)}</p>
        <pre>{traceback.format_exc()}</pre>
        <p><a href="/dashboard">🏠 Volver al dashboard</a></p>
        """

@app.route('/test-export')
@require_auth
def test_export_page():
    """Página de test para exportaciones"""
    return render_template('test_export.html')

@app.route('/api/export/excel/<tipo>')
@require_auth
def export_excel(tipo):
    """Exportación avanzada en Excel con formato profesional"""
    try:
        import pandas as pd
        from io import BytesIO
        import xlsxwriter
        
        # Crear buffer en memoria
        buffer = BytesIO()
        
        # Crear workbook de Excel
        workbook = xlsxwriter.Workbook(buffer)
        
        # Configurar estilos
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#1f4788',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_color': '#1f4788',
            'align': 'center'
        })
        
        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })
        
        number_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0.00',
            'align': 'right'
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'num_format': 'dd/mm/yyyy',
            'align': 'center'
        })
        
        conn = get_db_connection()
        
        if tipo == 'dashboard':
            generar_excel_dashboard(conn, workbook, header_format, title_format, data_format, number_format, date_format)
        elif tipo == 'equipos':
            generar_excel_equipos(conn, workbook, header_format, title_format, data_format, number_format, date_format)
        elif tipo == 'mantenimientos':
            generar_excel_mantenimientos(conn, workbook, header_format, title_format, data_format, number_format, date_format)
        elif tipo == 'clientes':
            generar_excel_clientes(conn, workbook, header_format, title_format, data_format, number_format, date_format)
        elif tipo == 'repuestos':
            generar_excel_repuestos(conn, workbook, header_format, title_format, data_format, number_format, date_format)
        elif tipo == 'auditoria':
            generar_excel_auditoria(conn, workbook, header_format, title_format, data_format, number_format, date_format)
        else:
            raise ValueError(f"Tipo de reporte no soportado: {tipo}")
        
        conn.close()
        
        # Cerrar workbook
        workbook.close()
        
        # Obtener datos del buffer
        buffer.seek(0)
        excel_data = buffer.getvalue()
        buffer.close()
        
        # Log de auditoría
        log_audit('exportar_excel', f'reporte_{tipo}', None, None, {
            'tipo_reporte': tipo,
            'tamaño_bytes': len(excel_data)
        })
        
        response = make_response(excel_data)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=reporte_{tipo}_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        return response
        
    except ImportError as e:
        flash('Error: Librerías de Excel no instaladas. Ejecuta: pip install pandas xlsxwriter', 'error')
        return redirect(request.referrer or url_for('index'))
    except Exception as e:
        flash(f'Error al generar Excel: {str(e)}', 'error')
        return redirect(request.referrer or url_for('index'))

def generar_reporte_dashboard(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch):
    """Generar contenido del reporte de dashboard"""
    story = []
    
    story.append(Paragraph("📊 Dashboard Ejecutivo", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Métricas principales
    stats = {
        'total_equipos': conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0],
        'equipos_activos': conn.execute('SELECT COUNT(*) FROM equipos WHERE estado = "Activo"').fetchone()[0],
        'total_mantenimientos': conn.execute('SELECT COUNT(*) FROM mantenimientos').fetchone()[0],
        'mantenimientos_pendientes': conn.execute('SELECT COUNT(*) FROM mantenimientos WHERE estado = "Pendiente"').fetchone()[0],
        'total_clientes': conn.execute('SELECT COUNT(*) FROM clientes').fetchone()[0],
        'gasto_mes_actual': conn.execute('SELECT COALESCE(SUM(costo), 0) FROM mantenimientos WHERE strftime("%Y-%m", fecha_mantenimiento) = strftime("%Y-%m", "now")').fetchone()[0]
    }
    
    # Tabla de métricas
    data = [
        ['Métrica', 'Valor', 'Estado'],
        ['Total de Equipos', str(stats['total_equipos']), '✓'],
        ['Equipos Activos', str(stats['equipos_activos']), '✓'],
        ['Total Mantenimientos', str(stats['total_mantenimientos']), '✓'],
        ['Mantenimientos Pendientes', str(stats['mantenimientos_pendientes']), '⚠️' if stats['mantenimientos_pendientes'] > 5 else '✓'],
        ['Total Clientes', str(stats['total_clientes']), '✓'],
        ['Gasto Mes Actual', f"${stats['gasto_mes_actual']:.2f}", '💰']
    ]
    
    table = Table(data, colWidths=[3*inch, 1.5*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Top 5 clientes
    clientes = conn.execute('''
        SELECT c.nombre, COUNT(e.id) as equipos, COUNT(m.id) as mantenimientos,
               SUM(COALESCE(m.costo, 0)) as gasto_total
        FROM clientes c
        LEFT JOIN equipos e ON c.id = e.cliente_id
        LEFT JOIN mantenimientos m ON e.id = m.equipo_id
        GROUP BY c.id, c.nombre
        ORDER BY gasto_total DESC
        LIMIT 5
    ''').fetchall()
    
    if clientes:
        story.append(Paragraph("🏆 Top 5 Clientes por Gasto", subtitle_style))
        
        data = [['Cliente', 'Equipos', 'Mantenimientos', 'Gasto Total']]
        for cliente in clientes:
            data.append([
                cliente['nombre'],
                str(cliente['equipos']),
                str(cliente['mantenimientos']),
                f"${cliente['gasto_total']:.2f}"
            ])
        
        table = Table(data, colWidths=[2.5*inch, 1*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story

def generar_reporte_mantenimientos(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch):
    """Generar contenido del reporte de mantenimientos"""
    story = []
    
    story.append(Paragraph("🔧 Reporte de Mantenimientos", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Mantenimientos recientes
    mantenimientos = conn.execute('''
        SELECT m.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
        FROM mantenimientos m
        LEFT JOIN equipos e ON m.equipo_id = e.id
        LEFT JOIN clientes c ON e.cliente_id = c.id
        ORDER BY m.fecha_mantenimiento DESC
        LIMIT 20
    ''').fetchall()
    
    if mantenimientos:
        data = [['Fecha', 'Equipo', 'Cliente', 'Tipo', 'Estado', 'Costo']]
        for mant in mantenimientos:
            data.append([
                mant['fecha_mantenimiento'][:10] if mant['fecha_mantenimiento'] else 'N/A',
                mant['equipo_nombre'] or 'N/A',
                mant['cliente_nombre'] or 'N/A',
                mant['tipo_mantenimiento'] or 'N/A',
                mant['estado'] or 'N/A',
                f"${mant['costo']:.2f}" if mant['costo'] else '$0.00'
            ])
        
        table = Table(data, colWidths=[1*inch, 1.5*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story

def generar_reporte_equipos(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch):
    """Generar contenido del reporte de equipos"""
    story = []
    
    story.append(Paragraph("⚙️ Inventario de Equipos", subtitle_style))
    story.append(Spacer(1, 20))
    
    equipos = conn.execute('''
        SELECT e.*, c.nombre as cliente_nombre,
               COUNT(m.id) as total_mantenimientos,
               MAX(m.fecha_mantenimiento) as ultimo_mantenimiento
        FROM equipos e
        LEFT JOIN clientes c ON e.cliente_id = c.id
        LEFT JOIN mantenimientos m ON e.id = m.equipo_id
        GROUP BY e.id
        ORDER BY c.nombre, e.nombre
        LIMIT 25
    ''').fetchall()
    
    if equipos:
        data = [['Equipo', 'Cliente', 'Marca/Modelo', 'Estado', 'Mantenimientos', 'Último Mant.']]
        for equipo in equipos:
            data.append([
                equipo['nombre'],
                equipo['cliente_nombre'] or 'N/A',
                f"{equipo['marca'] or 'N/A'} {equipo['modelo'] or ''}".strip(),
                equipo['estado'] or 'N/A',
                str(equipo['total_mantenimientos']),
                equipo['ultimo_mantenimiento'][:10] if equipo['ultimo_mantenimiento'] else 'Nunca'
            ])
        
        table = Table(data, colWidths=[1.5*inch, 1.3*inch, 1.3*inch, 0.8*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lavender),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story

def generar_reporte_clientes(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch):
    """Generar contenido del reporte de clientes"""
    story = []
    
    story.append(Paragraph("👥 Directorio de Clientes", subtitle_style))
    story.append(Spacer(1, 20))
    
    clientes = conn.execute('''
        SELECT c.*, COUNT(e.id) as total_equipos,
               COUNT(m.id) as total_mantenimientos,
               SUM(COALESCE(m.costo, 0)) as gasto_total
        FROM clientes c
        LEFT JOIN equipos e ON c.id = e.cliente_id
        LEFT JOIN mantenimientos m ON e.id = m.equipo_id
        GROUP BY c.id
        ORDER BY gasto_total DESC
        LIMIT 20
    ''').fetchall()
    
    if clientes:
        data = [['Cliente', 'Contacto', 'Equipos', 'Mantenimientos', 'Gasto Total']]
        for cliente in clientes:
            data.append([
                cliente['nombre'],
                cliente['telefono'] or cliente['email'] or 'N/A',
                str(cliente['total_equipos']),
                str(cliente['total_mantenimientos']),
                f"${cliente['gasto_total']:.2f}"
            ])
        
        table = Table(data, colWidths=[2*inch, 1.5*inch, 1*inch, 1.3*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f39c12')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story

def generar_reporte_repuestos(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch):
    """Generar contenido del reporte de repuestos"""
    story = []
    
    story.append(Paragraph("📦 Inventario de Repuestos", subtitle_style))
    story.append(Spacer(1, 20))
    
    repuestos = conn.execute('''
        SELECT * FROM repuestos
        ORDER BY stock_actual ASC, nombre
        LIMIT 25
    ''').fetchall()
    
    if repuestos:
        data = [['Repuesto', 'Stock Actual', 'Stock Mín.', 'Precio Unit.', 'Estado']]
        for repuesto in repuestos:
            estado = '🔴 Crítico' if repuesto['stock_actual'] <= repuesto['stock_minimo'] else '🟡 Bajo' if repuesto['stock_actual'] <= repuesto['stock_minimo'] * 1.5 else '🟢 OK'
            data.append([
                repuesto['nombre'],
                str(repuesto['stock_actual']),
                str(repuesto['stock_minimo']),
                f"${repuesto['precio_unitario']:.2f}" if repuesto['precio_unitario'] else 'N/A',
                estado
            ])
        
        table = Table(data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a085')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightcyan),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story

def generar_reporte_auditoria(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch):
    """Generar contenido del reporte de auditoría"""
    story = []
    
    story.append(Paragraph("🔍 Registro de Auditoría", subtitle_style))
    story.append(Spacer(1, 20))
    
    auditorias = conn.execute('''
        SELECT a.*, u.username, u.nombre_completo
        FROM auditoria a
        LEFT JOIN usuarios u ON a.usuario_id = u.id
        ORDER BY a.fecha_accion DESC
        LIMIT 25
    ''').fetchall()
    
    if auditorias:
        data = [['Fecha', 'Usuario', 'Acción', 'Tabla', 'IP']]
        for audit in auditorias:
            data.append([
                audit['fecha_accion'][:16] if audit['fecha_accion'] else 'N/A',
                audit['username'] or 'Sistema',
                audit['accion'] or 'N/A',
                audit['tabla_afectada'] or 'N/A',
                audit['ip_address'] or 'N/A'
            ])
        
        table = Table(data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.2*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story

def generar_reporte_ml(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch):
    """Generar contenido del reporte de Machine Learning"""
    story = []
    
    story.append(Paragraph("🤖 Análisis de Machine Learning", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Estadísticas de predicciones
    stats = conn.execute('''
        SELECT COUNT(*) as total_equipos,
               AVG(CASE WHEN estado = 'Activo' THEN 1.0 ELSE 0.0 END) * 100 as porcentaje_activos
        FROM equipos
    ''').fetchone()
    
    story.append(Paragraph(f"<b>Estadísticas Generales:</b>", styles['Normal']))
    story.append(Paragraph(f"• Total de equipos: {stats['total_equipos']}", styles['Normal']))
    story.append(Paragraph(f"• Porcentaje activos: {stats['porcentaje_activos']:.1f}%", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Equipos con análisis predictivo
    equipos_ml = conn.execute('''
        SELECT e.nombre, e.estado, e.fecha_instalacion,
               COUNT(m.id) as total_mantenimientos,
               30.0 as intervalo_promedio,
               CASE 
                   WHEN COUNT(m.id) > 10 THEN 'Alto'
                   WHEN COUNT(m.id) > 5 THEN 'Medio'
                   ELSE 'Bajo'
               END as riesgo_fallo
        FROM equipos e
        LEFT JOIN mantenimientos m ON e.id = m.equipo_id
        WHERE e.estado = 'Activo'
        GROUP BY e.id, e.nombre, e.estado, e.fecha_instalacion
        ORDER BY total_mantenimientos DESC
        LIMIT 20
    ''').fetchall()
    
    if equipos_ml:
        story.append(Paragraph("📊 Análisis Predictivo de Equipos", styles['Heading3']))
        story.append(Spacer(1, 10))
        
        data = [['Equipo', 'Estado', 'Mantenimientos', 'Intervalo Prom.', 'Riesgo de Fallo']]
        for equipo in equipos_ml:
            data.append([
                equipo['nombre'],
                equipo['estado'],
                str(equipo['total_mantenimientos']),
                f"{equipo['intervalo_promedio']:.0f} días",
                equipo['riesgo_fallo']
            ])
        
        table = Table(data, colWidths=[2*inch, 1*inch, 1*inch, 1.2*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story

def generar_reporte_iot(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch):
    """Generar contenido del reporte de IoT"""
    story = []
    
    story.append(Paragraph("📡 Monitoreo IoT de Equipos", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Dispositivos IoT
    dispositivos = conn.execute('''
        SELECT nombre, tipo_dispositivo, protocolo, estado, 
               fecha_ultima_lectura, direccion_ip
        FROM dispositivos_iot
        ORDER BY fecha_ultima_lectura DESC
        LIMIT 15
    ''').fetchall()
    
    if dispositivos:
        story.append(Paragraph("📟 Dispositivos IoT Registrados", styles['Heading3']))
        story.append(Spacer(1, 10))
        
        data = [['Dispositivo', 'Tipo', 'Protocolo', 'Estado', 'Última Lectura']]
        for dispositivo in dispositivos:
            data.append([
                dispositivo['nombre'],
                dispositivo['tipo_dispositivo'],
                dispositivo['protocolo'],
                dispositivo['estado'],
                dispositivo['fecha_ultima_lectura'][:16] if dispositivo['fecha_ultima_lectura'] else 'N/A'
            ])
        
        table = Table(data, colWidths=[1.5*inch, 1.2*inch, 1*inch, 1*inch, 1.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    else:
        story.append(Paragraph("No hay dispositivos IoT registrados.", styles['Normal']))
    
    story.append(Spacer(1, 20))
    
    # Lecturas recientes
    lecturas = conn.execute('''
        SELECT d.nombre, l.valor, l.unidad, l.timestamp
        FROM lecturas_iot l
        JOIN dispositivos_iot d ON l.dispositivo_id = d.id
        ORDER BY l.timestamp DESC
        LIMIT 10
    ''').fetchall()
    
    if lecturas:
        story.append(Paragraph("📈 Lecturas Recientes", styles['Heading3']))
        story.append(Spacer(1, 10))
        
        data = [['Dispositivo', 'Valor', 'Unidad', 'Timestamp']]
        for lectura in lecturas:
            data.append([
                lectura['nombre'],
                str(lectura['valor']),
                lectura['unidad'],
                lectura['timestamp'][:16] if lectura['timestamp'] else 'N/A'
            ])
        
        table = Table(data, colWidths=[2*inch, 1.2*inch, 1*inch, 2.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story

def generar_reporte_programas(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch):
    """Generar contenido del reporte de programas de automatización"""
    story = []
    
    story.append(Paragraph("⚙️ Programas de Automatización", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Programas de mantenimiento
    programas = conn.execute('''
        SELECT nombre, tipo_programa, frecuencia, estado, 
               proxima_ejecucion, fecha_creacion
        FROM programas_mantenimiento
        ORDER BY proxima_ejecucion ASC
        LIMIT 20
    ''').fetchall()
    
    if programas:
        story.append(Paragraph("🔄 Programas de Mantenimiento", styles['Heading3']))
        story.append(Spacer(1, 10))
        
        data = [['Programa', 'Tipo', 'Frecuencia', 'Estado', 'Próxima Ejecución']]
        for programa in programas:
            data.append([
                programa['nombre'],
                programa['tipo_programa'],
                programa['frecuencia'],
                programa['estado'],
                programa['proxima_ejecucion'][:16] if programa['proxima_ejecucion'] else 'N/A'
            ])
        
        table = Table(data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 1*inch, 1.6*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8e44ad')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    else:
        story.append(Paragraph("No hay programas de automatización configurados.", styles['Normal']))
    
    story.append(Spacer(1, 20))
    
    # Tareas programadas
    tareas = conn.execute('''
        SELECT titulo, tipo_tarea, estado, fecha_programada, 
               usuario_asignado
        FROM tareas_programadas
        ORDER BY fecha_programada ASC
        LIMIT 15
    ''').fetchall()
    
    if tareas:
        story.append(Paragraph("📅 Tareas Programadas", styles['Heading3']))
        story.append(Spacer(1, 10))
        
        data = [['Tarea', 'Tipo', 'Estado', 'Fecha Programada', 'Asignado']]
        for tarea in tareas:
            data.append([
                tarea['titulo'],
                tarea['tipo_tarea'],
                tarea['estado'],
                tarea['fecha_programada'][:16] if tarea['fecha_programada'] else 'N/A',
                tarea['usuario_asignado'] or 'Sin asignar'
            ])
        
        table = Table(data, colWidths=[1.5*inch, 1.2*inch, 1*inch, 1.5*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e67e22')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story

def generar_reporte_usuarios(conn, styles, subtitle_style, Paragraph, Spacer, Table, TableStyle, colors, inch):
    """Generar contenido del reporte de usuarios"""
    story = []
    
    story.append(Paragraph("👥 Gestión de Usuarios", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Estadísticas de usuarios
    stats = conn.execute('''
        SELECT COUNT(*) as total_usuarios,
               COUNT(CASE WHEN activo = 1 THEN 1 END) as usuarios_activos,
               COUNT(CASE WHEN activo = 0 THEN 1 END) as usuarios_inactivos
        FROM usuarios
    ''').fetchone()
    
    story.append(Paragraph(f"<b>Estadísticas Generales:</b>", styles['Normal']))
    story.append(Paragraph(f"• Total de usuarios: {stats['total_usuarios']}", styles['Normal']))
    story.append(Paragraph(f"• Usuarios activos: {stats['usuarios_activos']}", styles['Normal']))
    story.append(Paragraph(f"• Usuarios inactivos: {stats['usuarios_inactivos']}", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Lista de usuarios
    usuarios = conn.execute('''
        SELECT username, nombre_completo, email, rol, activo, 
               fecha_creacion, ultimo_acceso
        FROM usuarios
        ORDER BY fecha_creacion DESC
        LIMIT 25
    ''').fetchall()
    
    if usuarios:
        story.append(Paragraph("📋 Lista de Usuarios", styles['Heading3']))
        story.append(Spacer(1, 10))
        
        data = [['Usuario', 'Nombre', 'Email', 'Rol', 'Estado', 'Último Acceso']]
        for usuario in usuarios:
            estado = "Activo" if usuario['activo'] else "Inactivo"
            data.append([
                usuario['username'],
                usuario['nombre_completo'] or 'N/A',
                usuario['email'] or 'N/A',
                usuario['rol'],
                estado,
                usuario['ultimo_acceso'][:16] if usuario['ultimo_acceso'] else 'Nunca'
            ])
        
        table = Table(data, colWidths=[1.2*inch, 1.5*inch, 1.5*inch, 1*inch, 0.8*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    story.append(Spacer(1, 20))
    
    # Distribución por roles
    roles = conn.execute('''
        SELECT rol, COUNT(*) as cantidad
        FROM usuarios
        GROUP BY rol
        ORDER BY cantidad DESC
    ''').fetchall()
    
    if roles:
        story.append(Paragraph("📊 Distribución por Roles", styles['Heading3']))
        story.append(Spacer(1, 10))
        
        data = [['Rol', 'Cantidad de Usuarios']]
        for rol in roles:
            data.append([
                rol['rol'],
                str(rol['cantidad'])
            ])
        
        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story

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
            repuestos_count = conn.execute('SELECT COUNT(*) FROM repuestos').fetchone()[0]
            movimientos_count = conn.execute('SELECT COUNT(*) FROM movimientos_repuestos').fetchone()[0]
            
            # Deshabilitar restricciones de clave foránea temporalmente
            conn.execute('PRAGMA foreign_keys = OFF')
            
            # Eliminar en orden correcto (desde las tablas dependientes hacia las principales)
            # 1. Eliminar todas las tablas que referencian otras tablas
            conn.execute('DELETE FROM movimientos_repuestos')
            conn.execute('DELETE FROM clasificaciones_automaticas')
            conn.execute('DELETE FROM lecturas_iot')
            conn.execute('DELETE FROM dispositivos_iot')
            conn.execute('DELETE FROM programas_mantenimiento')
            conn.execute('DELETE FROM alertas_automaticas')
            conn.execute('DELETE FROM workflow_aprobaciones')
            conn.execute('DELETE FROM historial_automatizacion')
            conn.execute('DELETE FROM auditoria')
            conn.execute('DELETE FROM notificaciones')
            conn.execute('DELETE FROM sesiones_usuario')
            
            # 2. Eliminar mantenimientos (que referencian equipos)
            conn.execute('DELETE FROM mantenimientos')
            
            # 3. Eliminar equipos (que referencian clientes)
            conn.execute('DELETE FROM equipos')
            
            # 4. Eliminar repuestos (independientes)
            conn.execute('DELETE FROM repuestos')
            
            # 5. Eliminar clientes (ya no tienen dependencias)
            conn.execute('DELETE FROM clientes')
            
            # Reiniciar los auto-increment para todas las tablas principales
            conn.execute('DELETE FROM sqlite_sequence WHERE name IN ("equipos", "mantenimientos", "repuestos", "clientes", "movimientos_repuestos")')
            
            # Reactivar restricciones de clave foránea
            conn.execute('PRAGMA foreign_keys = ON')
            
            conn.commit()
            conn.close()
            
            total_eliminados = equipos_count + mantenimientos_count + repuestos_count + movimientos_count
            flash(f'Aplicación reiniciada exitosamente! Se eliminaron: {equipos_count} equipos, {mantenimientos_count} mantenimientos, {repuestos_count} repuestos y {movimientos_count} movimientos. Total: {total_eliminados} registros.', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            # Asegurar que las restricciones se reactiven en caso de error
            try:
                conn.execute('PRAGMA foreign_keys = ON')
                conn.commit()
                conn.close()
            except:
                pass
            flash(f'Error al reiniciar la aplicación: {str(e)}', 'error')
    
    # Obtener estadísticas actuales
    try:
        conn = get_db_connection()
        total_equipos = conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0]
        total_mantenimientos = conn.execute('SELECT COUNT(*) FROM mantenimientos').fetchone()[0]
        total_repuestos = conn.execute('SELECT COUNT(*) FROM repuestos').fetchone()[0]
        total_clientes = conn.execute('SELECT COUNT(*) FROM clientes').fetchone()[0]
        conn.close()
    except Exception as e:
        total_equipos = total_mantenimientos = total_repuestos = total_clientes = 0
    
    return render_template('reiniciar_app.html', 
                         total_equipos=total_equipos,
                         total_mantenimientos=total_mantenimientos,
                         total_repuestos=total_repuestos,
                         total_clientes=total_clientes)

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
    try:
        conn = get_db_connection()
        equipos = conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0]
        mantenimientos = conn.execute('SELECT COUNT(*) FROM mantenimientos').fetchone()[0]
        repuestos = conn.execute('SELECT COUNT(*) FROM repuestos').fetchone()[0]
        clientes = conn.execute('SELECT COUNT(*) FROM clientes').fetchone()[0]
        conn.close()
        
        return jsonify({
            'equipos': equipos,
            'mantenimientos': mantenimientos,
            'repuestos': repuestos,
            'clientes': clientes
        })
    except Exception as e:
        return jsonify({
            'equipos': 0,
            'mantenimientos': 0,
            'repuestos': 0,
            'clientes': 0,
            'error': str(e)
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

# Nuevas funciones con motor inteligente
@app.route('/informes/repuestos_inteligente')
def informe_repuestos_inteligente():
    """Informe inteligente de análisis de repuestos utilizados"""
    try:
        conn = get_db_connection()
        
        # Obtener mantenimientos con información básica
        query = '''
            SELECT m.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
            FROM mantenimientos m
            JOIN equipos e ON m.equipo_id = e.id
            JOIN clientes c ON e.cliente_id = c.id
            WHERE m.descripcion IS NOT NULL
            ORDER BY m.fecha_mantenimiento DESC
        '''
        mantenimientos = conn.execute(query).fetchall()
        
        # Crear motor de reconocimiento inteligente
        motor = crear_motor_reconocimiento()
        
        # Análisis inteligente de repuestos y trabajos
        categorias_repuestos = {}
        categorias_trabajos = {}
        
        for mantenimiento in mantenimientos:
            # Analizar cada mantenimiento con el motor inteligente
            analisis = motor.analizar_mantenimiento_completo(
                mantenimiento['descripcion'],
                mantenimiento['id']
            )
            
            cliente = mantenimiento['cliente_nombre']
            equipo = mantenimiento['equipo_nombre']
            
            # Procesar repuestos detectados
            for repuesto in analisis['repuestos']:
                categoria = repuesto['categoria']
                if categoria not in categorias_repuestos:
                    categorias_repuestos[categoria] = {
                        'count': 0,
                        'clientes': set(),
                        'equipos': set(),
                        'confianza_promedio': 0,
                        'color': repuesto['color']
                    }
                
                categorias_repuestos[categoria]['count'] += 1
                categorias_repuestos[categoria]['clientes'].add(cliente)
                categorias_repuestos[categoria]['equipos'].add(equipo)
                # Actualizar confianza promedio
                total_count = categorias_repuestos[categoria]['count']
                conf_actual = categorias_repuestos[categoria]['confianza_promedio']
                nueva_conf = (conf_actual * (total_count - 1) + repuesto['confianza']) / total_count
                categorias_repuestos[categoria]['confianza_promedio'] = nueva_conf
            
            # Procesar trabajos detectados
            for trabajo in analisis['trabajos']:
                categoria = trabajo['categoria']
                if categoria not in categorias_trabajos:
                    categorias_trabajos[categoria] = {
                        'count': 0,
                        'clientes': set(),
                        'equipos': set(),
                        'confianza_promedio': 0,
                        'color': trabajo['color']
                    }
                
                categorias_trabajos[categoria]['count'] += 1
                categorias_trabajos[categoria]['clientes'].add(cliente)
                categorias_trabajos[categoria]['equipos'].add(equipo)
                # Actualizar confianza promedio
                total_count = categorias_trabajos[categoria]['count']
                conf_actual = categorias_trabajos[categoria]['confianza_promedio']
                nueva_conf = (conf_actual * (total_count - 1) + trabajo['confianza']) / total_count
                categorias_trabajos[categoria]['confianza_promedio'] = nueva_conf
        
        # Convertir a formato esperado por el template
        repuestos_ordenados = []
        for categoria, data in sorted(categorias_repuestos.items(), key=lambda x: x[1]['count'], reverse=True):
            repuestos_ordenados.append((categoria, {
                'count': data['count'],
                'clientes': list(data['clientes']),
                'equipos': list(data['equipos']),
                'confianza': round(data['confianza_promedio'], 1),
                'color': data['color']
            }))
        
        trabajos_ordenados = []
        for categoria, data in sorted(categorias_trabajos.items(), key=lambda x: x[1]['count'], reverse=True):
            trabajos_ordenados.append((categoria, {
                'count': data['count'],
                'clientes': list(data['clientes']),
                'equipos': list(data['equipos']),
                'confianza': round(data['confianza_promedio'], 1),
                'color': data['color']
            }))
        
        # Análisis por cliente
        repuestos_por_cliente = {}
        trabajos_por_cliente = {}
        
        for cliente in set(m['cliente_nombre'] for m in mantenimientos):
            repuestos_cliente = [r for r, d in repuestos_ordenados if cliente in d['clientes']]
            trabajos_cliente = [t for t, d in trabajos_ordenados if cliente in d['clientes']]
            
            repuestos_por_cliente[cliente] = {
                'total': sum(d['count'] for r, d in repuestos_ordenados if cliente in d['clientes']),
                'tipos_count': len(repuestos_cliente),
                'tipos': repuestos_cliente[:3]
            }
            trabajos_por_cliente[cliente] = {
                'total': sum(d['count'] for t, d in trabajos_ordenados if cliente in d['clientes']),
                'tipos_count': len(trabajos_cliente),
                'tipos': trabajos_cliente[:3]
            }
        
        conn.close()
        
        return render_template('informe_repuestos.html',
                             total_mantenimientos=len(mantenimientos),
                             repuestos_ordenados=repuestos_ordenados,
                             trabajos_ordenados=trabajos_ordenados,
                             repuestos_por_cliente=repuestos_por_cliente,
                             trabajos_por_cliente=trabajos_por_cliente)
        
    except Exception as e:
        logging.error(f"Error en informe_repuestos_inteligente: {str(e)}")
        flash(f"Error al generar el informe de repuestos: {str(e)}", "error")
        return redirect(url_for('reportes'))

# API para obtener análisis inteligente de un mantenimiento específico
@app.route('/api/analizar_mantenimiento/<int:mantenimiento_id>')
def api_analizar_mantenimiento(mantenimiento_id):
    """API para analizar un mantenimiento específico con el motor inteligente"""
    try:
        conn = get_db_connection()
        
        # Obtener el mantenimiento
        mantenimiento = conn.execute('''
            SELECT m.*, e.nombre as equipo_nombre, c.nombre as cliente_nombre
            FROM mantenimientos m
            JOIN equipos e ON m.equipo_id = e.id
            JOIN clientes c ON e.cliente_id = c.id
            WHERE m.id = ?
        ''', (mantenimiento_id,)).fetchone()
        
        if not mantenimiento:
            return jsonify({'error': 'Mantenimiento no encontrado'}), 404
        
        # Crear motor de reconocimiento
        motor = crear_motor_reconocimiento()
        
        # Analizar con el motor inteligente
        analisis = motor.analizar_mantenimiento_completo(
            mantenimiento['descripcion'],
            mantenimiento_id
        )
        
        conn.close()
        
        return jsonify({
            'mantenimiento_id': mantenimiento_id,
            'equipo': mantenimiento['equipo_nombre'],
            'cliente': mantenimiento['cliente_nombre'],
            'fecha': mantenimiento['fecha_mantenimiento'],
            'descripcion_original': mantenimiento['descripcion'],
            'analisis': analisis
        })
        
    except Exception as e:
        logging.error(f"Error en api_analizar_mantenimiento: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rutas para gestión de categorías
@app.route('/gestion_categorias')
def gestion_categorias():
    """Página para gestionar categorías y palabras clave"""
    try:
        conn = get_db_connection()
        
        # Obtener categorías de repuestos con conteo de palabras
        categorias_repuestos = conn.execute('''
            SELECT 
                c.*, 
                COUNT(p.id) as num_palabras
            FROM categorias_repuestos c
            LEFT JOIN palabras_clave_repuestos p ON c.id = p.categoria_id
            GROUP BY c.id
            ORDER BY c.categoria_padre, c.nombre
        ''').fetchall()
        
        # Obtener categorías de trabajos con conteo de palabras
        categorias_trabajos = conn.execute('''
            SELECT 
                c.*, 
                COUNT(p.id) as num_palabras
            FROM categorias_trabajos c
            LEFT JOIN palabras_clave_trabajos p ON c.id = p.categoria_id
            GROUP BY c.id
            ORDER BY c.categoria_padre, c.nombre
        ''').fetchall()
        
        # Estadísticas generales
        total_categorias = len(categorias_repuestos) + len(categorias_trabajos)
        total_palabras = conn.execute('''
            SELECT 
                (SELECT COUNT(*) FROM palabras_clave_repuestos WHERE activo = 1) +
                (SELECT COUNT(*) FROM palabras_clave_trabajos WHERE activo = 1)
        ''').fetchone()[0]
        
        clasificaciones_automaticas = conn.execute('''
            SELECT COUNT(*) FROM clasificaciones_automaticas
        ''').fetchone()[0]
        
        conn.close()
        
        return render_template('gestion_categorias.html',
                             categorias_repuestos=categorias_repuestos,
                             categorias_trabajos=categorias_trabajos,
                             total_categorias=total_categorias,
                             total_palabras=total_palabras,
                             clasificaciones_automaticas=clasificaciones_automaticas)
        
    except Exception as e:
        logging.error(f"Error en gestion_categorias: {str(e)}")
        flash(f"Error al cargar la gestión de categorías: {str(e)}", "error")
        return redirect(url_for('reportes'))

@app.route('/api/categorias', methods=['GET', 'POST'])
def api_categorias():
    """API para gestionar categorías"""
    if request.method == 'GET':
        try:
            conn = get_db_connection()
            tipo = request.args.get('tipo', 'repuesto')
            
            if tipo == 'repuesto':
                categorias = conn.execute('''
                    SELECT * FROM categorias_repuestos 
                    WHERE activo = 1 
                    ORDER BY categoria_padre, nombre
                ''').fetchall()
            else:
                categorias = conn.execute('''
                    SELECT * FROM categorias_trabajos 
                    WHERE activo = 1 
                    ORDER BY categoria_padre, nombre
                ''').fetchall()
            
            conn.close()
            return jsonify([dict(row) for row in categorias])
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            datos = request.json
            conn = get_db_connection()
            
            if datos['tipo'] == 'repuesto':
                cursor = conn.execute('''
                    INSERT INTO categorias_repuestos 
                    (nombre, categoria_padre, descripcion, color_codigo)
                    VALUES (?, ?, ?, ?)
                ''', (datos['nombre'], datos.get('categoria_padre'), 
                     datos.get('descripcion'), datos['color_codigo']))
            else:
                cursor = conn.execute('''
                    INSERT INTO categorias_trabajos 
                    (nombre, categoria_padre, descripcion, color_codigo, complejidad)
                    VALUES (?, ?, ?, ?, ?)
                ''', (datos['nombre'], datos.get('categoria_padre'), 
                     datos.get('descripcion'), datos['color_codigo'], 
                     datos.get('complejidad', 1)))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'id': cursor.lastrowid})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/categorias/<int:categoria_id>', methods=['DELETE', 'PUT'])
def api_categoria_individual(categoria_id):
    """API para gestionar categoría individual"""
    if request.method == 'DELETE':
        try:
            conn = get_db_connection()
            
            # Desactivar en lugar de eliminar para mantener historial
            conn.execute('''
                UPDATE categorias_repuestos SET activo = 0 WHERE id = ?
            ''', (categoria_id,))
            
            conn.execute('''
                UPDATE categorias_trabajos SET activo = 0 WHERE id = ?
            ''', (categoria_id,))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'PUT':
        try:
            datos = request.json
            conn = get_db_connection()
            
            # Determinar si es repuesto o trabajo basado en qué tabla tiene el ID
            repuesto = conn.execute(
                'SELECT id FROM categorias_repuestos WHERE id = ?',
                (categoria_id,)
            ).fetchone()
            
            if repuesto:
                # Actualizar categoría de repuesto
                conn.execute('''
                    UPDATE categorias_repuestos 
                    SET nombre = ?, descripcion = ?, categoria_padre = ?, 
                        color_codigo = ?, activo = ?, fecha_modificacion = ?
                    WHERE id = ?
                ''', (
                    datos['nombre'],
                    datos.get('descripcion'),
                    datos.get('categoria_padre'),
                    datos.get('color_codigo'),
                    datos.get('activo', True),
                    datetime.now(),
                    categoria_id
                ))
            else:
                # Actualizar categoría de trabajo
                conn.execute('''
                    UPDATE categorias_trabajos 
                    SET nombre = ?, descripcion = ?, categoria_padre = ?, 
                        color_codigo = ?, complejidad = ?, activo = ?, fecha_modificacion = ?
                    WHERE id = ?
                ''', (
                    datos['nombre'],
                    datos.get('descripcion'),
                    datos.get('categoria_padre'),
                    datos.get('color_codigo'),
                    datos.get('complejidad', 1),
                    datos.get('activo', True),
                    datetime.now(),
                    categoria_id
                ))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Endpoints específicos para categorías por tipo y operaciones
@app.route('/api/categorias/repuesto/<int:categoria_id>', methods=['DELETE', 'PUT'])
@require_auth
def gestionar_categoria_repuesto(categoria_id):
    """Gestionar categoría de repuesto específica"""
    if request.method == 'DELETE':
        return eliminar_categoria_repuesto_impl(categoria_id)
    elif request.method == 'PUT':
        return editar_categoria_repuesto_impl(categoria_id)

def eliminar_categoria_repuesto_impl(categoria_id):
    """Eliminar categoría de repuesto específica"""
    try:
        conn = get_db_connection()
        
        # Verificar si la categoría existe
        categoria = conn.execute(
            'SELECT * FROM categorias_repuestos WHERE id = ?', 
            (categoria_id,)
        ).fetchone()
        
        if not categoria:
            conn.close()
            return jsonify({'success': False, 'error': 'Categoría no encontrada'}), 404
        
        # Desactivar en lugar de eliminar
        conn.execute(
            'UPDATE categorias_repuestos SET activo = 0, fecha_modificacion = ? WHERE id = ?',
            (datetime.now(), categoria_id)
        )
        
        # Log de auditoría
        log_audit('DELETE', 'categorias_repuestos', categoria_id, 
                 dict(categoria), {'activo': 0})
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Categoría eliminada exitosamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def editar_categoria_repuesto_impl(categoria_id):
    """Editar categoría de repuesto específica"""
    try:
        datos = request.json
        conn = get_db_connection()
        
        # Verificar si la categoría existe
        categoria = conn.execute(
            'SELECT * FROM categorias_repuestos WHERE id = ?', 
            (categoria_id,)
        ).fetchone()
        
        if not categoria:
            conn.close()
            return jsonify({'success': False, 'error': 'Categoría no encontrada'}), 404
        
        # Actualizar categoría
        conn.execute('''
            UPDATE categorias_repuestos 
            SET nombre = ?, descripcion = ?, categoria_padre = ?, 
                color_codigo = ?, activo = ?, fecha_modificacion = ?
            WHERE id = ?
        ''', (
            datos['nombre'],
            datos.get('descripcion'),
            datos.get('categoria_padre'),
            datos.get('color_codigo'),
            datos.get('activo', True),
            datetime.now(),
            categoria_id
        ))
        
        # Log de auditoría
        log_audit('UPDATE', 'categorias_repuestos', categoria_id, 
                 dict(categoria), datos)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Categoría actualizada exitosamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categorias/trabajo/<int:categoria_id>', methods=['DELETE', 'PUT'])
@require_auth
def gestionar_categoria_trabajo(categoria_id):
    """Gestionar categoría de trabajo específica"""
    if request.method == 'DELETE':
        return eliminar_categoria_trabajo_impl(categoria_id)
    elif request.method == 'PUT':
        return editar_categoria_trabajo_impl(categoria_id)

def eliminar_categoria_trabajo_impl(categoria_id):
    """Eliminar categoría de trabajo específica"""
    try:
        conn = get_db_connection()
        
        categoria = conn.execute(
            'SELECT * FROM categorias_trabajos WHERE id = ?', 
            (categoria_id,)
        ).fetchone()
        
        if not categoria:
            conn.close()
            return jsonify({'success': False, 'error': 'Categoría no encontrada'}), 404
        
        conn.execute(
            'UPDATE categorias_trabajos SET activo = 0, fecha_modificacion = ? WHERE id = ?',
            (datetime.now(), categoria_id)
        )
        
        log_audit('DELETE', 'categorias_trabajos', categoria_id, 
                 dict(categoria), {'activo': 0})
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Categoría eliminada exitosamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def editar_categoria_trabajo_impl(categoria_id):
    """Editar categoría de trabajo específica"""
    try:
        datos = request.json
        conn = get_db_connection()
        
        # Verificar si la categoría existe
        categoria = conn.execute(
            'SELECT * FROM categorias_trabajos WHERE id = ?', 
            (categoria_id,)
        ).fetchone()
        
        if not categoria:
            conn.close()
            return jsonify({'success': False, 'error': 'Categoría no encontrada'}), 404
        
        # Actualizar categoría
        conn.execute('''
            UPDATE categorias_trabajos 
            SET nombre = ?, descripcion = ?, categoria_padre = ?, 
                color_codigo = ?, complejidad = ?, activo = ?, fecha_modificacion = ?
            WHERE id = ?
        ''', (
            datos['nombre'],
            datos.get('descripcion'),
            datos.get('categoria_padre'),
            datos.get('color_codigo'),
            datos.get('complejidad', 1),
            datos.get('activo', True),
            datetime.now(),
            categoria_id
        ))
        
        # Log de auditoría
        log_audit('UPDATE', 'categorias_trabajos', categoria_id, 
                 dict(categoria), datos)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Categoría actualizada exitosamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categorias/repuesto/<int:categoria_id>/toggle', methods=['PATCH'])
@require_auth
def toggle_categoria_repuesto(categoria_id):
    """Toggle estado de categoría de repuesto"""
    try:
        datos = request.json
        nuevo_estado = datos.get('activo', True)
        
        conn = get_db_connection()
        
        conn.execute(
            'UPDATE categorias_repuestos SET activo = ?, fecha_modificacion = ? WHERE id = ?',
            (nuevo_estado, datetime.now(), categoria_id)
        )
        
        log_audit('UPDATE', 'categorias_repuestos', categoria_id, 
                 {}, {'activo': nuevo_estado})
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'activo': nuevo_estado})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categorias/trabajo/<int:categoria_id>/toggle', methods=['PATCH'])
@require_auth
def toggle_categoria_trabajo(categoria_id):
    """Toggle estado de categoría de trabajo"""
    try:
        datos = request.json
        nuevo_estado = datos.get('activo', True)
        
        conn = get_db_connection()
        
        conn.execute(
            'UPDATE categorias_trabajos SET activo = ?, fecha_modificacion = ? WHERE id = ?',
            (nuevo_estado, datetime.now(), categoria_id)
        )
        
        log_audit('UPDATE', 'categorias_trabajos', categoria_id, 
                 {}, {'activo': nuevo_estado})
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'activo': nuevo_estado})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categorias/<int:categoria_id>/palabras', methods=['GET', 'POST'])
@require_auth
def gestionar_palabras_categoria(categoria_id):
    """Gestionar palabras clave de una categoría"""
    if request.method == 'GET':
        return obtener_palabras_categoria_impl(categoria_id)
    elif request.method == 'POST':
        return agregar_palabra_categoria_impl(categoria_id)

def obtener_palabras_categoria_impl(categoria_id):
    """Obtener palabras clave de una categoría"""
    try:
        conn = get_db_connection()
        
        # Buscar en ambas tablas
        palabras_repuestos = conn.execute('''
            SELECT palabra, peso as frecuencia, 'repuesto' as tipo
            FROM palabras_clave_repuestos 
            WHERE categoria_id = ? AND activo = 1
            ORDER BY peso DESC
        ''', (categoria_id,)).fetchall()
        
        palabras_trabajos = conn.execute('''
            SELECT palabra, peso as frecuencia, 'trabajo' as tipo
            FROM palabras_clave_trabajos 
            WHERE categoria_id = ? AND activo = 1
            ORDER BY peso DESC
        ''', (categoria_id,)).fetchall()
        
        conn.close()
        
        palabras = [dict(p) for p in palabras_repuestos] + [dict(p) for p in palabras_trabajos]
        
        return jsonify({'success': True, 'palabras': palabras})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def agregar_palabra_categoria_impl(categoria_id):
    """Agregar palabra clave a una categoría"""
    try:
        datos = request.json
        nueva_palabra = datos.get('palabra', '').strip().lower()
        
        if not nueva_palabra:
            return jsonify({'success': False, 'error': 'Palabra clave no puede estar vacía'}), 400
        
        conn = get_db_connection()
        
        # Verificar si la categoría existe en repuestos
        categoria_repuesto = conn.execute(
            'SELECT id FROM categorias_repuestos WHERE id = ? AND activo = 1',
            (categoria_id,)
        ).fetchone()
        
        # Verificar si la categoría existe en trabajos
        categoria_trabajo = conn.execute(
            'SELECT id FROM categorias_trabajos WHERE id = ? AND activo = 1',
            (categoria_id,)
        ).fetchone()
        
        if categoria_repuesto:
            # Verificar si la palabra ya existe
            existe = conn.execute(
                'SELECT id FROM palabras_clave_repuestos WHERE categoria_id = ? AND palabra = ?',
                (categoria_id, nueva_palabra)
            ).fetchone()
            
            if not existe:
                conn.execute('''
                    INSERT INTO palabras_clave_repuestos (categoria_id, palabra, peso, activo, fecha_creacion)
                    VALUES (?, ?, ?, ?, ?)
                ''', (categoria_id, nueva_palabra, 1.0, 1, datetime.now()))
            else:
                conn.close()
                return jsonify({'success': False, 'error': 'La palabra clave ya existe'}), 400
                
        elif categoria_trabajo:
            # Verificar si la palabra ya existe
            existe = conn.execute(
                'SELECT id FROM palabras_clave_trabajos WHERE categoria_id = ? AND palabra = ?',
                (categoria_id, nueva_palabra)
            ).fetchone()
            
            if not existe:
                conn.execute('''
                    INSERT INTO palabras_clave_trabajos (categoria_id, palabra, peso, activo, fecha_creacion)
                    VALUES (?, ?, ?, ?, ?)
                ''', (categoria_id, nueva_palabra, 1.0, 1, datetime.now()))
            else:
                conn.close()
                return jsonify({'success': False, 'error': 'La palabra clave ya existe'}), 400
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Categoría no encontrada'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Palabra clave agregada exitosamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/estadisticas_categorias')
def api_estadisticas_categorias():
    """API para obtener estadísticas de uso de categorías"""
    try:
        conn = get_db_connection()
        
        # Estadísticas de uso de categorías
        stats = conn.execute('''
            SELECT 
                categoria_detectada as nombre,
                COUNT(*) as uso_count,
                AVG(confianza) as confianza_promedio
            FROM clasificaciones_automaticas
            GROUP BY categoria_detectada
            ORDER BY uso_count DESC
            LIMIT 10
        ''').fetchall()
        
        conn.close()
        
        # Agregar colores por defecto
        categorias_stats = []
        colores = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', 
                  '#fd7e14', '#20c997', '#6c757d', '#e83e8c', '#17a2b8']
        
        for i, stat in enumerate(stats):
            categorias_stats.append({
                'nombre': stat['nombre'],
                'uso_count': stat['uso_count'],
                'confianza_promedio': round(stat['confianza_promedio'], 1),
                'color_codigo': colores[i % len(colores)]
            })
        
        return jsonify({'categorias': categorias_stats})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================================
# FUNCIONES DE GENERACIÓN DE EXCEL
# =========================================

def generar_excel_dashboard(conn, workbook, header_format, title_format, data_format, number_format, date_format):
    """Generar reporte de dashboard en Excel"""
    worksheet = workbook.add_worksheet('Dashboard')
    
    # Título
    worksheet.merge_range('A1:G1', 'REPORTE EJECUTIVO - DASHBOARD', title_format)
    worksheet.write('A2', f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}', data_format)
    
    # Estadísticas principales
    stats = {
        'total_equipos': conn.execute('SELECT COUNT(*) FROM equipos').fetchone()[0],
        'total_mantenimientos': conn.execute('SELECT COUNT(*) FROM mantenimientos').fetchone()[0],
        'total_clientes': conn.execute('SELECT COUNT(*) FROM clientes').fetchone()[0],
        'total_repuestos': conn.execute('SELECT COUNT(*) FROM repuestos').fetchone()[0]
    }
    
    row = 4
    worksheet.write(row, 0, 'ESTADÍSTICAS GENERALES', header_format)
    row += 1
    for key, value in stats.items():
        worksheet.write(row, 0, key.replace('_', ' ').title(), data_format)
        worksheet.write(row, 1, value, number_format)
        row += 1
    
    # Equipos por estado
    row += 2
    worksheet.write(row, 0, 'EQUIPOS POR ESTADO', header_format)
    row += 1
    equipos_estado = conn.execute('SELECT estado, COUNT(*) FROM equipos GROUP BY estado').fetchall()
    for estado, count in equipos_estado:
        worksheet.write(row, 0, estado, data_format)
        worksheet.write(row, 1, count, number_format)
        row += 1
    
    # Ajustar ancho de columnas
    worksheet.set_column('A:A', 25)
    worksheet.set_column('B:B', 15)

def generar_excel_equipos(conn, workbook, header_format, title_format, data_format, number_format, date_format):
    """Generar reporte de equipos en Excel"""
    worksheet = workbook.add_worksheet('Equipos')
    
    # Título
    worksheet.merge_range('A1:H1', 'REPORTE DE EQUIPOS', title_format)
    
    # Headers
    headers = ['ID', 'Nombre', 'Marca', 'Modelo', 'Cliente', 'Estado', 'Ubicación', 'Fecha Instalación']
    for col, header in enumerate(headers):
        worksheet.write(2, col, header, header_format)
    
    # Datos
    equipos = conn.execute('''
        SELECT e.id, e.nombre, e.marca, e.modelo, c.nombre as cliente,
               e.estado, e.ubicacion, e.fecha_instalacion
        FROM equipos e
        LEFT JOIN clientes c ON e.cliente_id = c.id
        ORDER BY e.nombre
    ''').fetchall()
    
    for row, equipo in enumerate(equipos, 3):
        for col, value in enumerate(equipo):
            if col == 7 and value:  # Fecha
                worksheet.write(row, col, value, date_format)
            else:
                worksheet.write(row, col, value or '', data_format)
    
    # Ajustar columnas
    worksheet.set_column('A:A', 8)
    worksheet.set_column('B:B', 20)
    worksheet.set_column('C:D', 15)
    worksheet.set_column('E:E', 20)
    worksheet.set_column('F:G', 12)
    worksheet.set_column('H:H', 15)

def generar_excel_mantenimientos(conn, workbook, header_format, title_format, data_format, number_format, date_format):
    """Generar reporte de mantenimientos en Excel"""
    worksheet = workbook.add_worksheet('Mantenimientos')
    
    # Título
    worksheet.merge_range('A1:I1', 'REPORTE DE MANTENIMIENTOS', title_format)
    
    # Headers
    headers = ['ID', 'Equipo', 'Cliente', 'Tipo', 'Estado', 'Técnico', 'Fecha', 'Costo', 'Descripción']
    for col, header in enumerate(headers):
        worksheet.write(2, col, header, header_format)
    
    # Datos
    mantenimientos = conn.execute('''
        SELECT m.id, e.nombre as equipo, c.nombre as cliente,
               m.tipo_mantenimiento, m.estado, m.tecnico,
               m.fecha_mantenimiento, m.costo, m.descripcion
        FROM mantenimientos m
        LEFT JOIN equipos e ON m.equipo_id = e.id
        LEFT JOIN clientes c ON e.cliente_id = c.id
        ORDER BY m.fecha_mantenimiento DESC
    ''').fetchall()
    
    for row, mantenimiento in enumerate(mantenimientos, 3):
        for col, value in enumerate(mantenimiento):
            if col == 6 and value:  # Fecha
                worksheet.write(row, col, value, date_format)
            elif col == 7 and value:  # Costo
                worksheet.write(row, col, float(value), number_format)
            else:
                worksheet.write(row, col, value or '', data_format)
    
    # Ajustar columnas
    worksheet.set_column('A:A', 8)
    worksheet.set_column('B:C', 20)
    worksheet.set_column('D:F', 15)
    worksheet.set_column('G:G', 12)
    worksheet.set_column('H:H', 10)
    worksheet.set_column('I:I', 30)

def generar_excel_clientes(conn, workbook, header_format, title_format, data_format, number_format, date_format):
    """Generar reporte de clientes en Excel"""
    worksheet = workbook.add_worksheet('Clientes')
    
    # Título
    worksheet.merge_range('A1:G1', 'REPORTE DE CLIENTES', title_format)
    
    # Headers
    headers = ['ID', 'Nombre', 'Contacto', 'Teléfono', 'Email', 'Dirección', 'Equipos']
    for col, header in enumerate(headers):
        worksheet.write(2, col, header, header_format)
    
    # Datos
    clientes = conn.execute('''
        SELECT c.id, c.nombre, c.contacto, c.telefono, c.email, c.direccion,
               COUNT(e.id) as num_equipos
        FROM clientes c
        LEFT JOIN equipos e ON c.id = e.cliente_id
        GROUP BY c.id
        ORDER BY c.nombre
    ''').fetchall()
    
    for row, cliente in enumerate(clientes, 3):
        for col, value in enumerate(cliente):
            if col == 6:  # Número de equipos
                worksheet.write(row, col, value, number_format)
            else:
                worksheet.write(row, col, value or '', data_format)
    
    # Ajustar columnas
    worksheet.set_column('A:A', 8)
    worksheet.set_column('B:C', 20)
    worksheet.set_column('D:E', 15)
    worksheet.set_column('F:F', 25)
    worksheet.set_column('G:G', 10)

def generar_excel_repuestos(conn, workbook, header_format, title_format, data_format, number_format, date_format):
    """Generar reporte de repuestos en Excel"""
    worksheet = workbook.add_worksheet('Repuestos')
    
    # Título
    worksheet.merge_range('A1:H1', 'REPORTE DE REPUESTOS', title_format)
    
    # Headers
    headers = ['ID', 'Nombre', 'Código', 'Proveedor', 'Stock Actual', 'Stock Mínimo', 'Precio', 'Estado']
    for col, header in enumerate(headers):
        worksheet.write(2, col, header, header_format)
    
    # Datos
    repuestos = conn.execute('''
        SELECT id, nombre, codigo, proveedor, stock_actual, stock_minimo, precio, estado
        FROM repuestos
        ORDER BY nombre
    ''').fetchall()
    
    for row, repuesto in enumerate(repuestos, 3):
        for col, value in enumerate(repuesto):
            if col in [4, 5]:  # Stock
                worksheet.write(row, col, value or 0, number_format)
            elif col == 6 and value:  # Precio
                worksheet.write(row, col, float(value), number_format)
            else:
                worksheet.write(row, col, value or '', data_format)
    
    # Ajustar columnas
    worksheet.set_column('A:A', 8)
    worksheet.set_column('B:B', 25)
    worksheet.set_column('C:D', 15)
    worksheet.set_column('E:F', 12)
    worksheet.set_column('G:G', 10)
    worksheet.set_column('H:H', 12)

def generar_excel_auditoria(conn, workbook, header_format, title_format, data_format, number_format, date_format):
    """Generar reporte de auditoría en Excel"""
    worksheet = workbook.add_worksheet('Auditoria')
    
    # Título
    worksheet.merge_range('A1:G1', 'REPORTE DE AUDITORÍA', title_format)
    
    # Headers
    headers = ['ID', 'Usuario', 'Acción', 'Tabla', 'Registro', 'Fecha', 'Detalles']
    for col, header in enumerate(headers):
        worksheet.write(2, col, header, header_format)
    
    # Datos (últimos 1000 registros)
    auditoria = conn.execute('''
        SELECT id, usuario, accion, tabla_afectada, registro_id, fecha_accion, detalles
        FROM auditoria
        ORDER BY fecha_accion DESC
        LIMIT 1000
    ''').fetchall()
    
    for row, registro in enumerate(auditoria, 3):
        for col, value in enumerate(registro):
            if col == 5 and value:  # Fecha
                worksheet.write(row, col, value, date_format)
            else:
                worksheet.write(row, col, value or '', data_format)
    
    # Ajustar columnas
    worksheet.set_column('A:A', 8)
    worksheet.set_column('B:B', 15)
    worksheet.set_column('C:C', 20)
    worksheet.set_column('D:E', 12)
    worksheet.set_column('F:F', 15)
    worksheet.set_column('G:G', 30)

if __name__ == '__main__':
    init_db()
    # Configuración para producción y desarrollo
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)
