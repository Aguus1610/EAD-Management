#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de Reconocimiento Inteligente para Repuestos y Trabajos
============================================================

Este módulo contiene la lógica avanzada para clasificar automáticamente
repuestos y trabajos basándose en el sistema de categorías estructurado.
"""

import sqlite3
import re
import unicodedata
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class ClasificacionResultado:
    """Resultado de una clasificación"""
    categoria: str
    categoria_id: int
    confianza: float
    palabras_encontradas: List[str]
    es_categoria_padre: bool
    color_codigo: str

@dataclass
class DeteccionCompleta:
    """Resultado completo de detección para un texto"""
    texto_original: str
    texto_normalizado: str
    clasificaciones: List[ClasificacionResultado]
    mejor_clasificacion: Optional[ClasificacionResultado]
    confianza_total: float

class MotorReconocimiento:
    """Motor principal de reconocimiento inteligente"""
    
    def __init__(self, db_path: str = 'taller.db'):
        self.db_path = db_path
        self._cache_palabras_repuestos = None
        self._cache_palabras_trabajos = None
        self._cache_categorias_repuestos = None
        self._cache_categorias_trabajos = None
    
    def normalizar_texto(self, texto: str) -> str:
        """
        Normaliza texto para mejor reconocimiento
        - Convierte a minúsculas
        - Elimina acentos
        - Normaliza espacios
        - Elimina caracteres especiales innecesarios
        """
        if not texto:
            return ""
        
        # Convertir a minúsculas
        texto = texto.lower()
        
        # Eliminar acentos
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
        
        # Normalizar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto)
        
        # Eliminar caracteres especiales pero mantener espacios y números
        texto = re.sub(r'[^\w\s]', ' ', texto)
        
        # Limpiar espacios al inicio y final
        return texto.strip()
    
    def cargar_palabras_clave_repuestos(self) -> Dict:
        """Cargar y cachear palabras clave de repuestos"""
        if self._cache_palabras_repuestos is not None:
            return self._cache_palabras_repuestos
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        query = '''
            SELECT 
                p.palabra, 
                p.peso, 
                p.es_sinonimo,
                p.palabra_principal,
                c.id as categoria_id,
                c.nombre as categoria_nombre,
                c.categoria_padre,
                c.color_codigo
            FROM palabras_clave_repuestos p
            JOIN categorias_repuestos c ON p.categoria_id = c.id
            WHERE p.activo = 1 AND c.activo = 1
            ORDER BY p.peso DESC, c.categoria_padre NULLS LAST
        '''
        
        palabras = defaultdict(list)
        for row in conn.execute(query):
            palabras[self.normalizar_texto(row['palabra'])].append({
                'palabra_original': row['palabra'],
                'peso': row['peso'],
                'es_sinonimo': row['es_sinonimo'],
                'palabra_principal': row['palabra_principal'],
                'categoria_id': row['categoria_id'],
                'categoria_nombre': row['categoria_nombre'],
                'categoria_padre': row['categoria_padre'],
                'color_codigo': row['color_codigo']
            })
        
        conn.close()
        self._cache_palabras_repuestos = dict(palabras)
        return self._cache_palabras_repuestos
    
    def cargar_palabras_clave_trabajos(self) -> Dict:
        """Cargar y cachear palabras clave de trabajos"""
        if self._cache_palabras_trabajos is not None:
            return self._cache_palabras_trabajos
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        query = '''
            SELECT 
                p.palabra, 
                p.peso, 
                p.es_sinonimo,
                p.palabra_principal,
                c.id as categoria_id,
                c.nombre as categoria_nombre,
                c.categoria_padre,
                c.color_codigo,
                c.complejidad
            FROM palabras_clave_trabajos p
            JOIN categorias_trabajos c ON p.categoria_id = c.id
            WHERE p.activo = 1 AND c.activo = 1
            ORDER BY p.peso DESC, c.categoria_padre NULLS LAST
        '''
        
        palabras = defaultdict(list)
        for row in conn.execute(query):
            palabras[self.normalizar_texto(row['palabra'])].append({
                'palabra_original': row['palabra'],
                'peso': row['peso'],
                'es_sinonimo': row['es_sinonimo'],
                'palabra_principal': row['palabra_principal'],
                'categoria_id': row['categoria_id'],
                'categoria_nombre': row['categoria_nombre'],
                'categoria_padre': row['categoria_padre'],
                'color_codigo': row['color_codigo'],
                'complejidad': row['complejidad']
            })
        
        conn.close()
        self._cache_palabras_trabajos = dict(palabras)
        return self._cache_palabras_trabajos
    
    def detectar_repuestos(self, texto: str, umbral_confianza: float = 0.3) -> DeteccionCompleta:
        """
        Detecta repuestos en un texto con puntuación de confianza
        """
        texto_normalizado = self.normalizar_texto(texto)
        palabras_clave = self.cargar_palabras_clave_repuestos()
        
        clasificaciones = []
        palabras_encontradas = []
        
        # Buscar coincidencias exactas de palabras clave
        for palabra_norm, datos_palabra in palabras_clave.items():
            if palabra_norm in texto_normalizado:
                for dato in datos_palabra:
                    # Calcular confianza base
                    confianza = dato['peso']
                    
                    # Bonus por coincidencia exacta de palabra completa
                    if re.search(r'\b' + re.escape(palabra_norm) + r'\b', texto_normalizado):
                        confianza *= 1.5
                    
                    # Penalización por sinónimos
                    if dato['es_sinonimo']:
                        confianza *= 0.8
                    
                    # Bonus por categorías específicas (no padre)
                    if not dato['categoria_padre']:
                        confianza *= 0.9
                    else:
                        confianza *= 1.1
                    
                    # Normalizar confianza a rango 0-1
                    confianza = min(confianza / 2.0, 1.0)
                    
                    if confianza >= umbral_confianza:
                        clasificaciones.append(ClasificacionResultado(
                            categoria=dato['categoria_nombre'],
                            categoria_id=dato['categoria_id'],
                            confianza=confianza,
                            palabras_encontradas=[dato['palabra_original']],
                            es_categoria_padre=dato['categoria_padre'] is None,
                            color_codigo=dato['color_codigo']
                        ))
                        palabras_encontradas.append(dato['palabra_original'])
        
        # Eliminar duplicados y ordenar por confianza
        clasificaciones_unicas = {}
        for cls in clasificaciones:
            key = cls.categoria
            if key not in clasificaciones_unicas or cls.confianza > clasificaciones_unicas[key].confianza:
                clasificaciones_unicas[key] = cls
        
        clasificaciones_finales = sorted(clasificaciones_unicas.values(), 
                                       key=lambda x: x.confianza, reverse=True)
        
        # Seleccionar mejor clasificación
        mejor_clasificacion = clasificaciones_finales[0] if clasificaciones_finales else None
        confianza_total = max([c.confianza for c in clasificaciones_finales], default=0.0)
        
        return DeteccionCompleta(
            texto_original=texto,
            texto_normalizado=texto_normalizado,
            clasificaciones=clasificaciones_finales,
            mejor_clasificacion=mejor_clasificacion,
            confianza_total=confianza_total
        )
    
    def detectar_trabajos(self, texto: str, umbral_confianza: float = 0.3) -> DeteccionCompleta:
        """
        Detecta trabajos en un texto con puntuación de confianza
        """
        texto_normalizado = self.normalizar_texto(texto)
        palabras_clave = self.cargar_palabras_clave_trabajos()
        
        clasificaciones = []
        palabras_encontradas = []
        
        # Buscar coincidencias exactas de palabras clave
        for palabra_norm, datos_palabra in palabras_clave.items():
            if palabra_norm in texto_normalizado:
                for dato in datos_palabra:
                    # Calcular confianza base
                    confianza = dato['peso']
                    
                    # Bonus por coincidencia exacta de palabra completa
                    if re.search(r'\b' + re.escape(palabra_norm) + r'\b', texto_normalizado):
                        confianza *= 1.5
                    
                    # Penalización por sinónimos
                    if dato['es_sinonimo']:
                        confianza *= 0.8
                    
                    # Bonus por categorías específicas (no padre)
                    if not dato['categoria_padre']:
                        confianza *= 0.9
                    else:
                        confianza *= 1.1
                    
                    # Bonus por complejidad alta (trabajos más específicos)
                    if dato.get('complejidad', 1) >= 3:
                        confianza *= 1.2
                    
                    # Normalizar confianza a rango 0-1
                    confianza = min(confianza / 2.0, 1.0)
                    
                    if confianza >= umbral_confianza:
                        clasificaciones.append(ClasificacionResultado(
                            categoria=dato['categoria_nombre'],
                            categoria_id=dato['categoria_id'],
                            confianza=confianza,
                            palabras_encontradas=[dato['palabra_original']],
                            es_categoria_padre=dato['categoria_padre'] is None,
                            color_codigo=dato['color_codigo']
                        ))
                        palabras_encontradas.append(dato['palabra_original'])
        
        # Eliminar duplicados y ordenar por confianza
        clasificaciones_unicas = {}
        for cls in clasificaciones:
            key = cls.categoria
            if key not in clasificaciones_unicas or cls.confianza > clasificaciones_unicas[key].confianza:
                clasificaciones_unicas[key] = cls
        
        clasificaciones_finales = sorted(clasificaciones_unicas.values(), 
                                       key=lambda x: x.confianza, reverse=True)
        
        # Seleccionar mejor clasificación
        mejor_clasificacion = clasificaciones_finales[0] if clasificaciones_finales else None
        confianza_total = max([c.confianza for c in clasificaciones_finales], default=0.0)
        
        return DeteccionCompleta(
            texto_original=texto,
            texto_normalizado=texto_normalizado,
            clasificaciones=clasificaciones_finales,
            mejor_clasificacion=mejor_clasificacion,
            confianza_total=confianza_total
        )
    
    def guardar_clasificacion(self, mantenimiento_id: int, deteccion: DeteccionCompleta, tipo: str):
        """
        Guarda la clasificación en la base de datos para auditoría
        """
        conn = sqlite3.connect(self.db_path)
        
        if deteccion.mejor_clasificacion:
            palabras_json = str([c.palabras_encontradas for c in deteccion.clasificaciones])
            
            conn.execute('''
                INSERT INTO clasificaciones_automaticas 
                (mantenimiento_id, texto_original, tipo, categoria_detectada, confianza, palabras_encontradas)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                mantenimiento_id,
                deteccion.texto_original,
                tipo,
                deteccion.mejor_clasificacion.categoria,
                deteccion.confianza_total,
                palabras_json
            ))
        
        conn.commit()
        conn.close()
    
    def analizar_mantenimiento_completo(self, descripcion: str, mantenimiento_id: Optional[int] = None) -> Dict:
        """
        Analiza una descripción completa de mantenimiento para extraer repuestos y trabajos
        """
        if not descripcion:
            return {
                'repuestos': [],
                'trabajos': [],
                'confianza_repuestos': 0.0,
                'confianza_trabajos': 0.0,
                'resumen': 'Sin descripción para analizar'
            }
        
        # Separar repuestos y trabajos si están estructurados
        partes = descripcion.split('|')
        texto_repuestos = ""
        texto_trabajos = ""
        
        for parte in partes:
            parte = parte.strip()
            if parte.lower().startswith('repuesto'):
                texto_repuestos += " " + parte
            elif parte.lower().startswith('trabajo'):
                texto_trabajos += " " + parte
            else:
                # Si no está estructurado, analizar todo
                texto_repuestos += " " + parte
                texto_trabajos += " " + parte
        
        # Detectar repuestos
        deteccion_repuestos = self.detectar_repuestos(texto_repuestos)
        
        # Detectar trabajos
        deteccion_trabajos = self.detectar_trabajos(texto_trabajos)
        
        # Guardar clasificaciones si se proporciona ID
        if mantenimiento_id:
            if deteccion_repuestos.mejor_clasificacion:
                self.guardar_clasificacion(mantenimiento_id, deteccion_repuestos, 'repuesto')
            if deteccion_trabajos.mejor_clasificacion:
                self.guardar_clasificacion(mantenimiento_id, deteccion_trabajos, 'trabajo')
        
        return {
            'repuestos': [
                {
                    'categoria': c.categoria,
                    'confianza': round(c.confianza * 100, 1),
                    'palabras': c.palabras_encontradas,
                    'color': c.color_codigo
                }
                for c in deteccion_repuestos.clasificaciones[:5]  # Top 5
            ],
            'trabajos': [
                {
                    'categoria': c.categoria,
                    'confianza': round(c.confianza * 100, 1),
                    'palabras': c.palabras_encontradas,
                    'color': c.color_codigo
                }
                for c in deteccion_trabajos.clasificaciones[:5]  # Top 5
            ],
            'confianza_repuestos': round(deteccion_repuestos.confianza_total * 100, 1),
            'confianza_trabajos': round(deteccion_trabajos.confianza_total * 100, 1),
            'mejor_repuesto': deteccion_repuestos.mejor_clasificacion.categoria if deteccion_repuestos.mejor_clasificacion else None,
            'mejor_trabajo': deteccion_trabajos.mejor_clasificacion.categoria if deteccion_trabajos.mejor_clasificacion else None,
            'resumen': f"Detectados {len(deteccion_repuestos.clasificaciones)} tipos de repuestos y {len(deteccion_trabajos.clasificaciones)} tipos de trabajos"
        }
    
    def invalidar_cache(self):
        """Invalida el caché para recargar datos actualizados"""
        self._cache_palabras_repuestos = None
        self._cache_palabras_trabajos = None
        self._cache_categorias_repuestos = None
        self._cache_categorias_trabajos = None

# Función de conveniencia para uso externo
def crear_motor_reconocimiento(db_path: str = 'taller.db') -> MotorReconocimiento:
    """Crea una instancia del motor de reconocimiento"""
    return MotorReconocimiento(db_path)

# Función para testing
def test_motor():
    """Función de prueba del motor"""
    motor = crear_motor_reconocimiento()
    
    # Ejemplos de prueba
    ejemplos = [
        "Repuestos: 1 filtro de aceite, 2 litros aceite hidraulico | Trabajo realizado: Service general completo",
        "Cambio de mangueras hidraulicas y reparacion bomba principal",
        "Soldadura de cilindro elevacion y cambio retenes",
        "Service preventivo con cambio filtros aire y lubricacion general",
        "Reparacion electrica cables comando y reemplazo terminales"
    ]
    
    print("🧪 Probando Motor de Reconocimiento Inteligente")
    print("=" * 60)
    
    for i, ejemplo in enumerate(ejemplos, 1):
        print(f"\n📋 Ejemplo {i}: {ejemplo}")
        resultado = motor.analizar_mantenimiento_completo(ejemplo)
        
        print(f"🔧 Repuestos detectados ({resultado['confianza_repuestos']}% confianza):")
        for rep in resultado['repuestos']:
            print(f"  - {rep['categoria']} ({rep['confianza']}%)")
        
        print(f"⚙️ Trabajos detectados ({resultado['confianza_trabajos']}% confianza):")
        for trab in resultado['trabajos']:
            print(f"  - {trab['categoria']} ({trab['confianza']}%)")
        
        print(f"📊 {resultado['resumen']}")

if __name__ == "__main__":
    test_motor()
