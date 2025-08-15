/**
 * UNIVERSAL FIXES - JavaScript
 * Correcciones universales para funciones rotas en toda la aplicación
 */

// =============================================
// GLOBAL ERROR HANDLERS - DESACTIVADOS TEMPORALMENTE
// =============================================

// NOTA: Event listeners de error global desactivados para evitar notificaciones en cada página
// Solo se mantienen los logs en consola para debugging

// Capturar errores JavaScript no manejados (SOLO LOG, SIN NOTIFICACIONES)
window.addEventListener('error', function(event) {
    console.error('Error JavaScript global (sin notificación):', event.error);
    // NOTIFICACIONES DESACTIVADAS - Causan molestias en cada cambio de página
});

// Capturar promesas rechazadas (SOLO LOG, SIN NOTIFICACIONES)  
window.addEventListener('unhandledrejection', function(event) {
    console.error('Promesa rechazada (sin notificación):', event.reason);
    // NOTIFICACIONES DESACTIVADAS - Causan molestias en cada cambio de página
    event.preventDefault(); // Prevenir que aparezca en consola del navegador
});

// =============================================
// FUNCIONES GLOBALES PARA MODALES
// =============================================

/**
 * Función global para limpiar backdrop de modales
 * Previene el problema de ventana oscura que se queda
 */
window.limpiarModalBackdrop = function() {
    try {
        // Limpiar todos los backdrop que puedan existir
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => {
            backdrop.remove();
        });
        
        // Limpiar clases del body
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('padding-right');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('position');
        
        // Resetear scroll
        document.documentElement.style.removeProperty('overflow');
        
        console.log('Modal backdrop limpiado globalmente');
    } catch (error) {
        console.error('Error limpiando modal backdrop:', error);
    }
};

/**
 * Función para asegurar que los modales se cierren correctamente
 */
window.cerrarModalSeguro = function(modalId) {
    try {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            const instance = bootstrap.Modal.getInstance(modalElement);
            if (instance) {
                instance.hide();
            }
        }
        
        // Limpiar después de un pequeño delay
        setTimeout(window.limpiarModalBackdrop, 150);
    } catch (error) {
        console.error('Error cerrando modal:', error);
        window.limpiarModalBackdrop();
    }
};

// =============================================
// FALLBACKS PARA FUNCIONES FALTANTES
// =============================================

// NOTA: Las funciones de notificación se definen en notifications.js
// Solo crear fallbacks si notifications.js no se cargó correctamente

if (typeof window.showSuccess === 'undefined') {
    window.showSuccess = function(mensaje) {
        console.warn('Usando fallback showSuccess - notifications.js no cargado');
        console.log('SUCCESS:', mensaje);
        if (window.notificationSystem && window.notificationSystem.success) {
            window.notificationSystem.success(mensaje);
        } else {
            alert('✅ ' + mensaje);
        }
    };
}

if (typeof window.showError === 'undefined') {
    window.showError = function(mensaje) {
        console.warn('Usando fallback showError - notifications.js no cargado');
        console.error('ERROR:', mensaje);
        if (window.notificationSystem && window.notificationSystem.error) {
            window.notificationSystem.error(mensaje);
        } else {
            alert('❌ ' + mensaje);
        }
    };
}

if (typeof window.showInfo === 'undefined') {
    window.showInfo = function(mensaje) {
        console.warn('Usando fallback showInfo - notifications.js no cargado');
        console.info('INFO:', mensaje);
        if (window.notificationSystem && window.notificationSystem.info) {
            window.notificationSystem.info(mensaje);
        } else {
            alert('ℹ️ ' + mensaje);
        }
    };
}

// NOTA: showConfirm se define en notifications.js
// No sobrescribir si ya existe para mantener el sistema personalizado
if (typeof window.showConfirm === 'undefined') {
    // Fallback solo si notifications.js no se cargó
    window.showConfirm = function(mensaje, callback, opciones = {}) {
        console.warn('Usando fallback de confirmación - notifications.js no cargado');
        const resultado = confirm(mensaje);
        if (callback) {
            callback(resultado);
        }
        return resultado;
    };
}

// =============================================
// FIXES PARA FORMULARIOS
// =============================================

document.addEventListener('DOMContentLoaded', function() {
    // Fix para formularios que no tienen preventDefault
    document.querySelectorAll('form').forEach(function(form) {
        if (!form.dataset.fixedForm) {
            form.addEventListener('submit', function(event) {
                const submitBtn = this.querySelector('button[type="submit"]');
                
                // Prevenir doble envío
                if (submitBtn && submitBtn.disabled) {
                    event.preventDefault();
                    return false;
                }
                
                // Deshabilitar botón temporalmente
                if (submitBtn) {
                    submitBtn.disabled = true;
                    setTimeout(() => {
                        submitBtn.disabled = false;
                    }, 3000);
                }
            });
            
            form.dataset.fixedForm = 'true';
        }
    });
    
    // Fix para botones que no responden
    document.querySelectorAll('button[onclick], a[onclick]').forEach(function(element) {
        if (!element.dataset.fixedClick) {
            const originalOnclick = element.onclick;
            
            element.addEventListener('click', function(event) {
                try {
                    if (originalOnclick) {
                        const result = originalOnclick.call(this, event);
                        if (result === false) {
                            event.preventDefault();
                        }
                    }
                } catch (error) {
                    console.error('Error en onclick (sin notificación):', error);
                    event.preventDefault();
                    
                    // NOTIFICACIONES DE CLICK DESACTIVADAS - Causan molestias en navegación normal
                    // El usuario puede ver errores en consola si es necesario para debugging
                }
            });
            
            element.dataset.fixedClick = 'true';
        }
    });
    
    // Fix para elementos con data-attributes sin eventos
    fixMissingEventHandlers();
});

function fixMissingEventHandlers() {
    // Botones de eliminar sin eventos
    document.querySelectorAll('[data-categoria-id][data-tipo="repuesto"]:not([data-fixed-events])').forEach(function(btn) {
        if (btn.classList.contains('btn-eliminar-categoria')) {
            btn.addEventListener('click', function() {
                const id = this.dataset.categoriaId;
                const nombre = this.dataset.categoriaNombre || 'elemento';
                
                if (typeof eliminarCategoriaRepuesto === 'function') {
                    eliminarCategoriaRepuesto(id, nombre);
                } else {
                    console.warn('Función eliminarCategoriaRepuesto no encontrada');
                    if (confirm(`¿Eliminar categoría "${nombre}"?`)) {
                        window.location.href = `/api/categorias/repuesto/${id}`;
                    }
                }
            });
        }
        
        btn.dataset.fixedEvents = 'true';
    });
    
    // Botones de eliminar trabajos
    document.querySelectorAll('[data-categoria-id][data-tipo="trabajo"]:not([data-fixed-events])').forEach(function(btn) {
        if (btn.classList.contains('btn-eliminar-categoria')) {
            btn.addEventListener('click', function() {
                const id = this.dataset.categoriaId;
                const nombre = this.dataset.categoriaNombre || 'elemento';
                
                if (typeof eliminarCategoriaTrabajo === 'function') {
                    eliminarCategoriaTrabajo(id, nombre);
                } else {
                    console.warn('Función eliminarCategoriaTrabajo no encontrada');
                    if (confirm(`¿Eliminar categoría de trabajo "${nombre}"?`)) {
                        window.location.href = `/api/categorias/trabajo/${id}`;
                    }
                }
            });
        }
        
        btn.dataset.fixedEvents = 'true';
    });
}

// =============================================
// UTILS PARA DEBUGGING
// =============================================

// Función para detectar funciones faltantes
window.debugMissingFunctions = function() {
    const expectedFunctions = [
        'showSuccess', 'showError', 'showInfo', 'showConfirm',
        'editarCategoriaRepuesto', 'editarCategoriaTrabajo',
        'eliminarCategoriaRepuesto', 'eliminarCategoriaTrabajo',
        'toggleCategoriaEstado', 'verPalabrasCategoria'
    ];
    
    const missing = expectedFunctions.filter(func => typeof window[func] === 'undefined');
    
    if (missing.length > 0) {
        console.warn('Funciones faltantes:', missing);
        return missing;
    } else {
        console.log('✅ Todas las funciones principales están definidas');
        return [];
    }
};

// Ejecutar debug automáticamente
setTimeout(() => {
    window.debugMissingFunctions();
}, 1000);

// =============================================
// POLYFILLS PARA COMPATIBILIDAD
// =============================================

// Polyfill para fetch si no existe
if (typeof fetch === 'undefined') {
    window.fetch = function(url, options = {}) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open(options.method || 'GET', url);
            
            if (options.headers) {
                Object.keys(options.headers).forEach(key => {
                    xhr.setRequestHeader(key, options.headers[key]);
                });
            }
            
            xhr.onload = () => {
                resolve({
                    ok: xhr.status >= 200 && xhr.status < 300,
                    status: xhr.status,
                    json: () => Promise.resolve(JSON.parse(xhr.responseText))
                });
            };
            
            xhr.onerror = () => reject(new Error('Network error'));
            xhr.send(options.body);
        });
    };
}

console.log('🔧 Universal fixes cargados exitosamente');
