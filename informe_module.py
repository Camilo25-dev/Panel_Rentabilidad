"""
Módulo para generar el Informe de Rentabilidad
Diseñado para integrarse con el dashboard principal de SURA Investments
Soporta descarga en Excel y PDF
"""

import pandas as pd
import numpy as np
from dash import html, dcc, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc
import io
import base64
from datetime import datetime
import logging
import os
from pathlib import Path

# Importaciones para PDF
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm  # AGREGADO: importar mm aquí
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    # AGREGADO: Definir mm como fallback si ReportLab no está disponible
    mm = 1  # valor por defecto
    logging.warning("ReportLab no está instalado. La funcionalidad PDF no estará disponible.")

from precalculos_optimizado import obtener_informe_pdf_completo_precalculado


# Configuración del módulo
CONFIG = {
    'COLUMNAS_INFORME': ['Fondo', 'Serie', 'Valor Cuota', 'TAC', 'Diaria', '1 Mes', '3 Meses', '12 Meses', 'MTD', 'YTD', 'Año 2024', 'Año 2023', '3 Años*', '5 Años**'],
    'ORDEN_CATEGORIAS': [
        'Renta Fija Nacional',
        'Renta Fija Internacional', 
        'Multifondos',
        'Equity (Acciones)',
        'Estrategias Alternativas',
        'Otros'
    ]
}

def loading_content():
    """
    Función para mostrar contenido de carga
    """
    return html.Div([
        html.Div([
            html.I(className="fas fa-spinner fa-spin", style={'fontSize': '24px', 'color': '#0B2DCE'}),
            html.P("Cargando anexo mensual...", style={'marginTop': '10px', 'fontFamily': 'SuraSans-Regular'})
        ], style={
            'textAlign': 'center',
            'padding': '40px',
            'color': '#666'
        })
        ])

# =============================================================================
# NUEVAS FUNCIONES DE CÁLCULO PARA EL PDF MEJORADO
# =============================================================================

def calcular_rentabilidad_diaria(precios):
    """
    Calcula la rentabilidad del último día disponible
    """
    if len(precios) < 2:
        return np.nan
    
    precio_actual = precios.iloc[-1, 1]  # Último precio
    precio_anterior = precios.iloc[-2, 1]  # Precio del día anterior
    
    if pd.isna(precio_actual) or pd.isna(precio_anterior) or precio_anterior == 0:
        return np.nan
    
    return ((precio_actual / precio_anterior) - 1) * 100

def calcular_rentabilidad_mtd(precios, fecha_actual):
    """
    Calcula MTD: desde último dato del mes anterior hasta hoy
    """
    try:
        # Obtener el mes y año actual
        mes_actual = fecha_actual.month
        año_actual = fecha_actual.year
        
        # Calcular mes anterior
        if mes_actual == 1:
            mes_anterior = 12
            año_anterior = año_actual - 1
        else:
            mes_anterior = mes_actual - 1
            año_anterior = año_actual
        
        # Filtrar datos del mes anterior
        datos_mes_anterior = precios[
            (precios['Dates'].dt.month == mes_anterior) & 
            (precios['Dates'].dt.year == año_anterior)
        ]
        
        if len(datos_mes_anterior) == 0:
            return np.nan
        
        # Último precio del mes anterior
        precio_inicio_mtd = datos_mes_anterior.iloc[-1, 1]
        
        # Precio actual (o más reciente disponible)
        precio_actual = precios.iloc[-1, 1]
        
        if pd.isna(precio_inicio_mtd) or pd.isna(precio_actual) or precio_inicio_mtd == 0:
            return np.nan
        
        return ((precio_actual / precio_inicio_mtd) - 1) * 100
        
    except Exception as e:
        return np.nan

def calcular_rentabilidad_ytd_mejorado(precios, fecha_actual):
    """
    Calcula YTD: desde último dato del año anterior hasta hoy
    """
    try:
        año_actual = fecha_actual.year
        año_anterior = año_actual - 1
        
        # Filtrar datos del año anterior
        datos_año_anterior = precios[precios['Dates'].dt.year == año_anterior]
        
        if len(datos_año_anterior) == 0:
            return np.nan
        
        # Último precio del año anterior
        precio_inicio_ytd = datos_año_anterior.iloc[-1, 1]
        
        # Precio actual
        precio_actual = precios.iloc[-1, 1]
        
        if pd.isna(precio_inicio_ytd) or pd.isna(precio_actual) or precio_inicio_ytd == 0:
            return np.nan
        
        return ((precio_actual / precio_inicio_ytd) - 1) * 100
        
    except Exception as e:
        return np.nan

def calcular_rentabilidad_año_especifico(precios, año_objetivo):
    """
    Calcula rentabilidad de un año específico: desde último dato del año anterior
    hasta último dato del año objetivo
    """
    try:
        año_anterior = año_objetivo - 1
        
        # Datos del año anterior
        datos_año_anterior = precios[precios['Dates'].dt.year == año_anterior]
        if len(datos_año_anterior) == 0:
            return np.nan
        precio_inicio = datos_año_anterior.iloc[-1, 1]
        
        # Datos del año objetivo
        datos_año_objetivo = precios[precios['Dates'].dt.year == año_objetivo]
        if len(datos_año_objetivo) == 0:
            return np.nan
        precio_fin = datos_año_objetivo.iloc[-1, 1]
        
        if pd.isna(precio_inicio) or pd.isna(precio_fin) or precio_inicio == 0:
            return np.nan
        
        return ((precio_fin / precio_inicio) - 1) * 100
        
    except Exception as e:
        return np.nan

def calcular_rentabilidad_anualizada_con_validacion(precios, años_objetivo):
    """
    Calcula rentabilidad anualizada para un período ESPECÍFICO (3 o 5 años)
    
    Args:
        precios: DataFrame con columnas 'Dates' y precios
        años_objetivo: 3 o 5 años
    
    Returns:
        float: Rentabilidad anualizada en % o np.nan si no hay suficiente historial
    """
    try:
        if len(precios) < 2:
            return np.nan
        
        fecha_final = precios['Dates'].iloc[-1]
        fecha_inicial = precios['Dates'].iloc[0]
        
        # Calcular años de historial total disponible
        años_historial_total = (fecha_final - fecha_inicial).days / 365.25
        
        # VALIDACIÓN: Debe tener AL MENOS los años objetivo
        if años_historial_total < años_objetivo:
            return np.nan
        
        # Calcular fecha de inicio para el período objetivo
        # Ir hacia atrás exactamente X años desde la fecha final
        from datetime import timedelta
        fecha_inicio_objetivo = fecha_final - timedelta(days=años_objetivo * 365.25)
        
        # Filtrar datos para obtener el precio más cercano a la fecha objetivo
        datos_periodo = precios[precios['Dates'] >= fecha_inicio_objetivo]
        
        if len(datos_periodo) == 0:
            return np.nan
        
        # Precio inicial del período objetivo y precio final
        precio_inicial = datos_periodo.iloc[0, 1]  # Primer precio del período
        precio_final = precios.iloc[-1, 1]         # Último precio disponible
        
        if pd.isna(precio_inicial) or pd.isna(precio_final) or precio_inicial == 0:
            return np.nan
        
        # Calcular rentabilidad simple del período
        rentabilidad_total = (precio_final / precio_inicial) - 1
        
        # Convertir a rentabilidad anualizada usando exactamente los años objetivo
        rentabilidad_anualizada = (((1 + rentabilidad_total) ** (1/años_objetivo)) - 1) * 100
        
        return rentabilidad_anualizada
        
    except Exception as e:
        return np.nan

def obtener_años_automaticos(fecha_actual):
    """
    Obtiene los dos años previos de manera automática
    """
    año_actual = fecha_actual.year
    return año_actual - 1, año_actual - 2  # Ej: 2025 -> (2024, 2023)

def calcular_rentabilidad_periodo(precios, dias, precio_actual):
    """
    Función auxiliar para calcular rentabilidad por período
    """
    from datetime import timedelta
    fecha_objetivo = precios['Dates'].max() - timedelta(days=dias)
    precio_pasado = precios[precios['Dates'] >= fecha_objetivo]
    
    if len(precio_pasado) > 0:
        precio_inicial = precio_pasado.iloc[0, 1]
        return ((precio_actual / precio_inicial) - 1) * 100
    return np.nan

def calcular_rentabilidades_completas_pdf(df, codigos_seleccionados, nombres_mostrar):
    """
    Función completa para calcular todas las rentabilidades para el PDF mejorado
    """
    resultados = []
    fecha_actual = df['Dates'].max()
    año_1, año_2 = obtener_años_automaticos(fecha_actual)
    
    for i, (codigo, nombre) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
        if codigo in df.columns:
            precios = df[['Dates', codigo]].dropna()
            
            if len(precios) > 0:
                precio_actual = precios[codigo].iloc[-1]
                
                # Cálculos existentes
                rent_1m = calcular_rentabilidad_periodo(precios, 30, precio_actual)
                rent_3m = calcular_rentabilidad_periodo(precios, 90, precio_actual)
                rent_12m = calcular_rentabilidad_periodo(precios, 365, precio_actual)
                
                # Nuevos cálculos
                rent_diaria = calcular_rentabilidad_diaria(precios)
                rent_mtd = calcular_rentabilidad_mtd(precios, fecha_actual)
                rent_ytd = calcular_rentabilidad_ytd_mejorado(precios, fecha_actual)
                rent_año_1 = calcular_rentabilidad_año_especifico(precios, año_1)
                rent_año_2 = calcular_rentabilidad_año_especifico(precios, año_2)
                
                # Rentabilidades anualizadas con validación
                rent_3a_anual = calcular_rentabilidad_anualizada_con_validacion(precios, 3)
                rent_5a_anual = calcular_rentabilidad_anualizada_con_validacion(precios, 5)
                
                # Separar fondo y serie del nombre completo
                partes = nombre.split(' - ')
                fondo = partes[0] if len(partes) > 0 else nombre
                serie = partes[1] if len(partes) > 1 else 'N/A'
                
                resultados.append({
                    'Fondo': fondo,
                    'Serie': serie,
                    'Valor Cuota': round(precio_actual, 2),
                    'TAC': round(np.random.uniform(0.5, 2.5), 2),  # Simulado
                    'Diaria': rent_diaria,
                    '1 Mes': rent_1m,
                    '3 Meses': rent_3m,
                    '12 Meses': rent_12m,
                    'MTD': rent_mtd,
                    'YTD': rent_ytd,
                    f'Año {año_1}': rent_año_1,
                    f'Año {año_2}': rent_año_2,
                    '3 Años*': rent_3a_anual,
                    '5 Años**': rent_5a_anual
                })
    
    return pd.DataFrame(resultados).round(2)

def categorizar_fondos(fondos_unicos):
    """
    Categoriza los fondos según su tipo
    
    Args:
        fondos_unicos (list): Lista de nombres únicos de fondos
        
    Returns:
        dict: Diccionario con categorías y sus fondos correspondientes
    """
    categorias = {
        'Renta Fija Nacional': [],
        'Renta Fija Internacional': [],
        'Multifondos': [],
        'Equity (Acciones)': [],
        'Estrategias Alternativas': [],
        'Otros': []
    }
    
    for fondo in fondos_unicos:
        fondo_lower = fondo.lower()
        
        # Renta Fija Nacional
        if any(palabra in fondo_lower for palabra in ['renta', 'bonos', 'deuda']) and \
           any(palabra in fondo_lower for palabra in ['chile', 'chileno', 'nacional']):
            categorias['Renta Fija Nacional'].append(fondo)
            
        # Renta Fija Internacional
        elif any(palabra in fondo_lower for palabra in ['renta', 'bonos', 'deuda', 'fixed income']):
            categorias['Renta Fija Internacional'].append(fondo)
            
        # Multifondos
        elif any(palabra in fondo_lower for palabra in ['multiactivo', 'cartera', 'patrimonial']):
            categorias['Multifondos'].append(fondo)
            
        # Equity
        elif any(palabra in fondo_lower for palabra in ['equity', 'acciones', 'accionario']):
            categorias['Equity (Acciones)'].append(fondo)
            
        # Estrategias Alternativas
        elif any(palabra in fondo_lower for palabra in ['dynamic', 'estrategia', 'alternativa', 'hedge']):
            categorias['Estrategias Alternativas'].append(fondo)
            
        # Otros
        else:
            categorias['Otros'].append(fondo)
    
    return categorias

def crear_tabla_categoria(categoria, fondos_categoria, df_actual, fondos_a_series, fondo_serie_a_codigo, calcular_rentabilidades_func, moneda='CLP'):
    """
    Crea una tabla para una categoría específica de fondos
    """
    if not fondos_categoria:
        return html.Div()
    
    # Obtener códigos y nombres para esta categoría
    codigos_categoria = []
    nombres_categoria = []
    
    for fondo in fondos_categoria:
        if fondo in fondos_a_series:
            # Verificar que la moneda esté disponible para este fondo
            if moneda in fondos_a_series[fondo]:
                for serie in fondos_a_series[fondo][moneda]:
                    if (fondo, serie, moneda) in fondo_serie_a_codigo:
                        codigo = fondo_serie_a_codigo[(fondo, serie, moneda)]
                        nombre_completo = f"{fondo} - {serie}"
                        codigos_categoria.append(codigo)
                        nombres_categoria.append(nombre_completo)
    
    if not codigos_categoria:
        return html.Div()
    
    # Calcular rentabilidades usando la función pasada como parámetro
    tabla_data = obtener_informe_pdf_completo_precalculado(
        moneda, 
        codigos_categoria, 
        nombres_categoria
    )    
    # Seleccionar columnas para el informe
    columnas_disponibles = [col for col in CONFIG['COLUMNAS_INFORME'] if col in tabla_data.columns]
    tabla_data = tabla_data[columnas_disponibles]

    return html.Div([
        html.H5(categoria, style={
            'fontFamily': 'SuraSans-SemiBold', 
            'marginBottom': '15px',
            'color': '#24272A',
            'borderBottom': '2px solid #0B2DCE',
            'paddingBottom': '5px',
            'marginTop': '25px'
        }),
        
        dash_table.DataTable(
            data=tabla_data.to_dict('records'),
            columns=[
                {"name": "Nombre Fondo", "id": "Fondo", "presentation": "markdown"},
                {"name": "Serie", "id": "Serie"},
                {"name": "TAC (%)", "id": "TAC", "type": "numeric", "format": {"specifier": ".2f"}},
                {"name": "1 Mes (%)", "id": "1 Mes", "type": "numeric", "format": {"specifier": ".2f"}},
                {"name": "3 Meses (%)", "id": "3 Meses", "type": "numeric", "format": {"specifier": ".2f"}},
                {"name": "12 Meses (%)", "id": "12 Meses", "type": "numeric", "format": {"specifier": ".2f"}},
                {"name": "YTD (%)", "id": "YTD", "type": "numeric", "format": {"specifier": ".2f"}}
            ],
            style_table={
                'overflowX': 'auto', 
                'marginBottom': '30px',
                'border': '1px solid #dee2e6',
                'borderRadius': '5px'
            },
            style_cell={
                'textAlign': 'left',
                'fontFamily': 'SuraSans-Regular',
                'fontSize': '12px',
                'padding': '12px 8px',
                'border': '1px solid #dee2e6'
            },
            style_header={
                'backgroundColor': '#24272A',
                'color': 'white',
                'fontFamily': 'SuraSans-SemiBold',
                'fontWeight': 'bold',
                'textAlign': 'center',
                'border': '1px solid #24272A'
            },
            style_data={
                'border': '1px solid #dee2e6'
            },
            style_data_conditional=[
                # Colores para rentabilidades positivas
                {
                    'if': {'column_id': col, 'filter_query': f'{{{col}}} > 0'},
                    'color': '#28a745',
                    'fontWeight': 'bold'
                } for col in ['1 Mes', '3 Meses', '12 Meses', 'YTD']
            ] + [
                # Colores para rentabilidades negativas
                {
                    'if': {'column_id': col, 'filter_query': f'{{{col}}} < 0'},
                    'color': '#dc3545',
                    'fontWeight': 'bold'
                } for col in ['1 Mes', '3 Meses', '12 Meses', 'YTD']
            ] + [
                # Estilo para nombre del fondo
                {
                    'if': {'column_id': 'Fondo'},
                    'fontWeight': '600',
                    'color': '#24272A'
                },
                # Estilo para serie
                {
                    'if': {'column_id': 'Serie'},
                    'textAlign': 'center',
                    'fontWeight': 'bold',
                    'backgroundColor': '#f8f9fa'
                }
            ]
        )
    ])

def crear_modal_informe():
    """
    Crea el modal del informe de rentabilidad con opciones de descarga
    """
    return dbc.Modal([
        dbc.ModalHeader([
            dbc.ModalTitle([
                html.I(className="fas fa-chart-line", style={'marginRight': '10px', 'color': '#0B2DCE'}),
                "Informe de Rentabilidad por Categorías"
            ], style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '24px'}),
        ], close_button=True),
        
        dbc.ModalBody([
            # Panel de controles
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Moneda:", style={
                                'fontFamily': 'SuraSans-SemiBold', 
                                'fontSize': '14px',
                                'color': '#24272A'
                            }),
                            dcc.Dropdown(
                                id='moneda-selector-informe',
                                options=[
                                    {'label': '🇨🇱 Pesos Chilenos (CLP)', 'value': 'CLP'},
                                    {'label': '🇺🇸 Dólares (USD)', 'value': 'USD'}
                                ],
                                value='CLP',
                                style={'fontFamily': 'SuraSans-Regular'}
                            )
                        ], width=3),
                        
                        dbc.Col([
                            html.Label("Fecha del reporte:", style={
                                'fontFamily': 'SuraSans-SemiBold', 
                                'fontSize': '14px',
                                'color': '#24272A'
                            }),
                            html.P(
                                datetime.now().strftime("%d de %B de %Y"),
                                style={
                                    'fontFamily': 'SuraSans-Regular',
                                    'margin': '0',
                                    'padding': '8px 12px',
                                    'backgroundColor': '#f8f9fa',
                                    'border': '1px solid #dee2e6',
                                    'borderRadius': '4px',
                                    'fontSize': '14px'
                                }
                            )
                        ], width=3),
                        
                        dbc.Col([
                            html.Label("Descargar como:", style={
                                'fontFamily': 'SuraSans-SemiBold', 
                                'fontSize': '14px',
                                'color': '#24272A'
                            }),
                            html.Div([
                                dbc.ButtonGroup([
                                    dbc.Button([
                                        html.I(className="fas fa-file-excel", style={'marginRight': '8px'}),
                                        "Excel"
                                    ], 
                                    id="btn-descargar-excel", 
                                    color="success", 
                                    outline=True,
                                    size="sm",
                                    style={'fontFamily': 'SuraSans-Regular'}),
                                    
                                    dbc.Button([
                                        html.I(className="fas fa-file-pdf", style={'marginRight': '8px'}),
                                        "PDF"
                                    ], 
                                    id="btn-descargar-pdf", 
                                    color="danger", 
                                    outline=True,
                                    size="sm",
                                    disabled=not PDF_AVAILABLE,
                                    style={'fontFamily': 'SuraSans-Regular'})
                                ], size="sm")
                            ])
                        ], width=3),
                        
                        dbc.Col([
                            html.Label("Estado:", style={
                                'fontFamily': 'SuraSans-SemiBold', 
                                'fontSize': '14px',
                                'color': '#24272A'
                            }),
                            html.Div(id="estado-descarga", children=[
                                html.P("Listo para descargar", style={
                                    'fontFamily': 'SuraSans-Regular',
                                    'margin': '0',
                                    'padding': '8px 12px',
                                    'backgroundColor': '#d4edda',
                                    'border': '1px solid #c3e6cb',
                                    'borderRadius': '4px',
                                    'fontSize': '12px',
                                    'color': '#155724'
                                })
                            ])
                        ], width=3)
                    ])
                ])
            ], style={'marginBottom': '20px', 'border': '1px solid #dee2e6'}),
            
            # Componente oculto para descargas
            dcc.Download(id="download-informe"),
            
            # Contenedor para las tablas del informe
            html.Div(id='contenido-informe-rentabilidad')
            
        ], style={
            'padding': '20px', 
            'maxHeight': '75vh', 
            'overflowY': 'auto',
            'backgroundColor': '#f8f9fa'
        }),
        
    ], id="modal-informe", is_open=False, size="xl", centered=True)

def generar_excel_informe(datos_por_categoria, moneda):
    """
    Genera un archivo Excel con el informe de rentabilidad
    
    Args:
        datos_por_categoria (dict): Datos organizados por categoría
        moneda (str): Moneda seleccionada (CLP/USD)
        
    Returns:
        str: String base64 del archivo Excel
    """
    try:
        # Crear un buffer en memoria
        output = io.BytesIO()
        
        # Crear el archivo Excel
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # Hoja resumen
            resumen_data = []
            for categoria, tabla_data in datos_por_categoria.items():
                if not tabla_data.empty:
                    resumen_data.append({
                        'Categoría': categoria,
                        'Número de Fondos': len(tabla_data),
                        'Rentabilidad Promedio 1M (%)': round(tabla_data['1 Mes'].mean(), 2),
                        'Rentabilidad Promedio 3M (%)': round(tabla_data['3 Meses'].mean(), 2),
                        'Rentabilidad Promedio 12M (%)': round(tabla_data['12 Meses'].mean(), 2),
                        'Rentabilidad Promedio YTD (%)': round(tabla_data['YTD'].mean(), 2)
                    })
            
            if resumen_data:
                df_resumen = pd.DataFrame(resumen_data)
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
                
                # Formatear hoja resumen
                workbook = writer.book
                worksheet = writer.sheets['Resumen']
                
                # Ajustar ancho de columnas
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Hoja por cada categoría
            for categoria, tabla_data in datos_por_categoria.items():
                if not tabla_data.empty:
                    # Limpiar nombre para usar como nombre de hoja
                    sheet_name = categoria.replace('(', '').replace(')', '')[:31]
                    tabla_data.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Formatear hoja
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Obtener el contenido del buffer
        excel_data = output.getvalue()
        
        # Codificar en base64
        excel_b64 = base64.b64encode(excel_data).decode()
        
        return excel_b64
        
    except Exception as e:
        logging.error(f"Error generando Excel: {e}")
        return None


def calcular_ancho_columna_dinamico(datos_tabla, indice_columna, ancho_minimo=20*mm, ancho_maximo=60*mm):
    """
    Calcula el ancho óptimo de una columna basado en su contenido
    
    Args:
        datos_tabla (list): Datos de la tabla incluyendo headers
        indice_columna (int): Índice de la columna a analizar
        ancho_minimo (float): Ancho mínimo en mm
        ancho_maximo (float): Ancho máximo en mm
        
    Returns:
        float: Ancho calculado en mm
    """
    try:
        # Obtener todos los valores de la columna
        valores_columna = [fila[indice_columna] for fila in datos_tabla if len(fila) > indice_columna]
        
        if not valores_columna:
            return ancho_minimo
        
        # Calcular el texto más largo
        texto_mas_largo = max(valores_columna, key=len)
        longitud_maxima = len(str(texto_mas_largo))
        
        # Fórmula para calcular ancho basado en caracteres
        # Aproximadamente 2.5mm por caracter para fuente Helvetica tamaño 7-8
        ancho_calculado = longitud_maxima * 2.8 * mm
        
        # Aplicar límites mínimo y máximo
        ancho_final = max(ancho_minimo, min(ancho_calculado, ancho_maximo))
        
        return ancho_final
        
    except Exception as e:
        logging.warning(f"Error calculando ancho dinámico: {e}")
        return ancho_minimo

# def generar_pdf_informe(datos_por_categoria, moneda):
#     """
#     Genera un archivo PDF con el informe de rentabilidad MEJORADO
#     Con las nuevas columnas solicitadas
#     """
#     if not PDF_AVAILABLE:
#         return None
        
#     try:
#         from reportlab.lib.pagesizes import A4, landscape
#         from reportlab.lib.units import mm
#         from reportlab.platypus import PageBreak, PageTemplate, BaseDocTemplate, Frame
#         from reportlab.pdfbase import pdfmetrics
#         from reportlab.pdfbase.ttfonts import TTFont
        
#         # Registrar las fuentes SuraSans
#         try:
#             pdfmetrics.registerFont(TTFont('SuraSans-Regular', 'assets/SuraSans-Regular'))
#             pdfmetrics.registerFont(TTFont('SuraSans-SemiBold', 'assets/SuraSans-SemiBold'))
#             pdfmetrics.registerFont(TTFont('SuraSans-Bold', 'assets/SuraSans-Bold'))
#             fuentes_disponibles = True
#         except:
#             fuentes_disponibles = False
        
#         # Crear un buffer en memoria
#         buffer = io.BytesIO()
        
#         # Usar página HORIZONTAL (A4 rotado) para las nuevas columnas
#         page_size = landscape(A4)
        
#         doc = BaseDocTemplate(buffer, pagesize=page_size, 
#                               rightMargin=10*mm, leftMargin=10*mm,
#                               topMargin=30*mm, bottomMargin=10*mm)
        
#         # COLORES EXACTOS DEL INFORME OFICIAL SURA
#         COLOR_SURA_BLACK = colors.HexColor('#24272A')
#         COLOR_SURA_WHITE = colors.white
#         COLOR_SURA_GRAY = colors.HexColor('#D4D8D8')
#         COLOR_SUBTITLE_GRAY = colors.HexColor('#5A646E')
#         COLOR_POSITIVE = colors.HexColor('#008000')
#         COLOR_NEGATIVE = colors.HexColor('#FF0000')
#         COLOR_NEUTRAL = colors.black
#         COLOR_BG_ALTERNATING = colors.HexColor('#F8F9FA')
        
#         # Función para crear la barra superior con logos
#         def crear_barra_superior_header(canvas, doc):
#             canvas.saveState()
            
#             page_width = page_size[0]
#             page_height = page_size[1]
            
#             # Crear rectángulo negro para la barra
#             canvas.setFillColor(COLOR_SURA_BLACK)
#             canvas.rect(0, page_height - 25*mm, page_width, 25*mm, fill=1, stroke=0)
            
#             # Intentar agregar logo SURA a la izquierda
#             try:
#                 canvas.drawImage('assets/sura_logo_blanco.png', 
#                                15*mm, page_height - 22*mm, 
#                                width=60*mm, height=12*mm, 
#                                preserveAspectRatio=True,
#                                mask='auto')
#             except:
#                 canvas.setFillColor(COLOR_SURA_WHITE)
#                 canvas.setFont("Helvetica-Bold", 12)
#                 canvas.drawString(15*mm, page_height - 15*mm, "SURA")
            
#             # Intentar agregar logo INVESTMENTS a la derecha
#             try:
#                 canvas.drawImage('assets/investments_blanco.png', 
#                                page_width - 45*mm, page_height - 18*mm, 
#                                width=35*mm, height=6*mm,
#                                preserveAspectRatio=True,
#                                mask='auto')
#             except:
#                 canvas.setFillColor(COLOR_SURA_WHITE)
#                 canvas.setFont("Helvetica-Bold", 12)
#                 canvas.drawString(page_width - 80*mm, page_height - 15*mm, "INVESTMENTS")
            
#             canvas.restoreState()
        
#         # Crear frame para el contenido
#         frame = Frame(10*mm, 10*mm, page_size[0] - 20*mm, page_size[1] - 40*mm,
#                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        
#         # Crear template de página con header
#         template = PageTemplate(id='todas_paginas', frames=[frame], 
#                                onPage=crear_barra_superior_header)
#         doc.addPageTemplates([template])
        
#         # Obtener estilos
#         styles = getSampleStyleSheet()
        
#         # Crear header principal
#         header_style = ParagraphStyle(
#             'HeaderStyle',
#             parent=styles['Normal'],
#             fontSize=16,
#             spaceAfter=5,
#             alignment=TA_LEFT,
#             textColor=COLOR_SURA_BLACK,
#             fontName='SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold'
#         )
        
#         # Subtítulo
#         info_style = ParagraphStyle(
#             'InfoStyle',
#             parent=styles['Normal'],
#             fontSize=8,
#             spaceAfter=15,
#             alignment=TA_LEFT,
#             textColor=COLOR_SUBTITLE_GRAY,
#             fontName='SuraSans-Regular' if fuentes_disponibles else 'Helvetica'
#         )
        
#         category_style = ParagraphStyle(
#             'CategoryStyle',
#             parent=styles['Normal'],
#             fontSize=12,
#             leading=14,
#             spaceBefore=12,
#             spaceAfter=12,
#             textColor=COLOR_SURA_WHITE,
#             fontName='SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold',
#             backColor="#9BA4AE",
#             leftIndent=1,
#             rightIndent=0,
#             alignment=0
#         )
        
#         # Contenido del PDF
#         story = []
        
#         # HEADER PRINCIPAL
#         fecha_formateada = datetime.now().strftime("%d/%m/%Y")
#         header_text = f"INFORME DIARIO DE RENTABILIDAD AL {fecha_formateada}"
#         story.append(Paragraph(header_text, header_style))
        
#         # Subtítulo de moneda
#         subtitle_text = f"Rentabilidad Nominal en {moneda}"
#         story.append(Paragraph(subtitle_text, info_style))
        
#         story.append(Spacer(1, 15))
        
#         # Procesar cada categoría con el formato MEJORADO
#         for categoria in CONFIG['ORDEN_CATEGORIAS']:
#             if categoria in datos_por_categoria and not datos_por_categoria[categoria].empty:
#                 tabla_data = datos_por_categoria[categoria]
                
#                 # TÍTULO DE CATEGORÍA
#                 texto_con_espacios = f"<br/>{categoria.upper()}<br/>&nbsp;<br/>"
#                 category_header = Paragraph(texto_con_espacios, category_style)
#                 story.append(category_header)
                
#                 # HEADERS DE TABLA MEJORADOS - CON NUEVAS COLUMNAS
#                 # Obtener años automáticos para los headers
#                 año_actual = datetime.now().year
#                 año_1 = año_actual - 1
#                 año_2 = año_actual - 2
                
#                 headers = [
#                     'Fondo', 'Serie', 'Valor Cuota', 'Moneda', 'TAC', 'Diaria', 
#                     '1 MES', '3 MESES', '12 M', 'MTD', 'YTD', 
#                     f'Año {año_1}', f'Año {año_2}', '3 Años*', '5 Años**'
#                 ]
                
#                 table_data = [headers]
                
#                 # DATOS DE LA TABLA CON SEPARADORES
#                 fondos_agrupados = {}
#                 for _, row in tabla_data.iterrows():
#                     nombre_fondo = row['Fondo'].replace('FONDO MUTUO SURA ', '').replace('SURA ', '')
#                     if nombre_fondo not in fondos_agrupados:
#                         fondos_agrupados[nombre_fondo] = []
#                     fondos_agrupados[nombre_fondo].append(row)
                
#                 primer_fondo = True
#                 for nombre_fondo, filas_fondo in fondos_agrupados.items():
#                     # Agregar fila separadora antes de cada fondo (excepto el primero)
#                     if not primer_fondo:
#                         fila_separadora = [''] * len(headers)
#                         table_data.append(fila_separadora)
                    
#                     # Agregar todas las filas de este fondo
#                     for row in filas_fondo:
#                         def formatear_valor(valor):
#                             """Formatea valores con manejo de NaN"""
#                             if pd.isna(valor):
#                                 return "---"
#                             elif isinstance(valor, (int, float)):
#                                 return f"{valor:.2f}%"
#                             else:
#                                 return str(valor)
                        
#                         table_row = [
#                             nombre_fondo,                                    # Fondo
#                             str(row['Serie']),                              # Serie
#                             f"{row['Valor Cuota']:.2f}",                   # Valor Cuota
#                             moneda,                                         # Moneda
#                             f"{row['TAC']:.2f}%",                         # TAC
#                             formatear_valor(row['Diaria']),               # Diaria
#                             formatear_valor(row['1 Mes']),                # 1 MES
#                             formatear_valor(row['3 Meses']),              # 3 MESES
#                             formatear_valor(row['12 Meses']),             # 12 M
#                             formatear_valor(row['MTD']),                  # MTD
#                             formatear_valor(row['YTD']),                  # YTD
#                             formatear_valor(row[f'Año {año_1}']),         # Año anterior
#                             formatear_valor(row[f'Año {año_2}']),         # Dos años atrás
#                             formatear_valor(row['3 Años*']),              # 3 Años anualizada
#                             formatear_valor(row['5 Años**'])              # 5 Años anualizada
#                         ]
#                         table_data.append(table_row)
                    
#                     primer_fondo = False
                
#                 # CALCULAR ANCHOS DE COLUMNAS PARA PÁGINA HORIZONTAL
#                 ancho_total_disponible = page_size[0] - 20*mm
                
#                 # Nuevos anchos optimizados para 15 columnas
#                 anchos_columnas = [
#                     46*mm,  # Fondo (más ancho)
#                     12*mm,  # Serie
#                     18*mm,  # Valor Cuota
#                     14*mm,  # Moneda
#                     15*mm,  # TAC
#                     15*mm,  # Diaria
#                     15*mm,  # 1 MES
#                     15*mm,  # 3 MESES
#                     15*mm,  # 12 M
#                     15*mm,  # MTD
#                     15*mm,  # YTD
#                     18*mm,  # Año anterior
#                     18*mm,  # Dos años atrás
#                     18*mm,  # 3 Años*
#                     18*mm   # 5 Años**
#                 ]
                
#                 # Verificar que no exceda el ancho disponible
#                 ancho_total_calculado = sum(anchos_columnas)
#                 factor_expansion = ancho_total_disponible / ancho_total_calculado
#                 anchos_columnas = [ancho * factor_expansion for ancho in anchos_columnas]
                
#                 # Crear tabla
#                 table = Table(table_data, colWidths=anchos_columnas, repeatRows=1)
                
#                 # ESTILOS DE TABLA MEJORADOS
#                 table_style = [
#                     # HEADER - Fondo negro, texto blanco, centrado
#                     ('BACKGROUND', (0, 0), (-1, 0), COLOR_SURA_BLACK),
#                     ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_SURA_WHITE),
#                     ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
#                     ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
#                     ('FONTNAME', (0, 0), (-1, 0), 'SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold'),
#                     ('FONTSIZE', (0, 0), (-1, 0), 8),  # Fuente más pequeña por más columnas
#                     ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
#                     ('TOPPADDING', (0, 0), (-1, 0), 4),
                    
#                     # DATOS - Estilo general
#                     ('FONTNAME', (0, 1), (-1, -1), 'SuraSans-Regular' if fuentes_disponibles else 'Helvetica'),
#                     ('FONTSIZE', (0, 1), (-1, -1), 6.5),  # Fuente más pequeña
#                     ('TOPPADDING', (0, 1), (-1, -1), 2),
#                     ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
#                     ('LEFTPADDING', (0, 0), (-1, -1), 1),
#                     ('RIGHTPADDING', (0, 0), (-1, -1), 1),
                    
#                     # BORDES
#                     ('GRID', (0, 0), (-1, -1), 0.5, COLOR_SURA_GRAY),
#                     ('LINEBELOW', (0, 0), (-1, 0), 1, COLOR_SURA_BLACK),
                    
#                     # ALINEACIÓN POR COLUMNAS
#                     ('ALIGN', (0, 1), (0, -1), 'LEFT'),     # Fondo
#                     ('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Resto centrado
#                     ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    
#                     # PERMITIR WRAP DE TEXTO EN COLUMNA FONDO
#                     ('WORDWRAP', (0, 1), (0, -1), True),
#                 ]
                
#                 # APLICAR COLORES CONDICIONALES A TODAS LAS COLUMNAS DE RENTABILIDAD
#                 columnas_rentabilidad = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14]  # Índices de columnas de rentabilidad
                
#                 for row_idx in range(1, len(table_data)):
#                     # Verificar si es una fila separadora
#                     es_fila_separadora = all(cell == '' for cell in table_data[row_idx])
                    
#                     if es_fila_separadora:
#                         # Aplicar estilo de fila separadora gris
#                         table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), COLOR_SURA_GRAY))
#                         table_style.append(('TOPPADDING', (0, row_idx), (-1, row_idx), 1))
#                         table_style.append(('BOTTOMPADDING', (0, row_idx), (-1, row_idx), 1))
#                     else:
#                         # Aplicar colores a columnas de rentabilidad
#                         for col_idx in columnas_rentabilidad:
#                             try:
#                                 valor_str = table_data[row_idx][col_idx]
#                                 if valor_str != "---":
#                                     valor_numerico = float(valor_str.replace('%', ''))
                                    
#                                     if valor_numerico > 0:
#                                         table_style.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), COLOR_POSITIVE))
#                                         table_style.append(('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold'))
#                                     elif valor_numerico < 0:
#                                         table_style.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), COLOR_NEGATIVE))
#                                         table_style.append(('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold'))
#                             except (ValueError, IndexError):
#                                 pass
                        
#                         # FILAS ALTERNADAS
#                         if row_idx % 2 == 0:
#                             table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), COLOR_BG_ALTERNATING))
                
#                 # Aplicar estilos
#                 table.setStyle(TableStyle(table_style))
                
#                 story.append(table)
#                 story.append(Spacer(1, 15))
        
#         # FOOTER con notas explicativas
#         footer_style_principal = ParagraphStyle(
#             'FooterStylePrincipal',
#             parent=styles['Normal'],
#             fontSize=9,
#             alignment=TA_CENTER,
#             textColor=COLOR_SURA_BLACK,
#             fontName='SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold',
#             spaceAfter=8
#         )

#         footer_style_notas = ParagraphStyle(
#             'FooterStyleNotas',
#             parent=styles['Normal'],
#             fontSize=7,
#             alignment=TA_LEFT,
#             textColor=COLOR_SUBTITLE_GRAY,
#             fontName='SuraSans-Regular' if fuentes_disponibles else 'Helvetica',
#             spaceAfter=3
#         )

#         footer_style_secundario = ParagraphStyle(
#             'FooterStyleSecundario',
#             parent=styles['Normal'],
#             fontSize=8,
#             alignment=TA_CENTER,
#             textColor=COLOR_SUBTITLE_GRAY,
#             fontName='SuraSans-Regular' if fuentes_disponibles else 'Helvetica',
#             spaceAfter=5
#         )
        
#         # Definir hora de generación
#         hora_generacion = datetime.now().strftime("%d/%m/%Y")
        
#         # Agregar footer con explicaciones
#         story.append(Spacer(1, 20))

#         # Notas explicativas
#         story.append(Paragraph("<b>DEFINICIONES DE PERÍODOS:</b>", footer_style_notas))
#         story.append(Paragraph("• Diaria: Variación entre el último día disponible y el día anterior", footer_style_notas))
#         story.append(Paragraph("• MTD: Rentabilidad desde el último dato del mes anterior hasta la fecha actual", footer_style_notas))
#         story.append(Paragraph("• YTD: Rentabilidad desde el último dato del año anterior hasta la fecha actual", footer_style_notas))
#         story.append(Paragraph("• 1 Mes, 3 Meses, 12 Meses: Calculados en días calendario (30, 90 y 365 días respectivamente)", footer_style_notas))
#         story.append(Paragraph("• * Rentabilidad 3 Años: Rentabilidad Anualizada (solo si hay suficiente historial)", footer_style_notas))
#         story.append(Paragraph("• ** Rentabilidad 5 Años: Rentabilidad Anualizada (solo si hay suficiente historial)", footer_style_notas))

#         story.append(Spacer(1, 8))
#         story.append(Paragraph("<b>METODOLOGÍA DE CÁLCULO:</b>", footer_style_notas))
#         story.append(Paragraph("• Rentabilidades anualizadas calculadas mediante tasa de crecimiento anual compuesto (CAGR):", footer_style_notas))
#         story.append(Paragraph("&nbsp;&nbsp;R<sub>anualizada</sub> = (P<sub>t</sub>/P<sub>0</sub>)<sup>1/t</sup> - 1", footer_style_notas))
#         story.append(Paragraph("&nbsp;&nbsp;Donde: P<sub>t</sub> = Valor final, P<sub>0</sub> = Valor inicial, t = número de años del período", footer_style_notas))
#         story.append(Paragraph("• Todos los valores se redondean a 2 decimales para presentación final", footer_style_notas))
#         story.append(Paragraph("• Rentabilidad Fondos de Inversión calculada de acuerdo a variación de Valores Cuota", footer_style_notas))

#         story.append(Spacer(1, 8))
#         story.append(Paragraph("<b>FUENTES Y CONSIDERACIONES:</b>", footer_style_notas))
#         story.append(Paragraph("• TAC: Para Fondos Mutuos locales fuente CMF Chile. Para Fondos Mutuos extranjeros fuente Morningstar", footer_style_notas))
#         story.append(Paragraph("• Rentabilidad Multifondos no considera comisión de AFP y tiene un día de desfase respecto a Rentabilidad de Fondos Mutuos", footer_style_notas))

#         story.append(Spacer(1, 8))
#         story.append(Paragraph("<b>ADVERTENCIA:</b>", footer_style_notas))
#         story.append(Paragraph("La rentabilidad o ganancia obtenida en el pasado por estos fondos, no garantiza que ella se repita en el futuro. Los valores de las cuotas de los fondos son variables.", footer_style_notas))
        
#         story.append(Spacer(1, 10))
#         story.append(Paragraph("DOCUMENTO DE USO INTERNO", footer_style_principal))
#         story.append(Paragraph("© 2025 SURA Investments. Todos los derechos reservados.", footer_style_secundario))
#         story.append(Paragraph(f"Generado el {hora_generacion}", footer_style_secundario))
        
#         # Construir PDF
#         doc.build(story)
        
#         # Obtener contenido
#         pdf_data = buffer.getvalue()
#         buffer.close()
        
#         # Codificar en base64
#         pdf_b64 = base64.b64encode(pdf_data).decode()
        
#         return pdf_b64
        
#     except Exception as e:
#         logging.error(f"Error generando PDF mejorado: {e}")
#         return None

def generar_pdf_informe(datos_por_categoria, moneda):
    """
    Genera un archivo PDF con el informe de rentabilidad MEJORADO
    MODIFICADO PARA RENDER.COM
    """
    if not PDF_AVAILABLE:
        return None
        
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
        from reportlab.platypus import PageBreak, PageTemplate, BaseDocTemplate, Frame
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # CAMBIO: Registrar las fuentes SuraSans con rutas relativas
        try:
            # Buscar fuentes en múltiples ubicaciones
            font_paths = [
                './assets/',
                'assets/',
                './static/',
                'static/',
                './'
            ]
            
            fuentes_disponibles = False
            for path in font_paths:
                try:
                    regular_path = os.path.join(path, 'SuraSans-Regular.ttf')
                    semibold_path = os.path.join(path, 'SuraSans-SemiBold.ttf')
                    bold_path = os.path.join(path, 'SuraSans-Bold.ttf')
                    
                    if all(os.path.exists(f) for f in [regular_path, semibold_path, bold_path]):
                        pdfmetrics.registerFont(TTFont('SuraSans-Regular', regular_path))
                        pdfmetrics.registerFont(TTFont('SuraSans-SemiBold', semibold_path))
                        pdfmetrics.registerFont(TTFont('SuraSans-Bold', bold_path))
                        fuentes_disponibles = True
                        print(f"✅ Fuentes SuraSans cargadas desde: {path}")
                        break
                except Exception as e:
                    continue
            
            if not fuentes_disponibles:
                print("⚠️ No se pudieron cargar las fuentes SuraSans, usando fuentes del sistema")
                
        except Exception as e:
            print(f"⚠️ Error cargando fuentes: {e}")
            fuentes_disponibles = False
        
        # Crear un buffer en memoria
        buffer = io.BytesIO()
        
        # Usar página HORIZONTAL (A4 rotado) para las nuevas columnas
        page_size = landscape(A4)
        
        doc = BaseDocTemplate(buffer, pagesize=page_size, 
                              rightMargin=10*mm, leftMargin=10*mm,
                              topMargin=30*mm, bottomMargin=10*mm)
        
        # COLORES EXACTOS DEL INFORME OFICIAL SURA
        COLOR_SURA_BLACK = colors.HexColor('#24272A')
        COLOR_SURA_WHITE = colors.white
        COLOR_SURA_GRAY = colors.HexColor('#D4D8D8')
        COLOR_SUBTITLE_GRAY = colors.HexColor('#5A646E')
        COLOR_POSITIVE = colors.HexColor('#008000')
        COLOR_NEGATIVE = colors.HexColor('#FF0000')
        COLOR_NEUTRAL = colors.black
        COLOR_BG_ALTERNATING = colors.HexColor('#F8F9FA')
        
        # Función para crear la barra superior con logos
        def crear_barra_superior_header(canvas, doc):
            canvas.saveState()
            
            page_width = page_size[0]
            page_height = page_size[1]
            
            # Crear rectángulo negro para la barra
            canvas.setFillColor(COLOR_SURA_BLACK)
            canvas.rect(0, page_height - 25*mm, page_width, 25*mm, fill=1, stroke=0)
            
            # CAMBIO: Intentar agregar logo SURA con rutas múltiples
            logo_loaded = False
            logo_paths = ['./assets/', 'assets/', './static/', 'static/', './']
            
            for path in logo_paths:
                try:
                    logo_path = os.path.join(path, 'sura_logo_blanco.png')
                    if os.path.exists(logo_path):
                        canvas.drawImage(logo_path, 
                                       15*mm, page_height - 22*mm, 
                                       width=60*mm, height=12*mm, 
                                       preserveAspectRatio=True,
                                       mask='auto')
                        logo_loaded = True
                        break
                except Exception as e:
                    continue
            
            if not logo_loaded:
                # Fallback a texto si no se encuentra la imagen
                canvas.setFillColor(COLOR_SURA_WHITE)
                canvas.setFont("Helvetica-Bold", 12)
                canvas.drawString(15*mm, page_height - 15*mm, "SURA")
            
            # CAMBIO: Mismo tratamiento para logo INVESTMENTS
            investments_loaded = False
            for path in logo_paths:
                try:
                    investments_path = os.path.join(path, 'investments_blanco.png')
                    if os.path.exists(investments_path):
                        canvas.drawImage(investments_path, 
                                       page_width - 45*mm, page_height - 18*mm, 
                                       width=35*mm, height=6*mm,
                                       preserveAspectRatio=True,
                                       mask='auto')
                        investments_loaded = True
                        break
                except Exception as e:
                    continue
            
            if not investments_loaded:
                canvas.setFillColor(COLOR_SURA_WHITE)
                canvas.setFont("Helvetica-Bold", 12)
                canvas.drawString(page_width - 80*mm, page_height - 15*mm, "INVESTMENTS")
            
            canvas.restoreState()
        
        # Crear frame para el contenido
        frame = Frame(10*mm, 10*mm, page_size[0] - 20*mm, page_size[1] - 40*mm,
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        
        # Crear template de página con header
        template = PageTemplate(id='todas_paginas', frames=[frame], 
                               onPage=crear_barra_superior_header)
        doc.addPageTemplates([template])
        
        # Obtener estilos
        styles = getSampleStyleSheet()
        
        # Crear header principal
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=16,
            spaceAfter=5,
            alignment=TA_LEFT,
            textColor=COLOR_SURA_BLACK,
            fontName='SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold'
        )
        
        # Subtítulo
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=8,
            spaceAfter=15,
            alignment=TA_LEFT,
            textColor=COLOR_SUBTITLE_GRAY,
            fontName='SuraSans-Regular' if fuentes_disponibles else 'Helvetica'
        )
        
        category_style = ParagraphStyle(
            'CategoryStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=14,
            spaceBefore=12,
            spaceAfter=12,
            textColor=COLOR_SURA_WHITE,
            fontName='SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold',
            backColor="#9BA4AE",
            leftIndent=1,
            rightIndent=0,
            alignment=0
        )
        
        # Contenido del PDF
        story = []
        
        # HEADER PRINCIPAL
        fecha_formateada = datetime.now().strftime("%d/%m/%Y")
        header_text = f"INFORME DIARIO DE RENTABILIDAD AL {fecha_formateada}"
        story.append(Paragraph(header_text, header_style))
        
        # Subtítulo de moneda
        subtitle_text = f"Rentabilidad Nominal en {moneda}"
        story.append(Paragraph(subtitle_text, info_style))
        
        story.append(Spacer(1, 15))
        
        # Procesar cada categoría con el formato MEJORADO
        for categoria in CONFIG['ORDEN_CATEGORIAS']:
            if categoria in datos_por_categoria and not datos_por_categoria[categoria].empty:
                tabla_data = datos_por_categoria[categoria]
                
                # TÍTULO DE CATEGORÍA
                texto_con_espacios = f"<br/>{categoria.upper()}<br/>&nbsp;<br/>"
                category_header = Paragraph(texto_con_espacios, category_style)
                story.append(category_header)
                
                # HEADERS DE TABLA MEJORADOS - CON NUEVAS COLUMNAS
                # Obtener años automáticos para los headers
                año_actual = datetime.now().year
                año_1 = año_actual - 1
                año_2 = año_actual - 2
                
                headers = [
                    'Fondo', 'Serie', 'Valor Cuota', 'Moneda', 'TAC', 'Diaria', 
                    '1 MES', '3 MESES', '12 M', 'MTD', 'YTD', 
                    f'Año {año_1}', f'Año {año_2}', '3 Años*', '5 Años**'
                ]
                
                table_data = [headers]
                
                # DATOS DE LA TABLA CON SEPARADORES
                fondos_agrupados = {}
                for _, row in tabla_data.iterrows():
                    nombre_fondo = row['Fondo'].replace('FONDO MUTUO SURA ', '').replace('SURA ', '')
                    if nombre_fondo not in fondos_agrupados:
                        fondos_agrupados[nombre_fondo] = []
                    fondos_agrupados[nombre_fondo].append(row)
                
                primer_fondo = True
                for nombre_fondo, filas_fondo in fondos_agrupados.items():
                    # Agregar fila separadora antes de cada fondo (excepto el primero)
                    if not primer_fondo:
                        fila_separadora = [''] * len(headers)
                        table_data.append(fila_separadora)
                    
                    # Agregar todas las filas de este fondo
                    for row in filas_fondo:
                        def formatear_valor(valor):
                            """Formatea valores con manejo de NaN"""
                            if pd.isna(valor):
                                return "---"
                            elif isinstance(valor, (int, float)):
                                return f"{valor:.2f}%"
                            else:
                                return str(valor)
                        
                        table_row = [
                            nombre_fondo,                                    # Fondo
                            str(row['Serie']),                              # Serie
                            f"{row['Valor Cuota']:.2f}",                   # Valor Cuota
                            moneda,                                         # Moneda
                            f"{row['TAC']:.2f}%",                         # TAC
                            formatear_valor(row['Diaria']),               # Diaria
                            formatear_valor(row['1 Mes']),                # 1 MES
                            formatear_valor(row['3 Meses']),              # 3 MESES
                            formatear_valor(row['12 Meses']),             # 12 M
                            formatear_valor(row['MTD']),                  # MTD
                            formatear_valor(row['YTD']),                  # YTD
                            formatear_valor(row[f'Año {año_1}']),         # Año anterior
                            formatear_valor(row[f'Año {año_2}']),         # Dos años atrás
                            formatear_valor(row['3 Años*']),              # 3 Años anualizada
                            formatear_valor(row['5 Años**'])              # 5 Años anualizada
                        ]
                        table_data.append(table_row)
                    
                    primer_fondo = False
                
                # CALCULAR ANCHOS DE COLUMNAS PARA PÁGINA HORIZONTAL
                ancho_total_disponible = page_size[0] - 20*mm
                
                # Nuevos anchos optimizados para 15 columnas
                anchos_columnas = [
                    46*mm,  # Fondo (más ancho)
                    12*mm,  # Serie
                    18*mm,  # Valor Cuota
                    14*mm,  # Moneda
                    15*mm,  # TAC
                    15*mm,  # Diaria
                    15*mm,  # 1 MES
                    15*mm,  # 3 MESES
                    15*mm,  # 12 M
                    15*mm,  # MTD
                    15*mm,  # YTD
                    18*mm,  # Año anterior
                    18*mm,  # Dos años atrás
                    18*mm,  # 3 Años*
                    18*mm   # 5 Años**
                ]
                
                # Verificar que no exceda el ancho disponible
                ancho_total_calculado = sum(anchos_columnas)
                factor_expansion = ancho_total_disponible / ancho_total_calculado
                anchos_columnas = [ancho * factor_expansion for ancho in anchos_columnas]
                
                # Crear tabla
                table = Table(table_data, colWidths=anchos_columnas, repeatRows=1)
                
                # ESTILOS DE TABLA MEJORADOS
                table_style = [
                    # HEADER - Fondo negro, texto blanco, centrado
                    ('BACKGROUND', (0, 0), (-1, 0), COLOR_SURA_BLACK),
                    ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_SURA_WHITE),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),  # Fuente más pequeña por más columnas
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                    ('TOPPADDING', (0, 0), (-1, 0), 4),
                    
                    # DATOS - Estilo general
                    ('FONTNAME', (0, 1), (-1, -1), 'SuraSans-Regular' if fuentes_disponibles else 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 6.5),  # Fuente más pequeña
                    ('TOPPADDING', (0, 1), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
                    ('LEFTPADDING', (0, 0), (-1, -1), 1),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 1),
                    
                    # BORDES
                    ('GRID', (0, 0), (-1, -1), 0.5, COLOR_SURA_GRAY),
                    ('LINEBELOW', (0, 0), (-1, 0), 1, COLOR_SURA_BLACK),
                    
                    # ALINEACIÓN POR COLUMNAS
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),     # Fondo
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Resto centrado
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    
                    # PERMITIR WRAP DE TEXTO EN COLUMNA FONDO
                    ('WORDWRAP', (0, 1), (0, -1), True),
                ]
                
                # APLICAR COLORES CONDICIONALES A TODAS LAS COLUMNAS DE RENTABILIDAD
                columnas_rentabilidad = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14]  # Índices de columnas de rentabilidad
                
                for row_idx in range(1, len(table_data)):
                    # Verificar si es una fila separadora
                    es_fila_separadora = all(cell == '' for cell in table_data[row_idx])
                    
                    if es_fila_separadora:
                        # Aplicar estilo de fila separadora gris
                        table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), COLOR_SURA_GRAY))
                        table_style.append(('TOPPADDING', (0, row_idx), (-1, row_idx), 1))
                        table_style.append(('BOTTOMPADDING', (0, row_idx), (-1, row_idx), 1))
                    else:
                        # Aplicar colores a columnas de rentabilidad
                        for col_idx in columnas_rentabilidad:
                            try:
                                valor_str = table_data[row_idx][col_idx]
                                if valor_str != "---":
                                    valor_numerico = float(valor_str.replace('%', ''))
                                    
                                    if valor_numerico > 0:
                                        table_style.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), COLOR_POSITIVE))
                                        table_style.append(('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold'))
                                    elif valor_numerico < 0:
                                        table_style.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), COLOR_NEGATIVE))
                                        table_style.append(('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold'))
                            except (ValueError, IndexError):
                                pass
                        
                        # FILAS ALTERNADAS
                        if row_idx % 2 == 0:
                            table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), COLOR_BG_ALTERNATING))
                
                # Aplicar estilos
                table.setStyle(TableStyle(table_style))
                
                story.append(table)
                story.append(Spacer(1, 15))
        
        # FOOTER con notas explicativas
        footer_style_principal = ParagraphStyle(
            'FooterStylePrincipal',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=COLOR_SURA_BLACK,
            fontName='SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold',
            spaceAfter=8
        )

        footer_style_notas = ParagraphStyle(
            'FooterStyleNotas',
            parent=styles['Normal'],
            fontSize=7,
            alignment=TA_LEFT,
            textColor=COLOR_SUBTITLE_GRAY,
            fontName='SuraSans-Regular' if fuentes_disponibles else 'Helvetica',
            spaceAfter=3
        )

        footer_style_secundario = ParagraphStyle(
            'FooterStyleSecundario',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=COLOR_SUBTITLE_GRAY,
            fontName='SuraSans-Regular' if fuentes_disponibles else 'Helvetica',
            spaceAfter=5
        )
        
        # Definir hora de generación
        hora_generacion = datetime.now().strftime("%d/%m/%Y")
        
        # Agregar footer con explicaciones
        story.append(Spacer(1, 20))

        # Notas explicativas
        story.append(Paragraph("<b>DEFINICIONES DE PERÍODOS:</b>", footer_style_notas))
        story.append(Paragraph("• Diaria: Variación entre el último día disponible y el día anterior", footer_style_notas))
        story.append(Paragraph("• MTD: Rentabilidad desde el último dato del mes anterior hasta la fecha actual", footer_style_notas))
        story.append(Paragraph("• YTD: Rentabilidad desde el último dato del año anterior hasta la fecha actual", footer_style_notas))
        story.append(Paragraph("• 1 Mes, 3 Meses, 12 Meses: Calculados en días calendario (30, 90 y 365 días respectivamente)", footer_style_notas))
        story.append(Paragraph("• * Rentabilidad 3 Años: Rentabilidad Anualizada (solo si hay suficiente historial)", footer_style_notas))
        story.append(Paragraph("• ** Rentabilidad 5 Años: Rentabilidad Anualizada (solo si hay suficiente historial)", footer_style_notas))

        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>METODOLOGÍA DE CÁLCULO:</b>", footer_style_notas))
        story.append(Paragraph("• Rentabilidades anualizadas calculadas mediante tasa de crecimiento anual compuesto (CAGR):", footer_style_notas))
        story.append(Paragraph("&nbsp;&nbsp;R<sub>anualizada</sub> = (P<sub>t</sub>/P<sub>0</sub>)<sup>1/t</sup> - 1", footer_style_notas))
        story.append(Paragraph("&nbsp;&nbsp;Donde: P<sub>t</sub> = Valor final, P<sub>0</sub> = Valor inicial, t = número de años del período", footer_style_notas))
        story.append(Paragraph("• Todos los valores se redondean a 2 decimales para presentación final", footer_style_notas))
        story.append(Paragraph("• Rentabilidad Fondos de Inversión calculada de acuerdo a variación de Valores Cuota", footer_style_notas))

        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>FUENTES Y CONSIDERACIONES:</b>", footer_style_notas))
        story.append(Paragraph("• TAC: Para Fondos Mutuos locales fuente CMF Chile. Para Fondos Mutuos extranjeros fuente Morningstar", footer_style_notas))
        story.append(Paragraph("• Rentabilidad Multifondos no considera comisión de AFP y tiene un día de desfase respecto a Rentabilidad de Fondos Mutuos", footer_style_notas))

        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>ADVERTENCIA:</b>", footer_style_notas))
        story.append(Paragraph("La rentabilidad o ganancia obtenida en el pasado por estos fondos, no garantiza que ella se repita en el futuro. Los valores de las cuotas de los fondos son variables.", footer_style_notas))
        
        story.append(Spacer(1, 10))
        story.append(Paragraph("DOCUMENTO DE USO INTERNO", footer_style_principal))
        story.append(Paragraph("© 2025 SURA Investments. Todos los derechos reservados.", footer_style_secundario))
        story.append(Paragraph(f"Generado el {hora_generacion}", footer_style_secundario))
        
        # Construir PDF
        doc.build(story)
        
        # Obtener contenido
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Codificar en base64
        pdf_b64 = base64.b64encode(pdf_data).decode()
        
        return pdf_b64
        
    except Exception as e:
        logging.error(f"Error generando PDF mejorado: {e}")
        return None
    
def registrar_callbacks_informe(app, pesos_df, dolares_df, fondos_unicos, fondos_a_series, fondo_serie_a_codigo, calcular_rentabilidades_func):
    """
    Registra los callbacks necesarios para el módulo de informe
    """
    
    # Callback para abrir/cerrar modal de informe
    @callback(
        Output("modal-informe", "is_open"),
        [Input("informe-button", "n_clicks")],
        [State("modal-informe", "is_open")],
        prevent_initial_call=True
    )
    def toggle_modal_informe(btn_open, is_open):
        if btn_open:
            return not is_open
        return is_open

    # Callback para generar el contenido del informe
    @callback(
        [Output('contenido-informe-rentabilidad', 'children'),
         Output('informe-cache', 'data')],
        [Input('moneda-selector-informe', 'value'),
         Input("modal-informe", "is_open")],
        [State('informe-cache', 'data'),
         State('timestamp-cache', 'data')],
        prevent_initial_call=True
    )
    def generar_informe_rentabilidad(moneda, modal_abierto, informe_cache, timestamp_cache):
        from datetime import datetime
        
        if not modal_abierto:
            return loading_content(), informe_cache or {}
        
        hoy = datetime.now().strftime('%Y-%m-%d')
        cache_key = f"informe_{moneda}_{hoy}"
        
        # Verificar si ya tenemos este cálculo en caché
        if informe_cache and cache_key in informe_cache:
            return informe_cache[cache_key], informe_cache
        
        # Si no hay caché, calcular normalmente
        if pesos_df is None:
            resultado = loading_content()
        else:
            # CAMBIO: Usar solo fondos SURA filtrados para el PDF
            from Pagina import filtrar_solo_fondos_sura, FONDOS_SURA_PDF
            
            fondos_sura, fondos_a_series_sura, fondo_serie_codigo_sura = filtrar_solo_fondos_sura(
                fondos_unicos, fondos_a_series, fondo_serie_a_codigo
            )
            
            df_actual = pesos_df if moneda == 'CLP' else dolares_df
            categorias = categorizar_fondos(fondos_sura)  # Solo fondos SURA
            
            # Crear tablas para cada categoría
            tablas_categorias = []
            
            # Crear encabezado del informe
            encabezado = html.Div([
                html.H3([
                    html.I(className="fas fa-building", style={'marginRight': '10px', 'color': '#0B2DCE'}),
                    "SURA Investments - Informe de Rentabilidades"
                ], style={
                    'fontFamily': 'SuraSans-SemiBold',
                    'textAlign': 'center',
                    'color': '#24272A',
                    'marginBottom': '10px'
                }),
                html.P(f"Moneda: {moneda} | Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                       style={
                           'fontFamily': 'SuraSans-Regular', 
                           'textAlign': 'center',
                           'color': '#666',
                           'marginBottom': '30px',
                           'fontSize': '14px'
                       })
            ])
            
            tablas_categorias.append(encabezado)
            
            for categoria in CONFIG['ORDEN_CATEGORIAS']:
                if categoria in categorias and categorias[categoria]:
                    tabla = crear_tabla_categoria(
                        categoria, 
                        categorias[categoria], 
                        df_actual,
                        fondos_a_series_sura,     
                        fondo_serie_codigo_sura, 
                        calcular_rentabilidades_func,
                        moneda
                    )
                    if tabla.children:
                        tablas_categorias.append(tabla)
            
            if len(tablas_categorias) <= 1:
                resultado = html.Div([
                    encabezado,
                    dbc.Alert([
                        html.I(className="fas fa-exclamation-triangle", style={'marginRight': '10px'}),
                        "No se encontraron datos para mostrar en el informe."
                    ], color="warning", style={'marginTop': '20px'})
                ])
            else:
                resultado = html.Div(tablas_categorias)
        
        # Guardar en caché
        if not informe_cache:
            informe_cache = {}
        informe_cache[cache_key] = resultado
        
        return resultado, informe_cache
    
    # Callback para descarga Excel / PDF
    @callback(
        [Output("download-informe", "data"),
         Output("estado-descarga", "children")],
        [Input("btn-descargar-excel", "n_clicks"),
         Input("btn-descargar-pdf", "n_clicks")],
        [State("moneda-selector-informe", "value")],
        prevent_initial_call=True
    )
    def descargar_informe(n_clicks_excel, n_clicks_pdf, moneda):
        import dash
        from dash.exceptions import PreventUpdate
        
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if pesos_df is None:
            estado = html.P("Error: No hay datos disponibles", style={
                'fontFamily': 'SuraSans-Regular', 'margin': '0', 'padding': '8px 12px',
                'backgroundColor': '#f8d7da', 'border': '1px solid #f5c6cb',
                'borderRadius': '4px', 'fontSize': '12px', 'color': '#721c24'
            })
            return None, estado
        
        try:
            df_actual = pesos_df if moneda == 'CLP' else dolares_df
            
            # CAMBIO: Usar solo fondos SURA filtrados para el PDF/Excel
            from Pagina import filtrar_solo_fondos_sura, FONDOS_SURA_PDF
            
            fondos_sura, fondos_a_series_sura, fondo_serie_codigo_sura = filtrar_solo_fondos_sura(
                fondos_unicos, fondos_a_series, fondo_serie_a_codigo
            )
            
            categorias = categorizar_fondos(fondos_sura)  # Solo fondos SURA
            
            # Generar datos por categoría
            datos_por_categoria = {}
            for categoria in CONFIG['ORDEN_CATEGORIAS']:
                if categoria in categorias and categorias[categoria]:
                    codigos_categoria = []
                    nombres_categoria = []
                    
                    for fondo in categorias[categoria]:
                        if fondo in fondos_a_series_sura:
                            # Verificar series disponibles por moneda
                            if moneda in fondos_a_series_sura[fondo]:
                                for serie in fondos_a_series_sura[fondo][moneda]:
                                    if (fondo, serie, moneda) in fondo_serie_codigo_sura:
                                        codigo = fondo_serie_codigo_sura[(fondo, serie, moneda)]
                                        nombre_completo = f"{fondo} - {serie}"
                                        codigos_categoria.append(codigo)
                                        nombres_categoria.append(nombre_completo)
                    
                    if codigos_categoria:
                        # USAR PRECÁLCULOS EN LUGAR DE CÁLCULO TRADICIONAL
                        tabla_data = obtener_informe_pdf_completo_precalculado(moneda, list(fondo_serie_codigo_sura.values()), list(fondos_sura))
                        datos_por_categoria[categoria] = tabla_data

            
            # Generar archivo según el botón presionado
            if button_id == "btn-descargar-excel":
                excel_b64 = generar_excel_informe(datos_por_categoria, moneda)
                if excel_b64:
                    filename = f"informe_rentabilidad_{moneda}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                    estado = html.P("✅ Excel generado exitosamente", style={
                        'fontFamily': 'SuraSans-Regular', 'margin': '0', 'padding': '8px 12px',
                        'backgroundColor': '#d4edda', 'border': '1px solid #c3e6cb',
                        'borderRadius': '4px', 'fontSize': '12px', 'color': '#155724'
                    })
                    return dcc.send_bytes(
                        base64.b64decode(excel_b64),
                        filename=filename
                    ), estado
                else:
                    estado = html.P("❌ Error generando Excel", style={
                        'fontFamily': 'SuraSans-Regular', 'margin': '0', 'padding': '8px 12px',
                        'backgroundColor': '#f8d7da', 'border': '1px solid #f5c6cb',
                        'borderRadius': '4px', 'fontSize': '12px', 'color': '#721c24'
                    })
                    return None, estado
            
            elif button_id == "btn-descargar-pdf":
                if not PDF_AVAILABLE:
                    estado = html.P("❌ PDF no disponible - Instalar ReportLab", style={
                        'fontFamily': 'SuraSans-Regular', 'margin': '0', 'padding': '8px 12px',
                        'backgroundColor': '#fff3cd', 'border': '1px solid #ffeaa7',
                        'borderRadius': '4px', 'fontSize': '12px', 'color': '#856404'
                    })
                    return None, estado
                
                pdf_b64 = generar_pdf_informe(datos_por_categoria, moneda)
                if pdf_b64:
                    filename = f"informe_rentabilidad_{moneda}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    estado = html.P("✅ PDF generado exitosamente", style={
                        'fontFamily': 'SuraSans-Regular', 'margin': '0', 'padding': '8px 12px',
                        'backgroundColor': '#d4edda', 'border': '1px solid #c3e6cb',
                        'borderRadius': '4px', 'fontSize': '12px', 'color': '#155724'
                    })
                    return dcc.send_bytes(
                        base64.b64decode(pdf_b64),
                        filename=filename
                    ), estado
                else:
                    estado = html.P("❌ Error generando PDF", style={
                        'fontFamily': 'SuraSans-Regular', 'margin': '0', 'padding': '8px 12px',
                        'backgroundColor': '#f8d7da', 'border': '1px solid #f5c6cb',
                        'borderRadius': '4px', 'fontSize': '12px', 'color': '#721c24'
                    })
                    return None, estado
        
        except Exception as e:
            logging.error(f"Error en descarga: {e}")
            estado = html.P(f"❌ Error: {str(e)}", style={
                'fontFamily': 'SuraSans-Regular', 'margin': '0', 'padding': '8px 12px',
                'backgroundColor': '#f8d7da', 'border': '1px solid #f5c6cb',
                'borderRadius': '4px', 'fontSize': '12px', 'color': '#721c24'
            })
            return None, estado
        
        raise PreventUpdate
