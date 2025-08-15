/**
 * LOADING STATES - Sistema de estados de carga para botones y acciones
 * ===================================================================
 */

class LoadingStateManager {
    constructor() {
        this.loadingButtons = new Set();
        this.originalTexts = new Map();
        this.init();
    }

    init() {
        // Aplicar automáticamente a todos los formularios
        document.addEventListener('submit', (e) => {
            if (e.target.tagName === 'FORM') {
                this.handleFormSubmit(e.target);
            }
        });

        // Aplicar a botones con data-loading
        document.addEventListener('click', (e) => {
            if (e.target.dataset.loading) {
                this.setButtonLoading(e.target, e.target.dataset.loading);
            }
        });

        // Auto-aplicar a botones de submit
        document.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(btn => {
            if (!btn.dataset.noLoading) {
                btn.dataset.autoLoading = 'true';
            }
        });

        console.log('✅ Sistema de loading states inicializado');
    }

    handleFormSubmit(form) {
        const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
        
        if (submitButton && submitButton.dataset.autoLoading) {
            const loadingText = submitButton.dataset.loadingText || 'Procesando...';
            this.setButtonLoading(submitButton, loadingText);

            // Auto-restaurar después de 10 segundos como fallback
            setTimeout(() => {
                this.removeButtonLoading(submitButton);
            }, 10000);
        }

        // Deshabilitar todos los botones del formulario
        form.querySelectorAll('button, input[type="submit"]').forEach(btn => {
            if (btn.type !== 'submit') {
                btn.disabled = true;
                btn.dataset.wasDisabled = 'true';
            }
        });
    }

    setButtonLoading(button, loadingText = 'Cargando...') {
        if (this.loadingButtons.has(button)) return;

        // Guardar estado original
        this.originalTexts.set(button, {
            innerHTML: button.innerHTML,
            disabled: button.disabled,
            className: button.className
        });

        // Aplicar estado de carga
        button.disabled = true;
        button.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            ${loadingText}
        `;
        button.classList.add('btn-loading');

        this.loadingButtons.add(button);
    }

    removeButtonLoading(button) {
        if (!this.loadingButtons.has(button)) return;

        const original = this.originalTexts.get(button);
        if (original) {
            button.innerHTML = original.innerHTML;
            button.disabled = original.disabled;
            button.className = original.className;
        }

        this.loadingButtons.delete(button);
        this.originalTexts.delete(button);
    }

    setElementLoading(element, message = 'Cargando...') {
        element.innerHTML = `
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <div class="mt-2">${message}</div>
            </div>
        `;
    }

    // Métodos para AJAX y operaciones asíncronas
    async performAsyncAction(button, asyncFunction, options = {}) {
        const loadingText = options.loadingText || 'Procesando...';
        const successText = options.successText || '¡Completado!';
        const errorText = options.errorText || 'Error';

        try {
            this.setButtonLoading(button, loadingText);
            
            const result = await asyncFunction();
            
            // Mostrar éxito brevemente
            if (options.showSuccess) {
                button.innerHTML = `<i class="fas fa-check me-1"></i> ${successText}`;
                button.classList.add('btn-success');
                
                setTimeout(() => {
                    this.removeButtonLoading(button);
                }, 1500);
            } else {
                this.removeButtonLoading(button);
            }

            return result;

        } catch (error) {
            // Mostrar error brevemente
            button.innerHTML = `<i class="fas fa-times me-1"></i> ${errorText}`;
            button.classList.add('btn-danger');
            
            setTimeout(() => {
                this.removeButtonLoading(button);
            }, 2000);

            throw error;
        }
    }

    // Para formularios con AJAX
    handleAjaxForm(form, submitHandler) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitButton = form.querySelector('button[type="submit"]');
            
            try {
                await this.performAsyncAction(submitButton, async () => {
                    return await submitHandler(new FormData(form));
                }, {
                    loadingText: 'Guardando...',
                    successText: 'Guardado',
                    showSuccess: true
                });

                // Reset form si el envío fue exitoso
                if (form.dataset.resetOnSuccess !== 'false') {
                    form.reset();
                    // Limpiar validaciones
                    form.querySelectorAll('.is-valid, .is-invalid').forEach(field => {
                        field.classList.remove('is-valid', 'is-invalid');
                    });
                }

            } catch (error) {
                console.error('Error en formulario AJAX:', error);
                if (window.showError) {
                    window.showError('Error al procesar el formulario');
                }
            }
        });
    }

    // Estados de carga para elementos específicos
    setTableLoading(tableElement, message = 'Cargando datos...') {
        const tbody = tableElement.querySelector('tbody');
        if (tbody) {
            const colCount = tableElement.querySelectorAll('thead th').length || 3;
            tbody.innerHTML = `
                <tr>
                    <td colspan="${colCount}" class="text-center p-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Cargando...</span>
                        </div>
                        <div class="mt-2">${message}</div>
                    </td>
                </tr>
            `;
        }
    }

    setCardLoading(cardElement, message = 'Cargando...') {
        const cardBody = cardElement.querySelector('.card-body');
        if (cardBody) {
            cardBody.innerHTML = `
                <div class="text-center p-4">
                    <div class="spinner-border text-primary" role="status"></div>
                    <div class="mt-2">${message}</div>
                </div>
            `;
        }
    }

    // Progreso para operaciones largas
    showProgress(element, progress, message = '') {
        element.innerHTML = `
            <div class="text-center p-3">
                <div class="progress mb-2">
                    <div class="progress-bar" role="progressbar" 
                         style="width: ${progress}%" 
                         aria-valuenow="${progress}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                        ${progress}%
                    </div>
                </div>
                ${message ? `<div class="small text-muted">${message}</div>` : ''}
            </div>
        `;
    }
}

// Inicializar manager global
window.loadingManager = new LoadingStateManager();

// Funciones de conveniencia
window.setButtonLoading = (button, text) => window.loadingManager.setButtonLoading(button, text);
window.removeButtonLoading = (button) => window.loadingManager.removeButtonLoading(button);
window.setTableLoading = (table, message) => window.loadingManager.setTableLoading(table, message);
window.setCardLoading = (card, message) => window.loadingManager.setCardLoading(card, message);

// Auto-restaurar estados después de navigation
window.addEventListener('pageshow', function(e) {
    // Restaurar todos los botones de loading
    window.loadingManager.loadingButtons.forEach(button => {
        window.loadingManager.removeButtonLoading(button);
    });
    
    // Re-habilitar botones deshabilitados
    document.querySelectorAll('button[data-was-disabled]').forEach(btn => {
        btn.disabled = false;
        btn.removeAttribute('data-was-disabled');
    });
});

console.log('🔄 Sistema de loading states cargado');
