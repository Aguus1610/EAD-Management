/**
 * CACHE MANAGER - Sistema de cache del lado cliente
 * ===============================================
 */

class CacheManager {
    constructor() {
        this.cache = new Map();
        this.maxSize = 100; // Máximo 100 entradas
        this.defaultTTL = 5 * 60 * 1000; // 5 minutos por defecto
        this.stats = {
            hits: 0,
            misses: 0,
            sets: 0,
            evictions: 0
        };
        
        this.init();
    }

    init() {
        // Limpiar cache expirado cada 2 minutos
        setInterval(() => {
            this.cleanExpired();
        }, 2 * 60 * 1000);

        // Interceptar fetch para cache automático
        this.interceptFetch();
        
        console.log('💾 Sistema de cache inicializado');
    }

    interceptFetch() {
        const originalFetch = window.fetch;
        
        window.fetch = async (url, options = {}) => {
            // Solo cachear GET requests
            if (options.method && options.method !== 'GET') {
                return originalFetch(url, options);
            }

            // Solo cachear APIs específicas
            if (this.shouldCache(url)) {
                const cacheKey = this.getCacheKey(url, options);
                const cached = this.get(cacheKey);
                
                if (cached) {
                    // Retornar respuesta desde cache
                    return new Response(JSON.stringify(cached), {
                        status: 200,
                        headers: { 'Content-Type': 'application/json' }
                    });
                }

                // Hacer request y cachear resultado
                try {
                    const response = await originalFetch(url, options);
                    
                    if (response.ok && response.headers.get('content-type')?.includes('application/json')) {
                        const clonedResponse = response.clone();
                        const data = await clonedResponse.json();
                        
                        // Cachear con TTL específico según el endpoint
                        const ttl = this.getTTLForEndpoint(url);
                        this.set(cacheKey, data, ttl);
                    }
                    
                    return response;
                } catch (error) {
                    return originalFetch(url, options);
                }
            }

            return originalFetch(url, options);
        };
    }

    shouldCache(url) {
        const cacheableEndpoints = [
            '/api/stats',
            '/api/dashboard/metricas',
            '/api/categorias',
            '/api/estadisticas_categorias',
            '/api/reportes/charts'
        ];

        return cacheableEndpoints.some(endpoint => url.includes(endpoint));
    }

    getTTLForEndpoint(url) {
        const ttlMap = {
            '/api/stats': 2 * 60 * 1000,           // 2 minutos
            '/api/dashboard/metricas': 1 * 60 * 1000, // 1 minuto
            '/api/categorias': 10 * 60 * 1000,     // 10 minutos
            '/api/estadisticas_categorias': 5 * 60 * 1000, // 5 minutos
            '/api/reportes/charts': 3 * 60 * 1000   // 3 minutos
        };

        for (const endpoint in ttlMap) {
            if (url.includes(endpoint)) {
                return ttlMap[endpoint];
            }
        }

        return this.defaultTTL;
    }

    getCacheKey(url, options) {
        // Crear clave única basada en URL y parámetros relevantes
        const urlObj = new URL(url, window.location.origin);
        const params = Array.from(urlObj.searchParams.entries())
            .sort()
            .map(([k, v]) => `${k}=${v}`)
            .join('&');
        
        return `${urlObj.pathname}${params ? '?' + params : ''}`;
    }

    set(key, data, ttl = this.defaultTTL) {
        const now = Date.now();
        
        // Eviction si el cache está lleno
        if (this.cache.size >= this.maxSize) {
            this.evictLRU();
        }

        this.cache.set(key, {
            data: data,
            timestamp: now,
            expires: now + ttl,
            accessed: now
        });

        this.stats.sets++;
    }

    get(key) {
        const entry = this.cache.get(key);
        
        if (!entry) {
            this.stats.misses++;
            return null;
        }

        const now = Date.now();
        
        // Verificar si ha expirado
        if (now > entry.expires) {
            this.cache.delete(key);
            this.stats.misses++;
            return null;
        }

        // Actualizar tiempo de acceso
        entry.accessed = now;
        this.stats.hits++;
        
        return entry.data;
    }

    evictLRU() {
        // Evict Least Recently Used
        let oldestKey = null;
        let oldestTime = Date.now();

        for (const [key, entry] of this.cache.entries()) {
            if (entry.accessed < oldestTime) {
                oldestTime = entry.accessed;
                oldestKey = key;
            }
        }

        if (oldestKey) {
            this.cache.delete(oldestKey);
            this.stats.evictions++;
        }
    }

    cleanExpired() {
        const now = Date.now();
        let cleaned = 0;

        for (const [key, entry] of this.cache.entries()) {
            if (now > entry.expires) {
                this.cache.delete(key);
                cleaned++;
            }
        }

        if (cleaned > 0) {
            console.log(`🧹 Cache: ${cleaned} entradas expiradas eliminadas`);
        }
    }

    // Métodos públicos para uso manual
    invalidate(pattern) {
        let invalidated = 0;
        
        for (const key of this.cache.keys()) {
            if (key.includes(pattern)) {
                this.cache.delete(key);
                invalidated++;
            }
        }

        console.log(`🗑️ Cache: ${invalidated} entradas invalidadas (patrón: ${pattern})`);
    }

    clear() {
        const size = this.cache.size;
        this.cache.clear();
        console.log(`🧽 Cache: ${size} entradas eliminadas`);
    }

    getStats() {
        const hitRate = this.stats.hits + this.stats.misses > 0 ? 
                       (this.stats.hits / (this.stats.hits + this.stats.misses) * 100).toFixed(2) : 0;

        return {
            ...this.stats,
            hitRate: hitRate + '%',
            size: this.cache.size,
            maxSize: this.maxSize
        };
    }

    // Cache para elementos DOM
    cacheElement(key, elementHtml, ttl = this.defaultTTL) {
        this.set(`dom:${key}`, elementHtml, ttl);
    }

    getCachedElement(key) {
        return this.get(`dom:${key}`);
    }

    // Cache para resultados de búsqueda
    cacheSearch(query, results, ttl = 2 * 60 * 1000) {
        this.set(`search:${query}`, results, ttl);
    }

    getCachedSearch(query) {
        return this.get(`search:${query}`);
    }

    // Invalidación específica por tipo
    invalidateAPI(endpoint) {
        this.invalidate(endpoint);
    }

    invalidateSearch() {
        this.invalidate('search:');
    }

    invalidateDOM() {
        this.invalidate('dom:');
    }
}

// Inicializar cache manager global
window.cacheManager = new CacheManager();

// Funciones de conveniencia
window.cacheSet = (key, data, ttl) => window.cacheManager.set(key, data, ttl);
window.cacheGet = (key) => window.cacheManager.get(key);
window.cacheInvalidate = (pattern) => window.cacheManager.invalidate(pattern);
window.cacheStats = () => window.cacheManager.getStats();

// Helper para cachear resultados de funciones
window.withCache = function(key, fn, ttl) {
    const cached = window.cacheManager.get(key);
    if (cached !== null) {
        return Promise.resolve(cached);
    }

    const result = fn();
    
    if (result && typeof result.then === 'function') {
        // Es una promesa
        return result.then(data => {
            window.cacheManager.set(key, data, ttl);
            return data;
        });
    } else {
        // Es un valor sincrónico
        window.cacheManager.set(key, result, ttl);
        return result;
    }
};

// Eventos para invalidación automática
document.addEventListener('DOMContentLoaded', function() {
    // Invalidar cache después de operaciones que modifican datos
    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (form.method && form.method.toLowerCase() !== 'get') {
            // Invalidar cache relacionado después de un breve delay
            setTimeout(() => {
                window.cacheManager.invalidateAPI('/api/');
            }, 1000);
        }
    });

    // Invalidar cache en navegación
    window.addEventListener('beforeunload', function() {
        // Limpiar cache DOM antes de navegar
        window.cacheManager.invalidateDOM();
    });
});

console.log('⚡ Sistema de cache del cliente inicializado');
