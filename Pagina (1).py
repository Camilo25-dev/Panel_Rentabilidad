import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import dash
from dash import html, dcc, dash_table, callback, Input, Output, State, ALL, MATCH
import dash_bootstrap_components as dbc
from openpyxl import load_workbook
import os
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import uuid
from pathlib import Path

from precalculos_optimizado import (
    obtener_rentabilidades_acumuladas_precalculadas,
    obtener_rentabilidades_anualizadas_precalculadas,
    obtener_rentabilidades_por_año_precalculadas,
    verificar_precalculos_vigentes
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server
import informe_module
import anexo_mensual_module 

# =============================================================================
# FUNCIONES DE CARGA Y PROCESAMIENTO DE DATOS
# =============================================================================

def crear_disclaimer_acumulada():
    """Crea el disclaimer corporativo compacto para la tabla de Rentabilidad Acumulada"""
    return html.Div([
        html.Hr(style={'margin': '15px 0', 'borderColor': '#e9ecef', 'borderWidth': '1px'}),
        
        # Contenedor principal con fondo gris claro
        html.Div([
            # Título compacto
            html.H6("Notas Metodológicas", style={
                'fontFamily': 'SuraSans-SemiBold', 
                'color': '#24272A',
                'marginBottom': '8px',
                'fontSize': '13px',
                'textAlign': 'center'
            }),
            
            # Información técnica organizada
            html.Div([
                html.P([
                    html.Strong("Períodos fijos: "), 
                    "1 Mes = 30 días, 3 Meses = 90 días, 12 Meses = 365 días calendario."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("YTD: "), 
                    "Desde último valor del año anterior hasta fecha actual."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("3 y 5 Años: "), 
                    "Rentabilidad simple acumulada del período completo."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("TAC: "), 
                    "Tasa de Administración y Custodia anual vigente."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("Redondeo: "), 
                    "Todos los porcentajes a 2 decimales."
                ], style={'margin': '0 0 4px 0'}),
                
                
            ], style={
                'fontFamily': 'SuraSans-Regular', 
                'fontSize': '11px', 
                'color': '#495057',
                'lineHeight': '1.4'
            })
            
        ], style={
            'backgroundColor': '#f8f9fa',
            'border': '1px solid #e9ecef',
            'borderRadius': '6px',
            'padding': '12px',
            'marginTop': '10px'
        })
    ], style={'marginTop': '15px', 'marginBottom': '20px'})

def crear_disclaimer_anualizada():
    """Crea el disclaimer corporativo compacto para la tabla de Rentabilidad Anualizada"""
    return html.Div([
        html.Hr(style={'margin': '15px 0', 'borderColor': '#e9ecef', 'borderWidth': '1px'}),
        
        html.Div([
            html.H6("Notas Metodológicas", style={
                'fontFamily': 'SuraSans-SemiBold', 
                'color': '#24272A',
                'marginBottom': '8px',
                'fontSize': '13px',
                'textAlign': 'center'
            }),
            
            # Información técnica sobre rentabilidad anualizada
            html.Div([
                html.P([
                    html.Strong("Fórmula CAGR: "), 
                    "Rentabilidad_anualizada = (Valor_final/Valor_inicial)^(1/años) - 1."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("Tasa Compuesta: "), 
                    "Representa el crecimiento anual promedio sostenido durante el período."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("Períodos: "), 
                    "1 Año = 365 días, 3 Años = 1095 días, 5 Años = 1825 días."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("Validación: "), 
                    "Solo se calculan valores para fondos con datos suficientes del período solicitado."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("Redondeo: "), 
                    "Todos los porcentajes a 2 decimales."
                ], style={'margin': '0 0 4px 0'}),
                
                
            ], style={
                'fontFamily': 'SuraSans-Regular', 
                'fontSize': '11px', 
                'color': '#495057',
                'lineHeight': '1.4'
            })
            
        ], style={
            'backgroundColor': '#f8f9fa',
            'border': '1px solid #e9ecef',
            'borderRadius': '6px',
            'padding': '12px',
            'marginTop': '10px'
        })
    ], style={'marginTop': '15px', 'marginBottom': '20px'})

def crear_disclaimer_por_año():
    """Crea el disclaimer corporativo compacto para la tabla de Rentabilidad por Año"""
    return html.Div([
        html.Hr(style={'margin': '15px 0', 'borderColor': '#e9ecef', 'borderWidth': '1px'}),
        
        html.Div([
            html.H6("Notas Metodológicas", style={
                'fontFamily': 'SuraSans-SemiBold', 
                'color': '#24272A',
                'marginBottom': '8px',
                'fontSize': '13px',
                'textAlign': 'center'
            }),
            
            # Información técnica sobre rentabilidad por año
            html.Div([
                html.P([
                    html.Strong("Período: "), 
                    "Rentabilidades calculadas por año calendario completo."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("Año actual: "), 
                    "Para el año en curso, se calcula desde último dato del año anterior hasta fecha actual."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("Rentabilidad simple: "), 
                    "No es rentabilidad anualizada, es la variación total del año."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("Años completos: "), 
                    "Rentabilidad desde último dato del año anterior hasta último dato del año analizado."
                ], style={'margin': '0 0 4px 0'}),
                
                html.P([
                    html.Strong("Redondeo: "), 
                    "Todos los porcentajes a 2 decimales."
                ], style={'margin': '0 0 4px 0'}),
                
                
            ], style={
                'fontFamily': 'SuraSans-Regular', 
                'fontSize': '11px', 
                'color': '#495057',
                'lineHeight': '1.4'
            })
            
        ], style={
            'backgroundColor': '#f8f9fa',
            'border': '1px solid #e9ecef',
            'borderRadius': '6px',
            'padding': '12px',
            'marginTop': '10px'
        })
    ], style={'marginTop': '15px', 'marginBottom': '20px'})

def crear_mapeos_desde_columnas(pesos_df, dolares_df):
    """
    Crea mapeos de fondos y series basado en nombres de columnas
    """
    # Obtener todas las columnas (excluyendo 'Dates')
    columnas_clp = [col for col in pesos_df.columns if col != 'Dates']
    columnas_usd = [col for col in dolares_df.columns if col != 'Dates']
    
    fondos_a_series = {}
    fondo_serie_a_codigo = {}
    
    # Procesar columnas CLP
    for columna in columnas_clp:
        fondo, serie = separar_nombre_y_serie(columna)
        
        if fondo not in fondos_a_series:
            fondos_a_series[fondo] = {'CLP': [], 'USD': []}
        
        fondos_a_series[fondo]['CLP'].append(serie)
        fondo_serie_a_codigo[(fondo, serie, 'CLP')] = columna
    
    # Procesar columnas USD
    for columna in columnas_usd:
        fondo, serie = separar_nombre_y_serie(columna)
        
        if fondo not in fondos_a_series:
            fondos_a_series[fondo] = {'CLP': [], 'USD': []}
        
        fondos_a_series[fondo]['USD'].append(serie)
        fondo_serie_a_codigo[(fondo, serie, 'USD')] = columna
    
    fondos_unicos = list(fondos_a_series.keys())
    
    return fondos_unicos, fondos_a_series, fondo_serie_a_codigo


def separar_nombre_y_serie(nombre_columna):
    """
    Separa el nombre completo en fondo y serie
    Maneja casos con múltiples guiones
    """
    if ' - ' not in nombre_columna:
        return nombre_columna, 'Base'
    
    # Dividir por ' - ' y tomar la última parte como serie
    partes = nombre_columna.split(' - ')
    serie = partes[-1]
    fondo = ' - '.join(partes[:-1])
    
    return fondo, serie

def crear_mapeos_fondos_series(nombres_df):
    """
    Crea los mapeos necesarios para los dropdowns en cascada
    """
    fondos_raw = nombres_df.iloc[0, :].tolist()
    codigos_raw = nombres_df.iloc[1, :].tolist()  # Fila 2: códigos
    series_raw = nombres_df.iloc[2, :].tolist()   # Fila 3: series
    
    # Limpiar datos
    fondos = [f for f in fondos_raw if pd.notna(f)]
    codigos = [c for c in codigos_raw if pd.notna(c)]
    series = [s for s in series_raw if pd.notna(s)]
    
    # Crear mapeo: fondo → lista de series disponibles
    fondos_a_series = {}
    
    # Crear mapeo: (fondo, serie) → código de columna
    fondo_serie_a_codigo = {}
    
    for i, (fondo, codigo, serie) in enumerate(zip(fondos, codigos, series)):
        # Agregar serie al fondo
        if fondo not in fondos_a_series:
            fondos_a_series[fondo] = []
        fondos_a_series[fondo].append(serie)
        
        # Mapear combinación fondo+serie al código
        fondo_serie_a_codigo[(fondo, serie)] = codigo
    
    # Obtener lista única de fondos
    fondos_unicos = list(fondos_a_series.keys())
    
    return fondos_unicos, fondos_a_series, fondo_serie_a_codigo

# def cargar_datos_optimizado():
#     """
#     Función optimizada para cargar datos con Parquet o Excel como fallback
#     """
#     try:
#         # Rutas base
#         base_paths = [
#             './data/',
#             'data/',
#             'C:/Users/gcampos05/OneDrive - SURA INVESTMENTS/Documentos/Modelos/Panel Rentabilidades PY/presentacion/'
#         ]
        
#         # Buscar archivos Parquet primero
#         for base_path in base_paths:
#             parquet_clp = os.path.join(base_path, 'series_clp.parquet')
#             parquet_usd = os.path.join(base_path, 'series_usd.parquet')
            
#             if os.path.exists(parquet_clp) and os.path.exists(parquet_usd):
#                 print(f"🚀 Cargando desde Parquet: {base_path}")
#                 pesos_df = pd.read_parquet(parquet_clp)
#                 dolares_df = pd.read_parquet(parquet_usd)
#                 # Renombrar para compatibilidad
#                 pesos_df.rename(columns={'Date': 'Dates'}, inplace=True)
#                 dolares_df.rename(columns={'Date': 'Dates'}, inplace=True)
#                 break
#         else:
#             # Fallback a Excel (tu código actual)
#             posibles_rutas = [
#                 './data/series_hist_cl.xlsx',
#                 'data/series_hist_cl.xlsx',
#                 'C:/Users/gcampos05/OneDrive - SURA INVESTMENTS/Documentos/Modelos/Panel Rentabilidades PY/presentacion/series_hist_cl.xlsx'
#             ]
            
#             ruta_archivo = None
#             for ruta in posibles_rutas:
#                 if os.path.exists(ruta):
#                     ruta_archivo = ruta
#                     break
            
#             if ruta_archivo is None:
#                 print("Error: No se encontró el archivo")
#                 return None, None, [], {}, {}, []
            
#             print(f"📖 Cargando desde Excel: {ruta_archivo}")
#             pesos_df = pd.read_excel(ruta_archivo, sheet_name='series_clp', engine='openpyxl')
#             dolares_df = pd.read_excel(ruta_archivo, sheet_name='series_usd', engine='openpyxl')
            
#             pesos_df['Date'] = pd.to_datetime(pesos_df['Date'])
#             dolares_df['Date'] = pd.to_datetime(dolares_df['Date'])
#             pesos_df.rename(columns={'Date': 'Dates'}, inplace=True)
#             dolares_df.rename(columns={'Date': 'Dates'}, inplace=True)
        
#         fondos_unicos, fondos_a_series, fondo_serie_a_codigo = crear_mapeos_desde_columnas(pesos_df, dolares_df)
#         return pesos_df, dolares_df, fondos_unicos, fondos_a_series, fondo_serie_a_codigo, []
        
#     except Exception as e:
#         print(f"Error cargando datos: {e}")
#         return None, None, [], {}, {}, []

def cargar_datos_optimizado():
    """
    Función optimizada para cargar datos con Parquet o Excel como fallback
    MODIFICADA PARA RENDER.COM
    """
    try:
        # CAMBIO: Rutas adaptadas para Render.com
        base_paths = [
            './data/',           # Carpeta local en el proyecto
            'data/',            # Alternativa sin ./
            '.'                 # Directorio raíz del proyecto
        ]
        
        # Buscar archivos Parquet primero
        for base_path in base_paths:
            feather_clp = os.path.join(base_path, 'series_clp.feather')
            feather_usd = os.path.join(base_path, 'series_usd.feather')
            
            if os.path.exists(feather_clp) and os.path.exists(feather_usd):
                print(f"🚀 Cargando desde Feather: {base_path}")
                pesos_df = pd.read_feather(feather_clp)
                dolares_df = pd.read_feather(feather_usd)
                # Renombrar para compatibilidad
                pesos_df.rename(columns={'Date': 'Dates'}, inplace=True)
                dolares_df.rename(columns={'Date': 'Dates'}, inplace=True)
                break
        else:
            # CAMBIO: Fallback a Excel con rutas relativas
            posibles_rutas = [
                './data/series_hist_cl.xlsx',
                'data/series_hist_cl.xlsx',
                './series_hist_cl.xlsx',  # En caso de estar en raíz
                'series_hist_cl.xlsx'     # Directamente en raíz
            ]
            
            ruta_archivo = None
            for ruta in posibles_rutas:
                if os.path.exists(ruta):
                    ruta_archivo = ruta
                    break
            
            if ruta_archivo is None:
                print("Error: No se encontró el archivo")
                return None, None, [], {}, {}, []
            
            print(f"📖 Cargando desde Excel: {ruta_archivo}")
            pesos_df = pd.read_excel(ruta_archivo, sheet_name='series_clp', engine='openpyxl')
            dolares_df = pd.read_excel(ruta_archivo, sheet_name='series_usd', engine='openpyxl')
            
            pesos_df['Date'] = pd.to_datetime(pesos_df['Date'])
            dolares_df['Date'] = pd.to_datetime(dolares_df['Date'])
            pesos_df.rename(columns={'Date': 'Dates'}, inplace=True)
            dolares_df.rename(columns={'Date': 'Dates'}, inplace=True)
        
        fondos_unicos, fondos_a_series, fondo_serie_a_codigo = crear_mapeos_desde_columnas(pesos_df, dolares_df)
        return pesos_df, dolares_df, fondos_unicos, fondos_a_series, fondo_serie_a_codigo, []
        
    except Exception as e:
        print(f"Error cargando datos: {e}")
        return None, None, [], {}, {}, []
    
# Cargar datos al iniciar
pesos_df, dolares_df, fondos_unicos, fondos_a_series, fondo_serie_a_codigo, codigos = cargar_datos_optimizado()

# =============================================================================
# DEFINIR FONDOS ÍNDICES FIJOS - CORREGIDO
# =============================================================================

FONDOS_INDICES = [
    ("Fondo Mutuo SURA Cartera Patrimonial Conservadora", "F"),
    ("Fondo Mutuo SURA Renta Bonos Chile", "F"), 
    ("Fondo Mutuo SURA Multiactivo Moderado", "F"),
    ("Fondo Mutuo SURA Multiactivo Agresivo", "F")
]

# =============================================================================
# FONDOS SURA PARA PDFs - LISTA CONFIGURABLE
# =============================================================================

FONDOS_SURA_PDF = [
    "Fondo Mutuo SURA Estrategia Conservadora",
    "Fondo Mutuo SURA Multiactivo Agresivo", 
    "Fondo Mutuo SURA Multiactivo Moderado",
    "Fondo Mutuo SURA Renta Bonos Chile",
    "Fondo Mutuo SURA Renta Corporativa Largo Plazo",
    "Fondo Mutuo SURA Renta Corto Plazo Chile",
    "Fondo Mutuo SURA Renta Deposito Chile",
    "Fondo Mutuo SURA Renta Internacional",
    "Fondo Mutuo SURA Renta Local UF",
    "Fondo Mutuo SURA Seleccion Acciones Chile",
    "Fondo Mutuo SURA Seleccion Acciones Emergentes",
    "Fondo Mutuo SURA Seleccion Acciones Latam",
    "Fondo Mutuo SURA Seleccion Acciones USA",
    "Fondo Mutuo SURA Seleccion Global",
    "Fondo Mutuo SURA Renta Corto Plazo UF Chile",
    "Fondo Mutuo SURA Money Market Dólar",
    "Fondo Mutuo SURA Cartera Patrimonial Conservadora",
    "Renta Local",
    "Gestion Activa", 
    "Global Desarrollado",
    "Global Emergente",
    "Chile Equities"
]

def filtrar_solo_fondos_sura(fondos_unicos, fondos_a_series, fondo_serie_a_codigo):
    """
    Filtra solo los fondos SURA para usar en PDFs
    """
    fondos_sura_filtrados = {}
    fondo_serie_codigo_sura = {}
    
    for fondo in FONDOS_SURA_PDF:
        if fondo in fondos_a_series:
            fondos_sura_filtrados[fondo] = fondos_a_series[fondo]
            
            # Copiar los códigos correspondientes
            for moneda in ['CLP', 'USD']:
                if moneda in fondos_a_series[fondo]:
                    for serie in fondos_a_series[fondo][moneda]:
                        if (fondo, serie, moneda) in fondo_serie_a_codigo:
                            fondo_serie_codigo_sura[(fondo, serie, moneda)] = fondo_serie_a_codigo[(fondo, serie, moneda)]
    
    return list(fondos_sura_filtrados.keys()), fondos_sura_filtrados, fondo_serie_codigo_sura

def obtener_codigos_indices(moneda='CLP'):
    """
    Obtiene los códigos correspondientes a los fondos índices
    """
    codigos_indices = []
    nombres_indices = []
    
    for fondo, serie in FONDOS_INDICES:
        # CAMBIO: Buscar con moneda incluida
        if (fondo, serie, moneda) in fondo_serie_a_codigo:
            codigo = fondo_serie_a_codigo[(fondo, serie, moneda)]
            nombre_completo = f"{fondo} - {serie}"
            codigos_indices.append(codigo)
            nombres_indices.append(nombre_completo)
        else:
            print(f"No encontrado en {moneda}: {fondo} - {serie}")
    
    return codigos_indices, nombres_indices

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def procesar_selecciones_multiples(selecciones_json, moneda='CLP'):
    """
    Procesa las selecciones múltiples y devuelve códigos y nombres para mostrar
    """
    if not selecciones_json:
        return [], []
    
    codigos_seleccionados = []
    nombres_mostrar = []
    
    for seleccion in selecciones_json:
        fondo = seleccion['fondo']
        series_del_fondo = seleccion['series']
        
        for serie in series_del_fondo:
            # CAMBIO: Buscar con moneda incluida
            if (fondo, serie, moneda) in fondo_serie_a_codigo:
                codigo = fondo_serie_a_codigo[(fondo, serie, moneda)]
                nombre_completo = f"{fondo} - {serie}"
                
                codigos_seleccionados.append(codigo)
                nombres_mostrar.append(nombre_completo)
    
    return codigos_seleccionados, nombres_mostrar


# =============================================================================
# FUNCIONES DE CÁLCULO (MISMAS DE ANTES)
# =============================================================================

# def calcular_rentabilidades(df, codigos_seleccionados, nombres_mostrar):
#     resultados = []
#     fecha_actual = df['Dates'].max()
    
#     for i, (codigo, nombre) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
#         if codigo in df.columns:
#             precios = df[['Dates', codigo]].dropna()
            
#             if len(precios) > 0:
#                 precio_actual = precios[codigo].iloc[-1]
                
#                 # VALIDACIONES DE PERÍODO ANTES DE CALCULAR
#                 # 1 Mes (30 días)
#                 if validar_periodo_disponible(precios, 30, fecha_actual):
#                     rent_1m = calcular_rentabilidad_periodo(precios, 30, precio_actual)
#                 else:
#                     rent_1m = "-"
                
#                 # 3 Meses (90 días)
#                 if validar_periodo_disponible(precios, 90, fecha_actual):
#                     rent_3m = calcular_rentabilidad_periodo(precios, 90, precio_actual)
#                 else:
#                     rent_3m = "-"
                
#                 # 12 Meses (365 días)
#                 if validar_periodo_disponible(precios, 365, fecha_actual):
#                     rent_12m = calcular_rentabilidad_periodo(precios, 365, precio_actual)
#                 else:
#                     rent_12m = "-"
                
#                 # YTD (validación especial)
#                 if validar_periodo_ytd(precios, fecha_actual):
#                     rent_ytd = calcular_rentabilidad_ytd(precios, precio_actual)
#                 else:
#                     rent_ytd = "-"
                
#                 # 3 Años (1095 días)
#                 if validar_periodo_disponible(precios, 1095, fecha_actual):
#                     rent_3a = calcular_rentabilidad_periodo(precios, 1095, precio_actual)
#                 else:
#                     rent_3a = "-"
                
#                 # 5 Años (1825 días)
#                 if validar_periodo_disponible(precios, 1825, fecha_actual):
#                     rent_5a = calcular_rentabilidad_periodo(precios, 1825, precio_actual)
#                 else:
#                     rent_5a = "-"
                
#                 # Separar fondo y serie del nombre completo
#                 partes = nombre.split(' - ')
#                 fondo = partes[0] if len(partes) > 0 else nombre
#                 serie = partes[1] if len(partes) > 1 else 'N/A'
                
#                 resultados.append({
#                     'Fondo': fondo,
#                     'Serie': serie,
#                     'TAC': np.random.uniform(0.5, 2.5),
#                     '1 Mes': rent_1m,
#                     '3 Meses': rent_3m,
#                     '12 Meses': rent_12m,
#                     'YTD': rent_ytd,
#                     '3 Años': rent_3a,
#                     '5 Años': rent_5a
#                 })
#    
#     return pd.DataFrame(resultados).round(2)

def calcular_rentabilidades(df, codigos_seleccionados, nombres_mostrar):
    """
    VERSIÓN OPTIMIZADA: Usa pre-cálculos cuando están disponibles
    Fallback a cálculo en tiempo real si no hay pre-cálculos
    """
    # Detectar moneda basada en el DataFrame
    moneda = 'CLP' if df is pesos_df else 'USD'
    
    # Intentar usar pre-cálculos primero
    if verificar_precalculos_vigentes():
        try:
            print("⚡ Usando pre-cálculos para rentabilidades acumuladas...")
            resultado = obtener_rentabilidades_acumuladas_precalculadas(
                moneda, codigos_seleccionados, nombres_mostrar
            )
            if resultado is not None and not resultado.empty:
                return resultado
            else:
                print("⚠️ Pre-cálculos vacíos, usando cálculo en tiempo real...")
        except Exception as e:
            print(f"⚠️ Error en pre-cálculos: {e}, usando cálculo en tiempo real...")
    
    # FALLBACK: Cálculo original en tiempo real
    print("🔄 Calculando rentabilidades en tiempo real...")
    resultados = []
    fecha_actual = df['Dates'].max()
    
    for i, (codigo, nombre) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
        if codigo in df.columns:
            precios = df[['Dates', codigo]].dropna()
            
            if len(precios) > 0:
                precio_actual = precios[codigo].iloc[-1]
                
                # 1 Mes (30 días)
                if validar_periodo_disponible(precios, 30, fecha_actual):
                    rent_1m = calcular_rentabilidad_periodo(precios, 30, precio_actual)
                else:
                    rent_1m = "-"
                
                # 3 Meses (90 días)
                if validar_periodo_disponible(precios, 90, fecha_actual):
                    rent_3m = calcular_rentabilidad_periodo(precios, 90, precio_actual)
                else:
                    rent_3m = "-"
                
                # 12 Meses (365 días)
                if validar_periodo_disponible(precios, 365, fecha_actual):
                    rent_12m = calcular_rentabilidad_periodo(precios, 365, precio_actual)
                else:
                    rent_12m = "-"
                
                # YTD (validación especial)
                if validar_periodo_ytd(precios, fecha_actual):
                    rent_ytd = calcular_rentabilidad_ytd(precios, precio_actual)
                else:
                    rent_ytd = "-"
                
                # 3 Años (1095 días)
                if validar_periodo_disponible(precios, 1095, fecha_actual):
                    rent_3a = calcular_rentabilidad_periodo(precios, 1095, precio_actual)
                else:
                    rent_3a = "-"
                
                # 5 Años (1825 días)
                if validar_periodo_disponible(precios, 1825, fecha_actual):
                    rent_5a = calcular_rentabilidad_periodo(precios, 1825, precio_actual)
                else:
                    rent_5a = "-"
                
                # Separar fondo y serie del nombre completo
                partes = nombre.split(' - ')
                fondo = partes[0] if len(partes) > 0 else nombre
                serie = partes[1] if len(partes) > 1 else 'N/A'
                
                resultados.append({
                    'Fondo': fondo,
                    'Serie': serie,
                    'TAC': np.random.uniform(0.5, 2.5),
                    '1 Mes': rent_1m,
                    '3 Meses': rent_3m,
                    '12 Meses': rent_12m,
                    'YTD': rent_ytd,
                    '3 Años': rent_3a,
                    '5 Años': rent_5a
                })
    
    return pd.DataFrame(resultados).round(2)



# def calcular_rentabilidades_anualizadas(df, codigos_seleccionados, nombres_mostrar):
#     resultados = []
#     fecha_actual = df['Dates'].max()
    
#     for i, (codigo, nombre) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
#         if codigo in df.columns:
#             precios = df[['Dates', codigo]].dropna()
            
#             if len(precios) > 0:
#                 precio_actual = precios[codigo].iloc[-1]
#                 precio_inicial = precios[codigo].iloc[0]
#                 fecha_inicial = precios['Dates'].iloc[0]
#                 fecha_actual_fondo = precios['Dates'].iloc[-1]
                
#                 años_transcurridos = (fecha_actual_fondo - fecha_inicial).days / 365.25
                
#                 if años_transcurridos > 0:
#                     rent_anual_itd = (((precio_actual / precio_inicial) ** (1/años_transcurridos)) - 1) * 100
#                 else:
#                     rent_anual_itd = 0
                
#                 # VALIDACIONES PARA RENTABILIDADES ANUALIZADAS
#                 # 1 Año
#                 if validar_periodo_disponible(precios, 365, fecha_actual):
#                     rent_anual_1a = calcular_rentabilidad_anualizada_periodo(precios, 365)
#                 else:
#                     rent_anual_1a = "-"
                
#                 # 3 Años
#                 if validar_periodo_disponible(precios, 1095, fecha_actual):
#                     rent_anual_3a = calcular_rentabilidad_anualizada_periodo(precios, 1095)
#                 else:
#                     rent_anual_3a = "-"
                
#                 # 5 Años
#                 if validar_periodo_disponible(precios, 1825, fecha_actual):
#                     rent_anual_5a = calcular_rentabilidad_anualizada_periodo(precios, 1825)
#                 else:
#                     rent_anual_5a = "-"
                
#                 # Separar fondo y serie
#                 partes = nombre.split(' - ')
#                 fondo = partes[0] if len(partes) > 0 else nombre
#                 serie = partes[1] if len(partes) > 1 else 'N/A'
                
#                 resultados.append({
#                     'Fondo': fondo,
#                     'Serie': serie,
#                     '1 Año': rent_anual_1a,
#                     '3 Años': rent_anual_3a,
#                     '5 Años': rent_anual_5a,
#                     'ITD': rent_anual_itd,
#                     'Años Historial': round(años_transcurridos, 1)
#                 })
    
#     return pd.DataFrame(resultados).round(2)

def calcular_rentabilidades_anualizadas(df, codigos_seleccionados, nombres_mostrar):
    """
    VERSIÓN OPTIMIZADA: Usa pre-cálculos cuando están disponibles
    Fallback a cálculo en tiempo real si no hay pre-cálculos
    """
    # Detectar moneda basada en el DataFrame
    moneda = 'CLP' if df is pesos_df else 'USD'
    
    # Intentar usar pre-cálculos primero
    if verificar_precalculos_vigentes():
        try:
            print("⚡ Usando pre-cálculos para rentabilidades anualizadas...")
            resultado = obtener_rentabilidades_anualizadas_precalculadas(
                moneda, codigos_seleccionados, nombres_mostrar
            )
            if resultado is not None and not resultado.empty:
                return resultado
            else:
                print("⚠️ Pre-cálculos vacíos, usando cálculo en tiempo real...")
        except Exception as e:
            print(f"⚠️ Error en pre-cálculos: {e}, usando cálculo en tiempo real...")
    
    # FALLBACK: Cálculo original en tiempo real
    print("🔄 Calculando rentabilidades anualizadas en tiempo real...")
    resultados = []
    fecha_actual = df['Dates'].max()
    
    for i, (codigo, nombre) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
        if codigo in df.columns:
            precios = df[['Dates', codigo]].dropna()
            
            if len(precios) > 0:
                precio_actual = precios[codigo].iloc[-1]
                precio_inicial = precios[codigo].iloc[0]
                fecha_inicial = precios['Dates'].iloc[0]
                fecha_actual_fondo = precios['Dates'].iloc[-1]
                
                años_transcurridos = (fecha_actual_fondo - fecha_inicial).days / 365.25
                
                if años_transcurridos > 0:
                    rent_anual_itd = (((precio_actual / precio_inicial) ** (1/años_transcurridos)) - 1) * 100
                else:
                    rent_anual_itd = 0
                
                # VALIDACIONES PARA RENTABILIDADES ANUALIZADAS
                # 1 Año
                if validar_periodo_disponible(precios, 365, fecha_actual):
                    rent_anual_1a = calcular_rentabilidad_anualizada_periodo(precios, 365)
                else:
                    rent_anual_1a = "-"
                
                # 3 Años
                if validar_periodo_disponible(precios, 1095, fecha_actual):
                    rent_anual_3a = calcular_rentabilidad_anualizada_periodo(precios, 1095)
                else:
                    rent_anual_3a = "-"
                
                # 5 Años
                if validar_periodo_disponible(precios, 1825, fecha_actual):
                    rent_anual_5a = calcular_rentabilidad_anualizada_periodo(precios, 1825)
                else:
                    rent_anual_5a = "-"
                
                # Separar fondo y serie
                partes = nombre.split(' - ')
                fondo = partes[0] if len(partes) > 0 else nombre
                serie = partes[1] if len(partes) > 1 else 'N/A'
                
                resultados.append({
                    'Fondo': fondo,
                    'Serie': serie,
                    '1 Año': rent_anual_1a,
                    '3 Años': rent_anual_3a,
                    '5 Años': rent_anual_5a,
                    'ITD': rent_anual_itd,
                    'Años Historial': round(años_transcurridos, 1)
                })
    
    return pd.DataFrame(resultados).round(2)


# def calcular_rentabilidades_por_año(df, codigos_seleccionados, nombres_mostrar):
#     resultados = []
#     años = sorted(df['Dates'].dt.year.unique())
    
#     for i, (codigo, nombre) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
#         if codigo in df.columns:
#             precios = df[['Dates', codigo]].dropna()
            
#             if len(precios) > 0:
#                 # Separar fondo y serie
#                 partes = nombre.split(' - ')
#                 fondo = partes[0] if len(partes) > 0 else nombre
#                 serie = partes[1] if len(partes) > 1 else 'N/A'
                
#                 fila_resultado = {'Fondo': fondo, 'Serie': serie}
                
#                 # Fecha de inicio del fondo
#                 fecha_inicio_fondo = precios['Dates'].min()
                
#                 for año in años:
#                     # VALIDACIÓN: Solo calcular si el fondo ya existía ese año
#                     inicio_año = pd.Timestamp(año, 1, 1)
                    
#                     if fecha_inicio_fondo <= inicio_año:
#                         # El fondo ya existía al inicio del año
#                         datos_año = precios[precios['Dates'].dt.year == año]
                        
#                         if len(datos_año) > 1:
#                             precio_inicio = datos_año[codigo].iloc[0]
#                             precio_fin = datos_año[codigo].iloc[-1]
#                             rentabilidad = ((precio_fin / precio_inicio) - 1) * 100
#                             fila_resultado[str(año)] = round(rentabilidad, 2)
#                         else:
#                             fila_resultado[str(año)] = "-"
#                     else:
#                         # El fondo no existía ese año
#                         fila_resultado[str(año)] = "-"
                
#                 resultados.append(fila_resultado)
    
#     return pd.DataFrame(resultados)

def calcular_rentabilidades_por_año(df, codigos_seleccionados, nombres_mostrar):
    """
    VERSIÓN OPTIMIZADA: Usa pre-cálculos cuando están disponibles
    Fallback a cálculo en tiempo real si no hay pre-cálculos
    """
    # Detectar moneda basada en el DataFrame
    moneda = 'CLP' if df is pesos_df else 'USD'
    
    # Intentar usar pre-cálculos primero
    if verificar_precalculos_vigentes():
        try:
            print("⚡ Usando pre-cálculos para rentabilidades por año...")
            resultado = obtener_rentabilidades_por_año_precalculadas(
                moneda, codigos_seleccionados, nombres_mostrar
            )
            if resultado is not None and not resultado.empty:
                return resultado
            else:
                print("⚠️ Pre-cálculos vacíos, usando cálculo en tiempo real...")
        except Exception as e:
            print(f"⚠️ Error en pre-cálculos: {e}, usando cálculo en tiempo real...")
    
    # FALLBACK: Cálculo original en tiempo real
    print("🔄 Calculando rentabilidades por año en tiempo real...")
    resultados = []
    años = sorted(df['Dates'].dt.year.unique())
    
    for i, (codigo, nombre) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
        if codigo in df.columns:
            precios = df[['Dates', codigo]].dropna()
            
            if len(precios) > 0:
                # Separar fondo y serie
                partes = nombre.split(' - ')
                fondo = partes[0] if len(partes) > 0 else nombre
                serie = partes[1] if len(partes) > 1 else 'N/A'
                
                fila_resultado = {'Fondo': fondo, 'Serie': serie}
                
                # Fecha de inicio del fondo
                fecha_inicio_fondo = precios['Dates'].min()
                
                for año in años:
                    # VALIDACIÓN: Solo calcular si el fondo ya existía ese año
                    inicio_año = pd.Timestamp(año, 1, 1)
                    
                    if fecha_inicio_fondo <= inicio_año:
                        # El fondo ya existía al inicio del año
                        datos_año = precios[precios['Dates'].dt.year == año]
                        
                        if len(datos_año) > 1:
                            precio_inicio = datos_año[codigo].iloc[0]
                            precio_fin = datos_año[codigo].iloc[-1]
                            rentabilidad = ((precio_fin / precio_inicio) - 1) * 100
                            fila_resultado[str(año)] = round(rentabilidad, 2)
                        else:
                            fila_resultado[str(año)] = "-"
                    else:
                        # El fondo no existía ese año
                        fila_resultado[str(año)] = "-"
                
                resultados.append(fila_resultado)
    
    return pd.DataFrame(resultados)

def calcular_rentabilidad_periodo(precios, dias, precio_actual):
    fecha_objetivo = precios['Dates'].max() - timedelta(days=dias)
    precio_pasado = precios[precios['Dates'] >= fecha_objetivo]
    
    if len(precio_pasado) > 0:
        precio_inicial = precio_pasado.iloc[0, 1]
        return ((precio_actual / precio_inicial) - 1) * 100
    return np.nan

def calcular_rentabilidad_ytd(precios, precio_actual):
    """
    CORREGIDO: YTD desde último dato del año anterior hasta hoy
    """
    try:
        fecha_actual = precios['Dates'].max()
        año_actual = fecha_actual.year
        año_anterior = año_actual - 1
        
        # CAMBIO: Buscar el ÚLTIMO dato del año anterior (no el primero del año actual)
        datos_año_anterior = precios[precios['Dates'].dt.year == año_anterior]
        
        if len(datos_año_anterior) == 0:
            return np.nan
        
        # CAMBIO: Usar iloc[-1] para el último dato del año anterior
        precio_inicio_año = datos_año_anterior.iloc[-1, 1]  # Era iloc[0, 1]
        return ((precio_actual / precio_inicio_año) - 1) * 100
        
    except:
        return np.nan

def calcular_rentabilidad_anualizada_periodo(precios, dias):
    fecha_objetivo = precios['Dates'].max() - timedelta(days=dias)
    datos_periodo = precios[precios['Dates'] >= fecha_objetivo]
    
    if len(datos_periodo) > 1:
        precio_inicial = datos_periodo.iloc[0, 1]
        precio_final = datos_periodo.iloc[-1, 1]
        fecha_inicial = datos_periodo['Dates'].iloc[0]
        fecha_final = datos_periodo['Dates'].iloc[-1]
        
        años = (fecha_final - fecha_inicial).days / 365.25
        if años > 0:
            return (((precio_final / precio_inicial) ** (1/años)) - 1) * 100
    return np.nan

def calcular_retornos_acumulados_con_limite(df, codigos_seleccionados, fecha_inicio, fecha_fin):
    """
    VERSIÓN CORREGIDA: busca fechas exactas en los datos
    """
    if not codigos_seleccionados:
        return pd.DataFrame()
    
    # Obtener fecha límite del fondo más nuevo
    fecha_limite_inicio = obtener_fecha_inicio_mas_reciente(df, codigos_seleccionados)
    
    # Ajustar fecha de inicio si es necesario
    if fecha_limite_inicio and pd.to_datetime(fecha_inicio) < fecha_limite_inicio:
        fecha_inicio_ajustada = fecha_limite_inicio
    else:
        fecha_inicio_ajustada = pd.to_datetime(fecha_inicio)
    
    # NUEVO: Buscar la fecha exacta más cercana en los datos
    fecha_inicio_exacta = buscar_fecha_exacta_en_datos(df, fecha_inicio_ajustada)
    fecha_fin_exacta = buscar_fecha_exacta_en_datos(df, pd.to_datetime(fecha_fin))
    
    # Aplicar el filtro con las fechas exactas
    df_filtrado = df[(df['Dates'] >= fecha_inicio_exacta) & (df['Dates'] <= fecha_fin_exacta)].copy()
    
    if len(df_filtrado) == 0:
        return pd.DataFrame()
    
    retornos_data = {'Dates': df_filtrado['Dates']}
    
    for codigo in codigos_seleccionados:
        if codigo in df_filtrado.columns:
            precios = df_filtrado[codigo].dropna()
            if len(precios) > 0:
                precio_base = precios.iloc[0]
                retornos_acumulados = ((precios / precio_base) - 1) * 100
                retornos_data[codigo] = retornos_acumulados
    
    return pd.DataFrame(retornos_data)

def obtener_fecha_inicio_mas_reciente(df, codigos_seleccionados):
    """
    Obtiene la fecha de inicio más reciente (fondo más nuevo) entre los códigos seleccionados
    
    Args:
        df: DataFrame con datos de precios
        codigos_seleccionados: Lista de códigos de fondos seleccionados
        
    Returns:
        pd.Timestamp: Fecha de inicio del fondo más nuevo, o None si no hay datos
    """
    if not codigos_seleccionados or df is None:
        return None
    
    fechas_inicio = []
    
    for codigo in codigos_seleccionados:
        if codigo in df.columns:
            datos_fondo = df[['Dates', codigo]].dropna()
            if len(datos_fondo) > 0:
                fecha_inicio_fondo = datos_fondo['Dates'].min()
                fechas_inicio.append(fecha_inicio_fondo)
    
    if not fechas_inicio:
        return None
    
    # Retornar la fecha MÁS RECIENTE (fondo más nuevo)
    return max(fechas_inicio)

def calcular_anos_disponibles(fecha_inicio_mas_reciente, fecha_actual):
    """
    Calcula cuántos años de historial hay disponibles desde el fondo más nuevo
    
    Args:
        fecha_inicio_mas_reciente: Fecha de inicio del fondo más nuevo
        fecha_actual: Fecha actual/final
        
    Returns:
        float: Número de años disponibles
    """
    if not fecha_inicio_mas_reciente or not fecha_actual:
        return 0
    
    dias_disponibles = (fecha_actual - fecha_inicio_mas_reciente).days
    anos_disponibles = dias_disponibles / 365.25
    
    return anos_disponibles


def validar_periodo_disponible(precios, periodo_dias, fecha_actual=None):
    """
    Valida si hay suficiente historial para calcular el período solicitado
    
    Args:
        precios: DataFrame con 'Dates' y precios del fondo
        periodo_dias: Número de días del período (30, 90, 365, 1095, 1825)
        fecha_actual: Fecha actual (opcional)
        
    Returns:
        bool: True si hay suficiente historial, False si no
    """
    if len(precios) == 0:
        return False
    
    if fecha_actual is None:
        fecha_actual = precios['Dates'].max()
    
    fecha_inicio_requerida = fecha_actual - timedelta(days=periodo_dias)
    fecha_inicio_disponible = precios['Dates'].min()
    
    # Debe tener AL MENOS el período completo
    return fecha_inicio_disponible <= fecha_inicio_requerida

def validar_periodo_ytd(precios, fecha_actual=None):
    """
    Valida si hay datos del año anterior para calcular YTD
    """
    if len(precios) == 0:
        return False
    
    if fecha_actual is None:
        fecha_actual = precios['Dates'].max()
    
    año_anterior = fecha_actual.year - 1
    datos_año_anterior = precios[precios['Dates'].dt.year == año_anterior]
    
    return len(datos_año_anterior) > 0

def ajustar_fecha_segun_periodo_y_limite(fecha_fin, periodo, fecha_limite_inicio):
    """
    Ajusta la fecha de inicio según el período solicitado, respetando el límite del fondo más nuevo
    
    Args:
        fecha_fin: Fecha final
        periodo: Período solicitado ('1m', '3m', '6m', 'ytd', '1y', '3y', '5y', 'max')
        fecha_limite_inicio: Fecha más antigua permitida (fondo más nuevo)
        
    Returns:
        pd.Timestamp: Fecha de inicio ajustada
    """

    if not fecha_limite_inicio:
        # Sin límite, calcular normalmente
        if periodo == '1m':
            return fecha_fin - timedelta(days=30)
        elif periodo == '3m':
            return fecha_fin - timedelta(days=90)
        elif periodo == '6m':
            return fecha_fin - timedelta(days=180)
        elif periodo == 'ytd':
            # CAMBIO: YTD debe ir al año anterior, no al 1 de enero del año actual
            año_anterior = fecha_fin.year - 1
            return pd.Timestamp(año_anterior, 12, 31)  # Último día del año anterior
        elif periodo == '1y':
            return fecha_fin - timedelta(days=365)
        elif periodo == '3y':
            return fecha_fin - timedelta(days=1095)
        elif periodo == '5y':
            return fecha_fin - timedelta(days=1825)
        elif periodo == 'max':
            return fecha_limite_inicio
        else:
            return fecha_fin - timedelta(days=365)
    
    # Con límite, calcular y ajustar
    if periodo == '1m':
        fecha_inicio_calculada = fecha_fin - timedelta(days=30)
    elif periodo == '3m':
        fecha_inicio_calculada = fecha_fin - pd.DateOffset(months=3)
    elif periodo == '6m':
        fecha_inicio_calculada = fecha_fin - pd.DateOffset(months=6)
    elif periodo == 'ytd':
        # CAMBIO: Para YTD, buscar en el año anterior
        año_anterior = fecha_fin.year - 1
        fecha_inicio_calculada = pd.Timestamp(año_anterior, 12, 31)
    elif periodo == '1y':
        fecha_inicio_calculada = fecha_fin - timedelta(days=365)
    elif periodo == '3y':
        fecha_inicio_calculada = fecha_fin - timedelta(days=1095)
    elif periodo == '5y':
        fecha_inicio_calculada = fecha_fin - timedelta(days=1825)
    elif periodo == 'max':
        return fecha_limite_inicio
    else:
        fecha_inicio_calculada = fecha_fin - timedelta(days=365)
    
    # Retornar la fecha más reciente entre la calculada y el límite
    return fecha_inicio_calculada


def buscar_fecha_exacta_en_datos(df, fecha_objetivo, codigo=None):
    """
    Busca la fecha exacta en los datos, o la más cercana anterior si no existe
    
    Args:
        df: DataFrame con datos
        fecha_objetivo: Fecha que queremos buscar
        codigo: Código del fondo (opcional, para verificar que tenga datos)
        
    Returns:
        pd.Timestamp: Fecha encontrada en los datos
    """
    try:
        fechas_disponibles = df['Dates'].dropna().sort_values()
        
        # Si tenemos la fecha exacta, usarla
        if fecha_objetivo in fechas_disponibles.values:
            return fecha_objetivo
        
        # Si no, buscar la fecha más cercana anterior
        fechas_anteriores = fechas_disponibles[fechas_disponibles <= fecha_objetivo]
        
        if len(fechas_anteriores) > 0:
            return fechas_anteriores.iloc[-1]  # La más reciente de las anteriores
        else:
            # Si no hay fechas anteriores, usar la primera disponible
            return fechas_disponibles.iloc[0]
            
    except:
        return fecha_objetivo
    

def crear_grafico_retornos(df_retornos, codigos_seleccionados, nombres_mostrar):
    if df_retornos.empty:
        return go.Figure().add_annotation(
            text="No hay datos para el período seleccionado",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Validación de datos de entrada
    if not codigos_seleccionados or not nombres_mostrar:
        return go.Figure().add_annotation(
            text="No hay fondos seleccionados",
            x=0.5, y=0.5, showarrow=False
        )
    
    try:
        # Función auxiliar para formatear fechas en español
        def formatear_fecha_espanol(fecha):
            try:
                dias_es = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
                meses_es = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                           'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
                
                dia_semana = dias_es[fecha.weekday()]
                dia = fecha.day
                mes = meses_es[fecha.month - 1]
                año = fecha.year
                
                return f"{dia_semana} {dia} de {mes} {año}"
            except:
                return str(fecha)
        
        fig = go.Figure()
        
        paleta_primaria = ['#24272A', '#0B2DCE', '#5A646E', '#98A4AE', '#FFE946']
        paleta_secundaria = [
            '#727272', '#52C599', '#CC9967', '#9B5634', '#D4BE7F', 
            '#3C86B4', '#A0A0A0', '#7FD4B3', '#D5AB80', '#C9805C', 
            '#9E3541', '#A8CDE2', '#C8C8C8', '#A3E1C2', '#E0C1A2', 
            '#D49A7D', '#DE9CA6', '#CBB363'
        ]
        
        num_fondos = len(codigos_seleccionados)
        colores_a_usar = paleta_primaria if num_fondos <= 5 else paleta_secundaria
        
        # Preparar datos con validación
        try:
            fechas_formateadas = [formatear_fecha_espanol(fecha.date()) for fecha in df_retornos['Dates']]
        except:
            fechas_formateadas = [str(fecha) for fecha in df_retornos['Dates']]
        
        # Crear hover texts personalizados con manejo de errores
        hover_texts_por_traza = []
        
        for i, (codigo, nombre_mostrar) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
            hover_texts = []
            
            if codigo not in df_retornos.columns:
                hover_texts_por_traza.append([])
                continue
            
            for j in range(len(df_retornos)):
                try:
                    # Para cada punto, obtener todos los valores de fondos en esa fecha
                    valores_fecha = []
                    
                    for k, otro_codigo in enumerate(codigos_seleccionados):
                        if otro_codigo in df_retornos.columns and j < len(df_retornos[otro_codigo]):
                            try:
                                valor_otro = df_retornos[otro_codigo].iloc[j]
                                if pd.notna(valor_otro):
                                    # Preparar nombre más corto
                                    nombre_otro = nombres_mostrar[k].replace("FONDO MUTUO SURA ", "").replace("SURA ", "")
                                    if " - " in nombre_otro:
                                        partes = nombre_otro.split(" - ")
                                        nombre_final = f"{partes[0]} ({partes[1]})" if len(partes) > 1 else nombre_otro
                                    else:
                                        nombre_final = nombre_otro
                                    
                                    # Obtener color para este fondo
                                    color_fondo = colores_a_usar[k % len(colores_a_usar)]
                                    
                                    valores_fecha.append((nombre_final, float(valor_otro), color_fondo))
                            except (IndexError, TypeError, ValueError):
                                continue
                    
                    # ORDENAR POR VALOR DESCENDENTE (mayor rendimiento primero)
                    valores_fecha.sort(key=lambda x: x[1], reverse=True)
                    
                    # Crear texto del hover con fecha y todos los fondos ordenados
                    try:
                        fecha_str = fechas_formateadas[j] if j < len(fechas_formateadas) else str(df_retornos['Dates'].iloc[j])
                    except:
                        fecha_str = f"Fecha {j}"
                    
                    hover_text = f"<b>{fecha_str}</b><br><br>"
                    for nombre_fondo, valor_fondo, color_fondo in valores_fecha:
                        # Crear indicador de color con círculo colorado
                        hover_text += f"<span style='color:{color_fondo}'>●</span> <b>{nombre_fondo}:</b> {valor_fondo:.2f}%<br>"
                    
                    hover_texts.append(hover_text)
                    
                except Exception as e:
                    # En caso de error, crear un hover básico
                    hover_texts.append(f"<b>Error en datos</b><br>Punto {j}")
            
            hover_texts_por_traza.append(hover_texts)
        
        # Crear las trazas con validación
        for i, (codigo, nombre_mostrar) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
            if codigo not in df_retornos.columns:
                continue
                
            try:
                color_linea = colores_a_usar[i % len(colores_a_usar)]
                
                # Preparar nombre más corto para la leyenda
                nombre_corto = nombre_mostrar.replace("FONDO MUTUO SURA ", "").replace("SURA ", "")
                if " - " in nombre_corto:
                    partes = nombre_corto.split(" - ")
                    nombre_final = f"{partes[0]} ({partes[1]})" if len(partes) > 1 else nombre_corto
                else:
                    nombre_final = nombre_corto
                
                # Asegurar que tenemos hover texts para esta traza
                hover_texts_traza = hover_texts_por_traza[i] if i < len(hover_texts_por_traza) else []
                
                # Si no hay suficientes hover texts, rellenar con textos básicos
                while len(hover_texts_traza) < len(df_retornos):
                    hover_texts_traza.append(f"<b>{nombre_final}</b><br>Datos no disponibles")
                
                fig.add_trace(go.Scatter(
                    x=df_retornos['Dates'],
                    y=df_retornos[codigo],
                    mode='lines',
                    name=nombre_final,
                    line=dict(color=color_linea, width=2),
                    hovertemplate='%{text}<extra></extra>',
                    text=hover_texts_traza,
                    showlegend=True
                ))
                
            except Exception as e:
                # Si hay error en esta traza, continuar con la siguiente
                print(f"Error creando traza para {codigo}: {e}")
                continue
        
        # Configurar layout
        fig.update_layout(
            title={
                'text': 'Retornos Acumulados',
                'x': 0.5,
                'y': 0.95,
                'font': {'family': 'SuraSans-SemiBold', 'size': 18, 'color': '#24272A'}
            },
            xaxis_title='Fecha',
            yaxis_title='Retorno Acumulado (%)',
            font={'family': 'SuraSans-Regular', 'color': '#24272A'},
            
            hovermode='closest',
            
            hoverlabel=dict(
                bgcolor="rgba(255, 255, 255, 0.98)",
                bordercolor="rgba(0, 0, 0, 0.15)",
                font=dict(
                    family='SuraSans-Regular',
                    size=12,
                    color="#25405C"
                ),
                align="left",
                namelength=-1),

            xaxis=dict(
                showgrid=False,
                showspikes=True,
                spikecolor="rgba(36, 39, 42, 0.3)",
                spikesnap="cursor",
                spikemode="across",
                spikethickness=1,
                spikedash="dot",
                tickformat='%d/%m/%Y'
            ),
            yaxis=dict(
                tickformat='.1f',
                ticksuffix='%',
                showgrid=True,
                gridcolor='rgba(128,128,128,0.2)',
            ),

            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="center",
                x=0.5,
                font={'family': 'SuraSans-Regular', 'size': 10}
            ),
            height=500,
            margin=dict(t=60, b=50, l=50, r=50),
            template='plotly_white',
            plot_bgcolor='white',
            paper_bgcolor='white',
            
            # AGREGAR LOGO EN LA ESQUINA INFERIOR DERECHA (más abajo y más grande)
            images=[
                dict(
                    source="/assets/investments_logo.png",  # Ruta del logo
                    xref="paper", 
                    yref="paper",
                    x=0.99,  # Posición horizontal (cerca del borde derecho)
                    y=-0.27,  # Posición vertical (más abajo que la leyenda)
                    sizex=0.28,  # Ancho del logo (18% del gráfico - más grande)
                    sizey=0.22,  # Alto del logo (12% del gráfico - más grande)
                    xanchor="right",  # Anclar desde la derecha
                    yanchor="bottom",  # Anclar desde abajo
                    opacity=1,  # Más visible
                    layer="above"  # Mostrar encima del gráfico
                )
            ]
        )
        
        return fig
        
    except Exception as e:
        # Si hay cualquier error, devolver un gráfico con mensaje de error
        print(f"Error en crear_grafico_retornos: {e}")
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"Error al crear el gráfico: {str(e)}",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red")
        )
        error_fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=500
        )
        return error_fig
    
# =============================================================================
# FUNCIONES PARA CREAR COMPONENTES DINÁMICOS
# =============================================================================

def crear_selector_fondo(id_selector):
    """
    Crea un componente selector de fondo + series con botón de eliminar
    """
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Fondo:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'fondo-dropdown', 'index': id_selector},
                        options=[{'label': fondo, 'value': fondo} for fondo in fondos_unicos],
                        value=None,
                        placeholder="Selecciona un fondo...",
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=5),
                
                dbc.Col([
                    html.Label("Series:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'series-dropdown', 'index': id_selector},
                        options=[],
                        value=[],
                        multi=True,
                        placeholder="Primero selecciona un fondo",
                        disabled=True,
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=6),
                
                dbc.Col([
                    html.Br(),
                    dbc.Button(
                        "❌", 
                        id={'type': 'eliminar-selector', 'index': id_selector},
                        color="danger", 
                        size="sm",
                        style={'marginTop': '5px'}
                    )
                ], width=1)
            ])
        ])
    ], style={'marginBottom': '10px'})

# =============================================================================
# COMPONENTES UI
# =============================================================================

# Modal de información
modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Cómo usar el Portal de Rentabilidades", 
                                   style={'fontFamily': 'SuraSans-SemiBold'})),
    dbc.ModalBody([
        html.P("Bienvenido al Portal de Rentabilidades de SURA Investments", 
               style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '18px'}),
        html.Hr(),
        html.H5("Navegación:", style={'fontFamily': 'SuraSans-SemiBold'}),
        html.Ul([
            html.Li("Rentabilidad Acumulada: Visualiza el crecimiento acumulado de los fondos", 
                    style={'fontFamily': 'SuraSans-Regular'}),
            html.Li("Rentabilidad Anualizada: Consulta el rendimiento anual promedio", 
                    style={'fontFamily': 'SuraSans-Regular'}),
            html.Li("Rentabilidad por Año: Compara el desempeño año a año", 
                    style={'fontFamily': 'SuraSans-Regular'})
        ]),
        html.Hr(),
        html.H5("Nueva Funcionalidad:", style={'fontFamily': 'SuraSans-SemiBold'}),
        html.Ul([
            html.Li("Ahora puedes comparar múltiples fondos diferentes a la vez", 
                    style={'fontFamily': 'SuraSans-Regular'}),
            html.Li("Usa el botón '+ Agregar Fondo' para añadir más comparaciones", 
                    style={'fontFamily': 'SuraSans-Regular'}),
            html.Li("Cada fondo puede tener múltiples series seleccionadas", 
                    style={'fontFamily': 'SuraSans-Regular'}),
            html.Li("Ejemplo: ESTRATEGIA ACTIVA (Serie B) vs MULTIACTIVO (Series A,C,D)", 
                    style={'fontFamily': 'SuraSans-Regular'})
        ]),
        html.Hr(),
        html.P("Los datos se actualizan diariamente con información de Bloomberg.", 
               style={'fontFamily': 'SuraSans-Regular', 'fontStyle': 'italic'})
    ]),
    dbc.ModalFooter(
        dbc.Button("Cerrar", id="close-modal", className="ms-auto", 
                   style={'fontFamily': 'SuraSans-Regular'})
    ),
], id="info-modal", is_open=False, size="lg")

# Modal para gráfico en pantalla completa (ACUMULADA)
modal_grafico = dbc.Modal([
    dbc.ModalHeader([
        dbc.ModalTitle("Retornos Acumulados - Vista Completa", 
                      style={'fontFamily': 'SuraSans-SemiBold'}),
    ], close_button=True),
    dbc.ModalBody([
        dcc.Graph(
            id='grafico-retornos-modal', 
            style={'height': '85vh', 'width': '100%'},
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToAdd': ['toImage'],
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'retornos_acumulados_fullscreen',
                    'height': 1200,
                    'width': 1800,
                    'scale': 2
                }
            }
        )
    ], style={'padding': '5px'}),
], id="modal-grafico", is_open=False, size="xl", centered=True, 
   style={'maxWidth': '100', 'maxHeight': '95vh'})
# Modal para gráfico anualizada en pantalla completa (ANUALIZADA)
modal_grafico_anualizada = dbc.Modal([
    dbc.ModalHeader([
        dbc.ModalTitle("Rentabilidades Anualizadas - Vista Completa", 
                      style={'fontFamily': 'SuraSans-SemiBold'}),
    ], close_button=True),
    dbc.ModalBody([
        dcc.Graph(
            id='grafico-retornos-anualizados-modal', 
            style={'height': '85vh', 'width': '100%'},
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToAdd': ['toImage'],
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'rentabilidades_anualizadas_fullscreen',
                    'height': 1200,
                    'width': 1800,
                    'scale': 2
                }
            }
        )
    ], style={'padding': '5px'}),
], id="modal-grafico-anualizada", is_open=False, size="xl", centered=True, 
   style={'maxWidth': '100', 'maxHeight': '95vh'})


# Barra superior blanca
top_navbar = dbc.Navbar(
    dbc.Container([
        html.Img(
            src="/assets/sura_logo.png",
            height="50px",
            style={'marginRight': '20px'}
        ),
        # Este DIV agrupa los 3 botones y está a la derecha (auto margin left)
        html.Div([
            dbc.Button([
                html.I(className="fas fa-info-circle", style={'marginRight': '8px'}),
                "Información"
            ],
            id="info-button",
            color="dark",
            style={
                'fontFamily': 'SuraSans-Regular',
                'backgroundColor': '#24272A',
                'borderColor': '#24272A',
                'color': 'white',
                'marginRight': '10px'
            }),
            dbc.Button([
                html.I(className="fas fa-file-chart-line", style={'marginRight': '8px'}),
                "Informe Rentabilidad"
            ],
            id="informe-button",
            color="dark",
            style={
                'fontFamily': 'SuraSans-Regular',
                'backgroundColor': '#24272A',
                'borderColor': '#24272A',
                'color': 'white',
                'marginRight': '10px'
            }),
            dbc.Button([
                html.I(className="fas fa-calendar", style={'marginRight': '8px'}),
                "Anexo Retornos Mensuales"
            ],
            id="anexo-button",
            color="dark",
            style={
                'fontFamily': 'SuraSans-Regular',
                'backgroundColor': '#24272A',
                'borderColor': '#24272A',
                'color': 'white'
            }),
        ], style={'marginLeft': 'auto'}),

    ],  # <-- aquí cierras la lista de hijos de Container
       fluid=True,
       style={'display': 'flex', 'alignItems': 'center'}
    ),
    color="white",
    dark=False,
    sticky="top",
    style={'borderBottom': '1px solid #e0e0e0', 'height': '70px'}
)

# Barra inferior negra
bottom_navbar = html.Div([
   dbc.Container([
       html.H3(
           "INVESTMENTS", 
           style={
               'color': 'white', 
               'margin': '0', 
               'fontFamily': 'SuraSans-SemiBold',
               'fontSize': '24px',
               'letterSpacing': '2px'
           }
       )
   ], fluid=True, style={'display': 'flex', 'alignItems': 'center', 'height': '100%'})
], style={
   'backgroundColor': '#000000',
   'height': '50px',
   'width': '100%'
})
# Pestañas de navegación
tabs = dbc.Tabs([
   dbc.Tab(label="Rentabilidad Acumulada", tab_id="acumulada", 
           label_style={'fontFamily': 'SuraSans-Regular', 'fontWeight': 'bold'}),
   dbc.Tab(label="Rentabilidad Anualizada", tab_id="anualizada", 
           label_style={'fontFamily': 'SuraSans-Regular', 'fontWeight': 'bold'}),
   dbc.Tab(label="Rentabilidad por Año", tab_id="por_ano", 
           label_style={'fontFamily': 'SuraSans-Regular', 'fontWeight': 'bold'}),
], id="tabs", active_tab="acumulada", style={'marginTop': '20px'})

# CONTROLES CON NUEVA ESTRUCTURA - DOS SECCIONES INDEPENDIENTES
controles_acumulada = html.Div([
    # 1) Fila para el selector de moneda (arriba de todo)
    dbc.Row([
        dbc.Col([
            html.Label("Moneda:", style={'fontFamily': 'SuraSans-SemiBold'}),
            dcc.Dropdown(
                id='moneda-selector-acumulada',
                options=[
                    {'label': 'Pesos Chilenos (CLP)', 'value': 'CLP'},
                    {'label': 'Dólares (USD)', 'value': 'USD'}
                ],
                value='CLP',
                style={'fontFamily': 'SuraSans-Regular'}
            )
        ], width=4)
    ], style={'marginBottom': '30px'}),
    
    # ============================================================================
    # SECCIÓN 1: ÍNDICES PRINCIPALES (INDEPENDIENTE)
    # ============================================================================
    html.Div([
        # Título principal de sección
        html.H2("Rentabilidades - Índices Principales", 
                style={'fontFamily': 'SuraSans-SemiBold', 'marginBottom': '20px', 'color': '#24272A'}),
        
        # Botones de control SOLO para índices
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("Rentabilidad Acumulada", id="btn-indices-acumulada", 
                            color="dark", outline=False, style={'fontFamily': 'SuraSans-Regular'}),
                    dbc.Button("Rentabilidad Anualizada", id="btn-indices-anualizada", 
                            color="secondary", outline=True, style={'fontFamily': 'SuraSans-Regular'}),
                    dbc.Button("Rentabilidad por Año", id="btn-indices-por-ano", 
                            color="secondary", outline=True, style={'fontFamily': 'SuraSans-Regular'})
                ], size="md")
            ], width=12, style={'textAlign': 'center', 'marginBottom': '20px'})
        ]),
        
        # Contenedor para la tabla de índices (cambiará según el botón)
        html.Div(id='tabla-indices-dinamica'),
        
        html.Hr(style={'marginTop': '30px', 'marginBottom': '30px'})
    ]),
    
    # ============================================================================
    # SECCIÓN 2: FONDOS PERSONALIZADOS (INDEPENDIENTE)
    # ============================================================================
    html.Div([
        # Título principal de sección
        html.H2("Rentabilidades - Fondos Personalizados", 
                style={'fontFamily': 'SuraSans-SemiBold', 'marginBottom': '20px', 'color': '#24272A'}),
        
        # Botones de control SOLO para fondos personalizados
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("Rentabilidad Acumulada", id="btn-personalizados-acumulada", 
                            color="dark", outline=False, style={'fontFamily': 'SuraSans-Regular'}),
                    dbc.Button("Rentabilidad Anualizada", id="btn-personalizados-anualizada", 
                            color="secondary", outline=True, style={'fontFamily': 'SuraSans-Regular'}),
                    dbc.Button("Rentabilidad por Año", id="btn-personalizados-por-ano", 
                            color="secondary", outline=True, style={'fontFamily': 'SuraSans-Regular'})
                ], size="md")
            ], width=12, style={'textAlign': 'center', 'marginBottom': '20px'})
        ]),
        
        # Botón para agregar fondos personalizados
        dbc.Row([
            dbc.Col([
                dbc.Button([
                    html.I(className="fas fa-plus", style={'marginRight': '8px'}),
                    "Agregar Fondo Personalizado"
                ], 
                id="btn-agregar-fondo", 
                color="dark", 
                style={'fontFamily': 'SuraSans-Regular'})
            ], width=12, style={'textAlign': 'left', 'marginBottom': '20px'})
        ]),
        
        # Contenedor para los selectores dinámicos
        html.Div(id='selectores-container', children=[]),
        
        # Store para mantener el estado de las selecciones
        dcc.Store(id='selecciones-store', data=[]),
        
        html.Hr(style={'marginTop': '20px', 'marginBottom': '20px'}),
        
        # Contenedor para la tabla de personalizados (cambiará según el botón)
        html.Div(id='tabla-personalizados-dinamica'),
        
        # Sección del gráfico (mantiene la funcionalidad actual)
        html.H5("Gráfico de Retornos Acumulados:", style={'fontFamily': 'SuraSans-SemiBold', 'marginTop': '40px', 'marginBottom': '15px'}),
        
        dbc.Row([
            dbc.Col([
                dbc.Button([
                    html.I(className="fas fa-expand", style={'marginRight': '8px'}),
                    "Ver en Pantalla Completa"
                ], 
                id="btn-pantalla-completa", 
                color="dark",                    
                size="sm",
                style={
                    'fontFamily': 'SuraSans-Regular',
                    'marginBottom': '10px',
                    'color': 'white'             
                })
            ], width=12, style={'textAlign': 'right'})
        ]),
        
        dcc.Store(id="periodo-activo", data="btn-1y"),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Label("Desde:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px', 'marginBottom': '5px'}),
                    dcc.DatePickerSingle(
                        id='fecha-inicio-grafico',
                        date=datetime.now() - timedelta(days=365),
                        display_format='DD/MM/YYYY',
                        style={'width': '100%', 'marginBottom': '10px'}
                    ),
                    html.Label("Hasta:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px', 'marginBottom': '5px'}),
                    dcc.DatePickerSingle(
                        id='fecha-fin-grafico',
                        date=datetime.now(),
                        display_format='DD/MM/YYYY',
                        style={'width': '100%', 'marginBottom': '15px'}
                    ),
                    html.Div([
                        dbc.Button("1M", id="btn-1m", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                        dbc.Button("3M", id="btn-3m", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                        dbc.Button("6M", id="btn-6m", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                        dbc.Button("YTD", id="btn-ytd", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '50px', 'border': '1px solid black', 'color': 'black'}),
                        dbc.Button("1Y", id="btn-1y", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                        dbc.Button("3Y", id="btn-3y", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                        dbc.Button("5Y", id="btn-5y", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                        dbc.Button("Max", id="btn-max", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '50px', 'border': '1px solid black', 'color': 'black'}),
                    ], style={
                        'borderRadius': '5px',
                        'display': 'flex',
                        'flexWrap': 'wrap'
                    })
                ])
            ], width=3),
            
            dbc.Col([
                dcc.Graph(
                    id='grafico-retornos-acumulados',
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToAdd': ['toImage'],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'retornos_acumulados',
                            'height': 800,
                            'width': 1200,
                            'scale': 2
                        }
                    }
                )
            ], width=9)
        ], style={'marginBottom': '20px'})
    ])
    
], id="content-acumulada", style={'display': 'block'})

# PESTAÑAS DE ANUALIZADA Y POR AÑO (version simplificada para mantener funcionalidad básica)
controles_anualizada = html.Div([
    # Fila para pestañas
    dbc.Row([
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(label="Rentabilidad Acumulada", tab_id="acumulada", 
                        label_style={'fontFamily': 'SuraSans-Regular', 'fontWeight': 'bold'}),
                dbc.Tab(label="Rentabilidad Anualizada", tab_id="anualizada", 
                        label_style={'fontFamily': 'SuraSans-Regular', 'fontWeight': 'bold'}),
                dbc.Tab(label="Rentabilidad por Año", tab_id="por_ano", 
                        label_style={'fontFamily': 'SuraSans-Regular', 'fontWeight': 'bold'}),
            ], id="tabs-anualizada", active_tab="anualizada")
        ], width=8)
    ]),
    # Fila para selector de moneda
    dbc.Row([
        dbc.Col([
            html.Label("Moneda:", style={'fontFamily': 'SuraSans-SemiBold'}),
            dcc.Dropdown(
                id='moneda-selector-anualizada',
                options=[
                    {'label': 'Pesos Chilenos (CLP)', 'value': 'CLP'},
                    {'label': 'Dólares (USD)', 'value': 'USD'}
                ],
                value='CLP',
                style={'fontFamily': 'SuraSans-Regular'}
            )
        ], width=3)
    ], style={'marginTop': '30px', 'marginBottom': '20px', 'textAlign': 'left'}),

    html.H2("Rentabilidad Anualizada", 
            style={'fontFamily': 'SuraSans-SemiBold', 'marginBottom': '20px'}),

    html.P("Rentabilidades expresadas como tasa anual compuesta equivalente.", 
           style={'fontFamily': 'SuraSans-Regular', 'fontStyle': 'italic', 'marginBottom': '20px'}),

    # TABLA DE ÍNDICES FIJA PARA ANUALIZADA
    html.H5("Índices Principales:", style={'fontFamily': 'SuraSans-SemiBold', 'marginBottom': '15px'}),
    html.Div(id='tabla-indices-anualizada'),
    
    html.Hr(style={'marginTop': '20px', 'marginBottom': '20px'}),
    
    # NUEVA SECCIÓN: Botón para agregar fondos personalizados ANUALIZADA
    dbc.Row([
        dbc.Col([
            dbc.Button([
                html.I(className="fas fa-plus", style={'marginRight': '8px'}),
                "Agregar Fondo Personalizado"
            ], 
            id="btn-agregar-fondo-anualizada", 
            color="dark", 
            style={'fontFamily': 'SuraSans-Regular'})
        ], width=12, style={'textAlign': 'left', 'marginBottom': '20px'})
    ]),
    
    # NUEVA SECCIÓN: Contenedor para los selectores dinámicos ANUALIZADA
    html.Div(id='selectores-container-anualizada', children=[]),
    
    # NUEVA SECCIÓN: Store para mantener el estado de las selecciones ANUALIZADA
    dcc.Store(id='selecciones-store-anualizada', data=[]),
    
    html.Hr(style={'marginTop': '20px', 'marginBottom': '20px'}),
    
    # NUEVA SECCIÓN: Tabla de rentabilidades personalizadas ANUALIZADA
    html.H5("Tabla de Rentabilidades Personalizadas:", style={'fontFamily': 'SuraSans-SemiBold', 'marginBottom': '15px'}),
    html.Div(id='tabla-rentabilidades-anualizada'),
    
    # *** NUEVA SECCIÓN: GRÁFICO DE RENTABILIDADES ANUALIZADAS ***
    html.H5("Gráfico de Rentabilidades Anualizadas:", style={'fontFamily': 'SuraSans-SemiBold', 'marginTop': '40px', 'marginBottom': '15px'}),
    
    dbc.Row([
        dbc.Col([
            dbc.Button([
                html.I(className="fas fa-expand", style={'marginRight': '8px'}),
                "Ver en Pantalla Completa"
            ], 
            id="btn-pantalla-completa-anualizada", 
            color="dark",                    
            size="sm",
            style={
                'fontFamily': 'SuraSans-Regular',
                'marginBottom': '10px',
                'color': 'white'             
            })
        ], width=12, style={'textAlign': 'right'})
    ]),
    
    # Store para período activo (independiente)
    dcc.Store(id="periodo-activo-anualizada", data="btn-1y-anualizada"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Desde:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px', 'marginBottom': '5px'}),
                dcc.DatePickerSingle(
                    id='fecha-inicio-grafico-anualizada',
                    date=datetime.now() - timedelta(days=365),
                    display_format='DD/MM/YYYY',
                    style={'width': '100%', 'marginBottom': '10px'}
                ),
                html.Label("Hasta:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px', 'marginBottom': '5px'}),
                dcc.DatePickerSingle(
                    id='fecha-fin-grafico-anualizada',
                    date=datetime.now(),
                    display_format='DD/MM/YYYY',
                    style={'width': '100%', 'marginBottom': '15px'}
                ),
                html.Div([
                    dbc.Button("1M", id="btn-1m-anualizada", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("3M", id="btn-3m-anualizada", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("6M", id="btn-6m-anualizada", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("YTD", id="btn-ytd-anualizada", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '50px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("1Y", id="btn-1y-anualizada", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("3Y", id="btn-3y-anualizada", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("5Y", id="btn-5y-anualizada", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("Max", id="btn-max-anualizada", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '50px', 'border': '1px solid black', 'color': 'black'}),
                ], style={
                    'borderRadius': '5px',
                    'display': 'flex',
                    'flexWrap': 'wrap'
                })
            ])
        ], width=3),
        
        dbc.Col([
            dcc.Graph(
                id='grafico-retornos-anualizados',
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToAdd': ['toImage'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'retornos_anualizados',
                        'height': 800,
                        'width': 1200,
                        'scale': 2
                    }
                }
            )
        ], width=9)
    ], style={'marginBottom': '20px'})

], id="content-anualizada", style={'display': 'none'})


# 2. MODIFICAR controles_por_año (línea ~1130 aprox)
controles_por_año = html.Div([
    # Fila para pestañas
    dbc.Row([
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(label="Rentabilidad Acumulada", tab_id="acumulada", 
                        label_style={'fontFamily': 'SuraSans-Regular', 'fontWeight': 'bold'}),
                dbc.Tab(label="Rentabilidad Anualizada", tab_id="anualizada", 
                        label_style={'fontFamily': 'SuraSans-Regular', 'fontWeight': 'bold'}),
                dbc.Tab(label="Rentabilidad por Año", tab_id="por_ano", 
                        label_style={'fontFamily': 'SuraSans-Regular', 'fontWeight': 'bold'}),
            ], id="tabs-por-ano", active_tab="por_ano")
        ], width=8)
    ]),

    # Fila para selector de moneda
    dbc.Row([
        dbc.Col([
            html.Label("Moneda:", style={'fontFamily': 'SuraSans-SemiBold'}),
            dcc.Dropdown(
                id='moneda-selector-por-año',
                options=[
                    {'label': 'Pesos Chilenos (CLP)', 'value': 'CLP'},
                    {'label': 'Dólares (USD)', 'value': 'USD'}
                ],
                value='CLP',
                style={'fontFamily': 'SuraSans-Regular'}
            )
        ], width=3)
    ], style={'marginTop': '30px', 'marginBottom': '20px', 'textAlign': 'left'}),

    html.H2("Rentabilidad por Año", 
            style={'fontFamily': 'SuraSans-SemiBold', 'marginBottom': '20px'}),

    html.P("Rentabilidades calculadas año calendario completo (enero a diciembre).", 
           style={'fontFamily': 'SuraSans-Regular', 'fontStyle': 'italic', 'marginBottom': '20px'}),

    # TABLA DE ÍNDICES FIJA PARA POR AÑO
    html.H5("Índices Principales:", style={'fontFamily': 'SuraSans-SemiBold', 'marginBottom': '15px'}),
    html.Div(id='tabla-indices-por-ano'),
    
    html.Hr(style={'marginTop': '20px', 'marginBottom': '20px'}),
        # NUEVA SECCIÓN: Botón para agregar fondos personalizados POR AÑO
    dbc.Row([
        dbc.Col([
            dbc.Button([
                html.I(className="fas fa-plus", style={'marginRight': '8px'}),
                "Agregar Fondo Personalizado"
            ], 
            id="btn-agregar-fondo-por-ano", 
            color="dark", 
            style={'fontFamily': 'SuraSans-Regular'})
        ], width=12, style={'textAlign': 'left', 'marginBottom': '20px'})
    ]),

    # NUEVA SECCIÓN: Contenedor para los selectores dinámicos POR AÑO
    html.Div(id='selectores-container-por-ano', children=[]),
    
    # NUEVA SECCIÓN: Store para mantener el estado de las selecciones POR AÑO
    dcc.Store(id='selecciones-store-por-ano', data=[]),
    
    html.Hr(style={'marginTop': '20px', 'marginBottom': '20px'}),
    
    # NUEVA SECCIÓN: Tabla de rentabilidades personalizadas POR AÑO
    html.H5("Tabla de Rentabilidades Personalizadas:", style={'fontFamily': 'SuraSans-SemiBold', 'marginBottom': '15px'}),
    html.Div(id='tabla-rentabilidades-por-ano'),
        # *** NUEVA SECCIÓN: GRÁFICO DE RENTABILIDADES POR AÑO ***
    html.H5("Gráfico de Retornos Acumulados:", style={'fontFamily': 'SuraSans-SemiBold', 'marginTop': '40px', 'marginBottom': '15px'}),
    
    dbc.Row([
        dbc.Col([
            dbc.Button([
                html.I(className="fas fa-expand", style={'marginRight': '8px'}),
                "Ver en Pantalla Completa"
            ], 
            id="btn-pantalla-completa-por-ano", 
            color="dark",                    
            size="sm",
            style={
                'fontFamily': 'SuraSans-Regular',
                'marginBottom': '10px',
                'color': 'white'             
            })
        ], width=12, style={'textAlign': 'right'})
    ]),
    # Store para período activo (independiente)
    dcc.Store(id="periodo-activo-por-ano", data="btn-1y-por-ano"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Desde:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px', 'marginBottom': '5px'}),
                dcc.DatePickerSingle(
                    id='fecha-inicio-grafico-por-ano',
                    date=datetime.now() - timedelta(days=365),
                    display_format='DD/MM/YYYY',
                    style={'width': '100%', 'marginBottom': '10px'}
                ),
                html.Label("Hasta:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px', 'marginBottom': '5px'}),
                dcc.DatePickerSingle(
                    id='fecha-fin-grafico-por-ano',
                    date=datetime.now(),
                    display_format='DD/MM/YYYY',
                    style={'width': '100%', 'marginBottom': '15px'}
                ),
                html.Div([
                    dbc.Button("1M", id="btn-1m-por-ano", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("3M", id="btn-3m-por-ano", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("6M", id="btn-6m-por-ano", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("YTD", id="btn-ytd-por-ano", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '50px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("1Y", id="btn-1y-por-ano", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("3Y", id="btn-3y-por-ano", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("5Y", id="btn-5y-por-ano", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '45px', 'border': '1px solid black', 'color': 'black'}),
                    dbc.Button("Max", id="btn-max-por-ano", size="sm", outline=True, color="light", style={'margin': '2px', 'width': '50px', 'border': '1px solid black', 'color': 'black'}),
                ], style={
                    'borderRadius': '5px',
                    'display': 'flex',
                    'flexWrap': 'wrap'
                })
            ])
        ], width=3),
        
        dbc.Col([
            dcc.Graph(
                id='grafico-retornos-por-ano',
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToAdd': ['toImage'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'retornos_por_ano',
                        'height': 800,
                        'width': 1200,
                        'scale': 2
                    }
                }
            )
        ], width=9)
    ], style={'marginBottom': '20px'})

], id="content-por-año", style={'display': 'none'})

# =============================================================================
# 2. AGREGAR el modal para pantalla completa POR AÑO (en el layout principal):
# =============================================================================

# Modal para gráfico por año en pantalla completa
modal_grafico_por_ano = dbc.Modal([
    dbc.ModalHeader([
        dbc.ModalTitle("Retornos Acumulados - Vista Completa", 
                      style={'fontFamily': 'SuraSans-SemiBold'}),
    ], close_button=True),
    dbc.ModalBody([
        dcc.Graph(
            id='grafico-retornos-por-ano-modal', 
            style={'height': '85vh', 'width': '100%'},
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToAdd': ['toImage'],
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'retornos_por_ano_fullscreen',
                    'height': 1200,
                    'width': 1800,
                    'scale': 2
                }
            }
        )
    ], style={'padding': '5px'}),
], id="modal-grafico-por-ano", is_open=False, size="xl", centered=True, 
   style={'maxWidth': '100', 'maxHeight': '95vh'})

# =============================================================================
# 3. AGREGAR las funciones auxiliares para POR AÑO:
# =============================================================================
    
def crear_selector_fondo_por_ano(id_selector):
    """
    Crea un componente selector de fondo + series con botón de eliminar para POR AÑO
    """
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Fondo:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'fondo-dropdown-por-ano', 'index': id_selector},
                        options=[{'label': fondo, 'value': fondo} for fondo in fondos_unicos],
                        value=None,
                        placeholder="Selecciona un fondo...",
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=5),
                
                dbc.Col([
                    html.Label("Series:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'series-dropdown-por-ano', 'index': id_selector},
                        options=[],
                        value=[],
                        multi=True,
                        placeholder="Primero selecciona un fondo",
                        disabled=True,
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=6),
                
                dbc.Col([
                    html.Br(),
                    dbc.Button(
                        "❌", 
                        id={'type': 'eliminar-selector-por-ano', 'index': id_selector},
                        color="danger", 
                        size="sm",
                        style={'marginTop': '5px'}
                    )
                ], width=1)
            ])
        ])
    ], style={'marginBottom': '10px'})
def crear_selector_fondo_con_valores_por_ano(id_selector, fondo_valor=None, series_valor=None):
    """
    Crea un componente selector de fondo + series con valores pre-establecidos para POR AÑO
    """
    if fondo_valor and fondo_valor in fondos_a_series:
        series_opciones = [{'label': serie, 'value': serie} for serie in fondos_a_series[fondo_valor]]
        series_disabled = False
        series_placeholder = f"Selecciona series para {fondo_valor[:30]}..."
        if series_valor is None:
            series_valor = []
        elif not isinstance(series_valor, list):
            series_valor = [series_valor] if series_valor else []
    else:
        series_opciones = []
        series_disabled = True
        series_placeholder = "Primero selecciona un fondo"
        series_valor = []
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Fondo:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'fondo-dropdown-por-ano', 'index': id_selector},
                        options=[{'label': fondo, 'value': fondo} for fondo in fondos_unicos],
                        value=fondo_valor,
                        placeholder="Selecciona un fondo...",
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=5),
                
                dbc.Col([
                    html.Label("Series:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'series-dropdown-por-ano', 'index': id_selector},
                        options=series_opciones,
                        value=series_valor,
                        multi=True,
                        placeholder=series_placeholder,
                        disabled=series_disabled,
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=6),
                
                dbc.Col([
                    html.Br(),
                    dbc.Button(
                        "❌", 
                        id={'type': 'eliminar-selector-por-ano', 'index': id_selector},
                        color="danger", 
                        size="sm",
                        style={'marginTop': '5px'}
                    )
                ], width=1)
            ])
        ])
    ], style={'marginBottom': '10px'})

    
# Función 1: extraer_id_del_child_por_ano
def extraer_id_del_child_por_ano(child):
    """
    Extrae el ID de un componente hijo para POR AÑO
    """
    try:
        if isinstance(child, dict) and 'props' in child:
            card_body = child['props']['children']
            if isinstance(card_body, dict) and 'props' in card_body:
                row = card_body['props']['children']
                if isinstance(row, dict) and 'props' in row:
                    cols = row['props']['children']
                    if isinstance(cols, list) and len(cols) > 0:
                        first_col = cols[0]
                        if isinstance(first_col, dict) and 'props' in first_col:
                            col_children = first_col['props']['children']
                            if isinstance(col_children, list) and len(col_children) > 1:
                                fondo_dropdown = col_children[1]
                                if isinstance(fondo_dropdown, dict) and 'props' in fondo_dropdown:
                                    dropdown_id = fondo_dropdown['props'].get('id')
                                    if isinstance(dropdown_id, dict) and 'index' in dropdown_id:
                                        return dropdown_id['index']
        
        return buscar_id_recursivo_por_ano(child)
        
    except (KeyError, IndexError, TypeError, AttributeError):
        return None

# Función 2: buscar_id_recursivo_por_ano  
def buscar_id_recursivo_por_ano(componente, profundidad=0):
    """
    Busca recursivamente un ID de tipo 'fondo-dropdown-por-ano'
    """
    if profundidad > 10:
        return None
        
    try:
        if isinstance(componente, dict):
            if 'props' in componente:
                props = componente['props']
                if 'id' in props:
                    component_id = props['id']
                    if isinstance(component_id, dict) and component_id.get('type') == 'fondo-dropdown-por-ano':
                        return component_id.get('index')
                
                if 'children' in props:
                    children = props['children']
                    if isinstance(children, list):
                        for child in children:
                            resultado = buscar_id_recursivo_por_ano(child, profundidad + 1)
                            if resultado:
                                return resultado
                    elif children:
                        resultado = buscar_id_recursivo_por_ano(children, profundidad + 1)
                        if resultado:
                            return resultado
        
        elif isinstance(componente, list):
            for item in componente:
                resultado = buscar_id_recursivo_por_ano(item, profundidad + 1)
                if resultado:
                    return resultado
                    
    except (KeyError, TypeError, AttributeError):
        pass
    
    return None
    

# Stores para manejar estados independientes de las dos secciones
store_indices = dcc.Store(id='indices-tipo-activo', data='acumulada')
store_personalizados = dcc.Store(id='personalizados-tipo-activo', data='acumulada')

# Layout principal modificado
app.layout = html.Div([
    top_navbar,
    modal,
    modal_grafico,
    modal_grafico_anualizada,
    modal_grafico_por_ano,
    store_indices,  # ← YA TIENES ESTA LÍNEA
    store_personalizados,  # ← YA TIENES ESTA LÍNEA
    dcc.Store(id='datos-base-cache', storage_type='session'),    # ← NUEVA
    dcc.Store(id='informe-cache', storage_type='session'),       # ← NUEVA
    dcc.Store(id='anexo-cache', storage_type='session'),         # ← NUEVA
    dcc.Store(id='timestamp-cache', storage_type='session'),     # ← NUEVA
    informe_module.crear_modal_informe(),
    anexo_mensual_module.crear_modal_anexo_mensual(),
    bottom_navbar,
    dbc.Container([
        html.Div([
            controles_acumulada,
            controles_anualizada,
            controles_por_año
        ], style={'padding': '30px'})
    ], fluid=True)
], style={'margin': '0', 'padding': '0'})
# =============================================================================
# CALLBACKS
# =============================================================================



#Sección Anualizada:

@callback(
    Output('selectores-container-anualizada', 'children'),
    [Input('btn-agregar-fondo-anualizada', 'n_clicks'),
     Input({'type': 'eliminar-selector-anualizada', 'index': ALL}, 'n_clicks')],
    [State('selectores-container-anualizada', 'children'),
     State({'type': 'fondo-dropdown-anualizada', 'index': ALL}, 'value'),
     State({'type': 'series-dropdown-anualizada', 'index': ALL}, 'value')],
    prevent_initial_call=True
)
def actualizar_selectores_anualizada(n_clicks_agregar, n_clicks_eliminar, children_actuales, fondos_valores, series_valores):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return children_actuales or []
    
    trigger = ctx.triggered[0]
    
    # Si se presionó agregar fondo
    if trigger['prop_id'] == 'btn-agregar-fondo-anualizada.n_clicks' and n_clicks_agregar:
        children_actuales = children_actuales or []
        nuevo_id = str(uuid.uuid4())
        nuevo_selector = crear_selector_fondo_anualizada(nuevo_id)
        return children_actuales + [nuevo_selector]
    
    # Si se presionó eliminar algún selector
    elif 'eliminar-selector-anualizada' in trigger['prop_id']:
        if not children_actuales:
            return []
            
        # Extraer el ID del selector a eliminar
        import json
        prop_id_dict = json.loads(trigger['prop_id'].replace('.n_clicks', ''))
        id_a_eliminar = prop_id_dict['index']
        
        # Crear mapeo de IDs actuales con sus valores
        valores_por_id = {}
        for i, child in enumerate(children_actuales):
            child_id = extraer_id_del_child_anualizada(child)
            if child_id and i < len(fondos_valores or []) and i < len(series_valores or []):
                valores_por_id[child_id] = {
                    'fondo': fondos_valores[i],
                    'series': series_valores[i] or []
                }
        
        # Filtrar solo los elementos que NO sean el ID a eliminar
        children_preservados = []
        for child in children_actuales:
            child_id = extraer_id_del_child_anualizada(child)
            if child_id and child_id != id_a_eliminar:
                # Preservar este child con sus valores
                if child_id in valores_por_id:
                    child_preservado = crear_selector_fondo_con_valores_anualizada(
                        child_id,
                        valores_por_id[child_id]['fondo'],
                        valores_por_id[child_id]['series']
                    )
                    children_preservados.append(child_preservado)
                else:
                    children_preservados.append(child)
        
        return children_preservados
    
    return children_actuales or []

# Callback para actualizar series según fondo seleccionado - ANUALIZADA
@callback(
    Output({'type': 'series-dropdown-anualizada', 'index': MATCH}, 'options'),
    Output({'type': 'series-dropdown-anualizada', 'index': MATCH}, 'disabled'),
    Output({'type': 'series-dropdown-anualizada', 'index': MATCH}, 'placeholder'),
    Output({'type': 'series-dropdown-anualizada', 'index': MATCH}, 'value'),
    Input({'type': 'fondo-dropdown-anualizada', 'index': MATCH}, 'value'),
    State({'type': 'series-dropdown-anualizada', 'index': MATCH}, 'value'),
    prevent_initial_call=True
)
def actualizar_series_dinamico_anualizada(fondo_seleccionado, valor_series_actual):
    if not fondo_seleccionado or fondo_seleccionado not in fondos_a_series:
        return [], True, "Primero selecciona un fondo", []
    
    series_disponibles = fondos_a_series[fondo_seleccionado]
    opciones_series = [{'label': serie, 'value': serie} for serie in series_disponibles]
    
    if valor_series_actual:
        series_validas = [serie for serie in valor_series_actual if serie in series_disponibles]
        valor_a_mantener = series_validas
    else:
        valor_a_mantener = []
    
    return opciones_series, False, f"Selecciona series para {fondo_seleccionado[:30]}...", valor_a_mantener

# Callback para actualizar el store con las selecciones - ANUALIZADA
@callback(
    Output('selecciones-store-anualizada', 'data'),
    [Input({'type': 'fondo-dropdown-anualizada', 'index': ALL}, 'value'),
     Input({'type': 'series-dropdown-anualizada', 'index': ALL}, 'value')],
    [State('selectores-container-anualizada', 'children')]
)
def actualizar_selecciones_store_anualizada(fondos_valores, series_valores, children):
    if not children or not fondos_valores or not series_valores:
        return []
    
    selecciones = []
    
    for i, child in enumerate(children):
        if i < len(fondos_valores) and i < len(series_valores):
            fondo = fondos_valores[i]
            series = series_valores[i]
            
            if fondo and series:
                selecciones.append({
                    'fondo': fondo,
                    'series': series
                })
    
    return selecciones

# Callback para tabla de rentabilidades personalizadas - ANUALIZADA
@callback(
   Output('tabla-rentabilidades-anualizada', 'children'),
   [Input('moneda-selector-anualizada', 'value'),
    Input('selecciones-store-anualizada', 'data')]
)
def actualizar_tabla_rentabilidades_anualizada(moneda, selecciones_data):
    if not selecciones_data:
        return html.Div([
            html.P("Usa el botón 'Agregar Fondo Personalizado' para añadir fondos a esta tabla", 
                   style={'fontFamily': 'SuraSans-Regular', 'color': '#666', 'textAlign': 'center'}),
            crear_disclaimer_anualizada()
        ])
    
    if pesos_df is None:
        return html.P("No se pudieron cargar los datos", 
                     style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'})
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    
    codigos_seleccionados, nombres_mostrar = procesar_selecciones_multiples(selecciones_data, moneda)
    
    if not codigos_seleccionados:
        return html.Div([
            html.P("No se encontraron datos para las selecciones", 
                   style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'}),
            crear_disclaimer_anualizada()
        ])
    
    tabla_data = calcular_rentabilidades_anualizadas(df_actual, codigos_seleccionados, nombres_mostrar)
    tabla_data['Moneda'] = moneda
    
    columnas_orden = ['Fondo', 'Serie', 'Moneda', '1 Año', '3 Años', '5 Años']
    tabla_data = tabla_data[columnas_orden]
    
    tabla = dash_table.DataTable(
        data=tabla_data.to_dict('records'),
        columns=[{"name": col, "id": col, "type": "numeric", "format": {"specifier": ".2f"}} 
                if col not in ['Fondo', 'Serie', 'Moneda'] else {"name": col, "id": col} 
                for col in tabla_data.columns],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'center',
            'fontFamily': 'SuraSans-Regular',
            'fontSize': '12px'
        },
        style_header={
            'backgroundColor': '#000000',
            'color': 'white',
            'fontFamily': 'SuraSans-SemiBold',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} > 0'},
                'color': 'green'
            } for col in ['1 Año', '3 Años', '5 Años']
        ] + [
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} < 0'},
                'color': 'red'
            } for col in ['1 Año', '3 Años', '5 Años']
        ]
    )
    
    return html.Div([
        tabla,
        crear_disclaimer_anualizada()
    ])
#----------------------------------------------------------------------------------------------------------

@callback(
    Output("info-modal", "is_open"),
    [Input("info-button", "n_clicks"), 
     Input("close-modal", "n_clicks")],
    [State("info-modal", "is_open")]
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open
 

# =============================================================================
# CALLBACKS PARA LAS DOS SECCIONES INDEPENDIENTES
# =============================================================================

# Callback para manejar botones de ÍNDICES (Sección 1)
@callback(
    [Output('indices-tipo-activo', 'data'),
     Output('btn-indices-acumulada', 'color'),
     Output('btn-indices-acumulada', 'outline'),
     Output('btn-indices-anualizada', 'color'),
     Output('btn-indices-anualizada', 'outline'),
     Output('btn-indices-por-ano', 'color'),
     Output('btn-indices-por-ano', 'outline')],
    [Input('btn-indices-acumulada', 'n_clicks'),
     Input('btn-indices-anualizada', 'n_clicks'),
     Input('btn-indices-por-ano', 'n_clicks')],
    prevent_initial_call=True
)
def actualizar_botones_indices(btn_acum, btn_anual, btn_ano):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return 'acumulada', 'dark', False, 'light', True, 'light', True
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'btn-indices-acumulada':
        return 'acumulada', 'dark', False, 'secondary', True, 'secondary', True
    elif button_id == 'btn-indices-anualizada':
        return 'anualizada', 'secondary', True, 'dark', False, 'secondary', True
    elif button_id == 'btn-indices-por-ano':
        return 'por_ano', 'secondary', True, 'secondary', True, 'dark', False

    return 'acumulada', 'dark', False, 'secondary', True, 'secondary', True

# Callback para manejar botones de PERSONALIZADOS (Sección 2)
@callback(
    [Output('personalizados-tipo-activo', 'data'),
     Output('btn-personalizados-acumulada', 'color'),
     Output('btn-personalizados-acumulada', 'outline'),
     Output('btn-personalizados-anualizada', 'color'),
     Output('btn-personalizados-anualizada', 'outline'),
     Output('btn-personalizados-por-ano', 'color'),
     Output('btn-personalizados-por-ano', 'outline')],
    [Input('btn-personalizados-acumulada', 'n_clicks'),
     Input('btn-personalizados-anualizada', 'n_clicks'),
     Input('btn-personalizados-por-ano', 'n_clicks')],
    prevent_initial_call=True
)
def actualizar_botones_personalizados(btn_acum, btn_anual, btn_ano):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return 'acumulada', 'dark', False, 'light', True, 'light', True
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'btn-personalizados-acumulada':
        return 'acumulada', 'dark', False, 'secondary', True, 'secondary', True
    elif button_id == 'btn-personalizados-anualizada':
        return 'anualizada', 'secondary', True, 'dark', False, 'secondary', True
    elif button_id == 'btn-personalizados-por-ano':
        return 'por_ano', 'secondary', True, 'secondary', True, 'dark', False

    return 'acumulada', 'dark', False, 'secondary', True, 'secondary', True

# Callback para tabla de ÍNDICES (independiente)
@callback(
    Output('tabla-indices-dinamica', 'children'),
    [Input('moneda-selector-acumulada', 'value'),
     Input('indices-tipo-activo', 'data')]
)
def actualizar_tabla_indices_dinamica(moneda, tipo_activo):
    if pesos_df is None:
        return html.P("No se pudieron cargar los datos", 
                     style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'})
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    codigos_indices, nombres_indices = obtener_codigos_indices(moneda)
    
    if not codigos_indices:
        return html.P("No se encontraron los fondos índice", 
                     style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'})
    
    # Seleccionar función de cálculo según el tipo
    if tipo_activo == 'acumulada':
        tabla_data = calcular_rentabilidades(df_actual, codigos_indices, nombres_indices)
        tabla_data['Moneda'] = moneda
        columnas_orden = ['Fondo', 'Serie', 'Moneda', 'TAC', '1 Mes', '3 Meses', '12 Meses', 'YTD', '3 Años', '5 Años']
        tabla_data = tabla_data[columnas_orden]
        disclaimer = crear_disclaimer_acumulada()
        
    elif tipo_activo == 'anualizada':
        tabla_data = calcular_rentabilidades_anualizadas(df_actual, codigos_indices, nombres_indices)
        tabla_data['Moneda'] = moneda
        columnas_orden = ['Fondo', 'Serie', 'Moneda', '1 Año', '3 Años', '5 Años']
        tabla_data = tabla_data[columnas_orden]
        disclaimer = crear_disclaimer_anualizada()
        
    elif tipo_activo == 'por_ano':
        tabla_data = calcular_rentabilidades_por_año(df_actual, codigos_indices, nombres_indices)
        tabla_data['Moneda'] = moneda
        columnas_base = ['Fondo', 'Serie', 'Moneda']
        años_columnas = [col for col in tabla_data.columns if col not in columnas_base]
        años_columnas.sort(reverse=True)
        columnas_orden = columnas_base + años_columnas
        tabla_data = tabla_data[columnas_orden]
        disclaimer = crear_disclaimer_por_año()
    
    # Crear la tabla
    tabla = dash_table.DataTable(
        data=tabla_data.to_dict('records'),
        columns=[{"name": col, "id": col, "type": "numeric", "format": {"specifier": ".2f"}} 
                if col not in ['Fondo', 'Serie', 'Moneda'] else {"name": col, "id": col} 
                for col in tabla_data.columns],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'center',
            'fontFamily': 'SuraSans-Regular',
            'fontSize': '12px' if tipo_activo != 'por_ano' else '11px'
        },
        style_header={
            'backgroundColor': '#24272A',
            'color': 'white',
            'fontFamily': 'SuraSans-SemiBold',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} > 0'},
                'color': 'green'
            } for col in tabla_data.columns if col not in ['Fondo', 'Serie', 'Moneda']
        ] + [
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} < 0'},
                'color': 'red'
            } for col in tabla_data.columns if col not in ['Fondo', 'Serie', 'Moneda']
        ]
    )
    
    return html.Div([tabla, disclaimer])

# Callback para tabla de PERSONALIZADOS (independiente)
@callback(
    Output('tabla-personalizados-dinamica', 'children'),
    [Input('moneda-selector-acumulada', 'value'),
     Input('personalizados-tipo-activo', 'data'),
     Input('selecciones-store', 'data')]
)
def actualizar_tabla_personalizados_dinamica(moneda, tipo_activo, selecciones_data):
    if not selecciones_data:
        # Crear disclaimer según el tipo activo
        if tipo_activo == 'acumulada':
            disclaimer = crear_disclaimer_acumulada()
        elif tipo_activo == 'anualizada':
            disclaimer = crear_disclaimer_anualizada()
        else:
            disclaimer = crear_disclaimer_por_año()
            
        return html.Div([
            html.P("Usa el botón 'Agregar Fondo Personalizado' para añadir fondos a esta tabla", 
                   style={'fontFamily': 'SuraSans-Regular', 'color': '#666', 'textAlign': 'center'}),
            disclaimer
        ])
    
    if pesos_df is None:
        return html.P("No se pudieron cargar los datos", 
                     style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'})
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    codigos_seleccionados, nombres_mostrar = procesar_selecciones_multiples(selecciones_data, moneda)
    
    if not codigos_seleccionados:
        # Crear disclaimer según el tipo activo
        if tipo_activo == 'acumulada':
            disclaimer = crear_disclaimer_acumulada()
        elif tipo_activo == 'anualizada':
            disclaimer = crear_disclaimer_anualizada()
        else:
            disclaimer = crear_disclaimer_por_año()
            
        return html.Div([
            html.P("No se encontraron datos para las selecciones", 
                   style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'}),
            disclaimer
        ])
    
    # Seleccionar función de cálculo según el tipo
    if tipo_activo == 'acumulada':
        tabla_data = calcular_rentabilidades(df_actual, codigos_seleccionados, nombres_mostrar)
        tabla_data['Moneda'] = moneda
        columnas_orden = ['Fondo', 'Serie', 'Moneda', 'TAC', '1 Mes', '3 Meses', '12 Meses', 'YTD', '3 Años', '5 Años']
        tabla_data = tabla_data[columnas_orden]
        disclaimer = crear_disclaimer_acumulada()
        
    elif tipo_activo == 'anualizada':
        tabla_data = calcular_rentabilidades_anualizadas(df_actual, codigos_seleccionados, nombres_mostrar)
        tabla_data['Moneda'] = moneda
        columnas_orden = ['Fondo', 'Serie', 'Moneda', '1 Año', '3 Años', '5 Años']
        tabla_data = tabla_data[columnas_orden]
        disclaimer = crear_disclaimer_anualizada()
        
    elif tipo_activo == 'por_ano':
        tabla_data = calcular_rentabilidades_por_año(df_actual, codigos_seleccionados, nombres_mostrar)
        tabla_data['Moneda'] = moneda
        columnas_base = ['Fondo', 'Serie', 'Moneda']
        años_columnas = [col for col in tabla_data.columns if col not in columnas_base]
        años_columnas.sort(reverse=True)
        columnas_orden = columnas_base + años_columnas
        tabla_data = tabla_data[columnas_orden]
        disclaimer = crear_disclaimer_por_año()
    
    # Crear la tabla
    tabla = dash_table.DataTable(
        data=tabla_data.to_dict('records'),
        columns=[{"name": col, "id": col, "type": "numeric", "format": {"specifier": ".2f"}} 
                if col not in ['Fondo', 'Serie', 'Moneda'] else {"name": col, "id": col} 
                for col in tabla_data.columns],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'center',
            'fontFamily': 'SuraSans-Regular',
            'fontSize': '12px' if tipo_activo != 'por_ano' else '11px'
        },
        style_header={
            'backgroundColor': '#000000',
            'color': 'white',
            'fontFamily': 'SuraSans-SemiBold',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} > 0'},
                'color': 'green'
            } for col in tabla_data.columns if col not in ['Fondo', 'Serie', 'Moneda']
        ] + [
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} < 0'},
                'color': 'red'
            } for col in tabla_data.columns if col not in ['Fondo', 'Serie', 'Moneda']
        ]
    )
    
    return html.Div([tabla, disclaimer])

# Callback para agregar nuevo selector de fondo
# Callback para agregar nuevo selector de fondo - CORREGIDO
@callback(
    Output('selectores-container', 'children'),
    [Input('btn-agregar-fondo', 'n_clicks'),
     Input({'type': 'eliminar-selector', 'index': ALL}, 'n_clicks')],
    [State('selectores-container', 'children'),
     State({'type': 'fondo-dropdown', 'index': ALL}, 'value'),
     State({'type': 'series-dropdown', 'index': ALL}, 'value')],
    prevent_initial_call=True
)
def actualizar_selectores_corregido(n_clicks_agregar, n_clicks_eliminar, children_actuales, fondos_valores, series_valores):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return children_actuales or []
    
    trigger = ctx.triggered[0]
    
    # Si se presionó agregar fondo
    if trigger['prop_id'] == 'btn-agregar-fondo.n_clicks' and n_clicks_agregar:
        children_actuales = children_actuales or []
        nuevo_id = str(uuid.uuid4())
        nuevo_selector = crear_selector_fondo(nuevo_id)
        return children_actuales + [nuevo_selector]
    
    # Si se presionó eliminar algún selector
    elif 'eliminar-selector' in trigger['prop_id']:
        if not children_actuales:
            return []
            
        # Extraer el ID del selector a eliminar
        import json
        prop_id_dict = json.loads(trigger['prop_id'].replace('.n_clicks', ''))
        id_a_eliminar = prop_id_dict['index']
        
        # Crear mapeo de IDs actuales con sus valores
        valores_por_id = {}
        for i, child in enumerate(children_actuales):
            child_id = extraer_id_del_child_mejorado(child)
            if child_id and i < len(fondos_valores or []) and i < len(series_valores or []):
                valores_por_id[child_id] = {
                    'fondo': fondos_valores[i],
                    'series': series_valores[i] or []
                }
        
        # Filtrar solo los elementos que NO sean el ID a eliminar
        children_preservados = []
        for child in children_actuales:
            child_id = extraer_id_del_child_mejorado(child)
            if child_id and child_id != id_a_eliminar:
                # Preservar este child con sus valores
                if child_id in valores_por_id:
                    child_preservado = crear_selector_fondo_con_valores(
                        child_id,
                        valores_por_id[child_id]['fondo'],
                        valores_por_id[child_id]['series']
                    )
                    children_preservados.append(child_preservado)
                else:
                    children_preservados.append(child)
        
        return children_preservados
    
    return children_actuales or []

# Función auxiliar para crear selector con valores pre-establecidos - MEJORADA
def crear_selector_fondo_con_valores(id_selector, fondo_valor=None, series_valor=None):
    """
    Crea un componente selector de fondo + series con valores pre-establecidos
    """
    # Opciones de series basadas en el fondo seleccionado
    if fondo_valor and fondo_valor in fondos_a_series:
        series_opciones = [{'label': serie, 'value': serie} for serie in fondos_a_series[fondo_valor]]
        series_disabled = False
        series_placeholder = f"Selecciona series para {fondo_valor[:30]}..."
        # Asegurar que series_valor sea una lista
        if series_valor is None:
            series_valor = []
        elif not isinstance(series_valor, list):
            series_valor = [series_valor] if series_valor else []
    else:
        series_opciones = []
        series_disabled = True
        series_placeholder = "Primero selecciona un fondo"
        series_valor = []
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Fondo:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'fondo-dropdown', 'index': id_selector},
                        options=[{'label': fondo, 'value': fondo} for fondo in fondos_unicos],
                        value=fondo_valor,  # Valor pre-establecido
                        placeholder="Selecciona un fondo...",
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=5),
                
                dbc.Col([
                    html.Label("Series:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'series-dropdown', 'index': id_selector},
                        options=series_opciones,  # Opciones pre-establecidas
                        value=series_valor,  # Valor pre-establecido
                        multi=True,
                        placeholder=series_placeholder,
                        disabled=series_disabled,
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=6),
                
                dbc.Col([
                    html.Br(),
                    dbc.Button(
                        "❌", 
                        id={'type': 'eliminar-selector', 'index': id_selector},
                        color="danger", 
                        size="sm",
                        style={'marginTop': '5px'}
                    )
                ], width=1)
            ])
        ])
    ], style={'marginBottom': '10px'})

#Funcion Auxiliar
def extraer_id_del_child_mejorado(child):
    """
    Extrae el ID de un componente hijo de manera más robusta
    """
    try:
        # El child es un dbc.Card
        if isinstance(child, dict) and 'props' in child:
            # Navegar: Card -> CardBody -> Row -> Col[0] -> [dropdown de fondo]
            card_body = child['props']['children']
            if isinstance(card_body, dict) and 'props' in card_body:
                row = card_body['props']['children']
                if isinstance(row, dict) and 'props' in row:
                    cols = row['props']['children']
                    if isinstance(cols, list) and len(cols) > 0:
                        first_col = cols[0]  # Primera columna (Fondo)
                        if isinstance(first_col, dict) and 'props' in first_col:
                            col_children = first_col['props']['children']
                            if isinstance(col_children, list) and len(col_children) > 1:
                                fondo_dropdown = col_children[1]  # El dropdown de fondo
                                if isinstance(fondo_dropdown, dict) and 'props' in fondo_dropdown:
                                    dropdown_id = fondo_dropdown['props'].get('id')
                                    if isinstance(dropdown_id, dict) and 'index' in dropdown_id:
                                        return dropdown_id['index']
        
        # Método alternativo: buscar recursivamente
        return buscar_id_recursivo(child)
        
    except (KeyError, IndexError, TypeError, AttributeError):
        return None
def buscar_id_recursivo(componente, profundidad=0):
    """
    Busca recursivamente un ID de tipo 'fondo-dropdown' en la estructura del componente
    """
    if profundidad > 10:  # Evitar recursión infinita
        return None
        
    try:
        if isinstance(componente, dict):
            # Verificar si este componente tiene el ID que buscamos
            if 'props' in componente:
                props = componente['props']
                if 'id' in props:
                    component_id = props['id']
                    if isinstance(component_id, dict) and component_id.get('type') == 'fondo-dropdown':
                        return component_id.get('index')
                
                # Buscar en children
                if 'children' in props:
                    children = props['children']
                    if isinstance(children, list):
                        for child in children:
                            resultado = buscar_id_recursivo(child, profundidad + 1)
                            if resultado:
                                return resultado
                    elif children:
                        resultado = buscar_id_recursivo(children, profundidad + 1)
                        if resultado:
                            return resultado
        
        elif isinstance(componente, list):
            for item in componente:
                resultado = buscar_id_recursivo(item, profundidad + 1)
                if resultado:
                    return resultado
                    
    except (KeyError, TypeError, AttributeError):
        pass
    
    return None

#Gráfico:
def crear_grafico_retornos_anualizados(df_retornos, codigos_seleccionados, nombres_mostrar):
    """
    Crea gráfico de líneas para retornos - MISMA LÓGICA que crear_grafico_retornos
    Solo cambia el título del gráfico
    """
    if df_retornos.empty:
        return go.Figure().add_annotation(
            text="No hay datos para el período seleccionado",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Validación de datos de entrada
    if not codigos_seleccionados or not nombres_mostrar:
        fig_vacio = go.Figure()
        fig_vacio.add_annotation(
            text="Usa el botón 'Agregar Fondo Personalizado' para ver fondos en el gráfico",
            x=0.5, 
            y=0.5, 
            showarrow=False,
            font={'family': 'SuraSans-Regular', 'size': 16, 'color': '#666666'},
            xanchor='center',  
            yanchor='middle',
            xref='paper',
            yref='paper',
        )
        fig_vacio.update_layout(
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='#f8f9fa',
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            margin=dict(t=20, b=20, l=20, r=20),
            height=500
        )
        return fig_vacio
    
    try:
        # Función auxiliar para formatear fechas en español
        def formatear_fecha_espanol(fecha):
            try:
                dias_es = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
                meses_es = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                           'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
                
                dia_semana = dias_es[fecha.weekday()]
                dia = fecha.day
                mes = meses_es[fecha.month - 1]
                año = fecha.year
                
                return f"{dia_semana} {dia} de {mes} {año}"
            except:
                return str(fecha)
        
        fig = go.Figure()
        
        paleta_primaria = ['#24272A', '#0B2DCE', '#5A646E', '#98A4AE', '#FFE946']
        paleta_secundaria = [
            '#727272', '#52C599', '#CC9967', '#9B5634', '#D4BE7F', 
            '#3C86B4', '#A0A0A0', '#7FD4B3', '#D5AB80', '#C9805C', 
            '#9E3541', '#A8CDE2', '#C8C8C8', '#A3E1C2', '#E0C1A2', 
            '#D49A7D', '#DE9CA6', '#CBB363'
        ]
        
        num_fondos = len(codigos_seleccionados)
        colores_a_usar = paleta_primaria if num_fondos <= 5 else paleta_secundaria
        
        # Preparar datos con validación
        try:
            fechas_formateadas = [formatear_fecha_espanol(fecha.date()) for fecha in df_retornos['Dates']]
        except:
            fechas_formateadas = [str(fecha) for fecha in df_retornos['Dates']]
        
        # Crear hover texts personalizados con manejo de errores
        hover_texts_por_traza = []
        
        for i, (codigo, nombre_mostrar) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
            hover_texts = []
            
            if codigo not in df_retornos.columns:
                hover_texts_por_traza.append([])
                continue
            
            for j in range(len(df_retornos)):
                try:
                    # Para cada punto, obtener todos los valores de fondos en esa fecha
                    valores_fecha = []
                    
                    for k, otro_codigo in enumerate(codigos_seleccionados):
                        if otro_codigo in df_retornos.columns and j < len(df_retornos[otro_codigo]):
                            try:
                                valor_otro = df_retornos[otro_codigo].iloc[j]
                                if pd.notna(valor_otro):
                                    # Preparar nombre más corto
                                    nombre_otro = nombres_mostrar[k].replace("FONDO MUTUO SURA ", "").replace("SURA ", "")
                                    if " - " in nombre_otro:
                                        partes = nombre_otro.split(" - ")
                                        nombre_final = f"{partes[0]} ({partes[1]})" if len(partes) > 1 else nombre_otro
                                    else:
                                        nombre_final = nombre_otro
                                    
                                    # Obtener color para este fondo
                                    color_fondo = colores_a_usar[k % len(colores_a_usar)]
                                    
                                    valores_fecha.append((nombre_final, float(valor_otro), color_fondo))
                            except (IndexError, TypeError, ValueError):
                                continue
                    
                    # ORDENAR POR VALOR DESCENDENTE (mayor rendimiento primero)
                    valores_fecha.sort(key=lambda x: x[1], reverse=True)
                    
                    # Crear texto del hover con fecha y todos los fondos ordenados
                    try:
                        fecha_str = fechas_formateadas[j] if j < len(fechas_formateadas) else str(df_retornos['Dates'].iloc[j])
                    except:
                        fecha_str = f"Fecha {j}"
                    
                    hover_text = f"<b>{fecha_str}</b><br><br>"
                    for nombre_fondo, valor_fondo, color_fondo in valores_fecha:
                        # Crear indicador de color con círculo colorado
                        hover_text += f"<span style='color:{color_fondo}'>●</span> <b>{nombre_fondo}:</b> {valor_fondo:.2f}%<br>"
                    
                    hover_texts.append(hover_text)
                    
                except Exception as e:
                    # En caso de error, crear un hover básico
                    hover_texts.append(f"<b>Error en datos</b><br>Punto {j}")
            
            hover_texts_por_traza.append(hover_texts)
        
        # Crear las trazas con validación
        for i, (codigo, nombre_mostrar) in enumerate(zip(codigos_seleccionados, nombres_mostrar)):
            if codigo not in df_retornos.columns:
                continue
                
            try:
                color_linea = colores_a_usar[i % len(colores_a_usar)]
                
                # Preparar nombre más corto para la leyenda
                nombre_corto = nombre_mostrar.replace("FONDO MUTUO SURA ", "").replace("SURA ", "")
                if " - " in nombre_corto:
                    partes = nombre_corto.split(" - ")
                    nombre_final = f"{partes[0]} ({partes[1]})" if len(partes) > 1 else nombre_corto
                else:
                    nombre_final = nombre_corto
                
                # Asegurar que tenemos hover texts para esta traza
                hover_texts_traza = hover_texts_por_traza[i] if i < len(hover_texts_por_traza) else []
                
                # Si no hay suficientes hover texts, rellenar con textos básicos
                while len(hover_texts_traza) < len(df_retornos):
                    hover_texts_traza.append(f"<b>{nombre_final}</b><br>Datos no disponibles")
                
                fig.add_trace(go.Scatter(
                    x=df_retornos['Dates'],
                    y=df_retornos[codigo],
                    mode='lines',
                    name=nombre_final,
                    line=dict(color=color_linea, width=2),
                    hovertemplate='%{text}<extra></extra>',
                    text=hover_texts_traza,
                    showlegend=True
                ))
                
            except Exception as e:
                # Si hay error en esta traza, continuar con la siguiente
                print(f"Error creando traza para {codigo}: {e}")
                continue
        
    # Configurar layout - SOLO CAMBIAR EL TÍTULO
        fig.update_layout(
            title={
                'text': 'Retornos Acumulados',  # ← MISMO TÍTULO que el otro gráfico
                'x': 0.5,
                'y': 0.95,
                'font': {'family': 'SuraSans-SemiBold', 'size': 18, 'color': '#24272A'}
            },
            xaxis_title='Fecha',
            yaxis_title='Retorno Acumulado (%)',  # ← MISMO TÍTULO DEL EJE Y
            font={'family': 'SuraSans-Regular', 'color': '#24272A'},
            
            hovermode='closest',
            
            hoverlabel=dict(
                bgcolor="rgba(255, 255, 255, 0.98)",
                bordercolor="rgba(0, 0, 0, 0.15)",
                font=dict(
                    family='SuraSans-Regular',
                    size=12,
                    color="#25405C"
                ),
                align="left",
                namelength=-1),

            xaxis=dict(
                showgrid=False,
                showspikes=True,
                spikecolor="rgba(36, 39, 42, 0.3)",
                spikesnap="cursor",
                spikemode="across",
                spikethickness=1,
                spikedash="dot",
                tickformat='%d/%m/%Y'
            ),
            yaxis=dict(
                tickformat='.1f',
                ticksuffix='%',
                showgrid=True,
                gridcolor='rgba(128,128,128,0.2)',
            ),

            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="center",
                x=0.5,
                font={'family': 'SuraSans-Regular', 'size': 10}
            ),
            height=500,
            margin=dict(t=60, b=50, l=50, r=50),
            template='plotly_white',
            plot_bgcolor='white',
            paper_bgcolor='white',
            
            # AGREGAR LOGO EN LA ESQUINA INFERIOR DERECHA
            images=[
                dict(
                    source="/assets/investments_logo.png",
                    xref="paper", 
                    yref="paper",
                    x=0.99,
                    y=-0.27,
                    sizex=0.28,
                    sizey=0.22,
                    xanchor="right",
                    yanchor="bottom",
                    opacity=1,
                    layer="above"
                )
            ]
        )
        
        return fig
        
    except Exception as e:
        # Si hay cualquier error, devolver un gráfico con mensaje de error
        print(f"Error en crear_grafico_retornos_anualizados: {e}")
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"Error al crear el gráfico: {str(e)}",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red")
        )
        error_fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=500
        )
        return error_fig

#Call Back gráfico Anualizado. 

# Callback para inicializar fechas por defecto - ANUALIZADA
@callback(
    [Output('fecha-inicio-grafico-anualizada', 'date'),
     Output('fecha-fin-grafico-anualizada', 'date')],
    [Input('tabs-anualizada', 'active_tab')]
)
def inicializar_fechas_grafico_anualizada(active_tab):
    if pesos_df is not None:
        fecha_fin = pesos_df['Dates'].max()
        fecha_inicio = fecha_fin - timedelta(days=365)
        return fecha_inicio, fecha_fin
    else:
        fecha_fin = datetime.now()
        fecha_inicio = fecha_fin - timedelta(days=365)
        return fecha_inicio, fecha_fin

# Callback para botones de período - ANUALIZADA
@callback(
    [Output('fecha-inicio-grafico-anualizada', 'date', allow_duplicate=True),
     Output('fecha-fin-grafico-anualizada', 'date', allow_duplicate=True),
     Output('fecha-inicio-grafico-anualizada', 'min_date_allowed'),
     Output('btn-1m-anualizada', 'disabled'),
     Output('btn-3m-anualizada', 'disabled'),
     Output('btn-6m-anualizada', 'disabled'),
     Output('btn-ytd-anualizada', 'disabled'),
     Output('btn-1y-anualizada', 'disabled'),
     Output('btn-3y-anualizada', 'disabled'),
     Output('btn-5y-anualizada', 'disabled'),
     Output('btn-max-anualizada', 'disabled')],
    [Input('btn-1m-anualizada', 'n_clicks'),
     Input('btn-3m-anualizada', 'n_clicks'),
     Input('btn-6m-anualizada', 'n_clicks'),
     Input('btn-ytd-anualizada', 'n_clicks'),
     Input('btn-1y-anualizada', 'n_clicks'),
     Input('btn-3y-anualizada', 'n_clicks'),
     Input('btn-5y-anualizada', 'n_clicks'),
     Input('btn-max-anualizada', 'n_clicks'),
     Input('selecciones-store-anualizada', 'data'),
     Input('moneda-selector-anualizada', 'value')],
    prevent_initial_call=True
)
def actualizar_fechas_grafico_anualizada(btn1m, btn3m, btn6m, btnytd, btn1y, btn3y, btn5y, btnmax, selecciones_data, moneda):
    ctx = dash.callback_context
    
    if pesos_df is None:
        return dash.no_update, dash.no_update, None, False, False, False, False, False, False, False, False
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    fecha_fin = df_actual['Dates'].max()
    
    # Obtener códigos seleccionados
    codigos_seleccionados = []
    if selecciones_data:
        codigos_seleccionados, _ = procesar_selecciones_multiples(selecciones_data)
    
    # Obtener fecha límite (fondo más nuevo)
    fecha_limite_inicio = obtener_fecha_inicio_mas_reciente(df_actual, codigos_seleccionados)
    
    # Calcular años disponibles para deshabilitar botones
    anos_disponibles = 0
    if fecha_limite_inicio:
        anos_disponibles = calcular_anos_disponibles(fecha_limite_inicio, fecha_fin)
    
    # Determinar qué botones deshabilitar
    btn_1m_disabled = False
    btn_3m_disabled = False
    btn_6m_disabled = False
    btn_ytd_disabled = False
    btn_1y_disabled = anos_disponibles < 1
    btn_3y_disabled = anos_disponibles < 3
    btn_5y_disabled = anos_disponibles < 5
    btn_max_disabled = not fecha_limite_inicio
    
    # Si se presionó un botón, calcular nueva fecha de inicio
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id in ['btn-1m-anualizada', 'btn-3m-anualizada', 'btn-6m-anualizada', 'btn-ytd-anualizada', 'btn-1y-anualizada', 'btn-3y-anualizada', 'btn-5y-anualizada', 'btn-max-anualizada']:
            periodo = button_id.replace('btn-', '').replace('-anualizada', '')
            fecha_inicio = ajustar_fecha_segun_periodo_y_limite(fecha_fin, periodo, fecha_limite_inicio)
            
            return (fecha_inicio, fecha_fin, fecha_limite_inicio,
                   btn_1m_disabled, btn_3m_disabled, btn_6m_disabled, btn_ytd_disabled,
                   btn_1y_disabled, btn_3y_disabled, btn_5y_disabled, btn_max_disabled)
    
    # Si solo cambiaron las selecciones, ajustar fecha de inicio a los datos disponibles
    if fecha_limite_inicio:
        fecha_inicio_actual = max(fecha_limite_inicio, fecha_fin - timedelta(days=365))
    else:
        fecha_inicio_actual = fecha_fin - timedelta(days=365)
    
    return (fecha_inicio_actual, fecha_fin, fecha_limite_inicio,
           btn_1m_disabled, btn_3m_disabled, btn_6m_disabled, btn_ytd_disabled,
           btn_1y_disabled, btn_3y_disabled, btn_5y_disabled, btn_max_disabled)

# Callback para validar fechas manuales - ANUALIZADA
@callback(
    [Output('fecha-inicio-grafico-anualizada', 'date', allow_duplicate=True),
     Output('fecha-fin-grafico-anualizada', 'date', allow_duplicate=True)],
    [Input('fecha-inicio-grafico-anualizada', 'date'),
     Input('fecha-fin-grafico-anualizada', 'date')],
    [State('selecciones-store-anualizada', 'data'),
     State('moneda-selector-anualizada', 'value')],
    prevent_initial_call=True
)
def validar_fechas_manuales_anualizada(fecha_inicio_input, fecha_fin_input, selecciones_data, moneda):
    """
    Valida que las fechas manuales no excedan los límites del fondo más nuevo
    """
    if pesos_df is None or not fecha_inicio_input or not fecha_fin_input:
        return dash.no_update, dash.no_update
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    
    # Obtener códigos seleccionados
    codigos_seleccionados = []
    if selecciones_data:
        codigos_seleccionados, _ = procesar_selecciones_multiples(selecciones_data)
    
    # Obtener fecha límite
    fecha_limite_inicio = obtener_fecha_inicio_mas_reciente(df_actual, codigos_seleccionados)
    
    fecha_inicio_dt = pd.to_datetime(fecha_inicio_input)
    fecha_fin_dt = pd.to_datetime(fecha_fin_input)
    
    # Ajustar fecha de inicio si está antes del límite
    if fecha_limite_inicio and fecha_inicio_dt < fecha_limite_inicio:
        fecha_inicio_ajustada = fecha_limite_inicio
        return fecha_inicio_ajustada, fecha_fin_dt
    
    return dash.no_update, dash.no_update

# Callback para actualizar gráfico - ANUALIZADA
@callback(
    Output('grafico-retornos-anualizados', 'figure'),
    [Input('moneda-selector-anualizada', 'value'),
     Input('selecciones-store-anualizada', 'data'),
     Input('fecha-inicio-grafico-anualizada', 'date'),
     Input('fecha-fin-grafico-anualizada', 'date')]
)
def actualizar_grafico_retornos_anualizados(moneda, selecciones_data, fecha_inicio, fecha_fin):
    if pesos_df is None:
        fig_vacio = go.Figure()
        fig_vacio.add_annotation(
            text="No se pudieron cargar los datos",
            x=0.5, y=0.5, showarrow=False
        )
        return fig_vacio
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    
    if not selecciones_data:
        fig_vacio = go.Figure()
        fig_vacio.add_annotation(
            text="Usa el botón 'Agregar Fondo Personalizado' para ver fondos en el gráfico",
            x=0.5, 
            y=0.5, 
            showarrow=False,
            font={'family': 'SuraSans-Regular', 'size': 16, 'color': '#666666'},
            xanchor='center',  
            yanchor='middle',
            xref='paper',
            yref='paper',
        )
        fig_vacio.update_layout(
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='#f8f9fa',
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            margin=dict(t=20, b=20, l=20, r=20),
            height=500
        )
        return fig_vacio
    
    codigos_personalizados, nombres_personalizados = procesar_selecciones_multiples(selecciones_data)
    
    if not codigos_personalizados:
        fig_vacio = go.Figure()
        fig_vacio.add_annotation(
            text="No se encontraron datos para las selecciones personalizadas",
            x=0.5, 
            y=0.5, 
            showarrow=False,
            font={'family': 'SuraSans-Regular', 'size': 16, 'color': '#666666'},
            xanchor='center',  
            yanchor='middle',
            xref='paper',
            yref='paper',
        )
        fig_vacio.update_layout(
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='#f8f9fa',
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            margin=dict(t=20, b=20, l=20, r=20),
            height=500
        )
        return fig_vacio
    
    # USAR LA MISMA FUNCIÓN QUE RENTABILIDAD ACUMULADA
    df_retornos = calcular_retornos_acumulados_con_limite(
        df_actual, codigos_personalizados, 
        fecha_inicio, fecha_fin
    )
    
    return crear_grafico_retornos_anualizados(df_retornos, codigos_personalizados, nombres_personalizados)




# Callbacks para periodo activo y estilos de botones - ANUALIZADA
@callback(
    Output("periodo-activo-anualizada", "data"),
    Input("btn-1m-anualizada", "n_clicks"),
    Input("btn-3m-anualizada", "n_clicks"),
    Input("btn-6m-anualizada", "n_clicks"),
    Input("btn-ytd-anualizada", "n_clicks"),
    Input("btn-1y-anualizada", "n_clicks"),
    Input("btn-3y-anualizada", "n_clicks"),
    Input("btn-5y-anualizada", "n_clicks"),
    Input("btn-max-anualizada", "n_clicks"),
    prevent_initial_call=True
)
def actualizar_periodo_anualizada(*_):
    from dash import ctx
    return ctx.triggered_id

@callback(
    [
        Output("btn-1m-anualizada", "style"),
        Output("btn-3m-anualizada", "style"),
        Output("btn-6m-anualizada", "style"),
        Output("btn-ytd-anualizada", "style"),
        Output("btn-1y-anualizada", "style"),
        Output("btn-3y-anualizada", "style"),
        Output("btn-5y-anualizada", "style"),
        Output("btn-max-anualizada", "style"),
    ],
    [Input("periodo-activo-anualizada", "data"),
     Input('btn-1m-anualizada', 'disabled'),
     Input('btn-3m-anualizada', 'disabled'),
     Input('btn-6m-anualizada', 'disabled'),
     Input('btn-ytd-anualizada', 'disabled'),
     Input('btn-1y-anualizada', 'disabled'),
     Input('btn-3y-anualizada', 'disabled'),
     Input('btn-5y-anualizada', 'disabled'),
     Input('btn-max-anualizada', 'disabled')]
)
def resaltar_boton_activo_anualizada(periodo_activo, disabled_1m, disabled_3m, disabled_6m, 
                                   disabled_ytd, disabled_1y, disabled_3y, disabled_5y, disabled_max):
    def estilo(activo, deshabilitado, ancho="45px"):
        if deshabilitado:
            # Estilo para botones deshabilitados
            return {
                'margin': '2px', 'width': ancho,
                'backgroundColor': '#f8f9fa', 'color': '#6c757d',
                'border': '1px solid #dee2e6',
                'cursor': 'not-allowed',
                'opacity': 0.5
            }
        elif activo:
            # Estilo para botón activo
            return {
                'margin': '2px', 'width': ancho,
                'backgroundColor': 'black', 'color': 'white',
                'border': '1px solid black'
            }
        else:
            # Estilo para botones normales
            return {
                'margin': '2px', 'width': ancho,
                'backgroundColor': 'white', 'color': 'black',
                'border': '1px solid black'
            }

    return [
        estilo(periodo_activo == "btn-1m-anualizada", disabled_1m),
        estilo(periodo_activo == "btn-3m-anualizada", disabled_3m),
        estilo(periodo_activo == "btn-6m-anualizada", disabled_6m),
        estilo(periodo_activo == "btn-ytd-anualizada", disabled_ytd, ancho="50px"),
        estilo(periodo_activo == "btn-1y-anualizada", disabled_1y),
        estilo(periodo_activo == "btn-3y-anualizada", disabled_3y),
        estilo(periodo_activo == "btn-5y-anualizada", disabled_5y),
        estilo(periodo_activo == "btn-max-anualizada", disabled_max, ancho="50px"),
    ]


# =============================================================================
# 6. CALLBACKS PARA MODAL ANUALIZADA (agregar con los otros callbacks)
# =============================================================================

# Callback para abrir/cerrar modal de gráfico anualizada
@callback(
    Output("modal-grafico-anualizada", "is_open"),
    [Input("btn-pantalla-completa-anualizada", "n_clicks")],
    [State("modal-grafico-anualizada", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_grafico_anualizada(btn_open, is_open): 
    if btn_open:
        return not is_open
    return is_open

# Callback para sincronizar gráfico del modal anualizada
@callback(
    Output('grafico-retornos-anualizados-modal', 'figure'),
    [Input('grafico-retornos-anualizados', 'figure')],
    prevent_initial_call=True
)
def sincronizar_grafico_modal_anualizada(figure):
    if figure and 'data' in figure and len(figure['data']) > 0:
        figure_modal = figure.copy()
        
        figure_modal['layout'].update({
            'height': 750,
            'margin': dict(t=100, b=80, l=20, r=20),
            'title': {
                'text': 'Rentabilidades Acumulados',
                'x': 0.5,
                'y': 0.95,
                'font': {'family': 'SuraSans-SemiBold', 'size': 26, 'color': '#24272A'}
            },
            'legend': {
                'orientation': 'h',
                'x': 0.5,
                'y': -0.15,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'family': 'SuraSans-Regular', 'size': 14},
                'bgcolor': 'rgba(255,255,255,0.9)',
                'bordercolor': 'rgba(0,0,0,0.1)',
                'borderwidth': 1
            },
            'xaxis': {
                'showgrid': False,
                'showspikes': True,
                'spikecolor': 'rgba(36, 39, 42, 0.3)',
                'spikesnap': 'cursor',
                'spikemode': 'across',
                'spikethickness': 1,
                'spikedash': 'dot',
                'tickformat': '%d/%m/%Y'
            },
            'yaxis': {
                'title': {'text': 'Retorno Acumulado (%)', 'font': {'size': 18}},
                'tickfont': {'size': 14},
                'tickformat': '.1f',
                'ticksuffix': '%',
                'showgrid': True,
                'gridcolor': 'rgba(128,128,128,0.2)'
            },
            'plot_bgcolor': 'white',
            'paper_bgcolor': 'white',
            
            # AGREGAR LOGO TAMBIÉN EN EL MODAL
            'images': [
                dict(
                    source="/assets/investments_logo.png",
                    xref="paper", 
                    yref="paper",
                    x=1.02,
                    y=-0.30,
                    sizex=0.23,
                    sizey=0.17,
                    xanchor="right",
                    yanchor="bottom",
                    opacity=0.9,
                    layer="above"
                )
            ]
        })
        
        return figure_modal
    
    # Si no hay datos, mostrar mensaje
    fig_vacio = go.Figure()
    fig_vacio.add_annotation(
        text="Cargando datos...",
        x=0.5, y=0.5, showarrow=False,
        font={'family': 'SuraSans-Regular', 'size': 20, 'color': '#666666'}
    )
    fig_vacio.update_layout(
        plot_bgcolor='#f8f9fa', paper_bgcolor='#f8f9fa',
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
        margin=dict(t=20, b=20, l=20, r=20), height=750
    )
    return fig_vacio


@callback(
    Output({'type': 'series-dropdown', 'index': MATCH}, 'options'),
    Output({'type': 'series-dropdown', 'index': MATCH}, 'disabled'),
    Output({'type': 'series-dropdown', 'index': MATCH}, 'placeholder'),
    Output({'type': 'series-dropdown', 'index': MATCH}, 'value'),
    [Input({'type': 'fondo-dropdown', 'index': MATCH}, 'value'),
     Input('moneda-selector-acumulada', 'value')],  # AGREGAR moneda
    State({'type': 'series-dropdown', 'index': MATCH}, 'value'),
    prevent_initial_call=True
)
def actualizar_series_dinamico(fondo_seleccionado, moneda, valor_series_actual):
    if not fondo_seleccionado or fondo_seleccionado not in fondos_a_series:
        return [], True, "Primero selecciona un fondo", []
    
    # CAMBIO: Filtrar series disponibles por moneda
    if moneda in fondos_a_series[fondo_seleccionado]:
        series_disponibles = fondos_a_series[fondo_seleccionado][moneda]
    else:
        series_disponibles = []
    
    if not series_disponibles:
        return [], True, f"No hay series disponibles en {moneda}", []
    
    opciones_series = [{'label': serie, 'value': serie} for serie in series_disponibles]
    
    if valor_series_actual:
        series_validas = [serie for serie in valor_series_actual if serie in series_disponibles]
        valor_a_mantener = series_validas
    else:
        valor_a_mantener = []
    
    return opciones_series, False, f"Selecciona series para {fondo_seleccionado[:30]}...", valor_a_mantener

# Callback para actualizar el store con las selecciones
@callback(
    Output('selecciones-store', 'data'),
    [Input({'type': 'fondo-dropdown', 'index': ALL}, 'value'),
     Input({'type': 'series-dropdown', 'index': ALL}, 'value')],
    [State('selectores-container', 'children')]
)
def actualizar_selecciones_store(fondos_valores, series_valores, children):
    if not children or not fondos_valores or not series_valores:
        return []
    
    selecciones = []
    
    for i, child in enumerate(children):
        if i < len(fondos_valores) and i < len(series_valores):
            fondo = fondos_valores[i]
            series = series_valores[i]
            
            if fondo and series:  # Solo agregar si ambos tienen valores
                selecciones.append({
                    'fondo': fondo,
                    'series': series
                })
    
    return selecciones

# Callback para inicializar fechas por defecto
@callback(
    [Output('fecha-inicio-grafico', 'date'),
     Output('fecha-fin-grafico', 'date')],
    [Input('moneda-selector-acumulada', 'value')]
)
def inicializar_fechas_grafico(active_tab):
    if pesos_df is not None:
        fecha_fin = pesos_df['Dates'].max()
        fecha_inicio = fecha_fin - timedelta(days=365)
        return fecha_inicio, fecha_fin
    else:
        fecha_fin = datetime.now()
        fecha_inicio = fecha_fin - timedelta(days=365)
        return fecha_inicio, fecha_fin




# Callback para tabla de índices en pestaña anualizada 
@callback(
   Output('tabla-indices-anualizada', 'children'),
   [Input('moneda-selector-anualizada', 'value')]
)
def actualizar_tabla_indices_anualizada(moneda):
    if pesos_df is None:
        return html.P("No se pudieron cargar los datos", 
                     style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'})
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    
    codigos_indices, nombres_indices = obtener_codigos_indices(moneda)
    
    if not codigos_indices:
        return html.P("No se encontraron los fondos índice", 
                     style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'})
    
    tabla_data = calcular_rentabilidades_anualizadas(df_actual, codigos_indices, nombres_indices)
    tabla_data['Moneda'] = moneda
    
    # CAMBIO: Agregar '1 Año' a las columnas
    columnas_orden = ['Fondo', 'Serie', 'Moneda', '1 Año', '3 Años', '5 Años']
    tabla_data = tabla_data[columnas_orden]
    
    tabla = dash_table.DataTable(
        data=tabla_data.to_dict('records'),
        columns=[{"name": col, "id": col, "type": "numeric", "format": {"specifier": ".2f"}} 
                if col not in ['Fondo', 'Serie', 'Moneda'] else {"name": col, "id": col} 
                for col in tabla_data.columns],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'center',
            'fontFamily': 'SuraSans-Regular',
            'fontSize': '12px'
        },
        style_header={
            'backgroundColor': '#24272A',
            'color': 'white',
            'fontFamily': 'SuraSans-SemiBold',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} > 0'},
                'color': 'green'
            } for col in ['1 Año', '3 Años', '5 Años']
        ] + [
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} < 0'},
                'color': 'red'
            } for col in ['1 Año', '3 Años', '5 Años']
        ]
    )
    
    # AGREGAR DISCLAIMER DEBAJO DE LA TABLA
    return html.Div([
        tabla,
        crear_disclaimer_anualizada()  # ← LÍNEA QUE FALTABA
    ])

# Callback para tabla de índices en pestaña por año
@callback(
   Output('tabla-indices-por-ano', 'children'),
   [Input('moneda-selector-por-año', 'value')]
)
def actualizar_tabla_indices_por_ano(moneda):
    if pesos_df is None:
        return html.P("No se pudieron cargar los datos", 
                     style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'})
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    
    codigos_indices, nombres_indices = obtener_codigos_indices(moneda)
    
    if not codigos_indices:
        return html.P("No se encontraron los fondos índice", 
                     style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'})
    
    tabla_data = calcular_rentabilidades_por_año(df_actual, codigos_indices, nombres_indices)
    tabla_data['Moneda'] = moneda
    
    columnas_base = ['Fondo', 'Serie', 'Moneda']
    años_columnas = [col for col in tabla_data.columns if col not in columnas_base]
    años_columnas.sort(reverse=True)
    columnas_orden = columnas_base + años_columnas
    
    tabla_data = tabla_data[columnas_orden]
    
    tabla = dash_table.DataTable(
        data=tabla_data.to_dict('records'),
        columns=[{"name": col, "id": col, "type": "numeric", "format": {"specifier": ".2f"}} 
                if col not in ['Fondo', 'Serie', 'Moneda'] else {"name": col, "id": col} 
                for col in tabla_data.columns],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'center',
            'fontFamily': 'SuraSans-Regular',
            'fontSize': '11px'
        },
        style_header={
            'backgroundColor': '#24272A',
            'color': 'white',
            'fontFamily': 'SuraSans-SemiBold',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} > 0'},
                'color': 'green'
            } for col in años_columnas
        ] + [
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} < 0'},
                'color': 'red'
            } for col in años_columnas
        ]
    )
    
    # AGREGAR DISCLAIMER DEBAJO DE LA TABLA
    return html.Div([
        tabla,
        crear_disclaimer_por_año()  # ← LÍNEA QUE FALTABA
    ])


# Callback para botones de período
@callback(
    [Output('fecha-inicio-grafico', 'date', allow_duplicate=True),
     Output('fecha-fin-grafico', 'date', allow_duplicate=True),
     Output('fecha-inicio-grafico', 'min_date_allowed'),  # NUEVO: límite mínimo
     Output('btn-1m', 'disabled'),   # NUEVO: deshabilitar botones si no hay suficiente historial
     Output('btn-3m', 'disabled'),
     Output('btn-6m', 'disabled'),
     Output('btn-ytd', 'disabled'),
     Output('btn-1y', 'disabled'),
     Output('btn-3y', 'disabled'),
     Output('btn-5y', 'disabled'),
     Output('btn-max', 'disabled')],
    [Input('btn-1m', 'n_clicks'),
     Input('btn-3m', 'n_clicks'),
     Input('btn-6m', 'n_clicks'),
     Input('btn-ytd', 'n_clicks'),
     Input('btn-1y', 'n_clicks'),
     Input('btn-3y', 'n_clicks'),
     Input('btn-5y', 'n_clicks'),
     Input('btn-max', 'n_clicks'),
     Input('selecciones-store', 'data'),  # NUEVO: escuchar cambios en selecciones
     Input('moneda-selector-acumulada', 'value')],  # NUEVO: escuchar cambios en moneda
    prevent_initial_call=True
)
def actualizar_fechas_grafico_con_limites(btn1m, btn3m, btn6m, btnytd, btn1y, btn3y, btn5y, btnmax, selecciones_data, moneda):
    ctx = dash.callback_context
    
    if pesos_df is None:
        return dash.no_update, dash.no_update, None, False, False, False, False, False, False, False, False
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    fecha_fin = df_actual['Dates'].max()
    
    # Obtener códigos seleccionados
    codigos_seleccionados = []
    if selecciones_data:
        codigos_seleccionados, _ = procesar_selecciones_multiples(selecciones_data)
    
    # Obtener fecha límite (fondo más nuevo)
    fecha_limite_inicio = obtener_fecha_inicio_mas_reciente(df_actual, codigos_seleccionados)
    
    # Calcular años disponibles para deshabilitar botones
    anos_disponibles = 0
    if fecha_limite_inicio:
        anos_disponibles = calcular_anos_disponibles(fecha_limite_inicio, fecha_fin)
    
    # Determinar qué botones deshabilitar
    btn_1m_disabled = False
    btn_3m_disabled = False
    btn_6m_disabled = False
    btn_ytd_disabled = False
    btn_1y_disabled = anos_disponibles < 1
    btn_3y_disabled = anos_disponibles < 3
    btn_5y_disabled = anos_disponibles < 5
    btn_max_disabled = not fecha_limite_inicio
    
    # Si se presionó un botón, calcular nueva fecha de inicio
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id in ['btn-1m', 'btn-3m', 'btn-6m', 'btn-ytd', 'btn-1y', 'btn-3y', 'btn-5y', 'btn-max']:
            periodo = button_id.replace('btn-', '')
            fecha_inicio = ajustar_fecha_segun_periodo_y_limite(fecha_fin, periodo, fecha_limite_inicio)
            
            return (fecha_inicio, fecha_fin, fecha_limite_inicio,
                   btn_1m_disabled, btn_3m_disabled, btn_6m_disabled, btn_ytd_disabled,
                   btn_1y_disabled, btn_3y_disabled, btn_5y_disabled, btn_max_disabled)
    
    # Si solo cambiaron las selecciones, ajustar fecha de inicio a los datos disponibles
    if fecha_limite_inicio:
        # Mantener la fecha fin, pero ajustar fecha inicio si está fuera del rango
        fecha_inicio_actual = pd.to_datetime('2023-01-01')  # valor por defecto
        if ctx.triggered:
            # Usar fecha de inicio actual si no se presionó botón
            fecha_inicio_actual = max(fecha_limite_inicio, fecha_fin - timedelta(days=365))
        else:
            fecha_inicio_actual = fecha_limite_inicio
    else:
        fecha_inicio_actual = fecha_fin - timedelta(days=365)
    
    return (fecha_inicio_actual, fecha_fin, fecha_limite_inicio,
           btn_1m_disabled, btn_3m_disabled, btn_6m_disabled, btn_ytd_disabled,
           btn_1y_disabled, btn_3y_disabled, btn_5y_disabled, btn_max_disabled)



# NUEVO CALLBACK para validar cuando el usuario cambia las fechas manualmente
@callback(
    [Output('fecha-inicio-grafico', 'date', allow_duplicate=True),
     Output('fecha-fin-grafico', 'date', allow_duplicate=True)],
    [Input('fecha-inicio-grafico', 'date'),
     Input('fecha-fin-grafico', 'date')],
    [State('selecciones-store', 'data'),
     State('moneda-selector-acumulada', 'value')],
    prevent_initial_call=True
)
def validar_fechas_manuales(fecha_inicio_input, fecha_fin_input, selecciones_data, moneda):
    """
    Valida que las fechas manuales no excedan los límites del fondo más nuevo
    """
    if pesos_df is None or not fecha_inicio_input or not fecha_fin_input:
        return dash.no_update, dash.no_update
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    
    # Obtener códigos seleccionados
    codigos_seleccionados = []
    if selecciones_data:
        codigos_seleccionados, _ = procesar_selecciones_multiples(selecciones_data)
    
    # Obtener fecha límite
    fecha_limite_inicio = obtener_fecha_inicio_mas_reciente(df_actual, codigos_seleccionados)
    
    fecha_inicio_dt = pd.to_datetime(fecha_inicio_input)
    fecha_fin_dt = pd.to_datetime(fecha_fin_input)
    
    # Ajustar fecha de inicio si está antes del límite
    if fecha_limite_inicio and fecha_inicio_dt < fecha_limite_inicio:
        fecha_inicio_ajustada = fecha_limite_inicio
        return fecha_inicio_ajustada, fecha_fin_dt
    
    return dash.no_update, dash.no_update


# Callback para actualizar gráfico (SOLO FONDOS PERSONALIZADOS - SIN ÍNDICES)
@callback(
    Output('grafico-retornos-acumulados', 'figure'),
    [Input('moneda-selector-acumulada', 'value'),
     Input('selecciones-store', 'data'),
     Input('fecha-inicio-grafico', 'date'),
     Input('fecha-fin-grafico', 'date')]
)
def actualizar_grafico_retornos_con_limite(moneda, selecciones_data, fecha_inicio, fecha_fin):
    if pesos_df is None:
        fig_vacio = go.Figure()
        fig_vacio.add_annotation(
            text="No se pudieron cargar los datos",
            x=0.5, y=0.5, showarrow=False
        )
        return fig_vacio
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    
    if not selecciones_data:
        fig_vacio = go.Figure()
        fig_vacio.add_annotation(
            text="Usa el botón 'Agregar Fondo Personalizado' para ver fondos en el gráfico",
            x=0.5, 
            y=0.5, 
            showarrow=False,
            font={'family': 'SuraSans-Regular', 'size': 16, 'color': '#666666'},
            xanchor='center',  
            yanchor='middle',
            xref='paper',
            yref='paper',
        )
        fig_vacio.update_layout(
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='#f8f9fa',
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            margin=dict(t=20, b=20, l=20, r=20),
            height=500
        )
        return fig_vacio
    
    codigos_personalizados, nombres_personalizados = procesar_selecciones_multiples(selecciones_data)
    
    if not codigos_personalizados:
        fig_vacio = go.Figure()
        fig_vacio.add_annotation(
            text="No se encontraron datos para las selecciones personalizadas",
            x=0.5, 
            y=0.5, 
            showarrow=False,
            font={'family': 'SuraSans-Regular', 'size': 16, 'color': '#666666'},
            xanchor='center',  
            yanchor='middle',
            xref='paper',
            yref='paper',
        )
        fig_vacio.update_layout(
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='#f8f9fa',
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            margin=dict(t=20, b=20, l=20, r=20),
            height=500
        )
        return fig_vacio
    
    # USAR LA NUEVA FUNCIÓN CON LÍMITE
    df_retornos = calcular_retornos_acumulados_con_limite(
        df_actual, codigos_personalizados, 
        fecha_inicio, fecha_fin
    )
    
    return crear_grafico_retornos(df_retornos, codigos_personalizados, nombres_personalizados)


# Callback para abrir/cerrar modal de gráfico
@callback(
    Output("modal-grafico", "is_open"),
    [Input("btn-pantalla-completa", "n_clicks")],
    [State("modal-grafico", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_grafico(btn_open, is_open):
    if btn_open:
        return not is_open
    return is_open

# Callback para sincronizar gráfico del modal
@callback(
    Output('grafico-retornos-modal', 'figure'),
    [Input('grafico-retornos-acumulados', 'figure')],
    prevent_initial_call=True
)
def sincronizar_grafico_modal(figure):
    if figure and 'data' in figure and len(figure['data']) > 0:
        figure_modal = figure.copy()
        
        figure_modal['layout'].update({
            'height': 750,
            'margin': dict(t=100, b=80, l=20, r=20),
            'title': {
                'text': 'Retornos Acumulados',
                'x': 0.5,
                'y': 0.95,
                'font': {'family': 'SuraSans-SemiBold', 'size': 26, 'color': '#24272A'}
            },
            'legend': {
                'orientation': 'h',
                'x': 0.5,
                'y': -0.15,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'family': 'SuraSans-Regular', 'size': 14},
                'bgcolor': 'rgba(255,255,255,0.9)',
                'bordercolor': 'rgba(0,0,0,0.1)',
                'borderwidth': 1
            },
            'xaxis': {
                'showgrid': False,
                'showspikes': True,
                'spikecolor': 'rgba(36, 39, 42, 0.3)',
                'spikesnap': 'cursor',
                'spikemode': 'across',
                'spikethickness': 1,
                'spikedash': 'dot',
                'tickformat': '%d/%m/%Y'
            },
            'yaxis': {
                'title': {'text': 'Retorno Acumulado (%)', 'font': {'size': 18}},
                'tickfont': {'size': 14},
                'tickformat': '.1f',
                'ticksuffix': '%',
                'showgrid': True,
                'gridcolor': 'rgba(128,128,128,0.2)'
            },
            'plot_bgcolor': 'white',
            'paper_bgcolor': 'white',
            
            # AGREGAR LOGO TAMBIÉN EN EL MODAL (más abajo y más grande)
            'images': [
                dict(
                    source="/assets/investments_logo.png",
                    xref="paper", 
                    yref="paper",
                    x=1.02,
                    y=-0.30,  # Más abajo que la leyenda
                    sizex=0.23,  # Más grande en pantalla completa
                    sizey=0.17,  # Más grande en pantalla completa
                    xanchor="right",
                    yanchor="bottom",
                    opacity=0.9,
                    layer="above"
                )
            ]
        })
        
        return figure_modal
    
    # Si no hay datos, mostrar mensaje
    fig_vacio = go.Figure()
    fig_vacio.add_annotation(
        text="Cargando datos...",
        x=0.5, y=0.5, showarrow=False,
        font={'family': 'SuraSans-Regular', 'size': 20, 'color': '#666666'}
    )
    fig_vacio.update_layout(
        plot_bgcolor='#f8f9fa', paper_bgcolor='#f8f9fa',
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
        margin=dict(t=20, b=20, l=20, r=20), height=750
    )
    return fig_vacio

informe_module.registrar_callbacks_informe(
    app=app,
    pesos_df=pesos_df,
    dolares_df=dolares_df,
    fondos_unicos=fondos_unicos,
    fondos_a_series=fondos_a_series,
    fondo_serie_a_codigo=fondo_serie_a_codigo,
    calcular_rentabilidades_func=calcular_rentabilidades
)

# AGREGAR ESTAS LÍNEAS:
anexo_mensual_module.registrar_callbacks_anexo_mensual(
    app=app,
    pesos_df=pesos_df,
    dolares_df=dolares_df,
    fondos_unicos=fondos_unicos,
    fondos_a_series=fondos_a_series,
    fondo_serie_a_codigo=fondo_serie_a_codigo
)


from dash import ctx   

@app.callback(
    Output("periodo-activo", "data"),
    Input("btn-1m", "n_clicks"),
    Input("btn-3m", "n_clicks"),
    Input("btn-6m", "n_clicks"),
    Input("btn-ytd", "n_clicks"),
    Input("btn-1y", "n_clicks"),
    Input("btn-3y", "n_clicks"),
    Input("btn-5y", "n_clicks"),
    Input("btn-max", "n_clicks"),
    prevent_initial_call=True
)
def actualizar_periodo(*_):
    return ctx.triggered_id

@app.callback(
    [
        Output("btn-1m", "style"),
        Output("btn-3m", "style"),
        Output("btn-6m", "style"),
        Output("btn-ytd", "style"),
        Output("btn-1y", "style"),
        Output("btn-3y", "style"),
        Output("btn-5y", "style"),
        Output("btn-max", "style"),
    ],
    [Input("periodo-activo", "data"),
     Input('btn-1m', 'disabled'),   # NUEVO: considerar estado disabled
     Input('btn-3m', 'disabled'),
     Input('btn-6m', 'disabled'),
     Input('btn-ytd', 'disabled'),
     Input('btn-1y', 'disabled'),
     Input('btn-3y', 'disabled'),
     Input('btn-5y', 'disabled'),
     Input('btn-max', 'disabled')]
)

def resaltar_boton_activo(periodo_activo, disabled_1m, disabled_3m, disabled_6m, 
                         disabled_ytd, disabled_1y, disabled_3y, disabled_5y, disabled_max):
    def estilo(activo, deshabilitado, ancho="45px"):
        if deshabilitado:
            # Estilo para botones deshabilitados
            return {
                'margin': '2px', 'width': ancho,
                'backgroundColor': '#f8f9fa', 'color': '#6c757d',
                'border': '1px solid #dee2e6',
                'cursor': 'not-allowed',
                'opacity': 0.5
            }
        elif activo:
            # Estilo para botón activo
            return {
                'margin': '2px', 'width': ancho,
                'backgroundColor': 'black', 'color': 'white',
                'border': '1px solid black'
            }
        else:
            # Estilo para botones normales
            return {
                'margin': '2px', 'width': ancho,
                'backgroundColor': 'white', 'color': 'black',
                'border': '1px solid black'
            }

    return [
        estilo(periodo_activo == "btn-1m", disabled_1m),
        estilo(periodo_activo == "btn-3m", disabled_3m),
        estilo(periodo_activo == "btn-6m", disabled_6m),
        estilo(periodo_activo == "btn-ytd", disabled_ytd, ancho="50px"),
        estilo(periodo_activo == "btn-1y", disabled_1y),
        estilo(periodo_activo == "btn-3y", disabled_3y),
        estilo(periodo_activo == "btn-5y", disabled_5y),
        estilo(periodo_activo == "btn-max", disabled_max, ancho="50px"),
    ]

def crear_selector_fondo_anualizada(id_selector):
    """
    Crea un componente selector de fondo + series con botón de eliminar para ANUALIZADA
    """
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Fondo:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'fondo-dropdown-anualizada', 'index': id_selector},
                        options=[{'label': fondo, 'value': fondo} for fondo in fondos_unicos],
                        value=None,
                        placeholder="Selecciona un fondo...",
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=5),
                
                dbc.Col([
                    html.Label("Series:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'series-dropdown-anualizada', 'index': id_selector},
                        options=[],
                        value=[],
                        multi=True,
                        placeholder="Primero selecciona un fondo",
                        disabled=True,
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=6),
                
                dbc.Col([
                    html.Br(),
                    dbc.Button(
                        "❌", 
                        id={'type': 'eliminar-selector-anualizada', 'index': id_selector},
                        color="danger", 
                        size="sm",
                        style={'marginTop': '5px'}
                    )
                ], width=1)
            ])
        ])
    ], style={'marginBottom': '10px'})

def crear_selector_fondo_con_valores_anualizada(id_selector, fondo_valor=None, series_valor=None):
    """
    Crea un componente selector de fondo + series con valores pre-establecidos para ANUALIZADA
    """
    if fondo_valor and fondo_valor in fondos_a_series:
        series_opciones = [{'label': serie, 'value': serie} for serie in fondos_a_series[fondo_valor]]
        series_disabled = False
        series_placeholder = f"Selecciona series para {fondo_valor[:30]}..."
        if series_valor is None:
            series_valor = []
        elif not isinstance(series_valor, list):
            series_valor = [series_valor] if series_valor else []
    else:
        series_opciones = []
        series_disabled = True
        series_placeholder = "Primero selecciona un fondo"
        series_valor = []
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Fondo:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'fondo-dropdown-anualizada', 'index': id_selector},
                        options=[{'label': fondo, 'value': fondo} for fondo in fondos_unicos],
                        value=fondo_valor,
                        placeholder="Selecciona un fondo...",
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=5),
                
                dbc.Col([
                    html.Label("Series:", style={'fontFamily': 'SuraSans-SemiBold', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id={'type': 'series-dropdown-anualizada', 'index': id_selector},
                        options=series_opciones,
                        value=series_valor,
                        multi=True,
                        placeholder=series_placeholder,
                        disabled=series_disabled,
                        style={'fontFamily': 'SuraSans-Regular', 'fontSize': '14px'}
                    )
                ], width=6),
                
                dbc.Col([
                    html.Br(),
                    dbc.Button(
                        "❌", 
                        id={'type': 'eliminar-selector-anualizada', 'index': id_selector},
                        color="danger", 
                        size="sm",
                        style={'marginTop': '5px'}
                    )
                ], width=1)
            ])
        ])
    ], style={'marginBottom': '10px'})

def extraer_id_del_child_anualizada(child):
    """
    Extrae el ID de un componente hijo para ANUALIZADA
    """
    try:
        if isinstance(child, dict) and 'props' in child:
            card_body = child['props']['children']
            if isinstance(card_body, dict) and 'props' in card_body:
                row = card_body['props']['children']
                if isinstance(row, dict) and 'props' in row:
                    cols = row['props']['children']
                    if isinstance(cols, list) and len(cols) > 0:
                        first_col = cols[0]
                        if isinstance(first_col, dict) and 'props' in first_col:
                            col_children = first_col['props']['children']
                            if isinstance(col_children, list) and len(col_children) > 1:
                                fondo_dropdown = col_children[1]
                                if isinstance(fondo_dropdown, dict) and 'props' in fondo_dropdown:
                                    dropdown_id = fondo_dropdown['props'].get('id')
                                    if isinstance(dropdown_id, dict) and 'index' in dropdown_id:
                                        return dropdown_id['index']
        
        return buscar_id_recursivo_anualizada(child)
        
    except (KeyError, IndexError, TypeError, AttributeError):
        return None

def buscar_id_recursivo_anualizada(componente, profundidad=0):
    """
    Busca recursivamente un ID de tipo 'fondo-dropdown-anualizada'
    """
    if profundidad > 10:
        return None
        
    try:
        if isinstance(componente, dict):
            if 'props' in componente:
                props = componente['props']
                if 'id' in props:
                    component_id = props['id']
                    if isinstance(component_id, dict) and component_id.get('type') == 'fondo-dropdown-anualizada':
                        return component_id.get('index')
                
                if 'children' in props:
                    children = props['children']
                    if isinstance(children, list):
                        for child in children:
                            resultado = buscar_id_recursivo_anualizada(child, profundidad + 1)
                            if resultado:
                                return resultado
                    elif children:
                        resultado = buscar_id_recursivo_anualizada(children, profundidad + 1)
                        if resultado:
                            return resultado
        
        elif isinstance(componente, list):
            for item in componente:
                resultado = buscar_id_recursivo_anualizada(item, profundidad + 1)
                if resultado:
                    return resultado
                    
    except (KeyError, TypeError, AttributeError):
        pass
    
    return None

    # =============================================================================
# 4. CALLBACKS PARA POR AÑO (AGREGAR AL FINAL DEL ARCHIVO):
# =============================================================================

# Callback para actualizar selectores POR AÑO
@callback(
    Output('selectores-container-por-ano', 'children'),
    [Input('btn-agregar-fondo-por-ano', 'n_clicks'),
     Input({'type': 'eliminar-selector-por-ano', 'index': ALL}, 'n_clicks')],
    [State('selectores-container-por-ano', 'children'),
     State({'type': 'fondo-dropdown-por-ano', 'index': ALL}, 'value'),
     State({'type': 'series-dropdown-por-ano', 'index': ALL}, 'value')],
    prevent_initial_call=True
)
def actualizar_selectores_por_ano(n_clicks_agregar, n_clicks_eliminar, children_actuales, fondos_valores, series_valores):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return children_actuales or []
    
    trigger = ctx.triggered[0]
    
    # Si se presionó agregar fondo
    if trigger['prop_id'] == 'btn-agregar-fondo-por-ano.n_clicks' and n_clicks_agregar:
        children_actuales = children_actuales or []
        nuevo_id = str(uuid.uuid4())
        nuevo_selector = crear_selector_fondo_por_ano(nuevo_id)
        return children_actuales + [nuevo_selector]
    
    # Si se presionó eliminar algún selector
    elif 'eliminar-selector-por-ano' in trigger['prop_id']:
        if not children_actuales:
            return []
            
        # Extraer el ID del selector a eliminar
        import json
        prop_id_dict = json.loads(trigger['prop_id'].replace('.n_clicks', ''))
        id_a_eliminar = prop_id_dict['index']
        
        # Crear mapeo de IDs actuales con sus valores
        valores_por_id = {}
        for i, child in enumerate(children_actuales):
            child_id = extraer_id_del_child_por_ano(child)
            if child_id and i < len(fondos_valores or []) and i < len(series_valores or []):
                valores_por_id[child_id] = {
                    'fondo': fondos_valores[i],
                    'series': series_valores[i] or []
                }
        
        # Filtrar solo los elementos que NO sean el ID a eliminar
        children_preservados = []
        for child in children_actuales:
            child_id = extraer_id_del_child_por_ano(child)
            if child_id and child_id != id_a_eliminar:
                # Preservar este child con sus valores
                if child_id in valores_por_id:
                    child_preservado = crear_selector_fondo_con_valores_por_ano(
                        child_id,
                        valores_por_id[child_id]['fondo'],
                        valores_por_id[child_id]['series']
                    )
                    children_preservados.append(child_preservado)
                else:
                    children_preservados.append(child)
        
        return children_preservados
    
    return children_actuales or []

# Callback para actualizar series según fondo seleccionado - POR AÑO
@callback(
    Output({'type': 'series-dropdown-por-ano', 'index': MATCH}, 'options'),
    Output({'type': 'series-dropdown-por-ano', 'index': MATCH}, 'disabled'),
    Output({'type': 'series-dropdown-por-ano', 'index': MATCH}, 'placeholder'),
    Output({'type': 'series-dropdown-por-ano', 'index': MATCH}, 'value'),
    Input({'type': 'fondo-dropdown-por-ano', 'index': MATCH}, 'value'),
    State({'type': 'series-dropdown-por-ano', 'index': MATCH}, 'value'),
    prevent_initial_call=True
)
def actualizar_series_dinamico_por_ano(fondo_seleccionado, valor_series_actual):
    if not fondo_seleccionado or fondo_seleccionado not in fondos_a_series:
        return [], True, "Primero selecciona un fondo", []
    
    series_disponibles = fondos_a_series[fondo_seleccionado]
    opciones_series = [{'label': serie, 'value': serie} for serie in series_disponibles]
    
    if valor_series_actual:
        series_validas = [serie for serie in valor_series_actual if serie in series_disponibles]
        valor_a_mantener = series_validas
    else:
        valor_a_mantener = []
    
    return opciones_series, False, f"Selecciona series para {fondo_seleccionado[:30]}...", valor_a_mantener

# Callback para actualizar el store con las selecciones - POR AÑO
@callback(
    Output('selecciones-store-por-ano', 'data'),
    [Input({'type': 'fondo-dropdown-por-ano', 'index': ALL}, 'value'),
     Input({'type': 'series-dropdown-por-ano', 'index': ALL}, 'value')],
    [State('selectores-container-por-ano', 'children')]
)
def actualizar_selecciones_store_por_ano(fondos_valores, series_valores, children):
    if not children or not fondos_valores or not series_valores:
        return []
    
    selecciones = []
    
    for i, child in enumerate(children):
        if i < len(fondos_valores) and i < len(series_valores):
            fondo = fondos_valores[i]
            series = series_valores[i]
            
            if fondo and series:
                selecciones.append({
                    'fondo': fondo,
                    'series': series
                })
    
    return selecciones

# Callback para tabla de rentabilidades personalizadas - POR AÑO
@callback(
   Output('tabla-rentabilidades-por-ano', 'children'),
   [Input('moneda-selector-por-año', 'value'),
    Input('selecciones-store-por-ano', 'data')]
)
def actualizar_tabla_rentabilidades_por_ano(moneda, selecciones_data):
    if not selecciones_data:
        return html.Div([
            html.P("Usa el botón 'Agregar Fondo Personalizado' para añadir fondos a esta tabla", 
                   style={'fontFamily': 'SuraSans-Regular', 'color': '#666', 'textAlign': 'center'}),
            crear_disclaimer_por_año()
        ])
    
    if pesos_df is None:
        return html.P("No se pudieron cargar los datos", 
                     style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'})
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    
    codigos_seleccionados, nombres_mostrar = procesar_selecciones_multiples(selecciones_data, moneda)
    
    if not codigos_seleccionados:
        return html.Div([
            html.P("No se encontraron datos para las selecciones", 
                   style={'fontFamily': 'SuraSans-Regular', 'color': 'red', 'textAlign': 'center'}),
            crear_disclaimer_por_año()
        ])
    
    tabla_data = calcular_rentabilidades_por_año(df_actual, codigos_seleccionados, nombres_mostrar)
    tabla_data['Moneda'] = moneda
    
    columnas_base = ['Fondo', 'Serie', 'Moneda']
    años_columnas = [col for col in tabla_data.columns if col not in columnas_base]
    años_columnas.sort(reverse=True)
    columnas_orden = columnas_base + años_columnas
    
    tabla_data = tabla_data[columnas_orden]
    
    tabla = dash_table.DataTable(
        data=tabla_data.to_dict('records'),
        columns=[{"name": col, "id": col, "type": "numeric", "format": {"specifier": ".2f"}} 
                if col not in ['Fondo', 'Serie', 'Moneda'] else {"name": col, "id": col} 
                for col in tabla_data.columns],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'center',
            'fontFamily': 'SuraSans-Regular',
            'fontSize': '11px'
        },
        style_header={
            'backgroundColor': '#000000',
            'color': 'white',
            'fontFamily': 'SuraSans-SemiBold',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} > 0'},
                'color': 'green'
            } for col in años_columnas
        ] + [
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} < 0'},
                'color': 'red'
            } for col in años_columnas
        ]
    )
    
    return html.Div([
        tabla,
        crear_disclaimer_por_año()
    ])

# Callback para inicializar fechas por defecto - POR AÑO
@callback(
    [Output('fecha-inicio-grafico-por-ano', 'date'),
     Output('fecha-fin-grafico-por-ano', 'date')],
    [Input('tabs-por-ano', 'active_tab')]
)
def inicializar_fechas_grafico_por_ano(active_tab):
    if pesos_df is not None:
        fecha_fin = pesos_df['Dates'].max()
        fecha_inicio = fecha_fin - timedelta(days=365)
        return fecha_inicio, fecha_fin
    else:
        fecha_fin = datetime.now()
        fecha_inicio = fecha_fin - timedelta(days=365)
        return fecha_inicio, fecha_fin

# Callback para botones de período - POR AÑO
@callback(
    [Output('fecha-inicio-grafico-por-ano', 'date', allow_duplicate=True),
     Output('fecha-fin-grafico-por-ano', 'date', allow_duplicate=True),
     Output('fecha-inicio-grafico-por-ano', 'min_date_allowed'),
     Output('btn-1m-por-ano', 'disabled'),
     Output('btn-3m-por-ano', 'disabled'),
     Output('btn-6m-por-ano', 'disabled'),
     Output('btn-ytd-por-ano', 'disabled'),
     Output('btn-1y-por-ano', 'disabled'),
     Output('btn-3y-por-ano', 'disabled'),
     Output('btn-5y-por-ano', 'disabled'),
     Output('btn-max-por-ano', 'disabled')],
    [Input('btn-1m-por-ano', 'n_clicks'),
     Input('btn-3m-por-ano', 'n_clicks'),
     Input('btn-6m-por-ano', 'n_clicks'),
     Input('btn-ytd-por-ano', 'n_clicks'),
     Input('btn-1y-por-ano', 'n_clicks'),
     Input('btn-3y-por-ano', 'n_clicks'),
     Input('btn-5y-por-ano', 'n_clicks'),
     Input('btn-max-por-ano', 'n_clicks'),
     Input('selecciones-store-por-ano', 'data'),
     Input('moneda-selector-por-año', 'value')],
    prevent_initial_call=True
)
def actualizar_fechas_grafico_por_ano(btn1m, btn3m, btn6m, btnytd, btn1y, btn3y, btn5y, btnmax, selecciones_data, moneda):
    ctx = dash.callback_context
    
    if pesos_df is None:
        return dash.no_update, dash.no_update, None, False, False, False, False, False, False, False, False
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    fecha_fin = df_actual['Dates'].max()
    
    # Obtener códigos seleccionados
    codigos_seleccionados = []
    if selecciones_data:
        codigos_seleccionados, _ = procesar_selecciones_multiples(selecciones_data)
    
    # Obtener fecha límite (fondo más nuevo)
    fecha_limite_inicio = obtener_fecha_inicio_mas_reciente(df_actual, codigos_seleccionados)
    
    # Calcular años disponibles para deshabilitar botones
    anos_disponibles = 0
    if fecha_limite_inicio:
        anos_disponibles = calcular_anos_disponibles(fecha_limite_inicio, fecha_fin)
    
    # Determinar qué botones deshabilitar
    btn_1m_disabled = False
    btn_3m_disabled = False
    btn_6m_disabled = False
    btn_ytd_disabled = False
    btn_1y_disabled = anos_disponibles < 1
    btn_3y_disabled = anos_disponibles < 3
    btn_5y_disabled = anos_disponibles < 5
    btn_max_disabled = not fecha_limite_inicio
    
    # Si se presionó un botón, calcular nueva fecha de inicio
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id in ['btn-1m-por-ano', 'btn-3m-por-ano', 'btn-6m-por-ano', 'btn-ytd-por-ano', 'btn-1y-por-ano', 'btn-3y-por-ano', 'btn-5y-por-ano', 'btn-max-por-ano']:
            periodo = button_id.replace('btn-', '').replace('-por-ano', '')
            fecha_inicio = ajustar_fecha_segun_periodo_y_limite(fecha_fin, periodo, fecha_limite_inicio)
            
            return (fecha_inicio, fecha_fin, fecha_limite_inicio,
                   btn_1m_disabled, btn_3m_disabled, btn_6m_disabled, btn_ytd_disabled,
                   btn_1y_disabled, btn_3y_disabled, btn_5y_disabled, btn_max_disabled)
    
    # Si solo cambiaron las selecciones, ajustar fecha de inicio a los datos disponibles
    if fecha_limite_inicio:
        fecha_inicio_actual = max(fecha_limite_inicio, fecha_fin - timedelta(days=365))
    else:
        fecha_inicio_actual = fecha_fin - timedelta(days=365)
    
    return (fecha_inicio_actual, fecha_fin, fecha_limite_inicio,
           btn_1m_disabled, btn_3m_disabled, btn_6m_disabled, btn_ytd_disabled,
           btn_1y_disabled, btn_3y_disabled, btn_5y_disabled, btn_max_disabled)

# Callback para validar fechas manuales - POR AÑO
@callback(
    [Output('fecha-inicio-grafico-por-ano', 'date', allow_duplicate=True),
     Output('fecha-fin-grafico-por-ano', 'date', allow_duplicate=True)],
    [Input('fecha-inicio-grafico-por-ano', 'date'),
     Input('fecha-fin-grafico-por-ano', 'date')],
    [State('selecciones-store-por-ano', 'data'),
     State('moneda-selector-por-año', 'value')],
    prevent_initial_call=True
)
def validar_fechas_manuales_por_ano(fecha_inicio_input, fecha_fin_input, selecciones_data, moneda):
    if pesos_df is None or not fecha_inicio_input or not fecha_fin_input:
        return dash.no_update, dash.no_update
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    
    # Obtener códigos seleccionados
    codigos_seleccionados = []
    if selecciones_data:
        codigos_seleccionados, _ = procesar_selecciones_multiples(selecciones_data)
    
    # Obtener fecha límite
    fecha_limite_inicio = obtener_fecha_inicio_mas_reciente(df_actual, codigos_seleccionados)
    
    fecha_inicio_dt = pd.to_datetime(fecha_inicio_input)
    fecha_fin_dt = pd.to_datetime(fecha_fin_input)
    
    # Ajustar fecha de inicio si está antes del límite
    if fecha_limite_inicio and fecha_inicio_dt < fecha_limite_inicio:
        fecha_inicio_ajustada = fecha_limite_inicio
        return fecha_inicio_ajustada, fecha_fin_dt
    
    return dash.no_update, dash.no_update

# Callback para actualizar gráfico - POR AÑO
@callback(
    Output('grafico-retornos-por-ano', 'figure'),
    [Input('moneda-selector-por-año', 'value'),
     Input('selecciones-store-por-ano', 'data'),
     Input('fecha-inicio-grafico-por-ano', 'date'),
     Input('fecha-fin-grafico-por-ano', 'date')]
)
def actualizar_grafico_retornos_por_ano(moneda, selecciones_data, fecha_inicio, fecha_fin):
    if pesos_df is None:
        fig_vacio = go.Figure()
        fig_vacio.add_annotation(
            text="No se pudieron cargar los datos",
            x=0.5, y=0.5, showarrow=False
        )
        return fig_vacio
    
    df_actual = pesos_df if moneda == 'CLP' else dolares_df
    
    if not selecciones_data:
        fig_vacio = go.Figure()
        fig_vacio.add_annotation(
            text="Usa el botón 'Agregar Fondo Personalizado' para ver fondos en el gráfico",
            x=0.5, 
            y=0.5, 
            showarrow=False,
            font={'family': 'SuraSans-Regular', 'size': 16, 'color': '#666666'},
            xanchor='center',  
            yanchor='middle',
            xref='paper',
            yref='paper',
        )
        fig_vacio.update_layout(
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='#f8f9fa',
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            margin=dict(t=20, b=20, l=20, r=20),
            height=500
        )
        return fig_vacio
    
    codigos_personalizados, nombres_personalizados = procesar_selecciones_multiples(selecciones_data)
    
    if not codigos_personalizados:
        fig_vacio = go.Figure()
        fig_vacio.add_annotation(
            text="No se encontraron datos para las selecciones personalizadas",
            x=0.5, 
            y=0.5, 
            showarrow=False,
            font={'family': 'SuraSans-Regular', 'size': 16, 'color': '#666666'},
            xanchor='center',  
            yanchor='middle',
            xref='paper',
            yref='paper',
        )
        fig_vacio.update_layout(
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='#f8f9fa',
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            margin=dict(t=20, b=20, l=20, r=20),
            height=500
        )
        return fig_vacio
    
    # USAR LA MISMA FUNCIÓN QUE RENTABILIDAD ACUMULADA
    df_retornos = calcular_retornos_acumulados_con_limite(
        df_actual, codigos_personalizados, 
        fecha_inicio, fecha_fin
    )
    
    return crear_grafico_retornos(df_retornos, codigos_personalizados, nombres_personalizados)

# Callbacks para periodo activo y estilos de botones - POR AÑO
@callback(
    Output("periodo-activo-por-ano", "data"),
    Input("btn-1m-por-ano", "n_clicks"),
    Input("btn-3m-por-ano", "n_clicks"),
    Input("btn-6m-por-ano", "n_clicks"),
    Input("btn-ytd-por-ano", "n_clicks"),
    Input("btn-1y-por-ano", "n_clicks"),
    Input("btn-3y-por-ano", "n_clicks"),
    Input("btn-5y-por-ano", "n_clicks"),
    Input("btn-max-por-ano", "n_clicks"),
    prevent_initial_call=True
)
def actualizar_periodo_por_ano(*_):
    from dash import ctx
    return ctx.triggered_id

@callback(
    [
        Output("btn-1m-por-ano", "style"),
        Output("btn-3m-por-ano", "style"),
        Output("btn-6m-por-ano", "style"),
        Output("btn-ytd-por-ano", "style"),
        Output("btn-1y-por-ano", "style"),
        Output("btn-3y-por-ano", "style"),
        Output("btn-5y-por-ano", "style"),
        Output("btn-max-por-ano", "style"),
    ],
    [Input("periodo-activo-por-ano", "data"),
     Input('btn-1m-por-ano', 'disabled'),
     Input('btn-3m-por-ano', 'disabled'),
     Input('btn-6m-por-ano', 'disabled'),
     Input('btn-ytd-por-ano', 'disabled'),
     Input('btn-1y-por-ano', 'disabled'),
     Input('btn-3y-por-ano', 'disabled'),
     Input('btn-5y-por-ano', 'disabled'),
     Input('btn-max-por-ano', 'disabled')]
)
def resaltar_boton_activo_por_ano(periodo_activo, disabled_1m, disabled_3m, disabled_6m, 
                                 disabled_ytd, disabled_1y, disabled_3y, disabled_5y, disabled_max):
    def estilo(activo, deshabilitado, ancho="45px"):
        if deshabilitado:
            return {
                'margin': '2px', 'width': ancho,
                'backgroundColor': '#f8f9fa', 'color': '#6c757d',
                'border': '1px solid #dee2e6',
                'cursor': 'not-allowed',
                'opacity': 0.5
            }
        elif activo:
            return {
                'margin': '2px', 'width': ancho,
                'backgroundColor': 'black', 'color': 'white',
                'border': '1px solid black'
            }
        else:
            return {
                'margin': '2px', 'width': ancho,
                'backgroundColor': 'white', 'color': 'black',
                'border': '1px solid black'
            }

    return [
        estilo(periodo_activo == "btn-1m-por-ano", disabled_1m),
        estilo(periodo_activo == "btn-3m-por-ano", disabled_3m),
        estilo(periodo_activo == "btn-6m-por-ano", disabled_6m),
        estilo(periodo_activo == "btn-ytd-por-ano", disabled_ytd, ancho="50px"),
        estilo(periodo_activo == "btn-1y-por-ano", disabled_1y),
        estilo(periodo_activo == "btn-3y-por-ano", disabled_3y),
        estilo(periodo_activo == "btn-5y-por-ano", disabled_5y),
        estilo(periodo_activo == "btn-max-por-ano", disabled_max, ancho="50px"),
    ]

# Callback para abrir/cerrar modal de gráfico por año
@callback(
    Output("modal-grafico-por-ano", "is_open"),
    [Input("btn-pantalla-completa-por-ano", "n_clicks")],
    [State("modal-grafico-por-ano", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_grafico_por_ano(btn_open, is_open): 
    if btn_open:
        return not is_open
    return is_open

# Callback para sincronizar gráfico del modal por año
@callback(
    Output('grafico-retornos-por-ano-modal', 'figure'),
    [Input('grafico-retornos-por-ano', 'figure')],
    prevent_initial_call=True
)
def sincronizar_grafico_modal_por_ano(figure):
    if figure and 'data' in figure and len(figure['data']) > 0:
        figure_modal = figure.copy()
        
        figure_modal['layout'].update({
            'height': 750,
            'margin': dict(t=100, b=80, l=20, r=20),
            'title': {
                'text': 'Retornos Acumulados',
                'x': 0.5,
                'y': 0.95,
                'font': {'family': 'SuraSans-SemiBold', 'size': 26, 'color': '#24272A'}
            },
            'legend': {
                'orientation': 'h',
                'x': 0.5,
                'y': -0.15,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'family': 'SuraSans-Regular', 'size': 14},
                'bgcolor': 'rgba(255,255,255,0.9)',
                'bordercolor': 'rgba(0,0,0,0.1)',
                'borderwidth': 1
            },
            'xaxis': {
                'showgrid': False,
                'showspikes': True,
                'spikecolor': 'rgba(36, 39, 42, 0.3)',
                'spikesnap': 'cursor',
                'spikemode': 'across',
                'spikethickness': 1,
                'spikedash': 'dot',
                'tickformat': '%d/%m/%Y'
            },
            'yaxis': {
                'title': {'text': 'Retorno Acumulado (%)', 'font': {'size': 18}},
                'tickfont': {'size': 14},
                'tickformat': '.1f',
                'ticksuffix': '%',
                'showgrid': True,
                'gridcolor': 'rgba(128,128,128,0.2)'
            },
            'plot_bgcolor': 'white',
            'paper_bgcolor': 'white',
            
            'images': [
                dict(
                    source="/assets/investments_logo.png",
                    xref="paper", 
                    yref="paper",
                    x=1.02,
                    y=-0.30,
                    sizex=0.23,
                    sizey=0.17,
                    xanchor="right",
                    yanchor="bottom",
                    opacity=0.9,
                    layer="above"
                )
            ]
        })
        
        return figure_modal
    
    # Si no hay datos, mostrar mensaje
    fig_vacio = go.Figure()
    fig_vacio.add_annotation(
        text="Cargando datos...",
        x=0.5, y=0.5, showarrow=False,
        font={'family': 'SuraSans-Regular', 'size': 20, 'color': '#666666'}
    )
    fig_vacio.update_layout(
        plot_bgcolor='#f8f9fa', paper_bgcolor='#f8f9fa',
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
        margin=dict(t=20, b=20, l=20, r=20), height=750
    )
    return fig_vacio

# CALLBACK NUEVO - AGREGAR AL FINAL DE Pagina.py
@callback(
    [Output('datos-base-cache', 'data'),
     Output('timestamp-cache', 'data')],
    Input('url', 'pathname'),  # Se ejecuta al cargar la página
    State('datos-base-cache', 'data'),
    State('timestamp-cache', 'data'),
    prevent_initial_call=False
)
def inicializar_cache_datos(pathname, datos_cache, timestamp_cache):
    """
    Carga los datos base una sola vez por día
    """
    from datetime import datetime
    
    hoy = datetime.now().strftime('%Y-%m-%d')
    
    # Si no hay caché o es de otro día, cargar datos
    if not datos_cache or timestamp_cache != hoy:
        try:
            # Cargar datos frescos
            global pesos_df, dolares_df
            
            datos_frescos = {
                'pesos_procesado': True if pesos_df is not None else False,
                'dolares_procesado': True if dolares_df is not None else False,
                'fecha_carga': hoy
            }
            
            return datos_frescos, hoy
            
        except Exception as e:
            return {}, hoy
    
    # Si ya hay caché del mismo día, no hacer nada
    return datos_cache, timestamp_cache

# if __name__ == '__main__':
#     app.run(debug=True, use_reloader=False)
if __name__ == '__main__':
    # Configuración para Render.com
    port = int(os.environ.get('PORT', 8050))
    app.run_server(
        host='0.0.0.0',  # IMPORTANTE: Debe ser 0.0.0.0 para Render
        port=port,
        debug=False      # IMPORTANTE: False en producción
    )
#if __name__ == '__main__':
#    app.run(debug=True, port=8050)
