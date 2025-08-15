/**
 * Funcionalidad universal de ordenamiento para tablas
 * Uso: Agregar clase 'sortable' a los headers y data-column con el nombre de la columna
 */

document.addEventListener('DOMContentLoaded', function() {
    setupSortableColumns();
});

function setupSortableColumns() {
    document.querySelectorAll('.sortable').forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const table = this.closest('table');
            const column = this.dataset.column;
            sortTable(table, column);
        });
    });
}

function sortTable(table, column) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const isAscending = table.dataset.sortOrder !== 'asc';
    
    rows.sort((a, b) => {
        const aValue = getCellValue(a, column, table);
        const bValue = getCellValue(b, column, table);
        
        // Detectar si son números
        const aNum = parseFloat(aValue.replace(/[^0-9.-]/g, ''));
        const bNum = parseFloat(bValue.replace(/[^0-9.-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            // Ordenamiento numérico
            return isAscending ? aNum - bNum : bNum - aNum;
        }
        
        // Detectar si son fechas (formato YYYY-MM-DD o DD/MM/YYYY)
        const dateA = parseDate(aValue);
        const dateB = parseDate(bValue);
        
        if (dateA && dateB) {
            // Ordenamiento por fecha
            return isAscending ? dateA - dateB : dateB - dateA;
        }
        
        // Ordenamiento alfabético
        if (isAscending) {
            return aValue.localeCompare(bValue, undefined, {numeric: true, sensitivity: 'base'});
        } else {
            return bValue.localeCompare(aValue, undefined, {numeric: true, sensitivity: 'base'});
        }
    });
    
    // Actualizar el DOM
    rows.forEach(row => tbody.appendChild(row));
    
    // Actualizar el estado de ordenamiento
    table.dataset.sortOrder = isAscending ? 'asc' : 'desc';
    
    // Actualizar iconos
    table.querySelectorAll('.sortable i').forEach(icon => {
        icon.className = 'fas fa-sort';
    });
    
    const currentIcon = table.querySelector(`[data-column="${column}"] i`);
    if (currentIcon) {
        currentIcon.className = isAscending ? 'fas fa-sort-up' : 'fas fa-sort-down';
    }
}

function getCellValue(row, column, table) {
    const columnIndex = Array.from(table.querySelectorAll('th')).findIndex(th => th.dataset.column === column);
    
    if (columnIndex === -1) return '';
    
    const cell = row.cells[columnIndex];
    if (!cell) return '';
    
    // Extraer texto, ignorando badges y otros elementos HTML
    let cellText = cell.textContent.trim();
    
    // Limpiar caracteres especiales para ordenamiento
    cellText = cellText.replace(/[\$\€\£\%]/g, '');
    
    return cellText;
}

function parseDate(dateString) {
    if (!dateString || dateString === '-') return null;
    
    // Intentar varios formatos de fecha
    let date = null;
    
    // Formato YYYY-MM-DD
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
        date = new Date(dateString);
    }
    // Formato DD/MM/YYYY
    else if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(dateString)) {
        const parts = dateString.split('/');
        date = new Date(parts[2], parts[1] - 1, parts[0]);
    }
    // Formato DD-MM-YYYY
    else if (/^\d{1,2}-\d{1,2}-\d{4}$/.test(dateString)) {
        const parts = dateString.split('-');
        date = new Date(parts[2], parts[1] - 1, parts[0]);
    }
    
    return (date && !isNaN(date.getTime())) ? date : null;
}

// Función para agregar ordenamiento a una tabla específica
function enableTableSorting(tableId) {
    const table = document.getElementById(tableId);
    if (table) {
        table.querySelectorAll('.sortable').forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const column = this.dataset.column;
                sortTable(table, column);
            });
        });
    }
}

// Exportar funciones para uso global
window.TableSort = {
    setup: setupSortableColumns,
    sortTable: sortTable,
    enable: enableTableSorting
};
