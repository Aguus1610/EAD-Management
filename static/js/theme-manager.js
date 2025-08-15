/**
 * SISTEMA DE GESTIÓN DE TEMAS AVANZADO
 * ===================================
 * 
 * Maneja el cambio de temas, persistencia y efectos interactivos
 */

class ThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.themes = {
            light: {
                name: 'Claro',
                icon: '☀️'
            },
            dark: {
                name: 'Oscuro', 
                icon: '🌙'
            },
            corporate: {
                name: 'Corporativo',
                icon: '💼'
            },
            nature: {
                name: 'Naturaleza',
                icon: '🌿'
            }
        };
        
        this.init();
    }
    
    init() {
        // No crear el selector automáticamente - solo aplicar tema
        this.applyTheme(this.currentTheme);
        this.bindEvents();
        this.initAnimations();
    }
    
    createThemeSelector() {
        // Crear el selector de temas si no existe
        if (!document.querySelector('.theme-selector')) {
            const selector = document.createElement('div');
            selector.className = 'theme-selector fade-in';
            
            Object.keys(this.themes).forEach(theme => {
                const btn = document.createElement('button');
                btn.className = `theme-btn ${theme === this.currentTheme ? 'active' : ''}`;
                btn.setAttribute('data-theme', theme);
                btn.setAttribute('data-title', this.themes[theme].name);
                btn.innerHTML = this.themes[theme].icon;
                btn.onclick = () => this.setTheme(theme);
                selector.appendChild(btn);
            });
            
            document.body.appendChild(selector);
        }
    }
    
    setTheme(theme) {
        if (this.themes[theme]) {
            this.currentTheme = theme;
            this.applyTheme(theme);
            this.updateActiveButton(theme);
            localStorage.setItem('theme', theme);
            
            // Trigger evento personalizado
            document.dispatchEvent(new CustomEvent('themeChanged', {
                detail: { theme, themeName: this.themes[theme].name }
            }));
            
            this.showThemeNotification(this.themes[theme].name);
        }
    }
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        
        // Actualizar meta theme-color para PWA
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (metaThemeColor) {
            const colors = {
                light: '#667eea',
                dark: '#2d3748', 
                corporate: '#3182ce',
                nature: '#38a169'
            };
            metaThemeColor.setAttribute('content', colors[theme] || colors.light);
        }
    }
    
    updateActiveButton(theme) {
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-theme') === theme) {
                btn.classList.add('active');
            }
        });
    }
    
    showThemeNotification(themeName) {
        // Crear notificación temporal
        const notification = document.createElement('div');
        notification.className = 'theme-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-palette"></i>
                Tema cambiado a: <strong>${themeName}</strong>
            </div>
        `;
        
        // Estilos inline para la notificación
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: var(--bg-primary);
            color: var(--text-primary);
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: var(--shadow);
            border: 1px solid var(--border-color);
            z-index: 1060;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        // Mostrar con animación
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Ocultar después de 3 segundos
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    bindEvents() {
        // Escuchar cambios de tema del sistema
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addListener((e) => {
                if (!localStorage.getItem('theme')) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
        
        // Atajos de teclado para cambiar temas
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.altKey) {
                switch(e.key) {
                    case '1':
                        e.preventDefault();
                        this.setTheme('light');
                        break;
                    case '2':
                        e.preventDefault();
                        this.setTheme('dark');
                        break;
                    case '3':
                        e.preventDefault();
                        this.setTheme('corporate');
                        break;
                    case '4':
                        e.preventDefault();
                        this.setTheme('nature');
                        break;
                }
            }
        });
    }
    
    initAnimations() {
        // Añadir animaciones de entrada a elementos
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                }
            });
        });
        
        // Observar tarjetas y tablas
        document.querySelectorAll('.card, .table, .alert').forEach(el => {
            observer.observe(el);
        });
    }
    
    // Método para obtener tema actual
    getCurrentTheme() {
        return this.currentTheme;
    }
    
    // Método para verificar si es tema oscuro
    isDarkTheme() {
        return this.currentTheme === 'dark';
    }
}

/**
 * SISTEMA DE INTERACCIONES MEJORADAS
 * =================================
 */

class InteractionManager {
    constructor() {
        this.init();
    }
    
    init() {
        this.enhanceButtons();
        this.enhanceCards();
        this.enhanceForms();
        this.addLoadingStates();
        this.initTooltips();
        this.initMobileMenu();
    }
    
    enhanceButtons() {
        // Añadir efectos de clic a botones
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn')) {
                this.createRippleEffect(e.target, e);
            }
        });
    }
    
    createRippleEffect(button, event) {
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            transform: scale(0);
            animation: ripple 0.6s linear;
            pointer-events: none;
        `;
        
        // Asegurar posición relativa en el botón
        if (getComputedStyle(button).position === 'static') {
            button.style.position = 'relative';
        }
        
        button.style.overflow = 'hidden';
        button.appendChild(ripple);
        
        // Remover el ripple después de la animación
        setTimeout(() => ripple.remove(), 600);
    }
    
    enhanceCards() {
        // Añadir efectos hover a las tarjetas
        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-5px) scale(1.02)';
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0) scale(1)';
            });
        });
    }
    
    enhanceForms() {
        // Mejorar experiencia de formularios
        document.querySelectorAll('.form-control, .form-select').forEach(input => {
            // Efecto focus mejorado
            input.addEventListener('focus', () => {
                input.parentElement.classList.add('focused');
            });
            
            input.addEventListener('blur', () => {
                input.parentElement.classList.remove('focused');
            });
            
            // Validación en tiempo real
            input.addEventListener('input', () => {
                this.validateField(input);
            });
        });
    }
    
    validateField(field) {
        const isValid = field.checkValidity();
        field.classList.toggle('is-valid', isValid && field.value);
        field.classList.toggle('is-invalid', !isValid && field.value);
    }
    
    addLoadingStates() {
        // Añadir estados de carga a formularios
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn && !submitBtn.classList.contains('btn-loading')) {
                    submitBtn.classList.add('btn-loading');
                    submitBtn.disabled = true;
                    
                    // Restaurar después de 3 segundos si no hay redirección
                    setTimeout(() => {
                        submitBtn.classList.remove('btn-loading');
                        submitBtn.disabled = false;
                    }, 3000);
                }
            });
        });
    }
    
    initTooltips() {
        // Inicializar tooltips personalizados
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(element => {
            if (typeof bootstrap !== 'undefined') {
                new bootstrap.Tooltip(element);
            }
        });
    }
    
    initMobileMenu() {
        // Crear botón hamburguesa para móviles
        if (window.innerWidth <= 768) {
            this.createMobileMenuButton();
        }
        
        // Escuchar cambios de tamaño de ventana
        window.addEventListener('resize', () => {
            if (window.innerWidth <= 768) {
                this.createMobileMenuButton();
            } else {
                this.removeMobileMenuButton();
            }
        });
    }
    
    createMobileMenuButton() {
        if (!document.querySelector('.mobile-menu-btn')) {
            const menuBtn = document.createElement('button');
            menuBtn.className = 'mobile-menu-btn';
            menuBtn.innerHTML = '<i class="fas fa-bars"></i>';
            menuBtn.style.cssText = `
                position: fixed;
                top: 20px;
                left: 20px;
                z-index: 1050;
                background: var(--bg-accent);
                color: white;
                border: none;
                border-radius: 8px;
                width: 50px;
                height: 50px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                box-shadow: var(--shadow);
            `;
            
            menuBtn.onclick = () => this.toggleMobileMenu();
            document.body.appendChild(menuBtn);
        }
    }
    
    removeMobileMenuButton() {
        const menuBtn = document.querySelector('.mobile-menu-btn');
        if (menuBtn) {
            menuBtn.remove();
        }
    }
    
    toggleMobileMenu() {
        const sidebar = document.querySelector('.sidebar');
        const overlay = this.getOrCreateOverlay();
        
        sidebar.classList.toggle('show');
        overlay.classList.toggle('show');
    }
    
    getOrCreateOverlay() {
        let overlay = document.querySelector('.sidebar-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'sidebar-overlay';
            overlay.onclick = () => this.toggleMobileMenu();
            document.body.appendChild(overlay);
        }
        return overlay;
    }
}

/**
 * SISTEMA DE NOTIFICACIONES
 * ========================
 */

class NotificationSystem {
    constructor() {
        this.container = this.createContainer();
        this.queue = [];
        this.maxNotifications = 5;
    }
    
    createContainer() {
        const container = document.createElement('div');
        container.className = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1070;
            max-width: 350px;
        `;
        document.body.appendChild(container);
        return container;
    }
    
    show(message, type = 'info', duration = 5000) {
        const notification = this.createNotification(message, type);
        
        // Añadir a la cola
        this.queue.push(notification);
        
        // Limitar número de notificaciones
        if (this.queue.length > this.maxNotifications) {
            const oldest = this.queue.shift();
            if (oldest && oldest.parentNode) {
                this.removeNotification(oldest);
            }
        }
        
        // Mostrar notificación
        this.container.appendChild(notification);
        
        // Animación de entrada
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Auto-ocultar
        if (duration > 0) {
            setTimeout(() => {
                this.removeNotification(notification);
            }, duration);
        }
        
        return notification;
    }
    
    createNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        
        const colors = {
            success: 'var(--success)',
            error: 'var(--danger)',
            warning: 'var(--warning)',
            info: 'var(--info)'
        };
        
        notification.style.cssText = `
            background: var(--bg-primary);
            color: var(--text-primary);
            border-left: 4px solid ${colors[type] || colors.info};
            padding: 15px 20px;
            margin-bottom: 10px;
            border-radius: 8px;
            box-shadow: var(--shadow);
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
            cursor: pointer;
        `;
        
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fas ${icons[type] || icons.info}" style="color: ${colors[type] || colors.info};"></i>
                <span style="flex: 1;">${message}</span>
                <i class="fas fa-times" style="opacity: 0.5; cursor: pointer;"></i>
            </div>
        `;
        
        // Cerrar al hacer clic
        notification.onclick = () => this.removeNotification(notification);
        
        return notification;
    }
    
    removeNotification(notification) {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
            // Remover de la cola
            const index = this.queue.indexOf(notification);
            if (index > -1) {
                this.queue.splice(index, 1);
            }
        }, 300);
    }
    
    // Métodos de conveniencia
    success(message, duration) {
        return this.show(message, 'success', duration);
    }
    
    error(message, duration) {
        return this.show(message, 'error', duration);
    }
    
    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }
    
    info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

// Agregar estilos para animación de ripple
const rippleStyles = document.createElement('style');
rippleStyles.textContent = `
    @keyframes ripple {
        to { transform: scale(4); opacity: 0; }
    }
`;
document.head.appendChild(rippleStyles);

// Inicializar sistemas al cargar el DOM
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar gestores (solo si no existen)
    if (!window.themeManager) {
        window.themeManager = new ThemeManager();
    }
    if (!window.interactionManager) {
        window.interactionManager = new InteractionManager();
    }
    // NotificationSystem ya se inicializa en notifications.js
    
    // Notificación de bienvenida eliminada para evitar molestias
    
    // Añadir clases de animación a elementos existentes
    document.querySelectorAll('.card, .alert, .table').forEach((el, index) => {
        setTimeout(() => {
            el.classList.add('fade-in');
        }, index * 100);
    });
});

// Exportar para uso global
window.ThemeManager = ThemeManager;
window.InteractionManager = InteractionManager;
window.NotificationSystem = NotificationSystem;
