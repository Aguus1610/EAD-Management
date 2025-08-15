/**
 * VALIDACIÓN DE FORMULARIOS UNIVERSAL
 * ===================================
 * Sistema robusto de validación para todos los formularios
 */

class FormValidator {
    constructor() {
        this.rules = {};
        this.messages = {
            required: 'Este campo es obligatorio',
            email: 'Ingresa un email válido',
            min: 'Mínimo {min} caracteres',
            max: 'Máximo {max} caracteres',
            number: 'Debe ser un número válido',
            positive: 'Debe ser un número positivo',
            date: 'Fecha inválida',
            match: 'Los campos no coinciden'
        };
        this.init();
    }

    init() {
        // Aplicar validación a todos los formularios
        document.querySelectorAll('form').forEach(form => {
            if (!form.dataset.validationEnabled) {
                this.enableFormValidation(form);
                form.dataset.validationEnabled = 'true';
            }
        });
    }

    enableFormValidation(form) {
        // Validación en tiempo real
        form.addEventListener('input', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
                this.validateField(e.target);
            }
        });

        // Validación al enviar
        form.addEventListener('submit', (e) => {
            if (!this.validateForm(form)) {
                e.preventDefault();
                this.showFormErrors(form);
            }
        });
    }

    validateField(field) {
        const errors = [];
        const value = field.value.trim();
        const rules = this.getFieldRules(field);

        // Limpiar errores previos
        this.clearFieldError(field);

        // Aplicar reglas
        if (rules.required && !value) {
            errors.push(this.messages.required);
        }

        if (value && rules.email && !this.isValidEmail(value)) {
            errors.push(this.messages.email);
        }

        if (value && rules.min && value.length < rules.min) {
            errors.push(this.messages.min.replace('{min}', rules.min));
        }

        if (value && rules.max && value.length > rules.max) {
            errors.push(this.messages.max.replace('{max}', rules.max));
        }

        if (value && rules.number && !this.isValidNumber(value)) {
            errors.push(this.messages.number);
        }

        if (value && rules.positive && parseFloat(value) <= 0) {
            errors.push(this.messages.positive);
        }

        if (value && rules.date && !this.isValidDate(value)) {
            errors.push(this.messages.date);
        }

        if (rules.match && !this.fieldsMatch(field, rules.match)) {
            errors.push(this.messages.match);
        }

        // Mostrar errores
        if (errors.length > 0) {
            this.showFieldError(field, errors[0]);
            return false;
        }

        this.showFieldSuccess(field);
        return true;
    }

    validateForm(form) {
        let isValid = true;
        const fields = form.querySelectorAll('input, textarea, select');
        
        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    getFieldRules(field) {
        const rules = {};

        // Reglas desde atributos HTML5
        if (field.required) rules.required = true;
        if (field.type === 'email') rules.email = true;
        if (field.type === 'number') rules.number = true;
        if (field.type === 'date') rules.date = true;
        if (field.min) rules.min = parseInt(field.min);
        if (field.max) rules.max = parseInt(field.max);
        if (field.minLength) rules.min = field.minLength;
        if (field.maxLength) rules.max = field.maxLength;

        // Reglas desde data attributes
        if (field.dataset.positive) rules.positive = true;
        if (field.dataset.match) rules.match = field.dataset.match;

        return rules;
    }

    showFieldError(field, message) {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');

        // Buscar o crear elemento de error
        let errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'invalid-feedback';
            field.parentNode.appendChild(errorElement);
        }

        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }

    showFieldSuccess(field) {
        field.classList.add('is-valid');
        field.classList.remove('is-invalid');

        const errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid', 'is-valid');
        
        const errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }

    showFormErrors(form) {
        const invalidFields = form.querySelectorAll('.is-invalid');
        if (invalidFields.length > 0) {
            // Scroll al primer campo con error
            invalidFields[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
            invalidFields[0].focus();

            // Mostrar notificación general
            if (window.showError) {
                window.showError(`Por favor corrige ${invalidFields.length} error(es) en el formulario`);
            }
        }
    }

    // Métodos de validación
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    isValidNumber(value) {
        return !isNaN(parseFloat(value)) && isFinite(value);
    }

    isValidDate(dateString) {
        const date = new Date(dateString);
        return date instanceof Date && !isNaN(date);
    }

    fieldsMatch(field, matchFieldSelector) {
        const form = field.closest('form');
        const matchField = form.querySelector(matchFieldSelector);
        return matchField && field.value === matchField.value;
    }

    // Métodos públicos para uso externo
    addCustomRule(fieldSelector, validator, message) {
        // Implementar reglas personalizadas
        document.querySelectorAll(fieldSelector).forEach(field => {
            field.addEventListener('input', () => {
                if (!validator(field.value)) {
                    this.showFieldError(field, message);
                } else {
                    this.showFieldSuccess(field);
                }
            });
        });
    }

    validateFieldNow(fieldSelector) {
        const field = document.querySelector(fieldSelector);
        if (field) {
            return this.validateField(field);
        }
        return false;
    }
}

// Inicializar validador global
window.formValidator = new FormValidator();

// Reglas específicas para campos comunes
document.addEventListener('DOMContentLoaded', function() {
    // Validación de passwords
    window.formValidator.addCustomRule(
        'input[type="password"][data-confirm]',
        function(value) {
            const confirmField = document.querySelector('input[name="confirm_password"]');
            return confirmField && value === confirmField.value;
        },
        'Las contraseñas no coinciden'
    );

    // Validación de precios
    window.formValidator.addCustomRule(
        'input[data-price]',
        function(value) {
            return /^\d+(\.\d{1,2})?$/.test(value);
        },
        'Formato de precio inválido (ej: 100.50)'
    );

    // Validación de teléfonos
    window.formValidator.addCustomRule(
        'input[data-phone]',
        function(value) {
            return /^[\d\s\-\+\(\)]{10,15}$/.test(value);
        },
        'Número de teléfono inválido'
    );

    console.log('✅ Sistema de validación de formularios cargado');
});
