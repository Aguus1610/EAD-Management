/**
 * SISTEMA DE EXPORTACIÓN SIMPLE Y DIRECTO
 * =======================================
 * Solución simple que FUNCIONA
 */

console.log('🚀 Iniciando Simple Export System...');

// Función simple y directa para exportar PDF
function exportarPDF(tipo) {
    console.log('📄 exportarPDF llamado con tipo:', tipo);
    
    if (!tipo) {
        console.error('❌ Tipo no especificado');
        alert('Error: Tipo de exportación no especificado');
        return;
    }
    
    const url = `/api/export/pdf/${tipo}`;
    console.log('🌐 Abriendo URL:', url);
    
    try {
        // Método 1: Ventana nueva
        const newWindow = window.open(url, '_blank');
        
        if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
            console.warn('🚫 Popup bloqueado, intentando método alternativo');
            
            // Método 2: Location redirect
            window.location.href = url;
        } else {
            console.log('✅ Ventana abierta exitosamente');
        }
        
        // Mostrar mensaje de éxito
        if (typeof showInfo === 'function') {
            showInfo(`Generando reporte PDF: ${tipo}`);
        } else {
            console.log('✅ Generando PDF...');
        }
        
    } catch (error) {
        console.error('❌ Error abriendo PDF:', error);
        alert(`Error al abrir PDF: ${error.message}`);
    }
}

// Función simple para dashboard
function exportarDashboard(formato) {
    console.log('📊 exportarDashboard llamado con formato:', formato);
    
    if (formato === 'pdf') {
        exportarPDF('dashboard');
    } else if (formato === 'excel') {
        console.log('📊 Exportando Excel dashboard');
        const url = `/api/export/excel/dashboard`;
        window.open(url, '_blank');
    } else {
        console.warn('⚠️ Formato no reconocido:', formato);
        exportarPDF('dashboard'); // Default a PDF
    }
}

// Función simple para auditoría
function exportarAuditoria(formato) {
    console.log('📋 exportarAuditoria llamado con formato:', formato);
    
    if (formato === 'pdf') {
        exportarPDF('auditoria');
    } else if (formato === 'excel') {
        window.open(`/api/export/excel/auditoria`, '_blank');
    } else if (formato === 'csv') {
        window.open(`/api/export/excel/auditoria?format=csv`, '_blank');
    } else {
        exportarPDF('auditoria'); // Default a PDF
    }
}

// Función simple para programas
function exportarProgramas() {
    console.log('⚙️ exportarProgramas llamado');
    
    const respuesta = confirm('¿En qué formato desea exportar?\n\nOK = PDF\nCancelar = Excel');
    
    if (respuesta) {
        exportarPDF('programas');
    } else {
        window.open(`/api/export/excel/programas`, '_blank');
    }
}

// Alias para compatibilidad con nombres diferentes
window.exportPDF = function(tipo) {
    console.log('🔗 exportPDF alias llamado para:', tipo);
    exportarPDF(tipo);
};

window.exportarPDF = exportarPDF;
window.exportarDashboard = exportarDashboard;
window.exportarAuditoria = exportarAuditoria;
window.exportarProgramas = exportarProgramas;

// Test function
window.testSimpleExport = function(tipo = 'dashboard') {
    console.log('🧪 Testing simple export para:', tipo);
    console.log('🔍 URL que se usaría:', `/api/export/pdf/${tipo}`);
    
    if (confirm(`¿Ejecutar test real para ${tipo}?`)) {
        exportarPDF(tipo);
    }
};

// Auto-log al cargar
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Simple Export System cargado');
    console.log('📋 Funciones disponibles:');
    console.log('  - exportarPDF(tipo)');
    console.log('  - exportPDF(tipo) [alias]');
    console.log('  - exportarDashboard(formato)');
    console.log('  - exportarAuditoria(formato)');
    console.log('  - exportarProgramas()');
    console.log('  - testSimpleExport(tipo)');
});

console.log('✅ Simple Export System loaded successfully');
