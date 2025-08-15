# 📖 Manual del Usuario - Sistema de Gestión de Taller

## 🎯 Introducción

Bienvenido al Sistema de Gestión de Taller, una herramienta completa diseñada para administrar eficientemente talleres de mantenimiento de equipos. Este manual te guiará paso a paso para aprovechar al máximo todas las funcionalidades del sistema.

## 📋 Tabla de Contenidos

1. [Primeros Pasos](#-primeros-pasos)
2. [Navegación Principal](#-navegación-principal)
3. [Gestión de Clientes](#-gestión-de-clientes)
4. [Gestión de Equipos](#-gestión-de-equipos)
5. [Gestión de Mantenimientos](#-gestión-de-mantenimientos)
6. [Gestión de Repuestos](#-gestión-de-repuestos)
7. [Reportes y Análisis](#-reportes-y-análisis)
8. [Importación de Datos](#-importación-de-datos)
9. [Consejos y Mejores Prácticas](#-consejos-y-mejores-prácticas)
10. [Solución de Problemas](#-solución-de-problemas)

## 🚀 Primeros Pasos

### Acceso al Sistema

1. **Abrir navegador web** (Chrome, Firefox, Safari, Edge)
2. **Navegar a la dirección** proporcionada por tu administrador:
   - Local: `http://localhost:5000`
   - Red: `http://192.168.x.x:5000`
3. **Página de inicio**: Verás el dashboard principal con estadísticas generales

### Dashboard Principal

El dashboard muestra:
- 📊 **Resumen de estadísticas**: Total de equipos, clientes, mantenimientos
- 📈 **Equipos recientes**: Últimos equipos agregados al sistema
- 🎯 **Accesos rápidos**: Botones para las acciones más comunes

## 🧭 Navegación Principal

### Menú Principal

La barra de navegación superior contiene:

- **🏠 Dashboard**: Página principal con resumen
- **👥 Clientes**: Gestión completa de clientes
- **🛠️ Equipos**: Administración de equipos
- **🔧 Mantenimientos**: Registro y seguimiento de mantenimientos
- **📦 Repuestos**: Control de inventario de repuestos
- **📊 Reportes**: *(Menú desplegable)*
  - Reportes Básicos
  - Reportes Avanzados
  - Análisis Repuestos (sistema básico)
  - Análisis Mano de Obra (sistema básico)
  - **🧠 Análisis Inteligente** (NUEVO - sistema IA)
  - **⚙️ Gestionar Categorías** (NUEVO - administración)
- **📤 Importar Excel**: Carga masiva de datos
- **🔄 Reiniciar App**: Limpieza completa de datos

### Elementos de Interfaz

- **🔍 Buscadores**: Filtros de texto en tiempo real
- **📊 Ordenamiento**: Click en encabezados de columnas para ordenar
- **🏷️ Badges**: Indicadores de estado con colores
- **⚡ Botones de acción**: Iconos claros para cada operación
- **📱 Responsive**: Funciona en móviles y tablets

## 👥 Gestión de Clientes

### Listar Clientes

**Acceso**: Menú → Clientes

**Información mostrada**:
- 📝 Nombre y dirección
- 📞 Teléfono y email (enlaces directos)
- 📊 Cantidad de equipos y mantenimientos
- 📅 Fecha de creación
- ⚡ Acciones disponibles

**Funciones disponibles**:
- 👁️ **Ver detalles**: Información completa del cliente
- ✏️ **Editar**: Modificar datos del cliente
- 🗑️ **Eliminar**: Borrar cliente (solo si no tiene equipos)

### Crear Nuevo Cliente

**Acceso**: Clientes → "Nuevo Cliente"

**Proceso paso a paso**:

1. **Información básica** *(obligatorio)*:
   ```
   📝 Nombre: Nombre único del cliente
   📞 Teléfono: Número de contacto
   📧 Email: Correo electrónico
   🏠 Dirección: Ubicación física
   📄 Observaciones: Notas adicionales
   ```

2. **Agregar equipos** *(opcional)*:
   - Click en "➕ Agregar Equipo"
   - Completar información por cada equipo:
     - ⚙️ Nombre del equipo
     - 🏭 Marca y modelo
     - 🔢 Número de serie
     - 📍 Ubicación
     - 📝 Observaciones

3. **Guardar**: Click en "💾 Guardar Cliente y Equipos"

**✅ Resultado**: Cliente creado con todos sus equipos asociados

### Editar Cliente

**Acceso**: Clientes → Botón "✏️" en la fila del cliente

**Modificaciones permitidas**:
- Todos los datos de contacto
- Información adicional
- ⚠️ **No se pueden agregar/eliminar equipos desde aquí**

### Eliminar Cliente

**Acceso**: Clientes → Botón "🗑️" en la fila del cliente

**⚠️ Restricciones**:
- Solo se pueden eliminar clientes sin equipos
- Si tiene equipos, eliminar primero los equipos
- **Confirmación requerida** con información detallada

### Ver Detalles del Cliente

**Acceso**: Clientes → Botón "👁️" en la fila del cliente

**Información completa**:
- 📋 Datos del cliente
- 🛠️ Lista de equipos asociados
- 🔧 Mantenimientos recientes
- 📊 Estadísticas del cliente

## 🛠️ Gestión de Equipos

### Listar Equipos

**Acceso**: Menú → Equipos

**Filtros disponibles**:
- 🔍 **Búsqueda de texto**: Nombre, marca, modelo, serie, cliente
- 👥 **Por cliente**: Dropdown con todos los clientes
- 📊 **Por estado**: Activo, Inactivo, Mantenimiento, Fuera de Servicio
- 🧹 **Limpiar filtros**: Botón para reset

**Información mostrada**:
- ⚙️ Nombre del equipo
- 👥 Cliente propietario (badge azul)
- 🏭 Marca y modelo
- 📊 Estado actual (badge colorizado)
- ⚡ Acciones (editar/eliminar)

### Crear Nuevo Equipo

**Acceso**: Equipos → "Nuevo Equipo"

**Proceso detallado**:

1. **Asignación de cliente** *(obligatorio)*:
   ```
   👥 Cliente Propietario: [Dropdown con todos los clientes]
   💡 Tip: Si no está el cliente, usar el enlace para crear uno nuevo
   ```

2. **Información del equipo**:
   ```
   ⚙️ Nombre: Identificación única del equipo
   🏭 Marca: Fabricante del equipo
   🔧 Modelo: Modelo específico
   🔢 Serie: Número de serie único
   📅 Fecha Compra: Cuándo se adquirió
   📊 Estado: Activo (por defecto)
   📍 Ubicación: Dónde está ubicado
   📝 Observaciones: Notas adicionales
   ```

3. **Funciones inteligentes**:
   - 🤖 **Auto-completado**: Marca + Modelo = Nombre sugerido
   - ✅ **Validación visual**: Borde verde al seleccionar cliente
   - ⚠️ **Validaciones**: Campos obligatorios verificados

### Estados de Equipos

| Estado | Color | Significado |
|--------|-------|-------------|
| 🟢 Activo | Verde | Equipo operativo |
| ⚫ Inactivo | Gris | Equipo parado temporalmente |
| 🟡 Mantenimiento | Amarillo | En proceso de mantenimiento |
| 🔴 Fuera de Servicio | Rojo | Equipo no operativo |

### Editar Equipo

**Acceso**: Equipos → Botón "✏️"

**Modificaciones permitidas**:
- Cambiar cliente propietario
- Actualizar todos los datos técnicos
- Modificar estado operativo
- Actualizar ubicación y observaciones

### Eliminar Equipo

**Acceso**: Equipos → Botón "🗑️"

**⚠️ Restricciones**:
- Solo se pueden eliminar equipos sin mantenimientos
- **Confirmación requerida** con información del equipo y cliente
- Se muestran las condiciones de eliminación

## 🔧 Gestión de Mantenimientos

### Listar Mantenimientos

**Acceso**: Menú → Mantenimientos

**Información mostrada**:
- ⚙️ **Equipo**: Nombre del equipo intervenido
- 🏷️ **Tipo**: Badge colorizado por tipo de mantenimiento
- 📅 **Fecha**: Cuándo se realizó
- 👨‍🔧 **Técnico**: Quién lo realizó
- 💰 **Costo**: Valor del mantenimiento
- 📝 **Descripción**: Resumen del trabajo (truncado)
- ⚡ **Acciones**: Editar y eliminar

### Tipos de Mantenimiento

| Tipo | Color | Descripción |
|------|-------|-------------|
| 🟢 Preventivo | Verde | Mantenimiento programado |
| 🔴 Correctivo | Rojo | Reparación de falla |
| 🟠 Emergencia | Naranja | Atención urgente |
| 🔵 Inspección | Azul | Revisión y diagnóstico |
| 🟣 Reparación | Morado | Reparación específica |

### Estados de Mantenimiento

| Estado | Significado |
|--------|-------------|
| ⏳ Pendiente | Por realizar |
| 🔄 En Progreso | En ejecución |
| ✅ Completado | Finalizado |
| ❌ Cancelado | No realizado |

### Crear Nuevo Mantenimiento

**Acceso**: Mantenimientos → "Nuevo Mantenimiento"

**Información requerida**:

1. **Identificación**:
   ```
   ⚙️ Equipo: [Dropdown con Cliente - Equipo]
   📅 Fecha: Cuándo se realizó/realizará
   🏷️ Tipo: Preventivo, Correctivo, etc.
   📊 Estado: Pendiente, En Progreso, etc.
   ```

2. **Detalles del trabajo**:
   ```
   📝 Descripción: Trabajo realizado detalladamente
   👨‍🔧 Técnico: Quién realizó el trabajo
   💰 Costo: Valor del mantenimiento
   ```

3. **📝 Consejos para la descripción**:
   - Incluir repuestos utilizados
   - Detallar procedimientos realizados
   - Mencionar observaciones importantes
   - Indicar recomendaciones futuras

### Editar Mantenimiento

**Acceso**: Mantenimientos → Botón "✏️"

**✨ Funcionalidades avanzadas**:
- 🎨 **Cambio visual**: Color del borde según estado seleccionado
- 📋 **Panel informativo**: Muestra datos originales para referencia
- ✅ **Validación en tiempo real**: Campos obligatorios verificados
- 🔄 **Estado workflow**: Cambiar de Pendiente → En Progreso → Completado

**Modificaciones permitidas**:
- Cambiar equipo asignado
- Actualizar fecha y tipo
- Modificar estado del trabajo
- Editar descripción completa
- Cambiar técnico y costo

## 📦 Gestión de Repuestos

### Vista Principal de Repuestos

**Acceso**: Menú → Repuestos

**Panel de estadísticas**:
- 📊 Total de repuestos registrados
- ⚠️ Repuestos con stock bajo
- 🔴 Repuestos agotados
- 💰 Valor total del inventario

### Información por Repuesto

**Datos mostrados**:
- 📝 **Nombre y código**: Identificación única
- 📦 **Stock actual**: Cantidad disponible
- ⚡ **Control rápido**: Botones +/- para ajustar
- 📊 **Stock mínimo**: Nivel de reorden
- 💰 **Precio unitario**: Valor por unidad
- 🏢 **Proveedor**: Suministrador
- 🚨 **Estado**: Disponible, Stock Bajo, Agotado
- ⚡ **Acciones**: Editar y eliminar

### Estados de Stock

| Estado | Color | Condición |
|--------|-------|-----------|
| 🟢 Disponible | Verde | Stock > Mínimo |
| 🟡 Stock Bajo | Amarillo | Stock ≤ Mínimo |
| 🔴 Agotado | Rojo | Stock = 0 |

### Control de Stock

#### Ajustes Rápidos

**Botones de control inmediato**:
- **➖ Menos**: Reduce stock en 1 unidad
- **➕ Más**: Aumenta stock en 1 unidad
- **✏️ Personalizado**: Abre modal para ajuste específico

#### Ajuste Personalizado

**Acceso**: Botón "✏️" en el control de stock

**Proceso**:
1. **Nuevo stock**: Ingresar cantidad exacta
2. **Motivo**: Explicar el ajuste
   - "Compra de mercadería"
   - "Uso en mantenimiento"
   - "Ajuste por inventario"
   - "Devolución"
3. **Confirmar**: Se registra en el historial

### Crear Nuevo Repuesto

**Acceso**: Repuestos → "Nuevo Repuesto"

**Información completa**:

1. **Identificación**:
   ```
   📝 Nombre: Descripción clara del repuesto
   🔢 Código: Identificador único (opcional)
   📄 Descripción: Detalles técnicos
   ```

2. **Stock y precios**:
   ```
   📦 Stock inicial: Cantidad actual
   📊 Stock mínimo: Nivel de reorden
   💰 Precio unitario: Costo por unidad
   ```

3. **Proveedor y ubicación**:
   ```
   🏢 Proveedor: Suministrador principal
   📍 Ubicación: Dónde está almacenado
   ```

### Editar Repuesto

**Modificaciones permitidas**:
- Actualizar información descriptiva
- Cambiar precios y stock mínimo
- Modificar proveedor y ubicación
- ⚠️ **El stock actual se maneja por separado**

### Eliminar Repuesto

**⚠️ Restricciones estrictas**:
- Stock actual debe ser 0
- No debe tener movimientos de stock registrados
- Confirmación requerida con condiciones

**🔒 Protección de trazabilidad**:
Los repuestos con historial no se eliminan para mantener la auditoría completa.

## 📊 Reportes y Análisis

### Reportes Básicos

**Acceso**: Menú → Reportes → Reportes Básicos

**Contenido**:
- 📈 **Gráfico por mes**: Mantenimientos realizados
- 📋 **Top clientes**: Por cantidad de equipos
- 🔧 **Mantenimientos recientes**: Últimos trabajos
- 👥 **Clientes activos**: Con mantenimientos recientes

### Reportes Avanzados

**Acceso**: Menú → Reportes → Reportes Avanzados

**🎛️ Panel de filtros**:
- 📅 **Rango de fechas**: Desde/hasta específico
- 🕐 **Período**: Día, semana, mes, año
- 👥 **Cliente específico**: Filtrar por cliente
- ⚡ **Filtros rápidos**: Última semana, mes, año

**📊 Visualizaciones**:
- 📈 **Tendencias por período**: Evolución temporal
- 📅 **Actividad por día**: Distribución semanal
- 🎯 **Filtros dinámicos**: Resultados en tiempo real

### Análisis de Repuestos

**Acceso**: Menú → Reportes → Análisis Repuestos

**🔍 Detección inteligente**:
- 🤖 **40+ palabras clave**: Identifica repuestos en descripciones
- 📊 **Frecuencia de uso**: Cuáles se usan más
- 👥 **Por cliente**: Patrones de consumo
- 📈 **Tendencias mensuales**: Evolución del uso

**🎛️ Filtros disponibles**:
- 📅 Rango de fechas
- 👥 Cliente específico
- 👁️ Mostrar detalles de mantenimientos

**📈 Gráficos incluidos**:
- 📊 Tendencia mensual de uso
- 🏆 Top 10 repuestos más utilizados

### Análisis de Mano de Obra

**Acceso**: Menú → Reportes → Análisis Mano de Obra

**🔍 Clasificación automática**:

#### Por Complejidad:
- 🔴 **Trabajos Complejos**: Desarmar, soldadura, fabricación
- 🟡 **Trabajos Medios**: Instalaciones, reemplazos, ajustes
- 🟢 **Trabajos Simples**: Limpieza, lubricación, revisiones

#### Por Tipo:
- ⚡ **Eléctrico**: Motores, cables, sistemas eléctricos
- 🛠️ **Mecánico**: Engranajes, piezas mecánicas
- 💧 **Hidráulico**: Cilindros, sistemas hidráulicos
- 🔧 **Mantenimiento**: Service, revisiones generales
- 📋 **General**: Otros trabajos

**📊 Análisis incluido**:
- 🥧 Distribución de complejidad
- 🍩 Tipos de trabajo
- 📈 Análisis por cliente
- 📋 Trabajos recientes (opcional)

## 🧠 Sistema Inteligente de Reconocimiento

### ¿Qué es el Análisis Inteligente?

El **Sistema Inteligente** es una nueva funcionalidad avanzada que utiliza inteligencia artificial para analizar automáticamente las descripciones de mantenimientos y extraer información precisa sobre:

- **📦 Repuestos utilizados**: Identifica qué repuestos se usaron
- **🔧 Trabajos realizados**: Clasifica los tipos de trabajo
- **📊 Confianza**: Mide la precisión de cada clasificación
- **🎯 Categorías**: Organiza la información estructuradamente

### Acceso al Sistema Inteligente

**📍 Ubicación**: Menú → Reportes → "🧠 Análisis Inteligente"

### Análisis Inteligente - Página Principal

**Acceso**: Reportes → Análisis Inteligente

#### 📊 **Panel de Estadísticas**

Al acceder verás:

```
┌─────────────────────────────────────────────────────────┐
│ 📊 ESTADÍSTICAS INTELIGENTES                            │
├─────────────────────────────────────────────────────────┤
│ 📦 Total Repuestos Detectados: 156                     │
│ 🔧 Total Trabajos Clasificados: 203                    │
│ 🎯 Promedio de Confianza: 87.5%                        │
│ 📈 Análisis Completados: 89 mantenimientos             │
└─────────────────────────────────────────────────────────┘
```

#### 🔍 **Análisis Detallado por Categorías**

**Repuestos por Categoría**:
- 🔧 **Filtros**: 45 detecciones (Filtro aceite, Filtro aire, etc.)
- ⚙️ **Lubricantes**: 32 detecciones (Aceite motor, Grasa, etc.)
- 🔩 **Componentes**: 28 detecciones (Kit reparación, Sellos, etc.)
- 💧 **Hidráulicos**: 25 detecciones (Cilindros, Mangueras, etc.)
- ⚡ **Eléctricos**: 18 detecciones (Motores, Cables, etc.)

**Trabajos por Tipo**:
- 🔧 **Mantenimiento**: 78 clasificaciones
- 💧 **Hidráulico**: 45 clasificaciones  
- ⚙️ **Mecánico**: 38 clasificaciones
- ⚡ **Eléctrico**: 25 clasificaciones
- 🔥 **Soldadura**: 17 clasificaciones

#### 🎨 **Código de Colores por Confianza**

| Color | Confianza | Significado |
|-------|-----------|-------------|
| 🟢 Verde | 80-100% | Muy seguro |
| 🟡 Amarillo | 60-79% | Probable |
| 🔴 Rojo | <60% | Revisar |

#### 📈 **Análisis por Cliente**

Para cada cliente se muestra:
- Repuestos más utilizados
- Tipos de trabajo más frecuentes
- Promedio de confianza del análisis
- Cantidad de mantenimientos analizados

### Gestión de Categorías

**Acceso**: Reportes → Gestionar Categorías

Esta sección permite a los administradores configurar y optimizar el sistema inteligente.

#### 📋 **Vista Principal**

```
┌─────────────────────────────────────────────────────────┐
│ ⚙️ GESTIÓN DE CATEGORÍAS                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 📦 CATEGORÍAS DE REPUESTOS     🔧 CATEGORÍAS DE TRABAJOS│
│                                                         │
│ 🔧 Filtros           [Activa]  🔧 Mantenimiento [Activa]│
│ ⚙️ Lubricantes       [Activa]  💧 Hidráulico    [Activa]│
│ 🔩 Componentes       [Activa]  ⚙️ Mecánico      [Activa]│
│ 💧 Hidráulicos       [Activa]  ⚡ Eléctrico     [Activa]│
│ ⚡ Eléctricos        [Activa]  🔥 Soldadura     [Activa]│
│                                                         │
│ [➕ Agregar Categoría Repuesto] [➕ Agregar Cat. Trabajo]│
└─────────────────────────────────────────────────────────┘
```

#### ➕ **Crear Nueva Categoría**

**Proceso paso a paso**:

1. **Seleccionar tipo**:
   ```
   🔘 Categoría de Repuestos
   ⚪ Categoría de Trabajos
   ```

2. **Información básica**:
   ```
   📝 Nombre: Neumáticos
   🎨 Color: #FF5722 (naranja)
   📄 Descripción: Cubiertas, neumáticos y cámaras
   ```

3. **Palabras clave** *(separadas por comas)*:
   ```
   🔤 Palabras clave: 
   neumático, cubierta, llanta, goma, cámara, válvula
   ```

4. **Sinónimos opcionales**:
   ```
   🔗 Sinónimos adicionales:
   rueda, pneumático, tire
   ```

#### ✏️ **Editar Categoría Existente**

**Funciones disponibles**:
- Modificar nombre y descripción
- Cambiar color identificador
- Agregar/quitar palabras clave
- Actualizar sinónimos
- Desactivar categoría (no eliminar)

#### 📊 **Estadísticas de Uso**

Para cada categoría se muestra:
```
🔧 Filtros
├─ Detecciones: 45
├─ Confianza promedio: 92%
├─ Palabras clave activas: 12
├─ Última detección: Hace 2 días
└─ Estado: ✅ Activa
```

### Cómo Usar el Sistema Inteligente

#### 🎯 **Para Análisis Rutinarios**

1. **Acceder al análisis**: Reportes → Análisis Inteligente
2. **Revisar estadísticas**: Ver el resumen general
3. **Analizar por categorías**: Identificar patrones de uso
4. **Revisar confianza**: Verificar elementos con baja confianza
5. **Análisis por cliente**: Ver patrones específicos

#### 🔧 **Para Mejorar el Sistema**

1. **Identificar errores**: Buscar clasificaciones incorrectas
2. **Acceder a gestión**: Reportes → Gestionar Categorías
3. **Actualizar palabras clave**: Agregar términos faltantes
4. **Crear nuevas categorías**: Para elementos no cubiertos
5. **Verificar resultados**: Volver al análisis para confirmar mejoras

#### 📈 **Para Reportes Gerenciales**

1. **Análisis de tendencias**: Ver qué repuestos se usan más
2. **Patrones por cliente**: Identificar necesidades específicas
3. **Planificación de stock**: Basado en uso histórico inteligente
4. **Optimización de procesos**: Según tipos de trabajo más frecuentes

### Ventajas del Sistema Inteligente

#### ⏱️ **Ahorro de Tiempo**
- Clasificación automática vs manual
- Análisis inmediato de grandes volúmenes
- Reportes generados instantáneamente

#### 📈 **Precisión Mejorada**
- Reconocimiento de sinónimos y variaciones
- Clasificación consistente en todos los registros
- Mejora continua con más datos

#### 🎯 **Inteligencia Empresarial**
- Patrones de uso claros y medibles
- Tendencias identificadas automáticamente
- Decisiones basadas en datos precisos

#### 🔧 **Flexibilidad Total**
- Sistema adaptable a cualquier taller
- Categorías personalizables por industria
- Palabras clave específicas del negocio

### Consejos para Optimizar el Sistema

#### 🎯 **Configuración Inicial**

1. **Revisar categorías predefinidas**:
   - Verificar que cubran tu inventario
   - Agregar categorías específicas de tu taller
   - Personalizar palabras clave

2. **Probar con datos existentes**:
   - Ejecutar análisis completo
   - Revisar resultados de baja confianza
   - Ajustar palabras clave según necesidad

#### 🔄 **Mantenimiento Regular**

1. **Revisión semanal**:
   - Verificar nuevas detecciones
   - Identificar términos no reconocidos
   - Agregar palabras clave faltantes

2. **Optimización mensual**:
   - Analizar estadísticas de uso
   - Desactivar categorías no utilizadas
   - Crear categorías para nuevos patrones

#### 📊 **Uso de Resultados**

1. **Para compras**:
   - Identificar repuestos de alta rotación
   - Planificar stock basado en tendencias
   - Optimizar proveedores por categoría

2. **Para planificación**:
   - Predecir tipos de trabajo frecuentes
   - Asignar recursos según patrones
   - Capacitar técnicos en áreas específicas

### Solución de Problemas del Sistema IA

#### 🔍 **Detecciones Incorrectas**

**Problema**: El sistema clasifica incorrectamente
**Solución**:
1. Verificar palabras clave de la categoría
2. Agregar términos más específicos
3. Crear nueva categoría si es necesario
4. Revisar sinónimos que puedan confundir

#### 📉 **Baja Confianza General**

**Problema**: Muchas detecciones con confianza <60%
**Solución**:
1. Revisar descripciones de mantenimientos
2. Mejorar calidad de datos de entrada
3. Ampliar palabras clave de categorías existentes
4. Crear categorías más específicas

#### 🚫 **No Detecta Elementos Conocidos**

**Problema**: Repuestos/trabajos obvios no se detectan
**Solución**:
1. Verificar ortografía en descripciones
2. Agregar variaciones del término
3. Revisar que la categoría esté activa
4. Confirmar que las palabras clave incluyan el término

#### ⚡ **Análisis Lento**

**Problema**: El sistema tarda mucho en procesar
**Solución**:
1. Revisar cantidad de datos a procesar
2. Filtrar por fechas específicas
3. Analizar por cliente individual
4. Contactar soporte si persiste

## 📤 Importación de Datos

### Preparar Archivo Excel

**📋 Estructura requerida**:

```excel
Archivo: datos_taller.xlsx

Hoja1: CLIENTE_A
┌─────────────┬──────────────┬─────────────┬──────────────┐
│   EQUIPOS   │    FECHA     │  REPUESTOS  │  MANO DE OBRA│
├─────────────┼──────────────┼─────────────┼──────────────┤
│ Excavadora  │ 2024-01-15   │ Filtro aceite│ Cambio filtros│
│             │ 2024-01-16   │ Aceite motor│ Service general│
│ Bulldozer   │ 2024-01-20   │ Cadenas     │ Reparación    │
└─────────────┴──────────────┴─────────────┴──────────────┘

Hoja2: CLIENTE_B
┌─────────────┬──────────────┬─────────────┬──────────────┐
│   EQUIPOS   │    FECHA     │  REPUESTOS  │  MANO DE OBRA│
│    ...      │     ...      │     ...     │      ...     │
└─────────────┴──────────────┴─────────────┴──────────────┘
```

**✅ Reglas importantes**:
- Una hoja por cliente
- Nombre de hoja = Nombre del cliente
- Columnas pueden estar en cualquier orden
- Filas vacías en EQUIPOS = continuación del equipo anterior
- Fechas en formato reconocible (DD/MM/YYYY, YYYY-MM-DD)

### Proceso de Importación

**Acceso**: Menú → Importar Excel

**Pasos**:

1. **Seleccionar archivo**:
   ```
   📁 Examinar: Elegir archivo .xlsx
   ⚠️ Máximo: 16MB
   ✅ Formatos: .xlsx, .xls
   ```

2. **Información antes de importar**:
   - 📊 Se muestran las hojas detectadas
   - ⚠️ Advertencias sobre datos existentes
   - 🔄 Opción de reiniciar aplicación primero

3. **Importar**:
   - ⏳ Proceso automático con progreso
   - 📋 Resumen de registros creados
   - ✅ Confirmación de éxito

**📊 Resultado**:
- Clientes creados (uno por hoja)
- Equipos registrados y asignados
- Mantenimientos con fechas correctas
- Resumen detallado del proceso

### Reiniciar Aplicación

**Acceso**: Menú → Reiniciar App

**⚠️ Advertencia crítica**:
Esta función **elimina todos los datos** de:
- Mantenimientos
- Equipos
- **NO elimina**: Clientes, Repuestos

**Cuándo usar**:
- Antes de importar datos nuevos
- Para empezar con datos limpios
- ⚠️ **NUNCA** en producción sin backup

## 💡 Consejos y Mejores Prácticas

### Organización de Datos

1. **📝 Nomenclatura consistente**:
   ```
   ✅ Bien: "Excavadora CAT 320"
   ❌ Mal: "excav cat", "EXCAVADORA cat 320"
   ```

2. **👥 Clientes únicos**:
   - Un cliente por empresa
   - Usar nombres oficiales
   - Mantener datos de contacto actualizados

3. **📅 Fechas precisas**:
   - Usar fechas reales de mantenimiento
   - No usar fecha actual para trabajos históricos
   - Formato consistente

### Gestión de Mantenimientos

1. **📝 Descripciones detalladas**:
   ```
   ✅ Bien: "Cambio filtro de aceite marca X, código 123. 
            Reemplazo de 5L aceite 15W40. 
            Revisión general de motor."
   
   ❌ Mal: "service"
   ```

2. **🔄 Estados actualizados**:
   - Pendiente → En Progreso → Completado
   - Actualizar estado al avanzar trabajo
   - Cancelar solo si no se realizará

3. **💰 Costos reales**:
   - Incluir mano de obra + repuestos
   - Mantener histórico de precios
   - Útil para análisis de costos

### Control de Repuestos

1. **📊 Stock mínimo realista**:
   - Basado en consumo histórico
   - Considerar tiempo de reposición
   - Revisar periódicamente

2. **📝 Movimientos detallados**:
   - Motivo claro en cada ajuste
   - Referencias a mantenimientos
   - Mantener trazabilidad

3. **🔄 Revisiones periódicas**:
   - Inventario físico mensual
   - Ajustar stock mínimos
   - Eliminar repuestos obsoletos

### Reportes Efectivos

1. **🎯 Filtros específicos**:
   - Usar rangos de fecha relevantes
   - Filtrar por cliente para análisis específicos
   - Combinar diferentes reportes

2. **📈 Análisis de tendencias**:
   - Comparar períodos similares
   - Identificar patrones estacionales
   - Planificar mantenimientos preventivos

3. **💼 Uso empresarial**:
   - Reportes mensuales para gerencia
   - Análisis de costos por cliente
   - Planificación de recursos

## 🛠️ Solución de Problemas

### Problemas Comunes

#### 🚫 No puedo eliminar un cliente
**Causa**: Cliente tiene equipos asociados
**Solución**:
1. Ir a Equipos
2. Filtrar por el cliente
3. Eliminar o reasignar todos los equipos
4. Luego eliminar el cliente

#### 🚫 No puedo eliminar un equipo
**Causa**: Equipo tiene mantenimientos registrados
**Solución**:
1. Ir a Mantenimientos
2. Buscar mantenimientos del equipo
3. Eliminar mantenimientos (si es apropiado)
4. Luego eliminar el equipo

#### 🚫 Error al importar Excel
**Posibles causas**:
- Archivo corrupto o muy grande (>16MB)
- Formato no compatible (.xlsx requerido)
- Columnas mal estructuradas

**Soluciones**:
1. Verificar formato del archivo
2. Reducir tamaño eliminando hojas innecesarias
3. Revisar estructura de columnas
4. Usar archivo de ejemplo como plantilla

#### 📅 Fechas incorrectas en importación
**Causa**: Formato de fecha no reconocido
**Solución**:
1. Usar formato YYYY-MM-DD en Excel
2. O DD/MM/YYYY con separadores claros
3. Evitar formatos de texto

#### 🔍 No encuentro datos
**Verificar**:
- Filtros activos (limpiar filtros)
- Búsqueda con términos correctos
- Datos realmente existen en la base

#### 🐌 Sistema lento
**Optimizaciones**:
- Cerrar pestañas innecesarias del navegador
- Limpiar caché del navegador
- Verificar conexión de red
- Contactar administrador si persiste

### Contacto de Soporte

Si los problemas persisten:

1. **📝 Documentar el problema**:
   - ¿Qué estabas haciendo?
   - ¿Qué mensaje de error aparece?
   - ¿Pasos para reproducir?

2. **📱 Contactar soporte**:
   - Email: soporte@sistema-taller.com
   - WhatsApp: +54 9 11 xxxx-xxxx
   - Incluir capturas de pantalla

3. **🆘 Información útil**:
   - Navegador utilizado
   - Horario del problema
   - Datos específicos involucrados

## ✅ Checklist de Uso Diario

### 🌅 Al Iniciar el Día
- [ ] Revisar mantenimientos pendientes
- [ ] Verificar stock bajo de repuestos
- [ ] Programar trabajos del día

### 🔧 Durante los Trabajos
- [ ] Actualizar estado de mantenimientos
- [ ] Registrar repuestos utilizados
- [ ] Documentar trabajos realizados

### 🌆 Al Finalizar el Día
- [ ] Completar mantenimientos finalizados
- [ ] Actualizar costos reales
- [ ] Programar trabajos del día siguiente

### 📊 Semanalmente
- [ ] Generar reportes de actividad
- [ ] Revisar inventario de repuestos
- [ ] Analizar tendencias de mantenimiento
- [ ] **🧠 Ejecutar análisis inteligente**
- [ ] **🔍 Revisar clasificaciones de baja confianza**

### 📈 Mensualmente
- [ ] Reportes completos para gerencia
- [ ] Análisis de costos por cliente
- [ ] Planificación de mantenimientos preventivos
- [ ] **⚙️ Optimizar categorías del sistema IA**
- [ ] **📊 Revisar estadísticas de uso inteligente**
- [ ] **🎯 Ajustar palabras clave según patrones**
- [ ] Backup de datos

---

**🎯 ¡Este manual te ayudará a aprovechar al máximo el Sistema de Gestión de Taller!**

*Para sugerencias de mejora de este manual: documentacion@sistema-taller.com*
