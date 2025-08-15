/**
 * TOOLTIPS MANAGER - Sistema inteligente de tooltips
 * =================================================
 */

class TooltipsManager {
    constructor() {
        this.tooltips = new Map();
        this.helpTexts = {
            // Formularios
            'email': 'Ingresa un email válido (ejemplo: usuario@empresa.com)',
            'password': 'Mínimo 8 caracteres, incluye mayúsculas, minúsculas y números',
            'telefono': 'Formato: +1234567890 o 1234567890',
            'precio': 'Formato: 123.45 (usa punto para decimales)',
            'fecha': 'Formato: DD/MM/AAAA',
            
            // Equipos
            'serie_equipo': 'Número de serie único del equipo',
            'modelo_equipo': 'Modelo del fabricante',
            'estado_equipo': 'Estado actual del equipo (Activo, Inactivo, En Mantenimiento)',
            
            // Mantenimientos
            'tipo_mantenimiento': 'Preventivo, Correctivo, Predictivo',
            'prioridad': 'Baja, Media, Alta, Crítica',
            'tiempo_estimado': 'Tiempo estimado en horas',
            
            // Reportes
            'fecha_inicio': 'Fecha de inicio del período a consultar',
            'fecha_fin': 'Fecha de fin del período a consultar',
            'exportar_pdf': 'Generar reporte en formato PDF',
            'exportar_excel': 'Generar reporte en formato Excel',
            
            // Sistema
            'buscar': 'Buscar por cualquier campo visible en la tabla',
            'filtrar': 'Aplicar filtros a los resultados',
            'ordenar': 'Hacer clic para ordenar por esta columna',
            'acciones': 'Ver, editar o eliminar este registro',
            
            // Estados
            'activo': 'Elemento activo y en uso',
            'inactivo': 'Elemento desactivado temporalmente',
            'pendiente': 'Esperando aprobación o acción',
            'completado': 'Proceso finalizado correctamente',
            
            // Machine Learning
            'prediccion_ml': 'Predicción basada en análisis de datos históricos',
            'confianza_ml': 'Nivel de confianza del modelo (0-100%)',
            'recomendacion': 'Recomendación automática del sistema',
            
            // IoT
            'dispositivo_iot': 'Dispositivo conectado para monitoreo',
            'lectura_sensor': 'Última lectura del sensor',
            'estado_conexion': 'Estado de conexión del dispositivo',
            
            // Seguridad
            'permisos': 'Permisos asignados a este rol de usuario',
            'auditoria': 'Registro de acciones realizadas en el sistema',
            'sesion': 'Información de la sesión actual del usuario'
        };
        
        this.contextualHelp = {
            '/equipos': {
                'page_help': 'Gestiona todos los equipos del taller. Puedes agregar nuevos equipos, editarlos y ver su historial de mantenimientos.',
                'add_button': 'Agregar un nuevo equipo al sistema',
                'search_input': 'Buscar equipos por serie, marca, modelo o cliente'
            },
            '/clientes': {
                'page_help': 'Administra la información de tus clientes y visualiza sus equipos.',
                'add_button': 'Registrar un nuevo cliente',
                'search_input': 'Buscar clientes por nombre, teléfono o email'
            },
            '/mantenimientos': {
                'page_help': 'Programa y gestiona los mantenimientos de equipos.',
                'add_button': 'Programar un nuevo mantenimiento',
                'search_input': 'Buscar mantenimientos por equipo, cliente o fecha'
            },
            '/repuestos': {
                'page_help': 'Controla el inventario de repuestos y piezas.',
                'add_button': 'Agregar nuevo repuesto al inventario',
                'search_input': 'Buscar repuestos por nombre o descripción'
            },
            '/reportes': {
                'page_help': 'Genera reportes detallados y estadísticas del taller.',
                'export_buttons': 'Exportar reportes en diferentes formatos'
            }
        };
        
        this.init();
    }

    init() {
        // Inicializar tooltips de Bootstrap existentes
        this.initBootstrapTooltips();
        
        // Agregar tooltips automáticos
        this.addAutomaticTooltips();
        
        // Agregar ayuda contextual
        this.addContextualHelp();
        
        // Observar nuevos elementos
        this.observeNewElements();
        
        console.log('✅ Sistema de tooltips inicializado');
    }

    initBootstrapTooltips() {
        // Inicializar todos los tooltips de Bootstrap
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl, {
                delay: { show: 500, hide: 100 },
                placement: 'auto'
            });
        });
    }

    addAutomaticTooltips() {
        // Tooltips para campos de formulario por tipo
        document.querySelectorAll('input[type="email"]').forEach(input => {
            this.addTooltip(input, this.helpTexts.email);
        });

        document.querySelectorAll('input[type="password"]').forEach(input => {
            this.addTooltip(input, this.helpTexts.password);
        });

        document.querySelectorAll('input[type="tel"]').forEach(input => {
            this.addTooltip(input, this.helpTexts.telefono);
        });

        document.querySelectorAll('input[type="date"]').forEach(input => {
            this.addTooltip(input, this.helpTexts.fecha);
        });

        // Tooltips por atributos de datos
        Object.keys(this.helpTexts).forEach(key => {
            document.querySelectorAll(`[data-tooltip="${key}"]`).forEach(element => {
                this.addTooltip(element, this.helpTexts[key]);
            });
        });

        // Tooltips para iconos comunes
        document.querySelectorAll('.fa-edit').forEach(icon => {
            this.addTooltip(icon.closest('button, a'), 'Editar este registro');
        });

        document.querySelectorAll('.fa-trash').forEach(icon => {
            this.addTooltip(icon.closest('button, a'), 'Eliminar este registro');
        });

        document.querySelectorAll('.fa-eye').forEach(icon => {
            this.addTooltip(icon.closest('button, a'), 'Ver detalles');
        });

        document.querySelectorAll('.fa-download').forEach(icon => {
            this.addTooltip(icon.closest('button, a'), 'Descargar archivo');
        });

        document.querySelectorAll('.fa-print').forEach(icon => {
            this.addTooltip(icon.closest('button, a'), 'Imprimir reporte');
        });

        // Tooltips para estados
        document.querySelectorAll('.badge').forEach(badge => {
            const text = badge.textContent.toLowerCase().trim();
            if (this.helpTexts[text]) {
                this.addTooltip(badge, this.helpTexts[text]);
            }
        });
    }

    addContextualHelp() {
        const currentPath = window.location.pathname;
        const helpData = this.contextualHelp[currentPath];
        
        if (!helpData) return;

        // Ayuda de página
        if (helpData.page_help) {
            const pageTitle = document.querySelector('h1, h2, .page-title');
            if (pageTitle) {
                this.addTooltip(pageTitle, helpData.page_help, 'bottom');
            }
        }

        // Ayuda para botones específicos
        Object.keys(helpData).forEach(selector => {
            if (selector === 'page_help') return;
            
            const elements = document.querySelectorAll(this.getSelectorFromKey(selector));
            elements.forEach(element => {
                this.addTooltip(element, helpData[selector]);
            });
        });
    }

    getSelectorFromKey(key) {
        const selectorMap = {
            'add_button': '.btn-primary[href*="nuevo"], .btn-primary[onclick*="nuevo"]',
            'search_input': 'input[type="search"], input[placeholder*="buscar"], input[placeholder*="Buscar"]',
            'export_buttons': '.btn[href*="export"], .btn[onclick*="export"]'
        };
        
        return selectorMap[key] || `[data-help="${key}"]`;
    }

    addTooltip(element, text, placement = 'auto') {
        if (!element || element.hasAttribute('data-tooltip-added')) return;

        // Marcar como procesado
        element.setAttribute('data-tooltip-added', 'true');
        
        // Configurar tooltip
        element.setAttribute('data-bs-toggle', 'tooltip');
        element.setAttribute('data-bs-placement', placement);
        element.setAttribute('title', text);

        // Inicializar tooltip de Bootstrap
        const tooltip = new bootstrap.Tooltip(element, {
            delay: { show: 500, hide: 100 },
            placement: placement,
            trigger: 'hover focus'
        });

        this.tooltips.set(element, tooltip);
    }

    observeNewElements() {
        // Observer para elementos agregados dinámicamente
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Re-aplicar tooltips a nuevos elementos
                        this.processNewElement(node);
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    processNewElement(element) {
        // Procesar el elemento y sus hijos
        if (element.matches && element.matches('input[type="email"]')) {
            this.addTooltip(element, this.helpTexts.email);
        }

        // Procesar hijos
        if (element.querySelectorAll) {
            element.querySelectorAll('input[type="email"]').forEach(input => {
                this.addTooltip(input, this.helpTexts.email);
            });

            element.querySelectorAll('input[type="password"]').forEach(input => {
                this.addTooltip(input, this.helpTexts.password);
            });

            // Agregar más selectores según sea necesario
        }
    }

    // Métodos públicos
    addCustomTooltip(selector, text, placement = 'auto') {
        document.querySelectorAll(selector).forEach(element => {
            this.addTooltip(element, text, placement);
        });
    }

    removeTooltip(element) {
        const tooltip = this.tooltips.get(element);
        if (tooltip) {
            tooltip.dispose();
            this.tooltips.delete(element);
            element.removeAttribute('data-tooltip-added');
            element.removeAttribute('data-bs-toggle');
            element.removeAttribute('data-bs-placement');
            element.removeAttribute('title');
        }
    }

    updateTooltip(element, newText) {
        this.removeTooltip(element);
        this.addTooltip(element, newText);
    }

    // Helpers para casos específicos
    addFormTooltips(formElement) {
        const form = typeof formElement === 'string' ? 
                    document.querySelector(formElement) : formElement;
        
        if (!form) return;

        // Tooltips específicos para campos de formulario
        form.querySelectorAll('input, select, textarea').forEach(field => {
            const label = form.querySelector(`label[for="${field.id}"]`);
            const fieldName = field.name || field.id;
            
            // Generar tooltip basado en el tipo de campo
            let tooltipText = this.generateFieldTooltip(field, label);
            
            if (tooltipText) {
                this.addTooltip(field, tooltipText);
            }
        });
    }

    generateFieldTooltip(field, label) {
        const type = field.type;
        const name = field.name;
        const labelText = label ? label.textContent.toLowerCase() : '';

        // Tooltips basados en el tipo de campo
        const typeTooltips = {
            'email': this.helpTexts.email,
            'password': this.helpTexts.password,
            'tel': this.helpTexts.telefono,
            'date': this.helpTexts.fecha,
            'number': 'Ingresa solo números'
        };

        if (typeTooltips[type]) {
            return typeTooltips[type];
        }

        // Tooltips basados en el nombre del campo
        const namePatterns = {
            'precio': this.helpTexts.precio,
            'telefono': this.helpTexts.telefono,
            'email': this.helpTexts.email,
            'serie': 'Número de serie único',
            'modelo': 'Modelo del equipo',
            'marca': 'Marca del fabricante'
        };

        for (const pattern in namePatterns) {
            if (name.includes(pattern) || labelText.includes(pattern)) {
                return namePatterns[pattern];
            }
        }

        return null;
    }
}

// Inicializar manager global
window.tooltipsManager = new TooltipsManager();

// Funciones de conveniencia
window.addTooltip = (selector, text, placement) => {
    window.tooltipsManager.addCustomTooltip(selector, text, placement);
};

window.addFormTooltips = (formSelector) => {
    window.tooltipsManager.addFormTooltips(formSelector);
};

// Auto-aplicar tooltips a formularios cuando se cargan
document.addEventListener('DOMContentLoaded', function() {
    // Detectar y procesar formularios existentes
    document.querySelectorAll('form').forEach(form => {
        window.tooltipsManager.addFormTooltips(form);
    });
});

console.log('💡 Sistema de tooltips inteligentes cargado');
