"""
Módulo para generar el Anexo de Retornos Mensuales
Diseñado para integrarse con el dashboard principal de SURA Investments
Soporta descarga en Excel y PDF
"""

import pandas as pd
import numpy as np
from dash import html, dcc, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc
import io
import base64
from datetime import datetime, timedelta
import logging
import calendar
import os
from pathlib import Path

from precalculos_optimizado import (
    obtener_retornos_mensuales_precalculados,
    verificar_precalculos_vigentes
)

# Importaciones para PDF
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    mm = 1
    logging.warning("ReportLab no está instalado. La funcionalidad PDF no estará disponible.")

# Configuración del módulo
CONFIG = {
    'ORDEN_CATEGORIAS': [
        'Renta Fija Nacional',
        'Renta Fija Internacional', 
        'Multifondos',
        'Equity (Acciones)',
        'Estrategias Alternativas',
        'Otros'
    ]
}

# =============================================================================
# FUNCIONES DE CÁLCULO PARA RETORNOS MENSUALES
# =============================================================================

def obtener_meses_para_calculo(fecha_actual):
    """
    Obtiene los últimos 12 meses en formato para headers
    
    Args:
        fecha_actual: datetime de la fecha actual
        
    Returns:
        list: Lista de tuplas (mes_texto, año, mes_numero) para los últimos 12 meses
    """
    meses_es = [
        'ene', 'feb', 'mar', 'abr', 'may', 'jun',
        'jul', 'ago', 'sep', 'oct', 'nov', 'dic'
    ]
    
    meses_resultado = []
    
    # Empezar desde el mes actual hacia atrás
    for i in range(12):
        fecha_mes = fecha_actual - timedelta(days=30*i)
        mes_num = fecha_mes.month
        año = fecha_mes.year
        mes_texto = f"{meses_es[mes_num-1]}-{año}"
        
        meses_resultado.append((mes_texto, año, mes_num))
    
    return meses_resultado

def calcular_rentabilidad_mes(precios, año, mes):
    """
    Calcula la rentabilidad de un mes específico
    
    Args:
        precios: DataFrame con 'Dates' y precios
        año: int año del mes a calcular
        mes: int mes a calcular (1-12)
        
    Returns:
        float: Rentabilidad del mes en % o np.nan si no hay datos
    """
    try:
        # Filtrar datos del mes específico
        datos_mes = precios[
            (precios['Dates'].dt.year == año) & 
            (precios['Dates'].dt.month == mes)
        ]
        
        if len(datos_mes) == 0:
            return np.nan
        
        # Obtener mes anterior
        if mes == 1:
            mes_anterior = 12
            año_anterior = año - 1
        else:
            mes_anterior = mes - 1
            año_anterior = año
        
        # Filtrar datos del mes anterior
        datos_mes_anterior = precios[
            (precios['Dates'].dt.year == año_anterior) & 
            (precios['Dates'].dt.month == mes_anterior)
        ]
        
        if len(datos_mes_anterior) == 0:
            return np.nan
        
        # Último precio del mes anterior (precio inicial)
        precio_inicial = datos_mes_anterior.iloc[-1, 1]
        
        # Último precio del mes actual (precio final)
        precio_final = datos_mes.iloc[-1, 1]
        
        if pd.isna(precio_inicial) or pd.isna(precio_final) or precio_inicial == 0:
            return np.nan
        
        # Calcular rentabilidad mensual
        rentabilidad = ((precio_final / precio_inicial) - 1) * 100
        
        return rentabilidad
        
    except Exception as e:
        logging.warning(f"Error calculando rentabilidad mes {mes}/{año}: {e}")
        return np.nan

def calcular_rentabilidad_12_meses(precios, fecha_actual):
    """
    Calcula la rentabilidad de los últimos 12 meses
    """
    try:
        fecha_hace_12_meses = fecha_actual - timedelta(days=365)
        
        # Buscar precio más cercano a hace 12 meses
        datos_iniciales = precios[precios['Dates'] >= fecha_hace_12_meses]
        
        if len(datos_iniciales) == 0:
            return np.nan
        
        precio_inicial = datos_iniciales.iloc[0, 1]
        precio_final = precios.iloc[-1, 1]
        
        if pd.isna(precio_inicial) or pd.isna(precio_final) or precio_inicial == 0:
            return np.nan
        
        return ((precio_final / precio_inicial) - 1) * 100
        
    except Exception as e:
        return np.nan

# def calcular_retornos_mensuales_completos(df, codigos_seleccionados, nombres_mostrar):
#     """
#     Función principal para calcular todos los retornos mensuales
    
#     Args:
#         df: DataFrame con datos de precios
#         codigos_seleccionados: Lista de códigos de fondos
#         nombres_mostrar: Lista de nombres para mostrar
        
#     Returns:
#         pd.DataFrame: DataFrame con retornos mensuales por fondo
#     """
#     resultados = []
#     fecha_actual = df['Dates'].max()
    
#     # Obtener los meses para calcular
#     meses_calculo = obtener_meses_para_calculo(fecha_actual)
    
#     for i, (codigo, nombre) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
#         if codigo in df.columns:
#             precios = df[['Dates', codigo]].dropna()
            
#             if len(precios) > 0:
#                 # Separar fondo y serie del nombre completo
#                 partes = nombre.split(' - ')
#                 fondo = partes[0] if len(partes) > 0 else nombre
#                 serie = partes[1] if len(partes) > 1 else 'N/A'
                
#                 # Crear diccionario base del resultado
#                 resultado = {
#                     'Fondo': fondo,
#                     'Serie': serie
#                 }
                
#                 # Calcular rentabilidad para cada mes
#                 for mes_texto, año, mes_num in meses_calculo:
#                     rentabilidad_mes = calcular_rentabilidad_mes(precios, año, mes_num)
#                     resultado[mes_texto] = rentabilidad_mes
                
#                 # Calcular rentabilidad 12 meses
#                 rent_12m = calcular_rentabilidad_12_meses(precios, fecha_actual)
#                 resultado['12 M'] = rent_12m
                
#                 resultados.append(resultado)
    
#     return pd.DataFrame(resultados).round(2)


def calcular_retornos_mensuales_completos(df, codigos_seleccionados, nombres_mostrar):
    """
    VERSIÓN OPTIMIZADA: Usa pre-cálculos cuando están disponibles
    Fallback a cálculo en tiempo real si no hay pre-cálculos
    
    Args:
        df: DataFrame con datos de precios
        codigos_seleccionados: Lista de códigos de fondos
        nombres_mostrar: Lista de nombres para mostrar
        
    Returns:
        pd.DataFrame: DataFrame con retornos mensuales por fondo
    """
    # Detectar moneda basada en el DataFrame comparando con variables globales
    try:
        # Intentar importar y comparar con DataFrames globales de Pagina.py
        import Pagina
        
        if hasattr(Pagina, 'pesos_df') and hasattr(Pagina, 'dolares_df'):
            if df.equals(Pagina.pesos_df):
                moneda = 'CLP'
            elif df.equals(Pagina.dolares_df):
                moneda = 'USD'
            else:
                moneda = 'CLP'  # Fallback si no coincide
        else:
            moneda = 'CLP'  # Fallback si no existen las variables
            
    except Exception as e:
        # Si hay cualquier error en la importación o comparación
        moneda = 'CLP'  # Fallback seguro
    
    # Intentar usar pre-cálculos primero
    if verificar_precalculos_vigentes():
        try:
            print(f"⚡ Usando pre-cálculos para retornos mensuales ({moneda})...")
            resultado = obtener_retornos_mensuales_precalculados(
                moneda, codigos_seleccionados, nombres_mostrar
            )
            if resultado is not None and not resultado.empty:
                return resultado
            else:
                print("⚠️ Pre-cálculos vacíos, usando cálculo en tiempo real...")
        except Exception as e:
            print(f"⚠️ Error en pre-cálculos: {e}, usando cálculo en tiempo real...")
    
    # FALLBACK: Cálculo original en tiempo real
    print(f"🔄 Calculando retornos mensuales en tiempo real ({moneda})...")
    resultados = []
    fecha_actual = df['Dates'].max()
    
    # Obtener los meses para calcular
    meses_calculo = obtener_meses_para_calculo(fecha_actual)
    
    for i, (codigo, nombre) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
        if codigo in df.columns:
            precios = df[['Dates', codigo]].dropna()
            
            if len(precios) > 0:
                # Separar fondo y serie del nombre completo
                partes = nombre.split(' - ')
                fondo = partes[0] if len(partes) > 0 else nombre
                serie = partes[1] if len(partes) > 1 else 'N/A'
                
                # Crear diccionario base del resultado
                resultado = {
                    'Fondo': fondo,
                    'Serie': serie
                }
                
                # Calcular rentabilidad para cada mes
                for mes_texto, año, mes_num in meses_calculo:
                    rentabilidad_mes = calcular_rentabilidad_mes(precios, año, mes_num)
                    resultado[mes_texto] = rentabilidad_mes
                
                # Calcular rentabilidad 12 meses
                rent_12m = calcular_rentabilidad_12_meses(precios, fecha_actual)
                resultado['12 M'] = rent_12m
                
                resultados.append(resultado)
    
    return pd.DataFrame(resultados).round(2)



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

def categorizar_fondos(fondos_unicos):
    """
    Categoriza los fondos según su tipo (misma función que informe_module)
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

def crear_tabla_categoria_mensual(categoria, fondos_categoria, df_actual, fondos_a_series, fondo_serie_a_codigo, moneda='CLP'):
    """
    Crea una tabla para una categoría específica con retornos mensuales
    """
    if not fondos_categoria:
        return html.Div()
    
    # Obtener códigos y nombres para esta categoría
    codigos_categoria = []
    nombres_categoria = []
    
    for fondo in fondos_categoria:
        if fondo in fondos_a_series:
            if moneda in fondos_a_series[fondo]:                           # ✅ CORRECTO
                for serie in fondos_a_series[fondo][moneda]:               # ✅ CORRECTO
                    if (fondo, serie, moneda) in fondo_serie_a_codigo:     # ✅ CORRECTO
                        codigo = fondo_serie_a_codigo[(fondo, serie, moneda)] 
                        nombre_completo = f"{fondo} - {serie}"
                        codigos_categoria.append(codigo)
                        nombres_categoria.append(nombre_completo)
    
    if not codigos_categoria:
        return html.Div()
    
    # Calcular retornos mensuales
    tabla_data = calcular_retornos_mensuales_completos_con_moneda(df_actual, codigos_categoria, nombres_categoria, moneda)
    
    if tabla_data.empty:
        return html.Div()
    
    # Preparar columnas dinámicamente
    columnas_base = ['Fondo', 'Serie']
    columnas_meses = [col for col in tabla_data.columns if col not in columnas_base and col != '12 M']
    columnas_orden = columnas_base + columnas_meses + ['12 M']
    
    # Asegurarse de que todas las columnas existan
    columnas_disponibles = [col for col in columnas_orden if col in tabla_data.columns]
    tabla_data = tabla_data[columnas_disponibles]
    
    # Crear configuración de columnas para DataTable
    columns_config = []
    for col in columnas_disponibles:
        if col in ['Fondo', 'Serie']:
            columns_config.append({"name": col, "id": col})
        else:
            columns_config.append({
                "name": col, 
                "id": col, 
                "type": "numeric", 
                "format": {"specifier": ".2f"}
            })

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
            columns=columns_config,
            style_table={
                'overflowX': 'auto', 
                'marginBottom': '30px',
                'border': '1px solid #dee2e6',
                'borderRadius': '5px'
            },
            style_cell={
                'textAlign': 'center',
                'fontFamily': 'SuraSans-Regular',
                'fontSize': '11px',
                'padding': '8px 4px',
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
                # Colores para rentabilidades positivas en columnas de meses
                {
                    'if': {'column_id': col, 'filter_query': f'{{{col}}} > 0'},
                    'color': '#28a745',
                    'fontWeight': 'bold'
                } for col in columnas_meses + ['12 M']
            ] + [
                # Colores para rentabilidades negativas en columnas de meses
                {
                    'if': {'column_id': col, 'filter_query': f'{{{col}}} < 0'},
                    'color': '#dc3545',
                    'fontWeight': 'bold'
                } for col in columnas_meses + ['12 M']
            ] + [
                # Estilo para nombre del fondo
                {
                    'if': {'column_id': 'Fondo'},
                    'fontWeight': '600',
                    'color': '#24272A',
                    'textAlign': 'left'
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

# =============================================================================
# FUNCIONES PARA GENERAR EXCEL
# =============================================================================

def generar_excel_anexo_mensual(datos_por_categoria, moneda):
    """
    Genera un archivo Excel con el anexo de retornos mensuales
    """
    try:
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # Hoja resumen
            resumen_data = []
            for categoria, tabla_data in datos_por_categoria.items():
                if not tabla_data.empty:
                    # Obtener columnas de meses (excluyendo Fondo, Serie, 12 M)
                    columnas_meses = [col for col in tabla_data.columns 
                                    if col not in ['Fondo', 'Serie', '12 M']]
                    
                    if columnas_meses:
                        promedio_meses = tabla_data[columnas_meses].mean(axis=1).mean()
                    else:
                        promedio_meses = 0
                    
                    resumen_data.append({
                        'Categoría': categoria,
                        'Número de Fondos': len(tabla_data),
                        'Promedio Mensual (%)': round(promedio_meses, 2),
                        'Promedio 12M (%)': round(tabla_data['12 M'].mean(), 2) if '12 M' in tabla_data.columns else 0
                    })
            
            if resumen_data:
                df_resumen = pd.DataFrame(resumen_data)
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
                
                # Formatear hoja resumen
                workbook = writer.book
                worksheet = writer.sheets['Resumen']
                
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
        
        excel_data = output.getvalue()
        excel_b64 = base64.b64encode(excel_data).decode()
        
        return excel_b64
        
    except Exception as e:
        logging.error(f"Error generando Excel anexo mensual: {e}")
        return None

# =============================================================================
# FUNCIONES PARA GENERAR PDF
# =============================================================================

def generar_pdf_anexo_mensual(datos_por_categoria, moneda):
    """
    Genera un archivo PDF con el anexo de retornos mensuales
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
        
        # CAMBIO: Registrar fuentes con rutas múltiples (igual que en informe_module)
        try:
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
        
        buffer = io.BytesIO()
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
        COLOR_BG_ALTERNATING = colors.HexColor('#F8F9FA')
        
        # Función para crear la barra superior con logos
        def crear_barra_superior_header(canvas, doc):
            canvas.saveState()
            
            page_width = page_size[0]
            page_height = page_size[1]
            
            canvas.setFillColor(COLOR_SURA_BLACK)
            canvas.rect(0, page_height - 25*mm, page_width, 25*mm, fill=1, stroke=0)
            
            # CAMBIO: Logos con rutas múltiples
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
                canvas.setFillColor(COLOR_SURA_WHITE)
                canvas.setFont("Helvetica-Bold", 12)
                canvas.drawString(15*mm, page_height - 15*mm, "SURA")
            
            # Logo INVESTMENTS
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

        
        frame = Frame(10*mm, 10*mm, page_size[0] - 20*mm, page_size[1] - 40*mm,
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        
        template = PageTemplate(id='todas_paginas', frames=[frame], 
                               onPage=crear_barra_superior_header)
        doc.addPageTemplates([template])
        
        # Obtener estilos
        styles = getSampleStyleSheet()
        
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=16,
            spaceAfter=5,
            alignment=TA_LEFT,
            textColor=COLOR_SURA_BLACK,
            fontName='SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold'
        )
        
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
            leftIndent=0,  # Para que ocupe todo el ancho
            rightIndent=0,
            alignment=0
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
        
        # Contenido del PDF
        story = []
        
        # HEADER PRINCIPAL
        fecha_formateada = datetime.now().strftime("%d/%m/%Y")
        header_text = f"ANEXO RETORNOS MENSUALES AL {fecha_formateada}"
        story.append(Paragraph(header_text, header_style))
        
        # Subtítulo de moneda
        subtitle_text = f"Retornos Nominales en {moneda}"
        story.append(Paragraph(subtitle_text, info_style))
        
        story.append(Spacer(1, 15))
        
        # Procesar cada categoría
        for categoria in CONFIG['ORDEN_CATEGORIAS']:
            if categoria in datos_por_categoria and not datos_por_categoria[categoria].empty:
                tabla_data = datos_por_categoria[categoria]
                
                # TÍTULO DE CATEGORÍA
                texto_con_espacios = f"<br/>{categoria.upper()}<br/>&nbsp;<br/>"
                category_header = Paragraph(texto_con_espacios, category_style)
                story.append(category_header)
                
                # PREPARAR HEADERS DINÁMICOS
                columnas_base = ['Fondo', 'Serie']
                columnas_meses = [col for col in tabla_data.columns 
                                if col not in columnas_base and col != '12 M']
                headers = columnas_base + columnas_meses + ['12 M']
                
                table_data = [headers]
                
                # DATOS DE LA TABLA
                fondos_agrupados = {}
                for _, row in tabla_data.iterrows():
                    nombre_fondo = row['Fondo'].replace('FONDO MUTUO SURA ', '').replace('SURA ', '')
                    if nombre_fondo not in fondos_agrupados:
                        fondos_agrupados[nombre_fondo] = []
                    fondos_agrupados[nombre_fondo].append(row)
                
                primer_fondo = True
                for nombre_fondo, filas_fondo in fondos_agrupados.items():
                    if not primer_fondo:
                        fila_separadora = [''] * len(headers)
                        table_data.append(fila_separadora)
                    
                    for row in filas_fondo:
                        def formatear_valor_mensual(valor):
                            if pd.isna(valor):
                                return "---"
                            elif isinstance(valor, (int, float)):
                                return f"{valor:.2f}%"
                            else:
                                return str(valor)
                        
                        table_row = [nombre_fondo, str(row['Serie'])]
                        
                        # Agregar valores de meses
                        for col in columnas_meses:
                            if col in row:
                                table_row.append(formatear_valor_mensual(row[col]))
                            else:
                                table_row.append("---")
                        
                        # Agregar 12 M
                        if '12 M' in row:
                            table_row.append(formatear_valor_mensual(row['12 M']))
                        else:
                            table_row.append("---")
                        
                        table_data.append(table_row)
                    
                    primer_fondo = False
                
                # CALCULAR ANCHOS DE COLUMNAS DINÁMICAMENTE
                ancho_total_disponible = page_size[0] - 20*mm
                num_columnas = len(headers)
                
                # Asignar anchos proporcionales
                if num_columnas > 0:
                    ancho_fondo = ancho_total_disponible * 0.25  # 25% para fondo
                    ancho_serie = ancho_total_disponible * 0.08  # 8% para serie
                    ancho_restante = ancho_total_disponible - ancho_fondo - ancho_serie
                    ancho_por_mes = ancho_restante / (num_columnas - 2)  # Resto distribuido
                    
                    anchos_columnas = [ancho_fondo, ancho_serie] + [ancho_por_mes] * (num_columnas - 2)
                else:
                    anchos_columnas = [ancho_total_disponible / num_columnas] * num_columnas
                
                # Crear tabla
                table = Table(table_data, colWidths=anchos_columnas, repeatRows=1)
                
                # ESTILOS DE TABLA
                table_style = [
                    # HEADER
                    ('BACKGROUND', (0, 0), (-1, 0), COLOR_SURA_BLACK),
                    ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_SURA_WHITE),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'SuraSans-SemiBold' if fuentes_disponibles else 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                    ('TOPPADDING', (0, 0), (-1, 0), 4),
                    
                    # DATOS
                    ('FONTNAME', (0, 1), (-1, -1), 'SuraSans-Regular' if fuentes_disponibles else 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('TOPPADDING', (0, 1), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
                    ('LEFTPADDING', (0, 0), (-1, -1), 1),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 1),
                    
                    # BORDES
                    ('GRID', (0, 0), (-1, -1), 0.5, COLOR_SURA_GRAY),
                    ('LINEBELOW', (0, 0), (-1, 0), 1, COLOR_SURA_BLACK),
                    
                    # ALINEACIÓN
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),     # Fondo
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Resto centrado
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]
                
                # APLICAR COLORES CONDICIONALES
                columnas_rentabilidad = list(range(2, len(headers)))  # Todas las columnas menos Fondo y Serie
                
                for row_idx in range(1, len(table_data)):
                    es_fila_separadora = all(cell == '' for cell in table_data[row_idx])
                    
                    if es_fila_separadora:
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

        footer_style_secundario = ParagraphStyle(
            'FooterStyleSecundario',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=COLOR_SUBTITLE_GRAY,
            fontName='SuraSans-Regular' if fuentes_disponibles else 'Helvetica',
            spaceAfter=5
        )
        
        # Agregar footer con explicaciones
        story.append(Spacer(1, 20))
        
        # Notas explicativas para retornos mensuales
        story.append(Paragraph("<b>DEFINICIONES:</b>", footer_style_notas))
        story.append(Paragraph("• Retornos Mensuales: Calculados desde el último día del mes anterior hasta el último día del mes indicado", footer_style_notas))
        story.append(Paragraph("• 12 M: Retornos acumulados de los últimos 12 meses", footer_style_notas))
        story.append(Paragraph("• Todos los valores se redondean a 2 decimales para presentación final", footer_style_notas))
        
        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>FUENTES Y CONSIDERACIONES:</b>", footer_style_notas))
        story.append(Paragraph("• Para Fondos Mutuos locales fuente CMF Chile. Para Fondos Mutuos extranjeros fuente Morningstar", footer_style_notas))
        story.append(Paragraph("• Rentabilidad Fondos de Inversión calculada de acuerdo a variación de Valores Cuota", footer_style_notas))
        
        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>ADVERTENCIA:</b>", footer_style_notas))
        story.append(Paragraph("La rentabilidad o ganancia obtenida en el pasado por estos fondos, no garantiza que ella se repita en el futuro. Los valores de las cuotas de los fondos son variables.", footer_style_notas))
        
        # Definir hora de generación
        hora_generacion = datetime.now().strftime("%d/%m/%Y")
        
        story.append(Spacer(1, 10))
        story.append(Paragraph("DOCUMENTO DE USO INTERNO", footer_style_principal))
        story.append(Paragraph("© 2025 SURA Investments. Todos los derechos reservados.", footer_style_secundario))
        story.append(Paragraph(f"Generado el {hora_generacion}", footer_style_secundario))
        
        # Construir PDF
        doc.build(story)
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        pdf_b64 = base64.b64encode(pdf_data).decode()
        
        return pdf_b64
        
    except Exception as e:
        logging.error(f"Error generando PDF anexo mensual: {e}")
        return None

def calcular_retornos_mensuales_completos_con_moneda(df, codigos_seleccionados, nombres_mostrar, moneda):
    """
    Versión que recibe la moneda explícitamente para usar pre-cálculos
    """
    # Intentar usar pre-cálculos primero
    if verificar_precalculos_vigentes():
        try:
            print(f"⚡ Usando pre-cálculos para retornos mensuales ({moneda})...")
            resultado = obtener_retornos_mensuales_precalculados(
                moneda, codigos_seleccionados, nombres_mostrar
            )
            if resultado is not None and not resultado.empty:
                return resultado
            else:
                print("⚠️ Pre-cálculos vacíos, usando cálculo en tiempo real...")
        except Exception as e:
            print(f"⚠️ Error en pre-cálculos: {e}, usando cálculo en tiempo real...")
    
    # FALLBACK: usar la función original
    return calcular_retornos_mensuales_tiempo_real(df, codigos_seleccionados, nombres_mostrar)

def calcular_retornos_mensuales_tiempo_real(df, codigos_seleccionados, nombres_mostrar):
    """Versión original sin pre-cálculos"""
    resultados = []
    fecha_actual = df['Dates'].max()
    meses_calculo = obtener_meses_para_calculo(fecha_actual)
    
    for i, (codigo, nombre) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
        if codigo in df.columns:
            precios = df[['Dates', codigo]].dropna()
            if len(precios) > 0:
                partes = nombre.split(' - ')
                fondo = partes[0] if len(partes) > 0 else nombre
                serie = partes[1] if len(partes) > 1 else 'N/A'
                
                resultado = {'Fondo': fondo, 'Serie': serie}
                
                for mes_texto, año, mes_num in meses_calculo:
                    rentabilidad_mes = calcular_rentabilidad_mes(precios, año, mes_num)
                    resultado[mes_texto] = rentabilidad_mes
                
                rent_12m = calcular_rentabilidad_12_meses(precios, fecha_actual)
                resultado['12 M'] = rent_12m
                resultados.append(resultado)
    
    return pd.DataFrame(resultados).round(2)

# =============================================================================
# COMPONENTES UI
# =============================================================================

def crear_modal_anexo_mensual():
    """
    Crea el modal del anexo de retornos mensuales
    """
    return dbc.Modal([
        dbc.ModalHeader([
            dbc.ModalTitle([
                html.I(className="fas fa-calendar", style={'marginRight': '10px', 'color': '#0B2DCE'}),
                "Anexo de Retornos Mensuales"
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
                                id='moneda-selector-anexo',
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
                                    id="btn-descargar-excel-anexo", 
                                    color="success", 
                                    outline=True,
                                    size="sm",
                                    style={'fontFamily': 'SuraSans-Regular'}),
                                    
                                    dbc.Button([
                                        html.I(className="fas fa-file-pdf", style={'marginRight': '8px'}),
                                        "PDF"
                                    ], 
                                    id="btn-descargar-pdf-anexo", 
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
                            html.Div(id="estado-descarga-anexo", children=[
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
            dcc.Download(id="download-anexo"),
            
            # Contenedor para las tablas del anexo
            html.Div(id='contenido-anexo-mensual')
            
        ], style={
            'padding': '20px', 
            'maxHeight': '75vh', 
            'overflowY': 'auto',
            'backgroundColor': '#f8f9fa'
        }),
        
    ], id="modal-anexo", is_open=False, size="xl", centered=True)

# =============================================================================
# CALLBACKS
# =============================================================================

def registrar_callbacks_anexo_mensual(app, pesos_df, dolares_df, fondos_unicos, fondos_a_series, fondo_serie_a_codigo):
    """
    Registra los callbacks necesarios para el módulo de anexo mensual
    """
    
    # Callback para abrir/cerrar modal de anexo
    @callback(
        Output("modal-anexo", "is_open"),
        [Input("anexo-button", "n_clicks")],
        [State("modal-anexo", "is_open")],
        prevent_initial_call=True
    )
    def toggle_modal_anexo(btn_open, is_open):
        if btn_open:
            return not is_open
        return is_open

    # Callback para generar el contenido del anexo
    @callback(
        [Output('contenido-anexo-mensual', 'children'),
         Output('anexo-cache', 'data')],
        [Input('moneda-selector-anexo', 'value'),
         Input("modal-anexo", "is_open")],
        [State('anexo-cache', 'data'),
         State('timestamp-cache', 'data')],
        prevent_initial_call=True
    )
    def generar_anexo_mensual(moneda, modal_abierto, anexo_cache, timestamp_cache):
        from datetime import datetime
        
        if not modal_abierto:
            return loading_content(), anexo_cache or {}
        
        hoy = datetime.now().strftime('%Y-%m-%d')
        cache_key = f"anexo_{moneda}_{hoy}"
        
        # Verificar si ya tenemos este cálculo en caché
        if anexo_cache and cache_key in anexo_cache:
            return anexo_cache[cache_key], anexo_cache
        
        # Si no hay caché, calcular normalmente
        if pesos_df is None:
            resultado = loading_content()
        else:
            # CAMBIO: Usar solo fondos SURA filtrados para el anexo
            from Pagina import filtrar_solo_fondos_sura, FONDOS_SURA_PDF
            
            fondos_sura, fondos_a_series_sura, fondo_serie_codigo_sura = filtrar_solo_fondos_sura(
                fondos_unicos, fondos_a_series, fondo_serie_a_codigo
            )
            
            df_actual = pesos_df if moneda == 'CLP' else dolares_df
            categorias = categorizar_fondos(fondos_sura)  # Solo fondos SURA
            
            # Crear tablas para cada categoría
            tablas_categorias = []
            
            # Crear encabezado del anexo
            encabezado = html.Div([
                html.H3([
                    html.I(className="fas fa-building", style={'marginRight': '10px', 'color': '#0B2DCE'}),
                    "SURA Investments - Anexo de Retornos Mensuales"
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
                    tabla = crear_tabla_categoria_mensual(
                        categoria, 
                        categorias[categoria], 
                        df_actual,
                        fondos_a_series_sura,     # ✅ CORRECTO
                        fondo_serie_codigo_sura,  # ✅ CORRECTO
                        moneda  
                    )
                    if tabla.children:
                        tablas_categorias.append(tabla)
            
            if len(tablas_categorias) <= 1:
                resultado = html.Div([
                    encabezado,
                    dbc.Alert([
                        html.I(className="fas fa-exclamation-triangle", style={'marginRight': '10px'}),
                        "No se encontraron datos para mostrar en el anexo."
                    ], color="warning", style={'marginTop': '20px'})
                ])
            else:
                resultado = html.Div(tablas_categorias)
        
        # Guardar en caché
        if not anexo_cache:
            anexo_cache = {}
        anexo_cache[cache_key] = resultado
        
        return resultado, anexo_cache

    # Callback para descarga Excel y PDF
    @callback(
        [Output("download-anexo", "data"),
         Output("estado-descarga-anexo", "children")],
        [Input("btn-descargar-excel-anexo", "n_clicks"),
         Input("btn-descargar-pdf-anexo", "n_clicks")],
        [State("moneda-selector-anexo", "value")],
        prevent_initial_call=True
    )
    def descargar_anexo(n_clicks_excel, n_clicks_pdf, moneda):
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
            
            # CAMBIO: Usar solo fondos SURA filtrados
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
                            if moneda in fondos_a_series_sura[fondo]:
                                for serie in fondos_a_series_sura[fondo][moneda]:
                                    if (fondo, serie, moneda) in fondo_serie_codigo_sura:
                                        codigo = fondo_serie_codigo_sura[(fondo, serie, moneda)]
                                        nombre_completo = f"{fondo} - {serie}"
                                        codigos_categoria.append(codigo)
                                        nombres_categoria.append(nombre_completo)
                    
                    if codigos_categoria:
                        tabla_data = calcular_retornos_mensuales_completos(df_actual, codigos_categoria, nombres_categoria)
                        datos_por_categoria[categoria] = tabla_data
            
            # Generar archivo según el botón presionado
            if button_id == "btn-descargar-excel-anexo":
                excel_b64 = generar_excel_anexo_mensual(datos_por_categoria, moneda)
                if excel_b64:
                    filename = f"anexo_retornos_mensuales_{moneda}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
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
            
            elif button_id == "btn-descargar-pdf-anexo":
                if not PDF_AVAILABLE:
                    estado = html.P("❌ PDF no disponible - Instalar ReportLab", style={
                        'fontFamily': 'SuraSans-Regular', 'margin': '0', 'padding': '8px 12px',
                        'backgroundColor': '#fff3cd', 'border': '1px solid #ffeaa7',
                        'borderRadius': '4px', 'fontSize': '12px', 'color': '#856404'
                    })
                    return None, estado
                
                pdf_b64 = generar_pdf_anexo_mensual(datos_por_categoria, moneda)
                if pdf_b64:
                    filename = f"anexo_retornos_mensuales_{moneda}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
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
            logging.error(f"Error en descarga anexo: {e}")
            estado = html.P(f"❌ Error: {str(e)}", style={
                'fontFamily': 'SuraSans-Regular', 'margin': '0', 'padding': '8px 12px',
                'backgroundColor': '#f8d7da', 'border': '1px solid #f5c6cb',
                'borderRadius': '4px', 'fontSize': '12px', 'color': '#721c24'
            })
            return None, estado
        
        raise PreventUpdate
