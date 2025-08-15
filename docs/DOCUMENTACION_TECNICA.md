# 🔧 Documentación Técnica - Sistema de Gestión de Taller

## 📋 Índice

1. [Arquitectura del Sistema](#-arquitectura-del-sistema)
2. [Base de Datos](#-base-de-datos)
3. [Backend (Flask)](#-backend-flask)
4. [Frontend](#-frontend)
5. [API Endpoints](#-api-endpoints)
6. [Seguridad](#-seguridad)
7. [Mantenimiento](#-mantenimiento)
8. [Desarrollo](#-desarrollo)

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND                              │
├─────────────────┬─────────────────┬─────────────────────┤
│ HTML5 Templates │ Bootstrap 5.3   │ JavaScript ES6+     │
│ Jinja2          │ Font Awesome    │ Chart.js            │
└─────────────────┴─────────────────┴─────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    BACKEND                               │
├─────────────────┬─────────────────┬─────────────────────┤
│ Flask 2.0+      │ SQLite 3        │ Pandas              │
│ Python 3.8+     │ Werkzeug        │ OpenPyXL            │
│ 🧠 Motor IA     │ NLP Engine      │ Text Analysis       │
└─────────────────┴─────────────────┴─────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                 PERSISTENCIA                             │
├─────────────────┬─────────────────┬─────────────────────┤
│ SQLite Database │ File Storage    │ Logs                │
│ taller.db       │ uploads/        │ taller.log          │
└─────────────────┴─────────────────┴─────────────────────┘
```

### Patrón MVC

```python
MODEL (app.py + motor_reconocimiento.py)
├── Database Connection & Queries
├── Data Processing Functions
├── 🧠 Intelligent Recognition Engine
├── Text Analysis & Categorization
└── Business Logic

VIEW (templates/)
├── HTML Templates (Jinja2)
├── CSS Styling (Bootstrap)
├── JavaScript Interactions
├── 🎯 Smart Analytics UI
└── ⚙️ Category Management Interface

CONTROLLER (app.py)
├── Flask Routes
├── Request Handling
├── 🔌 AI Engine APIs
└── Response Generation
```

## 🗄️ Base de Datos

### Esquema de Base de Datos

```sql
-- Diagrama de Relaciones
clientes (1) ──────── (N) equipos (1) ──────── (N) mantenimientos
                                                        │
                                                        │
repuestos (1) ──────── (N) movimientos_repuestos (N) ───┘

-- 🧠 Sistema Inteligente de Categorización
categorias_repuestos (1) ──── (N) palabras_clave_repuestos
categorias_trabajos (1) ───── (N) palabras_clave_trabajos
mantenimientos (1) ────────── (N) clasificaciones_automaticas
```

### Tabla: clientes

```sql
CREATE TABLE clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,           -- Nombre único del cliente
    telefono TEXT,                         -- Número de contacto
    email TEXT,                            -- Correo electrónico
    direccion TEXT,                        -- Dirección física
    observaciones TEXT,                    -- Notas adicionales
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Índices**:
- PRIMARY KEY en `id`
- UNIQUE en `nombre`

**Restricciones**:
- `nombre` es obligatorio y único
- No se puede eliminar si tiene equipos asociados

### Tabla: equipos

```sql
CREATE TABLE equipos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,                    -- FK a clientes
    nombre TEXT NOT NULL,                  -- Nombre del equipo
    marca TEXT,                            -- Marca/fabricante
    modelo TEXT,                           -- Modelo específico
    numero_serie TEXT,                     -- Número de serie único
    fecha_compra DATE,                     -- Fecha de adquisición
    estado TEXT DEFAULT 'Activo',          -- Estado operativo
    ubicacion TEXT,                        -- Ubicación física
    observaciones TEXT,                    -- Notas adicionales
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes (id)
);
```

**Estados válidos**: `'Activo', 'Inactivo', 'Mantenimiento', 'Fuera de Servicio'`

**Restricciones**:
- `cliente_id` debe existir en tabla clientes
- No se puede eliminar si tiene mantenimientos asociados

### Tabla: mantenimientos

```sql
CREATE TABLE mantenimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id INTEGER,                     -- FK a equipos
    tipo_mantenimiento TEXT NOT NULL,      -- Tipo de mantenimiento
    fecha_mantenimiento DATE NOT NULL,     -- Fecha de realización
    descripcion TEXT,                      -- Descripción detallada
    costo REAL,                            -- Costo total
    tecnico TEXT,                          -- Técnico responsable
    estado TEXT DEFAULT 'Pendiente',       -- Estado del trabajo
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipo_id) REFERENCES equipos (id)
);
```

**Tipos válidos**: `'Preventivo', 'Correctivo', 'Emergencia', 'Inspección', 'Reparación'`
**Estados válidos**: `'Pendiente', 'En Progreso', 'Completado', 'Cancelado'`

### Tabla: repuestos

```sql
CREATE TABLE repuestos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,                  -- Nombre del repuesto
    codigo TEXT UNIQUE,                    -- Código identificador
    descripcion TEXT,                      -- Descripción técnica
    stock_actual INTEGER DEFAULT 0,       -- Cantidad en stock
    stock_minimo INTEGER DEFAULT 0,       -- Nivel de reorden
    precio_unitario REAL,                 -- Precio por unidad
    proveedor TEXT,                        -- Proveedor principal
    ubicacion TEXT,                        -- Ubicación en almacén
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Restricciones**:
- `codigo` debe ser único si se especifica
- `stock_actual` no puede ser negativo
- No se puede eliminar si `stock_actual > 0` o tiene movimientos

### Tabla: movimientos_repuestos

```sql
CREATE TABLE movimientos_repuestos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repuesto_id INTEGER,                   -- FK a repuestos
    mantenimiento_id INTEGER,              -- FK a mantenimientos (opcional)
    tipo_movimiento TEXT NOT NULL,         -- 'entrada', 'salida', 'ajuste'
    cantidad INTEGER NOT NULL,             -- Cantidad del movimiento
    motivo TEXT,                           -- Razón del movimiento
    fecha_movimiento DATE DEFAULT CURRENT_DATE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (repuesto_id) REFERENCES repuestos (id),
    FOREIGN KEY (mantenimiento_id) REFERENCES mantenimientos (id)
);
```

**Tipos de movimiento**:
- `'entrada'`: Incrementa stock (compras, devoluciones)
- `'salida'`: Decrementa stock (uso en mantenimiento)
- `'ajuste'`: Corrección de inventario (puede ser + o -)

### 🧠 Tablas del Sistema Inteligente

### Tabla: categorias_repuestos

```sql
CREATE TABLE categorias_repuestos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,           -- Nombre de la categoría
    descripcion TEXT,                      -- Descripción detallada
    color TEXT DEFAULT '#007bff',          -- Color identificador (hex)
    activa BOOLEAN DEFAULT 1,             -- Si está activa
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Propósito**: Define categorías principales de repuestos (Filtros, Lubricantes, etc.)

### Tabla: categorias_trabajos

```sql
CREATE TABLE categorias_trabajos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,           -- Nombre de la categoría
    descripcion TEXT,                      -- Descripción detallada
    color TEXT DEFAULT '#28a745',          -- Color identificador (hex)
    activa BOOLEAN DEFAULT 1,             -- Si está activa
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Propósito**: Define categorías principales de trabajos (Mantenimiento, Hidráulico, etc.)

### Tabla: palabras_clave_repuestos

```sql
CREATE TABLE palabras_clave_repuestos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id INTEGER,                  -- FK a categorias_repuestos
    palabra_clave TEXT NOT NULL,           -- Palabra o frase clave
    sinonimos TEXT,                        -- Sinónimos separados por comas
    peso_confianza REAL DEFAULT 1.0,      -- Peso para cálculo de confianza
    activa BOOLEAN DEFAULT 1,             -- Si está activa
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (categoria_id) REFERENCES categorias_repuestos (id)
);
```

**Propósito**: Almacena palabras clave y sinónimos para detectar repuestos en texto

### Tabla: palabras_clave_trabajos

```sql
CREATE TABLE palabras_clave_trabajos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id INTEGER,                  -- FK a categorias_trabajos
    palabra_clave TEXT NOT NULL,           -- Palabra o frase clave
    sinonimos TEXT,                        -- Sinónimos separados por comas
    peso_confianza REAL DEFAULT 1.0,      -- Peso para cálculo de confianza
    activa BOOLEAN DEFAULT 1,             -- Si está activa
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (categoria_id) REFERENCES categorias_trabajos (id)
);
```

**Propósito**: Almacena palabras clave y sinónimos para detectar tipos de trabajo en texto

### Tabla: clasificaciones_automaticas

```sql
CREATE TABLE clasificaciones_automaticas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mantenimiento_id INTEGER,              -- FK a mantenimientos
    tipo TEXT NOT NULL,                    -- 'repuesto' o 'trabajo'
    categoria_id INTEGER,                  -- ID de categoría detectada
    texto_detectado TEXT,                  -- Texto que activó la detección
    confianza REAL,                        -- Puntuación de confianza (0-100)
    palabras_clave_usadas TEXT,           -- Palabras clave que coincidieron
    fecha_clasificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mantenimiento_id) REFERENCES mantenimientos (id)
);
```

**Propósito**: Almacena el historial de clasificaciones automáticas realizadas por el motor IA

**Índices recomendados**:
```sql
CREATE INDEX idx_clasificaciones_mantenimiento ON clasificaciones_automaticas(mantenimiento_id);
CREATE INDEX idx_clasificaciones_tipo ON clasificaciones_automaticas(tipo);
CREATE INDEX idx_clasificaciones_confianza ON clasificaciones_automaticas(confianza);
CREATE INDEX idx_palabras_clave_categoria_repuestos ON palabras_clave_repuestos(categoria_id);
CREATE INDEX idx_palabras_clave_categoria_trabajos ON palabras_clave_trabajos(categoria_id);
```

## 🐍 Backend (Flask)

### Estructura de Archivos

```python
app.py
├── Imports & Configuration        # Líneas 1-49
├── Helper Functions              # Líneas 51-255
│   ├── procesar_hoja_excel()     # Procesamiento Excel
│   ├── get_db_connection()       # Conexión DB
│   └── init_db()                 # Inicialización DB
├── Routes: Dashboard             # Líneas 310-340
├── Routes: Clientes              # Líneas 342-520
├── Routes: Equipos               # Líneas 522-720
├── Routes: Mantenimientos        # Líneas 722-920
├── Routes: Repuestos             # Líneas 922-1120
├── Routes: Reportes              # Líneas 1122-1380
├── 🧠 Routes: Sistema Inteligente # Líneas 1400-1650
│   ├── informe_repuestos_inteligente()
│   ├── gestion_categorias()
│   ├── api_analizar_mantenimiento()
│   └── api_categorias()
├── Routes: Utilidades            # Líneas 1700-1900
└── Main Execution                # Líneas 2000+

motor_reconocimiento.py
├── Imports & Configuration        # Sistema NLP
├── 🔍 Text Processing Functions
│   ├── normalizar_texto()        # Limpieza y normalización
│   ├── extraer_frases_clave()    # Extracción de frases
│   └── calcular_confianza()      # Cálculo de precisión
├── 🎯 Classification Engine
│   ├── clasificar_repuestos()    # Detección de repuestos
│   ├── clasificar_trabajos()     # Detección de trabajos
│   └── crear_motor_reconocimiento() # Motor principal
└── 📊 Analysis Functions         # Funciones de análisis
```

### Configuración y Constantes

```python
# Configuración de la aplicación
app.config.update(
    DATABASE='taller.db',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB
    UPLOAD_FOLDER='uploads',
    DEBUG=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
)

# Constantes de negocio
ESTADOS_EQUIPO = ['Activo', 'Inactivo', 'Mantenimiento', 'Fuera de Servicio']
TIPOS_MANTENIMIENTO = ['Preventivo', 'Correctivo', 'Emergencia', 'Inspección', 'Reparación']
ESTADOS_MANTENIMIENTO = ['Pendiente', 'En Progreso', 'Completado', 'Cancelado']
```

### Funciones Helper Principales

#### `get_db_connection()`
```python
def get_db_connection():
    """
    Crea conexión SQLite con row_factory para acceso por nombre.
    
    Returns:
        sqlite3.Connection: Conexión configurada
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Permite acceso por nombre
    return conn
```

#### `procesar_hoja_excel(df, cliente_id, conn, sheet_name)`
```python
def procesar_hoja_excel(df, cliente_id, conn, sheet_name):
    """
    Procesa una hoja Excel para un cliente específico.
    
    - Detección automática de columnas
    - Agrupación de mantenimientos por equipo/fecha
    - Parsing inteligente de fechas
    - Manejo de filas de continuación
    
    Args:
        df: DataFrame de pandas
        cliente_id: ID del cliente propietario
        conn: Conexión a base de datos
        sheet_name: Nombre de la hoja Excel
        
    Returns:
        tuple: (equipos_creados, mantenimientos_creados)
    """
```

### Patrón de Routes

Todos los routes siguen un patrón consistente:

```python
@app.route('/entidad', methods=['GET'])
def listar_entidad():
    """Lista todas las entidades con filtros opcionales"""
    try:
        conn = get_db_connection()
        # Procesar filtros
        # Ejecutar query
        # Preparar datos para template
        return render_template('entidad.html', data=data)
    except Exception as e:
        logging.error(f"Error: {e}")
        flash('Error al cargar datos', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/entidad/nuevo', methods=['GET', 'POST'])
def nuevo_entidad():
    """Crear nueva entidad"""
    if request.method == 'POST':
        try:
            # Validar datos
            # Insertar en DB
            # Confirmar éxito
            flash('Entidad creada exitosamente', 'success')
            return redirect(url_for('listar_entidad'))
        except Exception as e:
            # Manejar error
            flash(f'Error: {e}', 'error')
    
    # GET: Mostrar formulario
    return render_template('nuevo_entidad.html')
```

### Manejo de Errores

```python
# Logging configurado globalmente
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('taller.log'),
        logging.StreamHandler()
    ]
)

# En cada route
try:
    # Lógica principal
except sqlite3.IntegrityError as e:
    flash('Error de integridad de datos', 'error')
    logging.error(f"Integrity error: {e}")
except Exception as e:
    flash('Error interno del servidor', 'error')
    logging.error(f"Unexpected error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
```

## 🎨 Frontend

### Template Structure

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="es">
<head>
    <!-- Meta tags, Bootstrap CSS, Font Awesome -->
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <!-- Menu items -->
    </nav>
    
    <!-- Flash Messages -->
    <div class="container mt-3">
        {% with messages = get_flashed_messages(with_categories=true) %}
            <!-- Alert banners -->
        {% endwith %}
    </div>
    
    <!-- Page Content -->
    <div class="container-fluid mt-4">
        {% block content %}{% endblock %}
    </div>
    
    <!-- Scripts: Bootstrap, Chart.js, Custom JS -->
</body>
</html>
```

### Componentes Reutilizables

#### Tablas con Ordenamiento

```html
<!-- En cada tabla -->
<table class="table table-hover sortable">
    <thead class="table-dark">
        <tr>
            <th class="sortable" data-sort="nombre">
                Nombre <i class="fas fa-sort sort-icon"></i>
            </th>
            <!-- Más columnas -->
        </tr>
    </thead>
    <tbody>
        <!-- Datos -->
    </tbody>
</table>

<!-- JavaScript global -->
<script src="{{ url_for('static', filename='js/table-sort.js') }}"></script>
```

#### Modales de Confirmación

```html
<!-- Modal estándar -->
<div class="modal fade" id="confirmarModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header bg-danger text-white">
                <h5>⚠️ Confirmar Eliminación</h5>
            </div>
            <div class="modal-body">
                <p>¿Estás seguro de que deseas eliminar este registro?</p>
                <div class="alert alert-warning">
                    <strong>Información del registro:</strong>
                    <div id="infoRegistro"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    Cancelar
                </button>
                <form id="formEliminar" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-danger">
                        Eliminar
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
```

#### Filtros Dinámicos

```html
<!-- Panel de filtros -->
<div class="row mb-3">
    <div class="col-md-4">
        <input type="text" class="form-control" id="buscarTexto" 
               placeholder="🔍 Buscar...">
    </div>
    <div class="col-md-3">
        <select class="form-control" id="filtroCliente">
            <option value="">Todos los clientes</option>
            <!-- Opciones dinámicas -->
        </select>
    </div>
    <div class="col-md-2">
        <button type="button" class="btn btn-outline-secondary" 
                onclick="limpiarFiltros()">
            🧹 Limpiar
        </button>
    </div>
</div>
```

### JavaScript Patterns

#### Event Delegation

```javascript
// Patrón usado en toda la aplicación
document.addEventListener('DOMContentLoaded', function() {
    // Event delegation para mejor rendimiento
    document.addEventListener('click', function(e) {
        // Manejar diferentes tipos de botones
        if (e.target.closest('.eliminar-registro')) {
            handleEliminar(e.target.closest('.eliminar-registro'));
        }
        
        if (e.target.closest('.ajustar-stock')) {
            handleAjustarStock(e.target.closest('.ajustar-stock'));
        }
        
        // Más handlers...
    });
});
```

#### Data Attributes

```html
<!-- HTML más limpio usando data attributes -->
<button class="btn btn-danger eliminar-registro"
        data-id="{{ registro.id }}"
        data-nombre="{{ registro.nombre }}"
        data-info="{{ registro.info_adicional }}">
    <i class="fas fa-trash"></i>
</button>
```

```javascript
// JavaScript correspondiente
function handleEliminar(button) {
    const id = button.dataset.id;
    const nombre = button.dataset.nombre;
    const info = button.dataset.info;
    
    // Usar datos para configurar modal
    confirmarEliminacion(id, nombre, info);
}
```

### Chart.js Integration

```javascript
// Configuración estándar para gráficos
const chartConfig = {
    type: 'line',
    data: {
        labels: monthLabels,
        datasets: [{
            label: 'Mantenimientos',
            data: dataValues,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            tension: 0.1
        }]
    },
    options: {
        responsive: true,
        plugins: {
            title: {
                display: true,
                text: 'Tendencia de Mantenimientos'
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    stepSize: 1
                }
            }
        }
    }
};

const ctx = document.getElementById('chartCanvas').getContext('2d');
new Chart(ctx, chartConfig);
```

## 🔌 API Endpoints

### Estructura de URLs

```
/                              # Dashboard principal
├── /clientes                  # CRUD clientes
│   ├── /nuevo                 # GET/POST crear
│   ├── /<id>                  # GET ver detalles
│   ├── /<id>/editar          # GET/POST editar
│   └── /<id>/eliminar        # POST eliminar
│
├── /equipos                   # CRUD equipos
│   ├── /nuevo                 # GET/POST crear
│   ├── /<id>/editar          # GET/POST editar
│   └── /<id>/eliminar        # POST eliminar
│
├── /mantenimientos           # CRUD mantenimientos
│   ├── /nuevo                # GET/POST crear
│   ├── /<id>/editar         # GET/POST editar
│   └── /<id>/eliminar       # POST eliminar
│
├── /repuestos               # CRUD repuestos
│   ├── /nuevo               # GET/POST crear
│   ├── /<id>/editar        # GET/POST editar
│   ├── /<id>/ajustar_stock # POST ajustar stock
│   └── /<id>/eliminar      # POST eliminar
│
├── /reportes               # Reportes básicos
├── /reportes/avanzados     # Reportes con filtros
├── /informes/repuestos     # Análisis repuestos
├── /informes/mano_obra     # Análisis mano de obra
│
├── /importar_excel         # GET/POST importación
└── /reiniciar_app         # GET/POST reiniciar datos
```

### Response Patterns

#### Respuestas HTML (Templates)

```python
# GET routes - Mostrar páginas
@app.route('/entidad')
def listar_entidad():
    return render_template('entidad.html', 
                         data=data, 
                         filters=filters,
                         stats=stats)

# POST routes - Procesar formularios
@app.route('/entidad/nuevo', methods=['POST'])
def crear_entidad():
    # Procesar datos
    flash('Entidad creada exitosamente', 'success')
    return redirect(url_for('listar_entidad'))
```

#### Respuestas JSON (Futuras APIs)

```python
# Para futuras expansiones a API REST
@app.route('/api/entidad/<id>')
def api_get_entidad(id):
    try:
        entidad = get_entidad_by_id(id)
        return jsonify({
            'success': True,
            'data': dict(entidad)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### Request Handling

#### Validación de Datos

```python
def validar_cliente(data):
    """Valida datos de cliente"""
    errors = []
    
    if not data.get('nombre', '').strip():
        errors.append('Nombre es obligatorio')
    
    if data.get('email') and '@' not in data['email']:
        errors.append('Email inválido')
    
    return errors

@app.route('/clientes/nuevo', methods=['POST'])
def crear_cliente():
    data = request.form.to_dict()
    errors = validar_cliente(data)
    
    if errors:
        for error in errors:
            flash(error, 'error')
        return render_template('nuevo_cliente.html', data=data)
    
    # Procesar datos válidos...
```

#### File Upload Handling

```python
@app.route('/importar_excel', methods=['POST'])
def importar_excel():
    if 'archivo' not in request.files:
        flash('No se seleccionó archivo', 'error')
        return redirect(request.url)
    
    file = request.files['archivo']
    
    if file.filename == '':
        flash('No se seleccionó archivo', 'error')
        return redirect(request.url)
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        flash('Formato de archivo no válido', 'error')
        return redirect(request.url)
    
    # Procesar archivo...
```

## 🔒 Seguridad

### Input Validation

```python
# Sanitización de entradas
def sanitize_input(value):
    """Sanitiza entrada de usuario"""
    if isinstance(value, str):
        return value.strip()
    return value

# En cada route
data = {k: sanitize_input(v) for k, v in request.form.items()}
```

### SQL Injection Prevention

```python
# ✅ Correcto - Usar parámetros
conn.execute('''
    SELECT * FROM equipos 
    WHERE cliente_id = ? AND estado = ?
''', (cliente_id, estado))

# ❌ Incorrecto - Concatenación directa
query = f"SELECT * FROM equipos WHERE cliente_id = {cliente_id}"
```

### File Upload Security

```python
ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)

def validate_file_size(file):
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)     # Reset
    return size <= MAX_FILE_SIZE
```

### Environment Variables

```python
# Configuración sensible via environment
SECRET_KEY = os.environ.get('SECRET_KEY', 'desarrollo_default')
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'taller.db')
```

## 🛠️ Mantenimiento

### Logging Strategy

```python
# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('taller.log'),  # Archivo persistente
        logging.StreamHandler()             # Consola
    ]
)

# Uso en routes
@app.route('/entidad/nuevo', methods=['POST'])
def crear_entidad():
    try:
        # Lógica principal
        logging.info(f"Nueva entidad creada: {entidad_id}")
    except Exception as e:
        logging.error(f"Error creando entidad: {e}")
        # Manejo de error
```

### Database Maintenance

```python
# Backup automático
def backup_database():
    """Crear backup de la base de datos"""
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"backup_{timestamp}.db"
    shutil.copy2('taller.db', backup_name)
    logging.info(f"Backup creado: {backup_name}")

# Limpieza de logs antiguos
def cleanup_old_logs():
    """Limpiar logs antiguos"""
    import glob
    import os
    from datetime import datetime, timedelta
    
    cutoff = datetime.now() - timedelta(days=30)
    
    for log_file in glob.glob("*.log.*"):
        if os.path.getctime(log_file) < cutoff.timestamp():
            os.remove(log_file)
            logging.info(f"Log eliminado: {log_file}")
```

### Performance Monitoring

```python
import time
from functools import wraps

def monitor_performance(f):
    """Decorator para monitorear rendimiento"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        end_time = time.time()
        
        duration = end_time - start_time
        if duration > 1.0:  # Log si toma más de 1 segundo
            logging.warning(f"Slow request: {f.__name__} took {duration:.2f}s")
        
        return result
    return decorated_function

# Uso
@app.route('/reportes/avanzados')
@monitor_performance
def reportes_avanzados():
    # Lógica del reporte...
```

## 👨‍💻 Desarrollo

### Development Setup

```bash
# Entorno de desarrollo
export FLASK_DEBUG=True
export SECRET_KEY=dev_secret_key

# Base de datos de desarrollo
cp taller.db taller_dev.db
export DATABASE_PATH=taller_dev.db

# Ejecutar en modo desarrollo
python app.py
```

### Code Standards

#### Python (PEP 8)

```python
# ✅ Correcto
def procesar_datos_cliente(cliente_id, incluir_equipos=True):
    """
    Procesa datos de un cliente específico.
    
    Args:
        cliente_id (int): ID del cliente
        incluir_equipos (bool): Si incluir equipos asociados
        
    Returns:
        dict: Datos procesados del cliente
    """
    resultado = {}
    
    try:
        conn = get_db_connection()
        # Lógica de procesamiento
        return resultado
    except Exception as e:
        logging.error(f"Error procesando cliente {cliente_id}: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
```

#### JavaScript (ES6+)

```javascript
// ✅ Correcto
class TablaOrdenable {
    constructor(tabla) {
        this.tabla = tabla;
        this.direccion = {};
        this.inicializar();
    }
    
    inicializar() {
        const encabezados = this.tabla.querySelectorAll('th.sortable');
        encabezados.forEach(th => {
            th.addEventListener('click', (e) => this.ordenar(e.target));
        });
    }
    
    ordenar(columna) {
        const campo = columna.dataset.sort;
        const direccion = this.toggleDireccion(campo);
        
        // Lógica de ordenamiento
        this.actualizarIconos(columna, direccion);
    }
}
```

#### HTML (Semantic)

```html
<!-- ✅ Correcto -->
<article class="card">
    <header class="card-header">
        <h2 class="card-title">Información del Cliente</h2>
    </header>
    
    <section class="card-body">
        <dl class="row">
            <dt class="col-sm-3">Nombre:</dt>
            <dd class="col-sm-9">{{ cliente.nombre }}</dd>
        </dl>
    </section>
    
    <footer class="card-footer">
        <nav aria-label="Acciones del cliente">
            <a href="#" class="btn btn-primary" role="button">Editar</a>
        </nav>
    </footer>
</article>
```

### Testing Strategy

```python
# tests/test_database.py
import unittest
import sqlite3
from app import get_db_connection, init_db

class TestDatabase(unittest.TestCase):
    def setUp(self):
        """Configurar DB de prueba"""
        self.test_db = 'test_taller.db'
        # Crear DB de prueba
    
    def test_crear_cliente(self):
        """Test creación de cliente"""
        conn = get_db_connection()
        # Test logic
        
    def tearDown(self):
        """Limpiar después de tests"""
        # Eliminar DB de prueba

# tests/test_routes.py
import unittest
from app import app

class TestRoutes(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def test_dashboard_load(self):
        """Test carga del dashboard"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
```

### Git Workflow

```bash
# Flujo de desarrollo
git checkout -b feature/nueva-funcionalidad
git add .
git commit -m "feat: agregar nueva funcionalidad X"
git push origin feature/nueva-funcionalidad

# Merge a main
git checkout main
git merge feature/nueva-funcionalidad
git tag v2.1.0
git push origin main --tags
```

### Deployment

```bash
# Preparar para producción
pip freeze > requirements.txt

# Variables de entorno de producción
export FLASK_DEBUG=False
export SECRET_KEY=production_secret_key
export DATABASE_PATH=/var/app/taller.db

# Usar servidor WSGI
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 🧠 Motor de Reconocimiento Inteligente

### Arquitectura del Sistema IA

El Motor de Reconocimiento Inteligente es un sistema de procesamiento de lenguaje natural (NLP) desarrollado específicamente para talleres de mantenimiento.

```python
┌─────────────────────────────────────────────────────────┐
│                🧠 MOTOR DE RECONOCIMIENTO               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📝 INPUT                🔍 PROCESSING       📊 OUTPUT  │
│  ┌─────────────┐        ┌─────────────┐    ┌──────────┐ │
│  │ Descripción │   ─→   │ Análisis    │ ─→ │ Categoría│ │
│  │ Mantenimiento│        │ de Texto    │    │ + Confian│ │
│  └─────────────┘        └─────────────┘    └──────────┘ │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🔤 NORMALIZACIÓN     🎯 CLASIFICACIÓN    📊 CONFIANZA  │
│  ├─ Limpieza texto    ├─ Palabras clave  ├─ Peso total │
│  ├─ Minúsculas       ├─ Sinónimos       ├─ Normalizado │
│  ├─ Acentos          ├─ Fuzzy matching  └─ 0-100%      │
│  └─ Caracteres       └─ Context aware                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Componentes del Motor

#### 🔍 **Módulo de Normalización de Texto**

```python
def normalizar_texto(texto):
    """
    Normaliza texto para análisis consistente.
    
    Transformaciones aplicadas:
    - Conversión a minúsculas
    - Eliminación de acentos y caracteres especiales
    - Limpieza de espacios múltiples
    - Separación de palabras compuestas
    
    Args:
        texto (str): Texto original a normalizar
        
    Returns:
        str: Texto normalizado para análisis
        
    Example:
        Input:  "Cambió el filtro de aceite del motor"
        Output: "cambio filtro aceite motor"
    """
```

**Características**:
- **Limpieza robusta**: Maneja acentos, signos de puntuación, números
- **Consistencia**: Mismo texto siempre produce mismo resultado
- **Preservación semántica**: Mantiene significado esencial
- **Optimización**: Procesamiento rápido para grandes volúmenes

#### 🎯 **Motor de Clasificación**

```python
def clasificar_repuestos(texto_normalizado, palabras_clave_db):
    """
    Clasifica repuestos en texto usando IA.
    
    Algoritmo:
    1. Buscar coincidencias exactas de palabras clave
    2. Evaluar sinónimos y variaciones
    3. Aplicar fuzzy matching para similitud
    4. Calcular puntuación de confianza ponderada
    5. Filtrar resultados por umbral mínimo
    
    Args:
        texto_normalizado (str): Texto limpio para analizar
        palabras_clave_db (list): Palabras clave desde base datos
        
    Returns:
        list: Lista de detecciones con confianza y contexto
        
    Example:
        Input:  "cambio filtro aceite motor"
        Output: [
            {
                'categoria': 'Filtros',
                'texto_detectado': 'filtro aceite',
                'confianza': 95.5,
                'palabras_clave': ['filtro', 'aceite'],
                'color': '#007bff'
            }
        ]
    """
```

#### 📊 **Sistema de Confianza**

**Factores de Confianza**:

1. **Coincidencia Exacta** (100%):
   ```python
   if palabra_clave.lower() in texto_normalizado:
       confianza = 100.0 * peso_palabra
   ```

2. **Sinónimos** (90%):
   ```python
   for sinonimo in lista_sinonimos:
       if sinonimo in texto_normalizado:
           confianza = 90.0 * peso_palabra
   ```

3. **Fuzzy Matching** (70-89%):
   ```python
   from difflib import SequenceMatcher
   ratio = SequenceMatcher(None, palabra_clave, fragmento).ratio()
   if ratio > 0.8:
       confianza = ratio * 85.0 * peso_palabra
   ```

4. **Contexto Múltiple** (Bonus +10%):
   ```python
   if multiple_keywords_found:
       confianza += 10.0  # Bonus por contexto
   ```

**Clasificación de Confianza**:
- **🟢 Alta (80-100%)**: Clasificación muy confiable
- **🟡 Media (60-79%)**: Clasificación probable, revisar si es crítico
- **🔴 Baja (<60%)**: Requiere revisión manual

### API del Motor de Reconocimiento

#### Función Principal

```python
def crear_motor_reconocimiento():
    """
    Crea y configura el motor de reconocimiento inteligente.
    
    Returns:
        dict: Motor configurado con funciones de análisis
        
    Estructura del motor retornado:
    {
        'analizar_mantenimiento': function,
        'clasificar_repuestos': function,  
        'clasificar_trabajos': function,
        'estadisticas': function,
        'version': '1.0'
    }
    """
```

#### Función de Análisis Completo

```python
def analizar_mantenimiento(descripcion, mantenimiento_id=None):
    """
    Analiza una descripción completa de mantenimiento.
    
    Args:
        descripcion (str): Texto del mantenimiento
        mantenimiento_id (int, optional): ID para logging
        
    Returns:
        dict: Resultado completo del análisis
        
    Ejemplo de retorno:
    {
        'repuestos_detectados': [
            {
                'categoria': 'Filtros',
                'items': ['filtro aceite', 'filtro aire'],
                'confianza_promedio': 92.5,
                'color': '#007bff'
            }
        ],
        'trabajos_detectados': [
            {
                'categoria': 'Mantenimiento',
                'items': ['cambio filtros', 'service'],
                'confianza_promedio': 88.0,
                'color': '#28a745'
            }
        ],
        'estadisticas': {
            'total_detecciones': 4,
            'confianza_general': 90.25,
            'tiempo_procesamiento': 0.045
        }
    }
    """
```

### Optimizaciones de Rendimiento

#### 🚀 **Caching Inteligente**

```python
# Cache de palabras clave para evitar consultas DB repetidas
palabra_cache = {}
ultimo_refresh = None

def obtener_palabras_clave_cached():
    global palabra_cache, ultimo_refresh
    
    ahora = datetime.now()
    if not ultimo_refresh or (ahora - ultimo_refresh).minutes > 15:
        palabra_cache = cargar_palabras_clave_db()
        ultimo_refresh = ahora
    
    return palabra_cache
```

#### ⚡ **Procesamiento Batch**

```python
def analizar_multiples_mantenimientos(mantenimientos):
    """
    Procesa múltiples mantenimientos en lote para mejor rendimiento.
    
    Optimizaciones:
    - Una sola carga de palabras clave
    - Normalización vectorizada
    - Análisis paralelo por chunks
    - Resultados agregados eficientemente
    """
```

#### 🎯 **Índices de Base de Datos**

```sql
-- Índices optimizados para el motor IA
CREATE INDEX idx_palabras_clave_texto ON palabras_clave_repuestos(palabra_clave);
CREATE INDEX idx_palabras_clave_activa ON palabras_clave_repuestos(activa);
CREATE INDEX idx_categorias_activa ON categorias_repuestos(activa);

-- Índices compuestos para búsquedas frecuentes
CREATE INDEX idx_palabras_categoria_activa ON palabras_clave_repuestos(categoria_id, activa);
```

### Configuración y Personalización

#### 🎛️ **Parámetros Configurables**

```python
# motor_reconocimiento.py - Configuración
CONFIG_MOTOR = {
    'umbral_confianza_minimo': 50.0,    # Confianza mínima para incluir
    'peso_coincidencia_exacta': 1.0,    # Multiplicador exact match
    'peso_sinonimo': 0.9,              # Multiplicador sinónimos
    'peso_fuzzy_minimo': 0.8,          # Umbral fuzzy matching
    'bonus_contexto_multiple': 10.0,   # Bonus por múltiples palabras
    'max_resultados_categoria': 10,    # Máx resultados por categoría
    'cache_duracion_minutos': 15,      # Duración cache palabras clave
    'debug_mode': False                # Modo debug para desarrollo
}
```

#### 🔧 **Personalización por Industria**

```python
def personalizar_motor_taller(tipo_taller):
    """
    Personaliza el motor según tipo de taller.
    
    Args:
        tipo_taller (str): 'automotriz', 'industrial', 'construccion'
        
    Returns:
        dict: Configuración personalizada
    """
    
    configuraciones = {
        'automotriz': {
            'categorias_prioritarias': ['Filtros', 'Lubricantes', 'Frenos'],
            'palabras_comunes': ['motor', 'transmision', 'frenos'],
            'umbral_confianza': 70.0
        },
        'industrial': {
            'categorias_prioritarias': ['Hidraulicos', 'Neumaticos', 'Eléctricos'],
            'palabras_comunes': ['bomba', 'cilindro', 'valvula'],
            'umbral_confianza': 65.0
        }
    }
    
    return configuraciones.get(tipo_taller, configuraciones['automotriz'])
```

### Métricas y Monitoreo

#### 📊 **Estadísticas de Uso**

```python
def obtener_estadisticas_motor():
    """
    Recopila estadísticas del motor de reconocimiento.
    
    Returns:
        dict: Métricas completas del sistema
    """
    
    return {
        'rendimiento': {
            'total_analisis': 1254,
            'tiempo_promedio_ms': 45.2,
            'analisis_por_hora': 156,
            'cache_hit_rate': 0.87
        },
        'precision': {
            'confianza_promedio': 87.3,
            'detecciones_alta_confianza': 0.73,
            'detecciones_baja_confianza': 0.08
        },
        'categorias_mas_usadas': [
            {'nombre': 'Filtros', 'detecciones': 342, 'confianza_prom': 91.2},
            {'nombre': 'Lubricantes', 'detecciones': 298, 'confianza_prom': 89.5},
            {'nombre': 'Hidraulicos', 'detecciones': 201, 'confianza_prom': 85.1}
        ]
    }
```

#### 🔍 **Debugging y Diagnóstico**

```python
def debug_analisis(descripcion, verbose=True):
    """
    Función de debug para analizar paso a paso.
    
    Args:
        descripcion (str): Texto a analizar
        verbose (bool): Mostrar detalles paso a paso
        
    Returns:
        dict: Análisis detallado con pasos intermedios
    """
    
    resultado = {
        'texto_original': descripcion,
        'texto_normalizado': normalizar_texto(descripcion),
        'palabras_clave_evaluadas': [],
        'coincidencias_encontradas': [],
        'calculos_confianza': [],
        'resultado_final': None
    }
    
    # ... lógica de debug paso a paso
    
    return resultado
```

### Integración con Flask

#### 🔌 **Endpoints API**

```python
@app.route('/api/analizar_mantenimiento/<int:mantenimiento_id>')
def api_analizar_mantenimiento(mantenimiento_id):
    """
    API endpoint para análisis individual.
    
    Returns:
        JSON: Resultado del análisis IA
    """
    try:
        motor = crear_motor_reconocimiento()
        
        # Obtener descripción desde DB
        conn = get_db_connection()
        mantenimiento = conn.execute(
            'SELECT descripcion FROM mantenimientos WHERE id = ?',
            (mantenimiento_id,)
        ).fetchone()
        
        if not mantenimiento:
            return jsonify({'error': 'Mantenimiento no encontrado'}), 404
        
        # Ejecutar análisis
        resultado = motor['analizar_mantenimiento'](
            mantenimiento['descripcion'], 
            mantenimiento_id
        )
        
        return jsonify({
            'success': True,
            'mantenimiento_id': mantenimiento_id,
            'analisis': resultado
        })
        
    except Exception as e:
        logging.error(f"Error en análisis IA: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500
```

#### 🎯 **Integración con Templates**

```python
@app.route('/informes/repuestos_inteligente')
def informe_repuestos_inteligente():
    """
    Página principal del sistema inteligente.
    """
    try:
        motor = crear_motor_reconocimiento()
        
        # Obtener todos los mantenimientos
        conn = get_db_connection()
        mantenimientos = conn.execute('''
            SELECT id, descripcion, fecha_mantenimiento,
                   cliente_nombre, equipo_nombre
            FROM mantenimientos_view
            ORDER BY fecha_mantenimiento DESC
        ''').fetchall()
        
        # Análisis masivo
        resultados_completos = []
        for mant in mantenimientos:
            resultado = motor['analizar_mantenimiento'](mant['descripcion'])
            resultado['mantenimiento'] = dict(mant)
            resultados_completos.append(resultado)
        
        # Preparar datos para template
        datos_template = procesar_resultados_template(resultados_completos)
        
        return render_template(
            'informe_repuestos_inteligente.html',
            **datos_template
        )
        
    except Exception as e:
        logging.error(f"Error en informe inteligente: {e}")
        flash('Error al generar análisis inteligente', 'error')
        return redirect(url_for('reportes'))
```

---

Esta documentación técnica proporciona una visión completa del sistema para desarrolladores y administradores técnicos. Para información de usuario final, consultar `MANUAL_USUARIO.md`.
