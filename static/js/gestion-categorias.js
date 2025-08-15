/**
 * Gestión de Categorías - JavaScript
 * Maneja eventos y funciones para la página de gestión de categorías
 */

document.addEventListener('DOMContentLoaded', function() {
    // Manejar botones de editar categorías con data attributes
    document.querySelectorAll('.btn-editar-categoria').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const id = this.dataset.categoriaId;
            const nombre = this.dataset.categoriaNombre;
            const descripcion = this.dataset.categoriaDescripcion || '';
            const padre = this.dataset.categoriaPadre || '';
            const activo = this.dataset.categoriaActivo === 'true';
            const tipo = this.dataset.tipo;
            
            if (tipo === 'repuesto') {
                editarCategoriaRepuesto(id, nombre, descripcion, padre, activo);
            } else if (tipo === 'trabajo') {
                const complejidad = this.dataset.categoriaComplejidad || 1;
                editarCategoriaTrabajo(id, nombre, descripcion, padre, complejidad, activo);
            }
        });
    });
    
    // Manejar botones de ver palabras clave
    document.querySelectorAll('.btn-ver-palabras').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const id = this.dataset.categoriaId;
            const nombre = this.dataset.categoriaNombre;
            verPalabrasCategoria(id, nombre);
        });
    });
    
    // Manejar botones de eliminar
    document.querySelectorAll('.btn-eliminar-categoria').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const id = this.dataset.categoriaId;
            const nombre = this.dataset.categoriaNombre;
            const tipo = this.dataset.tipo;
            
            if (tipo === 'repuesto') {
                eliminarCategoriaRepuesto(id, nombre);
            } else if (tipo === 'trabajo') {
                eliminarCategoriaTrabajo(id, nombre);
            }
        });
    });
    
    // Manejar botones de toggle estado
    document.querySelectorAll('.btn-toggle-categoria').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const id = this.dataset.categoriaId;
            const tipo = this.dataset.tipo;
            const activo = this.dataset.categoriaActivo === 'true';
            toggleCategoriaEstado(id, tipo, activo);
        });
    });
});

// Funciones auxiliares para escape de caracteres
function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

function unescapeHtml(text) {
    if (typeof text !== 'string') return text;
    
    const map = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#039;': "'"
    };
    
    return text.replace(/&(amp|lt|gt|quot|#039);/g, function(m, entity) { return map['&' + entity + ';']; });
}

// ===================================
// FUNCIONES PRINCIPALES (FALTANTES)
// ===================================

function editarCategoriaRepuesto(id, nombre, descripcion, padre, activo) {
    console.log('Editando categoría repuesto:', id, nombre);
    
    // Limpiar cualquier modal anterior
    limpiarModalBackdrop();
    
    try {
        const modal = new bootstrap.Modal(document.getElementById('modalEditarCategoria'), {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        
        // Precargar datos en el modal
        document.getElementById('editCategoriaId').value = id;
        document.getElementById('editTipoCategoria').value = 'repuesto';
        document.getElementById('editNombreCategoria').value = nombre || '';
        document.getElementById('editDescripcionCategoria').value = descripcion || '';
        document.getElementById('editCategoriaPadre').value = padre || '';
        document.getElementById('editActivoCategoria').checked = activo === true || activo === 'true';
        
        // Ocultar campo de complejidad para repuestos
        const complejidadContainer = document.getElementById('editComplejidadContainer');
        if (complejidadContainer) {
            complejidadContainer.style.display = 'none';
        }
        
        // Agregar event listener para limpiar al cerrar
        const modalElement = document.getElementById('modalEditarCategoria');
        modalElement.addEventListener('hidden.bs.modal', limpiarModalBackdrop, { once: true });
        
        modal.show();
    } catch (error) {
        console.error('Error showing modal:', error);
        // Fallback a alert
        alert(`Editando categoría: ${nombre}\nID: ${id}\nActivo: ${activo}`);
    }
}

function editarCategoriaTrabajo(id, nombre, descripcion, padre, complejidad, activo) {
    console.log('Editando categoría trabajo:', id, nombre);
    
    // Limpiar cualquier modal anterior
    limpiarModalBackdrop();
    
    try {
        const modal = new bootstrap.Modal(document.getElementById('modalEditarCategoria'), {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        
        // Precargar datos en el modal
        document.getElementById('editCategoriaId').value = id;
        document.getElementById('editTipoCategoria').value = 'trabajo';
        document.getElementById('editNombreCategoria').value = nombre || '';
        document.getElementById('editDescripcionCategoria').value = descripcion || '';
        document.getElementById('editCategoriaPadre').value = padre || '';
        document.getElementById('editActivoCategoria').checked = activo === true || activo === 'true';
        document.getElementById('editComplejidadCategoria').value = complejidad || 1;
        
        // Mostrar campo de complejidad para trabajos
        const complejidadContainer = document.getElementById('editComplejidadContainer');
        if (complejidadContainer) {
            complejidadContainer.style.display = 'block';
        }
        
        // Agregar event listener para limpiar al cerrar
        const modalElement = document.getElementById('modalEditarCategoria');
        modalElement.addEventListener('hidden.bs.modal', limpiarModalBackdrop, { once: true });
        
        modal.show();
    } catch (error) {
        console.error('Error showing modal:', error);
        // Fallback a alert
        alert(`Editando categoría de trabajo: ${nombre}\nID: ${id}\nComplejidad: ${complejidad}\nActivo: ${activo}`);
    }
}

function verPalabrasCategoria(id, nombre) {
    console.log('Viendo palabras clave para:', id, nombre);
    
    // Limpiar cualquier modal anterior
    limpiarModalBackdrop();
    
    // Hacer petición para obtener palabras clave
    fetch(`/api/categorias/${id}/palabras`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                try {
                    // Usar modal personalizado
                    const modal = new bootstrap.Modal(document.getElementById('modalPalabrasCategoria'), {
                        backdrop: true,
                        keyboard: true,
                        focus: true
                    });
                    
                    // Configurar título
                    document.getElementById('palabrasCategoriaTitle').textContent = `Palabras clave: ${nombre}`;
                    
                    // Almacenar ID para agregar nuevas palabras
                    window.currentCategoriaId = id;
                    
                    // Mostrar palabras
                    const container = document.getElementById('palabrasContainer');
                    container.innerHTML = '';
                    
                    if (data.palabras && data.palabras.length > 0) {
                        data.palabras.forEach(palabra => {
                            const badge = document.createElement('span');
                            badge.className = 'badge bg-primary me-1 mb-1';
                            badge.textContent = `${palabra.palabra} (${palabra.frecuencia})`;
                            container.appendChild(badge);
                        });
                    } else {
                        container.innerHTML = '<p class="text-muted">No hay palabras clave registradas</p>';
                    }
                    
                    // Agregar event listener para limpiar al cerrar
                    const modalElement = document.getElementById('modalPalabrasCategoria');
                    modalElement.addEventListener('hidden.bs.modal', limpiarModalBackdrop, { once: true });
                    
                    modal.show();
                } catch (error) {
                    console.error('Error showing modal:', error);
                    // Fallback a alert
                    const palabras = data.palabras || [];
                    const mensaje = palabras.length > 0 
                        ? `Palabras clave de "${nombre}":\n\n${palabras.map(p => `• ${p.palabra} (${p.frecuencia} veces)`).join('\n')}`
                        : `No hay palabras clave registradas para "${nombre}"`;
                    alert(mensaje);
                }
            } else {
                alert('Error al cargar palabras clave');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error de conexión');
        });
}

function eliminarCategoriaRepuesto(id, nombre) {
    console.log('Eliminando categoría repuesto:', id, nombre);
    
    const mensaje = `¿Está seguro de que desea eliminar la categoría "${nombre}"?`;
    
    // Usar confirmación personalizada con callback
    window.showConfirm(mensaje, function(confirmed) {
        if (confirmed) {
            realizarEliminacionCategoria(id, 'repuesto', nombre);
        }
    });
}

function eliminarCategoriaTrabajo(id, nombre) {
    console.log('Eliminando categoría trabajo:', id, nombre);
    
    const mensaje = `¿Está seguro de que desea eliminar la categoría de trabajo "${nombre}"?`;
    
    // Usar confirmación personalizada con callback
    window.showConfirm(mensaje, function(confirmed) {
        if (confirmed) {
            realizarEliminacionCategoria(id, 'trabajo', nombre);
        }
    });
}

function toggleCategoriaEstado(id, tipo, estadoActual) {
    const nuevoEstado = !estadoActual;
    const accion = nuevoEstado ? 'activar' : 'desactivar';
    
    console.log(`Toggle categoría ${tipo}:`, id, `${accion}`);
    
    const mensaje = `¿Está seguro de que desea ${accion} esta categoría?`;
    
    // Usar confirmación personalizada con callback
    window.showConfirm(mensaje, function(confirmed) {
        if (confirmed) {
            realizarToggleEstado(id, tipo, nuevoEstado);
        }
    });
}

// ===================================
// FUNCIONES AUXILIARES
// ===================================

function realizarEliminacionCategoria(id, tipo, nombre) {
    const endpoint = tipo === 'repuesto' ? `/api/categorias/repuesto/${id}` : `/api/categorias/trabajo/${id}`;
    
    fetch(endpoint, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
            .then(data => {
            if (data.success) {
                window.showSuccess(`Categoría "${nombre}" eliminada exitosamente`);
                // Recargar página después de 1 segundo
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                window.showError(`Error: ${data.error || 'No se pudo eliminar la categoría'}`);
            }
        })
        .catch(error => {
            console.error('Error eliminando categoría:', error);
            window.showError('Error de conexión al eliminar categoría');
        });
}

function realizarToggleEstado(id, tipo, nuevoEstado) {
    fetch(`/api/categorias/${tipo}/${id}/toggle`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ activo: nuevoEstado })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const accion = nuevoEstado ? 'activada' : 'desactivada';
            window.showSuccess(`Categoría ${accion} exitosamente`);
            // Recargar página después de 1.5 segundos
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            window.showError(`Error: ${data.error || 'No se pudo cambiar el estado'}`);
        }
    })
    .catch(error => {
        console.error('Error cambiando estado:', error);
        window.showError('Error de conexión al cambiar estado');
    });
}

// ===================================
// FUNCIONES PARA LIMPIAR MODALES
// ===================================

/**
 * Función para limpiar completamente el backdrop de modales
 * Soluciona el problema de ventana oscura que se queda
 */
function limpiarModalBackdrop() {
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
        
        // Limpiar instancias de Bootstrap modales
        const modales = document.querySelectorAll('.modal');
        modales.forEach(modal => {
            const instance = bootstrap.Modal.getInstance(modal);
            if (instance) {
                try {
                    instance.dispose();
                } catch (e) {
                    console.log('Modal ya eliminado:', e);
                }
            }
        });
        
        console.log('Modal backdrop limpiado exitosamente');
    } catch (error) {
        console.error('Error limpiando modal backdrop:', error);
    }
}

/**
 * Función para cerrar todos los modales activos
 */
function cerrarTodosLosModales() {
    try {
        const modales = document.querySelectorAll('.modal.show');
        modales.forEach(modal => {
            const instance = bootstrap.Modal.getInstance(modal);
            if (instance) {
                instance.hide();
            }
        });
        
        // Esperar un poco y limpiar
        setTimeout(limpiarModalBackdrop, 150);
    } catch (error) {
        console.error('Error cerrando modales:', error);
        limpiarModalBackdrop();
    }
}
