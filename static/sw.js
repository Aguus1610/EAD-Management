/**
 * SERVICE WORKER - GESTIÓN DE TALLER PWA
 * ====================================
 * 
 * Maneja caching, notificaciones push y funcionalidad offline
 */

const CACHE_NAME = 'gestion-taller-v2.0.0';
const STATIC_CACHE = 'static-v2.0.0';
const DYNAMIC_CACHE = 'dynamic-v2.0.0';

// Archivos que se cachean inmediatamente al instalar
const STATIC_FILES = [
    '/',
    '/static/css/themes.css',
    '/static/js/theme-manager.js',
    '/static/js/table-sort.js',
    '/static/manifest.json',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

// Rutas que se cachean dinámicamente
const DYNAMIC_ROUTES = [
    '/clientes',
    '/equipos', 
    '/mantenimientos',
    '/repuestos',
    '/reportes'
];

// Instalación del Service Worker
self.addEventListener('install', event => {
    console.log('🔧 Service Worker: Instalando...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('📦 Service Worker: Cacheando archivos estáticos');
                return cache.addAll(STATIC_FILES);
            })
            .catch(error => {
                console.error('❌ Error cacheando archivos estáticos:', error);
            })
    );
    
    // Forzar activación inmediata
    self.skipWaiting();
});

// Activación del Service Worker
self.addEventListener('activate', event => {
    console.log('🚀 Service Worker: Activando...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    // Eliminar caches antiguos
                    if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                        console.log('🗑️ Service Worker: Eliminando cache antiguo:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            // Tomar control inmediato de todas las páginas
            return self.clients.claim();
        })
    );
});

// Interceptar requests (estrategia cache-first para estáticos, network-first para dinámicos)
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Ignorar requests no-HTTP y chrome-extension
    if (!url.protocol.startsWith('http') || url.protocol.startsWith('chrome-extension')) {
        return;
    }
    
    // Estrategia para archivos estáticos
    if (isStaticFile(request.url)) {
        event.respondWith(cacheFirst(request));
    }
    // Estrategia para rutas dinámicas de la app
    else if (isDynamicRoute(url.pathname)) {
        event.respondWith(networkFirst(request));
    }
    // Estrategia para API calls
    else if (url.pathname.startsWith('/api/')) {
        event.respondWith(apiStrategy(request));
    }
    // Default: network first
    else {
        event.respondWith(networkFirst(request));
    }
});

// Estrategia Cache First (para archivos estáticos)
async function cacheFirst(request) {
    try {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.error('❌ Cache First failed:', error);
        return getOfflinePage();
    }
}

// Estrategia Network First (para contenido dinámico)
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('🌐 Network failed, serving from cache:', request.url);
        
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        return getOfflinePage();
    }
}

// Estrategia especial para API calls
async function apiStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Solo cachear respuestas GET exitosas
            if (request.method === 'GET') {
                const cache = await caches.open(DYNAMIC_CACHE);
                cache.put(request, networkResponse.clone());
            }
        }
        
        return networkResponse;
    } catch (error) {
        // Para API calls offline, devolver datos cacheados solo para GET
        if (request.method === 'GET') {
            const cachedResponse = await caches.match(request);
            if (cachedResponse) {
                return cachedResponse;
            }
        }
        
        // Para POST/PUT/DELETE offline, devolver error JSON
        return new Response(
            JSON.stringify({
                error: 'Sin conexión a internet',
                offline: true,
                timestamp: new Date().toISOString()
            }),
            {
                status: 503,
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );
    }
}

// Página offline de fallback
async function getOfflinePage() {
    const offlineHTML = `
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Sin Conexión - Gestión Taller</title>
            <style>
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    padding: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                }
                .offline-container {
                    max-width: 500px;
                    padding: 2rem;
                }
                .offline-icon {
                    font-size: 4rem;
                    margin-bottom: 1rem;
                }
                h1 { margin-bottom: 1rem; }
                p { opacity: 0.9; margin-bottom: 2rem; }
                .retry-btn {
                    background: rgba(255,255,255,0.2);
                    border: 2px solid rgba(255,255,255,0.3);
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 1rem;
                    transition: all 0.3s ease;
                }
                .retry-btn:hover {
                    background: rgba(255,255,255,0.3);
                    transform: translateY(-2px);
                }
            </style>
        </head>
        <body>
            <div class="offline-container">
                <div class="offline-icon">📡</div>
                <h1>Sin Conexión a Internet</h1>
                <p>No se puede conectar al servidor. Revisa tu conexión e intenta nuevamente.</p>
                <button class="retry-btn" onclick="window.location.reload()">
                    🔄 Reintentar
                </button>
            </div>
            <script>
                // Auto-retry cuando se recupere la conexión
                window.addEventListener('online', () => {
                    window.location.reload();
                });
            </script>
        </body>
        </html>
    `;
    
    return new Response(offlineHTML, {
        headers: {
            'Content-Type': 'text/html'
        }
    });
}

// Utilidades
function isStaticFile(url) {
    return url.includes('/static/') || 
           url.includes('bootstrap') || 
           url.includes('fontawesome') || 
           url.includes('chart.js') ||
           url.includes('googleapis.com');
}

function isDynamicRoute(pathname) {
    return DYNAMIC_ROUTES.some(route => pathname.startsWith(route));
}

// Manejo de notificaciones push
self.addEventListener('push', event => {
    console.log('📱 Push notification received');
    
    const options = {
        body: 'Tienes actualizaciones pendientes en tu taller',
        icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🔧</text></svg>',
        badge: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🔧</text></svg>',
        vibrate: [200, 100, 200],
        tag: 'taller-update',
        requireInteraction: true,
        actions: [
            {
                action: 'view',
                title: 'Ver Detalles',
                icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>'
            },
            {
                action: 'dismiss',
                title: 'Descartar',
                icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>'
            }
        ]
    };
    
    if (event.data) {
        try {
            const data = event.data.json();
            options.body = data.message || options.body;
            options.title = data.title || 'Gestión de Taller';
        } catch (e) {
            console.warn('No se pudo parsear los datos de la notificación');
        }
    }
    
    event.waitUntil(
        self.registration.showNotification('Gestión de Taller', options)
    );
});

// Manejo de clics en notificaciones
self.addEventListener('notificationclick', event => {
    console.log('🔔 Notification clicked:', event.action);
    
    event.notification.close();
    
    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow('/')
        );
    } else if (event.action === 'dismiss') {
        // Solo cerrar la notificación
        return;
    } else {
        // Click en el cuerpo de la notificación
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Sync en background (para operaciones offline)
self.addEventListener('sync', event => {
    console.log('🔄 Background sync:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    try {
        // Aquí puedes implementar lógica para sincronizar datos offline
        console.log('📤 Sincronizando datos pendientes...');
        
        // Ejemplo: enviar datos guardados localmente
        const pendingData = await getPendingData();
        if (pendingData.length > 0) {
            for (const data of pendingData) {
                try {
                    await fetch('/api/sync', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                    await removePendingData(data.id);
                } catch (error) {
                    console.error('Error sincronizando:', error);
                }
            }
        }
        
        console.log('✅ Sincronización completada');
    } catch (error) {
        console.error('❌ Error en sincronización:', error);
    }
}

// Funciones auxiliares para datos pendientes (implementar según necesidad)
async function getPendingData() {
    // Implementar lógica para obtener datos pendientes del IndexedDB
    return [];
}

async function removePendingData(id) {
    // Implementar lógica para remover datos sincronizados del IndexedDB
    console.log('Removed pending data:', id);
}

// Limpieza periódica de cache
setInterval(async () => {
    const cache = await caches.open(DYNAMIC_CACHE);
    const keys = await cache.keys();
    
    // Mantener solo los últimos 50 elementos en cache dinámico
    if (keys.length > 50) {
        const keysToDelete = keys.slice(0, keys.length - 50);
        await Promise.all(keysToDelete.map(key => cache.delete(key)));
        console.log(`🧹 Limpieza de cache: eliminados ${keysToDelete.length} elementos`);
    }
}, 1000 * 60 * 30); // Cada 30 minutos
