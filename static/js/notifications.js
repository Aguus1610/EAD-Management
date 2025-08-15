/**
 * SISTEMA DE NOTIFICACIONES PROPIAS DE LA APP
 * Reemplaza las notificaciones del navegador por un sistema interno
 */

class NotificationSystem {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.init();
    }

    init() {
        // Crear contenedor si no existe
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'notifications-container';
            this.container.id = 'notifications-container';
            document.body.appendChild(this.container);
        }
    }

    /**
     * Mostrar notificación
     * @param {string} message - Mensaje a mostrar
     * @param {string} type - Tipo: success, error, warning, info
     * @param {Object} options - Opciones adicionales
     */
    show(message, type = 'info', options = {}) {
        const defaults = {
            title: this.getDefaultTitle(type),
            duration: this.getDefaultDuration(type),
            autoClose: true,
            closable: true,
            id: this.generateId()
        };

        const config = { ...defaults, ...options };
        
        // Prevenir duplicados
        if (this.notifications.has(config.id)) {
            return;
        }

        const notification = this.createNotification(message, type, config);
        this.container.appendChild(notification);
        this.notifications.set(config.id, notification);

        // Mostrar con animación
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        // Auto-cerrar si está configurado
        if (config.autoClose && config.duration > 0) {
            this.setupAutoClose(notification, config);
        }

        // Limpiar notificaciones antiguas (máximo 5)
        this.cleanupOldNotifications();

        return config.id;
    }

    /**
     * Crear elemento DOM de notificación
     */
    createNotification(message, type, config) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.dataset.id = config.id;

        const header = document.createElement('div');
        header.className = 'notification-header';

        const title = document.createElement('h6');
        title.className = 'notification-title';
        title.textContent = config.title;

        const closeBtn = document.createElement('button');
        closeBtn.className = 'notification-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.title = 'Cerrar';

        if (config.closable) {
            closeBtn.addEventListener('click', () => {
                this.hide(config.id);
            });
        } else {
            closeBtn.style.display = 'none';
        }

        header.appendChild(title);
        header.appendChild(closeBtn);

        const messageEl = document.createElement('p');
        messageEl.className = 'notification-message';
        messageEl.textContent = message;

        notification.appendChild(header);
        notification.appendChild(messageEl);

        // Agregar barra de progreso si auto-close
        if (config.autoClose && config.duration > 0) {
            const progress = document.createElement('div');
            progress.className = 'notification-progress';
            notification.appendChild(progress);
        }

        return notification;
    }

    /**
     * Configurar auto-cierre con barra de progreso
     */
    setupAutoClose(notification, config) {
        const progress = notification.querySelector('.notification-progress');
        
        if (progress) {
            progress.style.width = '100%';
            progress.style.transition = `width ${config.duration}ms linear`;
            
            // Iniciar animación de progreso
            setTimeout(() => {
                progress.style.width = '0%';
            }, 50);
        }

        // Cerrar después del tiempo especificado
        setTimeout(() => {
            if (this.notifications.has(config.id)) {
                this.hide(config.id);
            }
        }, config.duration);
    }

    /**
     * Ocultar notificación
     */
    hide(id) {
        if (!this.notifications.has(id)) return;

        const notification = this.notifications.get(id);
        notification.classList.add('hide');

        // Remover del DOM después de la animación
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            this.notifications.delete(id);
        }, 300);
    }

    /**
     * Limpiar notificaciones antiguas
     */
    cleanupOldNotifications() {
        const maxNotifications = 5;
        const notificationEls = this.container.querySelectorAll('.notification');
        
        if (notificationEls.length > maxNotifications) {
            const oldest = notificationEls[0];
            const id = oldest.dataset.id;
            this.hide(id);
        }
    }

    /**
     * Títulos por defecto según tipo
     */
    getDefaultTitle(type) {
        const titles = {
            success: 'Éxito',
            error: 'Error',
            warning: 'Advertencia',
            info: 'Información'
        };
        return titles[type] || 'Notificación';
    }

    /**
     * Duración por defecto según tipo
     */
    getDefaultDuration(type) {
        const durations = {
            success: 3000,
            error: 5000,
            warning: 4000,
            info: 3000
        };
        return durations[type] || 3000;
    }

    /**
     * Generar ID único
     */
    generateId() {
        return `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    // Métodos de conveniencia
    success(message, options = {}) {
        return this.show(message, 'success', options);
    }

    error(message, options = {}) {
        return this.show(message, 'error', { ...options, duration: 5000 });
    }

    warning(message, options = {}) {
        return this.show(message, 'warning', options);
    }

    info(message, options = {}) {
        return this.show(message, 'info', options);
    }

    /**
     * Cerrar todas las notificaciones
     */
    clear() {
        this.notifications.forEach((notification, id) => {
            this.hide(id);
        });
    }
}

// Crear instancia global
window.notificationSystem = new NotificationSystem();

// Sobrescribir funciones globales para usar nuestro sistema
window.showSuccess = function(message, options = {}) {
    return window.notificationSystem.success(message, options);
};

window.showError = function(message, options = {}) {
    return window.notificationSystem.error(message, options);
};

window.showWarning = function(message, options = {}) {
    return window.notificationSystem.warning(message, options);
};

window.showInfo = function(message, options = {}) {
    return window.notificationSystem.info(message, options);
};

// Mantener compatibilidad con código existente
window.showAlert = function(message, type = 'info') {
    switch(type) {
        case 'success':
            return window.showSuccess(message);
        case 'error':
            return window.showError(message);
        case 'warning':
            return window.showWarning(message);
        default:
            return window.showInfo(message);
    }
};

// Sistema de confirmación propio (NO usar confirm del navegador)
window.showConfirm = function(message, callback, options = {}) {
    const defaults = {
        title: 'Confirmar acción',
        confirmText: 'Confirmar',
        cancelText: 'Cancelar',
        type: 'warning'
    };
    
    const config = { ...defaults, ...options };
    
    // Crear modal de confirmación personalizado
    const modalId = 'confirmModal-' + Date.now();
    const modalHTML = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true" data-bs-backdrop="true" data-bs-keyboard="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-question-circle text-warning"></i>
                            ${config.title}
                        </h5>
                    </div>
                    <div class="modal-body">
                        <p>${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-action="cancel">
                            ${config.cancelText}
                        </button>
                        <button type="button" class="btn btn-warning" data-action="confirm">
                            ${config.confirmText}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Agregar modal al DOM
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modalElement = document.getElementById(modalId);
    
    // Variable para controlar que solo se ejecute una vez
    let modalClosed = false;
    
    // Función para cerrar y limpiar modal completamente
    function hideAndRemoveModal() {
        if (modalClosed) return; // Prevenir múltiples ejecuciones
        modalClosed = true;
        
        console.log('Iniciando limpieza de modal:', modalId);
        
        try {
            const modalInstance = bootstrap.Modal.getInstance(modalElement);
            if (modalInstance) {
                modalInstance.hide();
            }
            
            // Inmediatamente ocultar el modal
            modalElement.style.display = 'none';
            modalElement.classList.remove('show');
            modalElement.setAttribute('aria-hidden', 'true');
            
            // Limpiar backdrop inmediatamente y después del timeout
            const limpiarTodo = () => {
                // Remover el modal del DOM
                if (modalElement && modalElement.parentNode) {
                    modalElement.parentNode.removeChild(modalElement);
                }
                
                // Limpiar TODOS los backdrop que puedan existir - específicamente "modal-backdrop fade show"
                const backdrops = document.querySelectorAll('.modal-backdrop, .modal-backdrop.fade, .modal-backdrop.show, .modal-backdrop.fade.show');
                backdrops.forEach(backdrop => {
                    console.log('Removiendo backdrop:', backdrop.className);
                    backdrop.remove();
                });
                
                // Limpiar clases del body de forma agresiva
                document.body.classList.remove('modal-open');
                document.body.style.removeProperty('padding-right');
                document.body.style.removeProperty('overflow');
                document.body.style.removeProperty('position');
                
                // Asegurar que el scroll funcione
                document.documentElement.style.removeProperty('overflow');
                
                console.log('✅ Modal completamente limpiado:', modalId);
            };
            
            // Limpiar inmediatamente
            limpiarTodo();
            
            // Y también después de un delay para asegurar
            setTimeout(limpiarTodo, 150);
            setTimeout(limpiarTodo, 300);
            
        } catch (error) {
            console.error('Error cerrando modal:', error);
            // Limpieza de emergencia agresiva
            const emergencyClean = () => {
                if (modalElement && modalElement.parentNode) {
                modalElement.parentNode.removeChild(modalElement);
            }
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('padding-right');
            document.body.style.removeProperty('overflow');
                document.body.style.removeProperty('position');
                document.documentElement.style.removeProperty('overflow');
            };
            emergencyClean();
        }
    }
    
    // Configurar eventos de los botones
    modalElement.addEventListener('click', function(e) {
        e.stopPropagation();
        const action = e.target.dataset.action;
        if (action === 'confirm') {
            console.log('✅ Botón Confirmar presionado');
            if (callback) callback(true);
            hideAndRemoveModal();
        } else if (action === 'cancel') {
            console.log('❌ Botón Cancelar presionado - iniciando limpieza agresiva');
            if (callback) callback(false);
            hideAndRemoveModal();
            
            // Limpieza adicional específica para el botón cancelar
            setTimeout(() => {
                const backdropsPersistentes = document.querySelectorAll('.modal-backdrop.fade.show, .modal-backdrop.show, .modal-backdrop');
                if (backdropsPersistentes.length > 0) {
                    console.log('🚨 DETECTADO: backdrop persistente después de cancelar');
                    backdropsPersistentes.forEach(backdrop => {
                        console.log('🗑️ Eliminando backdrop persistente:', backdrop.className);
                        backdrop.remove();
                    });
                    
                    // Forzar limpieza del body
                    document.body.classList.remove('modal-open');
                    document.body.style.removeProperty('padding-right');
                    document.body.style.removeProperty('overflow');
                    document.body.style.removeProperty('position');
                    
                    console.log('✅ Limpieza post-cancelar completada');
                }
            }, 100);
        }
    });
    
    // Manejar click en el backdrop (fuera del modal)
    modalElement.addEventListener('click', function(e) {
        if (e.target === modalElement) {
            console.log('Click en backdrop - cerrando modal');
            if (callback) callback(false);
            hideAndRemoveModal();
        }
    });
    
    // Manejar tecla Escape
    modalElement.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            console.log('Tecla Escape presionada');
            if (callback) callback(false);
            hideAndRemoveModal();
        }
    });
    
    // Evento cuando el modal se oculta completamente
    modalElement.addEventListener('hidden.bs.modal', function() {
        console.log('Evento hidden.bs.modal disparado');
        hideAndRemoveModal();
    });
    
    // Mostrar modal
    try {
        const modal = new bootstrap.Modal(modalElement, {
            backdrop: true,
            keyboard: true,
            focus: true
        });
    modal.show();
        console.log('Modal mostrado:', modalId);
    } catch (error) {
        console.error('Error mostrando modal:', error);
        hideAndRemoveModal();
    }
    
    return true;
};

// Prevenir notificaciones duplicadas del navegador
if ('Notification' in window) {
    // Interceptar solicitudes de permisos de notificación
    const originalRequestPermission = Notification.requestPermission;
    Notification.requestPermission = function() {
        console.log('Solicitud de notificación del navegador interceptada');
        return Promise.resolve('denied');
    };
    
    // Interceptar creación de notificaciones
    const OriginalNotification = window.Notification;
    window.Notification = function(title, options = {}) {
        console.log('Notificación del navegador interceptada:', title);
        // Convertir a notificación propia
        window.showInfo(options.body || title);
        // Retornar un objeto mock para compatibilidad
        return {
            close: function() {},
            addEventListener: function() {},
            removeEventListener: function() {}
        };
    };
    
    // Copiar propiedades estáticas
    Object.setPrototypeOf(window.Notification, OriginalNotification);
    window.Notification.permission = 'denied';
    window.Notification.requestPermission = originalRequestPermission;
}

// Función global de emergencia para limpiar modales bloqueados
window.limpiarModalesBloqueados = function() {
    console.log('🧹 Limpiando modales bloqueados...');
    
    // Cerrar todos los modales activos
    const modalesAbiertos = document.querySelectorAll('.modal.show, .modal');
    modalesAbiertos.forEach(modal => {
        try {
        const instance = bootstrap.Modal.getInstance(modal);
        if (instance) {
            instance.hide();
                instance.dispose();
        }
        modal.style.display = 'none';
        modal.classList.remove('show');
            modal.setAttribute('aria-hidden', 'true');
        } catch (error) {
            console.warn('Error cerrando modal individual:', error);
        }
    });
    
    // Remover TODOS los backdrop de forma agresiva - específicamente "modal-backdrop fade show"
    const backdrops = document.querySelectorAll('.modal-backdrop, .modal-backdrop.fade, .modal-backdrop.show, .modal-backdrop.fade.show');
    backdrops.forEach(backdrop => {
        console.log('🧹 Limpiando backdrop encontrado:', backdrop.className);
        backdrop.remove();
    });
    
    // Limpiar clases del body de forma exhaustiva
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('padding-right');
    document.body.style.removeProperty('overflow');
    document.body.style.removeProperty('position');
    
    // También limpiar del documentElement
    document.documentElement.style.removeProperty('overflow');
    document.documentElement.classList.remove('modal-open');
    
    // Limpiar modales temporales de confirmación
    const modalesTemp = document.querySelectorAll('[id^="confirmModal-"]');
    modalesTemp.forEach(modal => {
        if (modal.parentNode) {
            modal.parentNode.removeChild(modal);
        }
    });
    
    // Forzar reflow para asegurar que los cambios se apliquen
    document.body.offsetHeight;
    
    console.log('✅ Limpieza de modales completada - página restaurada');
};

// Función de acceso rápido para el usuario en caso de emergencia
window.fixModal = window.limpiarModalesBloqueados;

// Función súper específica para eliminar "modal-backdrop fade show"
window.eliminarBackdropEspecifico = function() {
    console.log('🎯 Eliminando específicamente: modal-backdrop fade show');
    
    // Buscar todos los elementos que coincidan con las clases problemáticas
    const selectores = [
        '.modal-backdrop.fade.show',
        '.modal-backdrop.show',
        '.modal-backdrop.fade',
        '.modal-backdrop'
    ];
    
    let elementosEliminados = 0;
    
    selectores.forEach(selector => {
        const elementos = document.querySelectorAll(selector);
        elementos.forEach(elemento => {
            console.log(`🗑️ Eliminando elemento:`, elemento.className);
            elemento.remove();
            elementosEliminados++;
        });
    });
    
    // Limpiar clases del body específicamente relacionadas con modales
    const clasesBody = ['modal-open'];
    clasesBody.forEach(clase => {
        if (document.body.classList.contains(clase)) {
            document.body.classList.remove(clase);
            console.log(`🧹 Removida clase del body: ${clase}`);
        }
    });
    
    // Limpiar estilos específicos
    const estilosLimpiar = ['padding-right', 'overflow', 'position'];
    estilosLimpiar.forEach(estilo => {
        if (document.body.style[estilo]) {
            document.body.style.removeProperty(estilo);
            console.log(`🎨 Removido estilo del body: ${estilo}`);
        }
    });
    
    console.log(`✅ Limpieza específica completada. Elementos eliminados: ${elementosEliminados}`);
    return elementosEliminados;
};

// Observador para detectar y eliminar modal-backdrop automáticamente
let backdropObserver = null;

function iniciarObservadorBackdrop() {
    if (backdropObserver) return;
    
    backdropObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && node.classList && node.classList.contains('modal-backdrop')) {
                        console.log('🔍 Modal backdrop detectado automáticamente:', node.className);
                        
                        // Dar tiempo para que Bootstrap maneje el modal normalmente
                        setTimeout(() => {
                            if (document.body.contains(node)) {
                                console.log('🗑️ Eliminando backdrop persistente automáticamente');
                                node.remove();
                                
                                // Limpiar estado del body
                                document.body.classList.remove('modal-open');
                                document.body.style.removeProperty('padding-right');
                                document.body.style.removeProperty('overflow');
                                document.body.style.removeProperty('position');
                            }
                        }, 5000); // Esperar 5 segundos antes de limpiar automáticamente
                    }
                });
            }
        });
    });
    
    backdropObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    console.log('👀 Observador de backdrop iniciado');
}

// Limpieza preventiva al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    // Iniciar observador de backdrop
    iniciarObservadorBackdrop();
    
    // Limpiar cualquier modal residual al cargar la página
    setTimeout(() => {
        const backdrops = document.querySelectorAll('.modal-backdrop');
        if (backdrops.length > 0) {
            console.log('Limpiando backdrop residual al cargar página');
            backdrops.forEach(backdrop => backdrop.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('padding-right');
            document.body.style.removeProperty('overflow');
        }
    }, 100);
});

// También limpiar en el evento de carga completa
window.addEventListener('load', function() {
    setTimeout(() => {
        const backdrops = document.querySelectorAll('.modal-backdrop');
        if (backdrops.length > 0) {
            console.log('Limpieza final de backdrop en window.load');
            window.limpiarModalesBloqueados();
        }
    }, 200);
});

// Función de limpieza periódica para detectar backdrops huérfanos
function limpiezaPeriodicaBackdrops() {
    const backdrops = document.querySelectorAll('.modal-backdrop');
    if (backdrops.length > 0) {
        // Verificar si hay algún modal realmente abierto
        const modalesAbiertos = document.querySelectorAll('.modal.show');
        if (modalesAbiertos.length === 0) {
            console.log('🧹 Detectados backdrops huérfanos, limpiando...');
            backdrops.forEach(backdrop => {
                console.log('🗑️ Eliminando backdrop huérfano:', backdrop.className);
                backdrop.remove();
            });
            
            // Limpiar estado del body
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('padding-right');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('position');
        }
    }
}

// Ejecutar limpieza periódica cada 3 segundos
setInterval(limpiezaPeriodicaBackdrops, 3000);

console.log('✅ Sistema de notificaciones propias inicializado con limpieza automática');
