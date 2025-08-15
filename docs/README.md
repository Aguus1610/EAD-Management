# 🔧 Sistema de Gestión de Taller

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-v2.0+-green.svg)
![Bootstrap](https://img.shields.io/badge/Bootstrap-v5.3-purple.svg)
![SQLite](https://img.shields.io/badge/SQLite-v3.0+-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

Sistema completo para la gestión de talleres de mantenimiento de equipos. Incluye gestión de clientes, equipos, mantenimientos, repuestos y reportes avanzados con análisis de datos.

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Tecnologías](#-tecnologías)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [API](#-api)
- [Contribución](#-contribución)
- [Licencia](#-licencia)

## ✨ Características

### 🏢 Gestión de Clientes
- ✅ **Registro completo**: Nombre, teléfono, email, dirección, observaciones
- ✅ **Vista detallada**: Información del cliente con equipos y mantenimientos asociados
- ✅ **Edición y eliminación**: Control completo con validaciones de integridad
- ✅ **Creación con equipos**: Posibilidad de agregar equipos al crear el cliente

### 🛠️ Gestión de Equipos
- ✅ **Registro detallado**: Nombre, marca, modelo, número de serie, estado, ubicación
- ✅ **Asignación de clientes**: Cada equipo pertenece a un cliente específico
- ✅ **Estados múltiples**: Activo, Inactivo, En Mantenimiento, Fuera de Servicio
- ✅ **Filtros avanzados**: Por cliente, estado, búsqueda de texto
- ✅ **Historial completo**: Todos los mantenimientos realizados

### 🔧 Gestión de Mantenimientos
- ✅ **Tipos múltiples**: Preventivo, Correctivo, Emergencia, Inspección, Reparación
- ✅ **Estados de workflow**: Pendiente, En Progreso, Completado, Cancelado
- ✅ **Campos completos**: Fecha, descripción, costo, técnico responsable
- ✅ **Edición completa**: Modificar todos los campos después de crear
- ✅ **Validaciones**: Integridad referencial con equipos

### 📦 Gestión de Repuestos
- ✅ **Inventario completo**: Stock actual, stock mínimo, precio unitario
- ✅ **Control de stock**: Ajustes rápidos (+/-) y personalizados
- ✅ **Alertas automáticas**: Stock bajo y productos agotados
- ✅ **Historial de movimientos**: Trazabilidad completa
- ✅ **Proveedores**: Gestión de información de proveedores

### 📊 Reportes y Análisis
- ✅ **Reportes básicos**: Estadísticas generales y gráficos
- ✅ **Reportes avanzados**: Filtros por fecha, cliente, período
- ✅ **Análisis de repuestos**: Detección inteligente de repuestos utilizados
- ✅ **Análisis de mano de obra**: Clasificación por complejidad y tipo
- ✅ **🧠 SISTEMA INTELIGENTE**: Motor de reconocimiento avanzado con IA
- ✅ **🎯 Categorización automática**: Clasificación inteligente de texto
- ✅ **📊 Puntuación de confianza**: Medición de precisión del análisis
- ✅ **🔗 Sinónimos automáticos**: Reconocimiento de variaciones de términos
- ✅ **⚙️ Gestión de categorías**: Interfaz para administrar clasificaciones
- ✅ **Gráficos interactivos**: Chart.js con múltiples tipos de visualización
- ✅ **Exportación**: Capacidad de exportar reportes

### 📤 Importación de Datos
- ✅ **Excel automático**: Importa desde archivos Excel estructurados
- ✅ **Multi-hoja**: Cada hoja Excel representa un cliente
- ✅ **Detección inteligente**: Reconoce columnas por nombre o posición
- ✅ **Validación de fechas**: Procesamiento correcto de fechas históricas
- ✅ **Reinicio de datos**: Limpieza completa para nuevas importaciones

## 🚀 Tecnologías

### Backend
- **Python 3.8+**: Lenguaje principal
- **Flask 2.0+**: Framework web ligero y flexible
- **SQLite 3**: Base de datos embebida
- **Pandas**: Procesamiento de datos Excel
- **OpenPyXL**: Lectura de archivos Excel
- **🧠 Motor de Reconocimiento IA**: Sistema inteligente de categorización
- **🔍 Análisis de texto NLP**: Procesamiento de lenguaje natural
- **📊 Análisis de confianza**: Sistema de puntuación de precisión

### Frontend
- **HTML5**: Estructura semántica
- **CSS3**: Estilos personalizados
- **Bootstrap 5.3**: Framework CSS responsivo
- **JavaScript ES6+**: Interactividad del cliente
- **Chart.js**: Gráficos interactivos
- **Font Awesome**: Iconografía

### Herramientas
- **Git**: Control de versiones
- **Logging**: Sistema de logs integrado
- **Environment Variables**: Configuración segura

## 📦 Instalación

### Prerrequisitos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Git (opcional, para clonar el repositorio)

### Pasos de Instalación

1. **Clonar el repositorio** (o descargar el código)
   ```bash
   git clone <url-del-repositorio>
   cd sistema-gestion-taller
   ```

2. **Crear un entorno virtual** (recomendado)
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicializar la base de datos**
   ```bash
   python -c "from app import init_db; init_db()"
   ```

5. **Ejecutar la aplicación**
   ```bash
   python app.py
   ```

6. **Acceder a la aplicación**
   - Abrir navegador en: `http://localhost:5000`
   - O en la red local: `http://192.168.x.x:5000`

## ⚙️ Configuración

### Variables de Entorno

Crear un archivo `.env` en el directorio raíz:

```env
# Configuración de Flask
SECRET_KEY=tu_clave_secreta_muy_segura
FLASK_DEBUG=False

# Configuración de Base de Datos
DATABASE_PATH=taller.db

# Configuración de Archivos
MAX_CONTENT_LENGTH=16777216  # 16MB
UPLOAD_FOLDER=uploads
```

### Configuración de Producción

Para entornos de producción, considera:

1. **Usar un servidor WSGI** como Gunicorn:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Configurar HTTPS** con nginx o Apache

3. **Backup automático** de la base de datos

4. **Monitoreo** con herramientas como Supervisor

## 📖 Uso

### Primera Configuración

1. **Crear el primer cliente**
   - Ir a "Clientes" → "Nuevo Cliente"
   - Llenar información básica
   - Opcionalmente agregar equipos

2. **Importar datos desde Excel** (opcional)
   - Ir a "Importar Excel"
   - Subir archivo con estructura correcta
   - Cada hoja = un cliente

3. **Agregar equipos manualmente**
   - Ir a "Equipos" → "Nuevo Equipo"
   - Asignar cliente obligatoriamente
   - Completar información técnica

### Flujo de Trabajo Típico

1. **📝 Registrar mantenimiento**
   - "Mantenimientos" → "Nuevo Mantenimiento"
   - Seleccionar equipo y tipo
   - Completar descripción detallada

2. **📦 Gestionar repuestos**
   - "Repuestos" → Ver inventario
   - Ajustar stock según uso
   - Agregar nuevos repuestos

3. **📊 Generar reportes**
   - "Reportes" → Seleccionar tipo
   - Aplicar filtros necesarios
   - Analizar datos y gráficos

### Estructura de Excel para Importación

El archivo Excel debe tener:

```
Hoja1: CLIENTE_A
│
├── Columna A: EQUIPOS (nombres de equipos)
├── Columna B: FECHA (fechas de mantenimiento)
├── Columna C: REPUESTOS (repuestos utilizados)
└── Columna D: MANO DE OBRA (descripción del trabajo)

Hoja2: CLIENTE_B
│
├── ... (misma estructura)
```

## 📁 Estructura del Proyecto

```
sistema-gestion-taller/
│
├── 📄 app.py                    # Aplicación principal Flask
├── 📄 motor_reconocimiento.py   # 🧠 Motor de IA para categorización
├── 📄 requirements.txt         # Dependencias Python
├── 📄 README.md                # Documentación principal
├── 📄 MANUAL_USUARIO.md        # Manual del usuario
├── 📄 DOCUMENTACION_TECNICA.md # Documentación técnica
├── 📄 RESUMEN_MEJORAS.md       # Historial de mejoras
├── 📄 taller.db                # Base de datos SQLite
├── 📄 taller.log               # Archivo de logs
│
├── 📁 static/                  # Archivos estáticos
│   └── 📁 js/
│       └── 📄 table-sort.js    # Ordenamiento de tablas
│
├── 📁 templates/               # Templates HTML
│   ├── 📄 base.html            # Template base
│   ├── 📄 index.html           # Página principal
│   ├── 📄 clientes.html        # Lista de clientes
│   ├── 📄 equipos.html         # Lista de equipos
│   ├── 📄 mantenimientos.html  # Lista de mantenimientos
│   ├── 📄 repuestos.html       # Gestión de repuestos
│   ├── 📄 reportes.html        # Reportes básicos
│   ├── 📄 reportes_avanzados.html # Reportes avanzados
│   ├── 📄 informe_repuestos_inteligente.html # 🧠 Análisis IA
│   ├── 📄 gestion_categorias.html # ⚙️ Gestión de categorías
│   └── 📄 ...                  # Otros templates
│
└── 📁 scripts/                 # Scripts auxiliares
    ├── 📄 examinar_datos.py    # Análisis de datos
    ├── 📄 verificar_fechas.py  # Verificación de fechas
    └── 📄 analizar_excel_completo.py # Análisis Excel
```

## 🔌 API

### Endpoints Principales

#### Clientes
- `GET /clientes` - Lista todos los clientes
- `POST /clientes/nuevo` - Crear nuevo cliente
- `GET /clientes/<id>` - Ver detalles del cliente
- `POST /clientes/<id>/editar` - Editar cliente
- `POST /clientes/<id>/eliminar` - Eliminar cliente

#### Equipos
- `GET /equipos` - Lista todos los equipos (con filtros)
- `POST /equipos/nuevo` - Crear nuevo equipo
- `POST /equipos/<id>/editar` - Editar equipo
- `POST /equipos/<id>/eliminar` - Eliminar equipo

#### Mantenimientos
- `GET /mantenimientos` - Lista todos los mantenimientos
- `POST /mantenimientos/nuevo` - Crear nuevo mantenimiento
- `POST /mantenimientos/<id>/editar` - Editar mantenimiento
- `POST /mantenimientos/<id>/eliminar` - Eliminar mantenimiento

#### Repuestos
- `GET /repuestos` - Lista todos los repuestos
- `POST /repuestos/nuevo` - Crear nuevo repuesto
- `POST /repuestos/<id>/editar` - Editar repuesto
- `POST /repuestos/<id>/ajustar_stock` - Ajustar stock
- `POST /repuestos/<id>/eliminar` - Eliminar repuesto

#### Reportes
- `GET /reportes` - Reportes básicos
- `GET /reportes/avanzados` - Reportes avanzados con filtros
- `GET /informes/repuestos` - Análisis de repuestos (sistema básico)
- `GET /informes/mano_obra` - Análisis de mano de obra (sistema básico)
- `GET /informes/repuestos_inteligente` - 🧠 Análisis inteligente con IA
- `GET /gestion_categorias` - ⚙️ Gestión de categorías inteligentes

#### APIs del Sistema Inteligente
- `GET /api/analizar_mantenimiento/<id>` - Análisis individual con IA
- `GET /api/categorias` - Listar categorías de repuestos/trabajos
- `POST /api/categorias` - Crear nueva categoría
- `PUT /api/categorias/<id>` - Actualizar categoría
- `DELETE /api/categorias/<id>` - Desactivar categoría
- `GET /api/estadisticas_categorias` - Estadísticas de uso de categorías

#### Utilidades
- `POST /importar_excel` - Importar datos desde Excel
- `POST /reiniciar_app` - Reiniciar aplicación (limpiar datos)
- `GET /api/stats` - Estadísticas en tiempo real

## 🛡️ Seguridad

### Validaciones Implementadas

1. **Integridad Referencial**
   - No se pueden eliminar clientes con equipos
   - No se pueden eliminar equipos con mantenimientos
   - Los repuestos con historial no se eliminan

2. **Validación de Datos**
   - Campos obligatorios verificados
   - Tipos de datos correctos
   - Rangos de valores válidos

3. **Sanitización**
   - Escape de caracteres especiales
   - Validación de archivos subidos
   - Límites de tamaño de archivo

## 🔧 Mantenimiento

### Backup de Base de Datos

```bash
# Crear backup
cp taller.db backup_$(date +%Y%m%d_%H%M%S).db

# Restaurar backup
cp backup_YYYYMMDD_HHMMSS.db taller.db
```

### Logs

Los logs se almacenan en `taller.log` con información de:
- Acceso a rutas
- Errores de aplicación
- Importaciones de datos
- Operaciones de base de datos

### Actualizaciones

1. Hacer backup de la base de datos
2. Actualizar código fuente
3. Instalar nuevas dependencias: `pip install -r requirements.txt`
4. Ejecutar migraciones si las hay
5. Reiniciar aplicación

## 🤝 Contribución

### Cómo Contribuir

1. Fork del repositorio
2. Crear branch para nueva funcionalidad: `git checkout -b nueva-funcionalidad`
3. Hacer commit de cambios: `git commit -m 'Agregar nueva funcionalidad'`
4. Push al branch: `git push origin nueva-funcionalidad`
5. Crear Pull Request

### Estándares de Código

- **Python**: Seguir PEP 8
- **JavaScript**: Usar ES6+
- **HTML**: HTML5 semántico
- **CSS**: BEM methodology
- **Documentación**: Docstrings en todas las funciones

### Reportar Bugs

Usar el sistema de Issues con:
- Descripción clara del problema
- Pasos para reproducir
- Comportamiento esperado vs actual
- Screenshots si aplica
- Información del entorno

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 📞 Soporte

Para soporte técnico o consultas:
- 📧 Email: soporte@sistema-taller.com
- 📱 WhatsApp: +54 9 11 xxxx-xxxx
- 🌐 Web: https://sistema-taller.com

## 🙏 Agradecimientos

- **Bootstrap Team** - Framework CSS
- **Flask Team** - Framework web Python
- **Chart.js Team** - Librería de gráficos
- **Font Awesome** - Iconografía
- **SQLite Team** - Base de datos

---

**⭐ Si este proyecto te ha sido útil, considera darle una estrella en GitHub!**

## 🧠 Sistema Inteligente de Reconocimiento

### ¿Qué es el Sistema Inteligente?

El **Motor de Reconocimiento Inteligente** es una funcionalidad avanzada que utiliza técnicas de procesamiento de lenguaje natural (NLP) para analizar automáticamente las descripciones de mantenimientos y categorizar:

- **📦 Repuestos utilizados**: Identifica automáticamente qué repuestos fueron usados
- **🔧 Tipos de trabajo**: Clasifica los trabajos realizados por categoría
- **📊 Puntuación de confianza**: Mide qué tan seguro está el sistema de cada clasificación
- **🎯 Categorías estructuradas**: Organiza la información de manera coherente

### Características Avanzadas

#### 🎯 **Categorización Automática**
```
Sistema tradicional: "cambio filtro aceite"
Sistema inteligente: 
┌─ Repuesto: "Filtro de Aceite" (95% confianza)
├─ Categoría: "Filtros"
├─ Trabajo: "Mantenimiento Preventivo" (90% confianza)
└─ Tipo: "Lubricación"
```

#### 🔗 **Reconocimiento de Sinónimos**
El sistema entiende variaciones y sinónimos:
- "aceite motor" = "aceite de motor" = "lubricante motor"
- "soldadura" = "soldado" = "reparar soldando"
- "kit reparacion" = "juego reparación" = "set de reparación"

#### 📊 **Análisis de Confianza**
- **🟢 Alta (80-100%)**: Clasificación muy segura
- **🟡 Media (60-79%)**: Clasificación probable
- **🔴 Baja (<60%)**: Requiere revisión manual

#### ⚙️ **Gestión de Categorías**
Interface completa para administradores:
- Crear nuevas categorías de repuestos/trabajos
- Gestionar palabras clave y sinónimos
- Ver estadísticas de uso y efectividad
- Desactivar categorías obsoletas

### Beneficios del Sistema

1. **⏱️ Ahorro de tiempo**: Categorización automática vs manual
2. **📈 Consistencia**: Clasificaciones uniformes en todos los registros
3. **🔍 Mejores reportes**: Análisis más precisos y detallados
4. **📊 Inteligencia empresarial**: Patrones de uso y tendencias claras
5. **🎯 Precisión creciente**: El sistema mejora con más datos

### Acceso al Sistema Inteligente

**Desde el menú Reportes**:
- **🧠 Análisis Inteligente**: Análisis completo con IA
- **⚙️ Gestionar Categorías**: Administración del sistema

**APIs disponibles**:
- Análisis individual de mantenimientos
- Gestión programática de categorías
- Estadísticas de uso del sistema

---

Desarrollado con ❤️ para talleres de mantenimiento