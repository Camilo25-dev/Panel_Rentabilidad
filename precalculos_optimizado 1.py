# precalculos_optimizado.py - ARCHIVO EJECUTABLE OPTIMIZADO
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
import os
import logging

def generar_precalculos_completos():
    """
    Genera TODOS los cálculos estáticos usando las MISMAS FÓRMULAS del código original
    """
    print("🔄 Generando pre-cálculos optimizados...")
    
    # 1. VERIFICAR ARCHIVOS BASE
    if not os.path.exists('./series_clp.feather'):
        print("❌ Error: No se encontró series_clp.feather")
        return None
    if not os.path.exists('./series_usd.feather'):
        print("❌ Error: No se encontró series_usd.feather")
        return None
    
    # 2. CARGAR DATOS BASE
    print("📂 Cargando datos base...")
    pesos_df = pd.read_feather('./series_clp.feather')
    dolares_df = pd.read_feather('./series_usd.feather')
    
    # Asegurar columna de fechas
    if 'Date' in pesos_df.columns:
        pesos_df.rename(columns={'Date': 'Dates'}, inplace=True)
    if 'Date' in dolares_df.columns:
        dolares_df.rename(columns={'Date': 'Dates'}, inplace=True)
    
    # 3. CREAR ESTRUCTURA DE PRE-CÁLCULOS
    precalculos = {
        'timestamp': datetime.now().isoformat(),
        'fecha_generacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'metadata': {
            'total_fondos_clp': len([col for col in pesos_df.columns if col != 'Dates']),
            'total_fondos_usd': len([col for col in dolares_df.columns if col != 'Dates']),
            'fecha_datos_mas_reciente': max(pesos_df['Dates'].max(), dolares_df['Dates'].max()).isoformat()
        },
        'CLP': {},
        'USD': {}
    }
    
    # 4. PRE-CALCULAR PARA CADA MONEDA
    for moneda, df in [('CLP', pesos_df), ('USD', dolares_df)]:
        print(f"💰 Calculando {moneda}...")
        
        # Solo columnas numéricas (excluir Dates)
        columnas_fondos = [col for col in df.columns if col != 'Dates']
        print(f"   Fondos encontrados: {len(columnas_fondos)}")
        
        # ESTRUCTURA PARA DIFERENTES TIPOS DE CÁLCULOS
        precalculos[moneda] = {
            'rentabilidades_acumuladas': {},      # Para tabla de rentabilidades acumuladas
            'rentabilidades_anualizadas': {},     # Para tabla de rentabilidades anualizadas  
            'rentabilidades_por_año': {},         # Para tabla de rentabilidades por año
            'retornos_mensuales': {},             # Para anexo mensual
            'informe_pdf_completo': {},           # Para informe PDF completo
            'indices_principales': {},            # Para índices principales
            'valor_cuota_actual': {}              # Para valor cuota actual
        }
        
        # PROCESAR CADA FONDO
        for i, codigo_fondo in enumerate(columnas_fondos):
            if (i + 1) % 100 == 0:
                print(f"   Procesando fondo {i+1}/{len(columnas_fondos)}")
            
            try:
                # Obtener datos del fondo con fechas
                precios = df[['Dates', codigo_fondo]].dropna()
                
                if len(precios) > 30:  # Mínimo 30 días de datos
                    # =====================================================================
                    # A) RENTABILIDADES ACUMULADAS (misma fórmula que calcular_rentabilidades)
                    # =====================================================================
                    rentab_acum = calcular_rentabilidades_acumuladas_fondo(precios)
                    if rentab_acum:
                        precalculos[moneda]['rentabilidades_acumuladas'][codigo_fondo] = rentab_acum
                    
                    # =====================================================================
                    # B) RENTABILIDADES ANUALIZADAS (misma fórmula que calcular_rentabilidades_anualizadas)
                    # =====================================================================
                    rentab_anual = calcular_rentabilidades_anualizadas_fondo(precios)
                    if rentab_anual:
                        precalculos[moneda]['rentabilidades_anualizadas'][codigo_fondo] = rentab_anual
                    
                    # =====================================================================
                    # C) RENTABILIDADES POR AÑO (misma fórmula que calcular_rentabilidades_por_año)
                    # =====================================================================
                    rentab_por_año = calcular_rentabilidades_por_año_fondo(precios)
                    if rentab_por_año:
                        precalculos[moneda]['rentabilidades_por_año'][codigo_fondo] = rentab_por_año
                    
                    # =====================================================================
                    # D) RETORNOS MENSUALES (misma fórmula que calcular_retornos_mensuales_completos)
                    # =====================================================================
                    retornos_mens = calcular_retornos_mensuales_fondo(precios)
                    if retornos_mens:
                        precalculos[moneda]['retornos_mensuales'][codigo_fondo] = retornos_mens
                    
                    # =====================================================================
                    # E) INFORME PDF COMPLETO (misma fórmula que calcular_rentabilidades_completas_pdf)
                    # =====================================================================
                    informe_completo = calcular_informe_pdf_completo_fondo(precios)
                    if informe_completo:
                        precalculos[moneda]['informe_pdf_completo'][codigo_fondo] = informe_completo
                    
                    # =====================================================================
                    # F) VALOR CUOTA ACTUAL
                    # =====================================================================
                    valor_actual = float(precios.iloc[-1, 1]) if len(precios) > 0 else None
                    if valor_actual:
                        precalculos[moneda]['valor_cuota_actual'][codigo_fondo] = {
                            'valor': valor_actual,
                            'fecha': precios['Dates'].iloc[-1].isoformat()
                        }
                        
            except Exception as e:
                logging.warning(f"Error procesando fondo {codigo_fondo}: {e}")
                continue
        
        # Mostrar estadísticas
        stats = {
            'acumuladas': len(precalculos[moneda]['rentabilidades_acumuladas']),
            'anualizadas': len(precalculos[moneda]['rentabilidades_anualizadas']),
            'por_año': len(precalculos[moneda]['rentabilidades_por_año']),
            'mensuales': len(precalculos[moneda]['retornos_mensuales']),
            'informe': len(precalculos[moneda]['informe_pdf_completo']),
            'valores': len(precalculos[moneda]['valor_cuota_actual'])
        }
        print(f"   ✅ {moneda}: {stats}")
    
    # 5. GUARDAR PRE-CÁLCULOS
    print("💾 Guardando pre-cálculos...")
    
    # Crear directorio data si no existe
    os.makedirs('./data', exist_ok=True)
    
    with open('./data/precalculos_optimizado.pkl', 'wb') as f:
        pickle.dump(precalculos, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    # Mostrar tamaño del archivo
    tamaño_mb = os.path.getsize('./data/precalculos_optimizado.pkl') / (1024*1024)
    print(f"📁 Archivo creado: ./data/precalculos_optimizado.pkl ({tamaño_mb:.1f}MB)")
    
    return precalculos

# =============================================================================
# FUNCIONES DE CÁLCULO - MISMAS FÓRMULAS QUE EL CÓDIGO ORIGINAL
# =============================================================================

def validar_periodo_disponible(precios, periodo_dias, fecha_actual=None):
    """Misma función que en Pagina.py"""
    if len(precios) == 0:
        return False
    
    if fecha_actual is None:
        fecha_actual = precios['Dates'].max()
    
    fecha_inicio_requerida = fecha_actual - timedelta(days=periodo_dias)
    fecha_inicio_disponible = precios['Dates'].min()
    
    return fecha_inicio_disponible <= fecha_inicio_requerida

def validar_periodo_ytd(precios, fecha_actual=None):
    """Misma función que en Pagina.py"""
    if len(precios) == 0:
        return False
    
    if fecha_actual is None:
        fecha_actual = precios['Dates'].max()
    
    año_anterior = fecha_actual.year - 1
    datos_año_anterior = precios[precios['Dates'].dt.year == año_anterior]
    
    return len(datos_año_anterior) > 0

def calcular_rentabilidad_periodo(precios, dias, precio_actual):
    """Misma función que en Pagina.py e informe_module.py"""
    from datetime import timedelta
    fecha_objetivo = precios['Dates'].max() - timedelta(days=dias)
    precio_pasado = precios[precios['Dates'] >= fecha_objetivo]
    
    if len(precio_pasado) > 0:
        precio_inicial = precio_pasado.iloc[0, 1]
        return ((precio_actual / precio_inicial) - 1) * 100
    return np.nan

def calcular_rentabilidad_ytd(precios, precio_actual):
    """Misma función YTD corregida que en Pagina.py"""
    try:
        fecha_actual = precios['Dates'].max()
        año_actual = fecha_actual.year
        año_anterior = año_actual - 1
        
        # Buscar el ÚLTIMO dato del año anterior (no el primero del año actual)
        datos_año_anterior = precios[precios['Dates'].dt.year == año_anterior]
        
        if len(datos_año_anterior) == 0:
            return np.nan
        
        # Usar iloc[-1] para el último dato del año anterior
        precio_inicio_año = datos_año_anterior.iloc[-1, 1]
        return ((precio_actual / precio_inicio_año) - 1) * 100
        
    except:
        return np.nan

def calcular_rentabilidad_anualizada_periodo(precios, dias):
    """Misma función que en Pagina.py"""
    try:
        if len(precios) < 2:
            return np.nan
            
        fecha_objetivo = precios['Dates'].max() - timedelta(days=dias)
        datos_periodo = precios[precios['Dates'] >= fecha_objetivo]
        
        if len(datos_periodo) == 0:
            return np.nan
            
        precio_inicial = datos_periodo.iloc[0, 1]
        precio_final = precios.iloc[-1, 1]
        
        if pd.isna(precio_inicial) or pd.isna(precio_final) or precio_inicial == 0:
            return np.nan
        
        # Calcular años exactos del período
        años_periodo = dias / 365.25
        
        # Rentabilidad anualizada
        rentabilidad_anualizada = (((precio_final / precio_inicial) ** (1/años_periodo)) - 1) * 100
        
        return rentabilidad_anualizada
        
    except Exception as e:
        return np.nan

def calcular_rentabilidades_acumuladas_fondo(precios):
    """
    Replica exactamente la lógica de calcular_rentabilidades() en Pagina.py
    """
    try:
        if len(precios) == 0:
            return None
            
        precio_actual = precios.iloc[-1, 1]
        fecha_actual = precios['Dates'].max()
        
        resultado = {
            'precio_actual': float(precio_actual),
            'fecha_actual': fecha_actual.isoformat(),
            'TAC': np.random.uniform(0.5, 2.5),  # Simulado como en original
        }
        
        # 1 Mes (30 días)
        if validar_periodo_disponible(precios, 30, fecha_actual):
            resultado['1_mes'] = calcular_rentabilidad_periodo(precios, 30, precio_actual)
        else:
            resultado['1_mes'] = "-"
        
        # 3 Meses (90 días)
        if validar_periodo_disponible(precios, 90, fecha_actual):
            resultado['3_meses'] = calcular_rentabilidad_periodo(precios, 90, precio_actual)
        else:
            resultado['3_meses'] = "-"
        
        # 12 Meses (365 días)
        if validar_periodo_disponible(precios, 365, fecha_actual):
            resultado['12_meses'] = calcular_rentabilidad_periodo(precios, 365, precio_actual)
        else:
            resultado['12_meses'] = "-"
        
        # YTD (validación especial)
        if validar_periodo_ytd(precios, fecha_actual):
            resultado['YTD'] = calcular_rentabilidad_ytd(precios, precio_actual)
        else:
            resultado['YTD'] = "-"
        
        # 3 Años (1095 días)
        if validar_periodo_disponible(precios, 1095, fecha_actual):
            resultado['3_anos'] = calcular_rentabilidad_periodo(precios, 1095, precio_actual)
        else:
            resultado['3_anos'] = "-"
        
        # 5 Años (1825 días)
        if validar_periodo_disponible(precios, 1825, fecha_actual):
            resultado['5_anos'] = calcular_rentabilidad_periodo(precios, 1825, precio_actual)
        else:
            resultado['5_anos'] = "-"
        
        return resultado
        
    except Exception as e:
        return None

def calcular_rentabilidades_anualizadas_fondo(precios):
    """
    Replica exactamente la lógica de calcular_rentabilidades_anualizadas() en Pagina.py
    """
    try:
        if len(precios) == 0:
            return None
            
        precio_actual = precios.iloc[-1, 1]
        precio_inicial = precios.iloc[0, 1]
        fecha_inicial = precios['Dates'].iloc[0]
        fecha_actual_fondo = precios['Dates'].iloc[-1]
        
        años_transcurridos = (fecha_actual_fondo - fecha_inicial).days / 365.25
        
        if años_transcurridos > 0:
            rent_anual_itd = (((precio_actual / precio_inicial) ** (1/años_transcurridos)) - 1) * 100
        else:
            rent_anual_itd = 0
        
        resultado = {
            'precio_actual': float(precio_actual),
            'fecha_actual': fecha_actual_fondo.isoformat(),
            'ITD': rent_anual_itd,
            'años_historial': round(años_transcurridos, 1)
        }
        
        # VALIDACIONES PARA RENTABILIDADES ANUALIZADAS
        fecha_actual = precios['Dates'].max()
        
        # 1 Año
        if validar_periodo_disponible(precios, 365, fecha_actual):
            resultado['1_año'] = calcular_rentabilidad_anualizada_periodo(precios, 365)
        else:
            resultado['1_año'] = "-"
        
        # 3 Años
        if validar_periodo_disponible(precios, 1095, fecha_actual):
            resultado['3_años'] = calcular_rentabilidad_anualizada_periodo(precios, 1095)
        else:
            resultado['3_años'] = "-"
        
        # 5 Años
        if validar_periodo_disponible(precios, 1825, fecha_actual):
            resultado['5_años'] = calcular_rentabilidad_anualizada_periodo(precios, 1825)
        else:
            resultado['5_años'] = "-"
        
        return resultado
        
    except Exception as e:
        return None

def calcular_rentabilidades_por_año_fondo(precios):
    """
    Replica exactamente la lógica de calcular_rentabilidades_por_año() en Pagina.py
    """
    try:
        if len(precios) == 0:
            return None
            
        años = sorted(precios['Dates'].dt.year.unique())
        fecha_inicio_fondo = precios['Dates'].min()
        
        resultado = {
            'precio_actual': float(precios.iloc[-1, 1]),
            'fecha_actual': precios['Dates'].iloc[-1].isoformat(),
            'años_disponibles': años,
            'rentabilidades_anuales': {}
        }
        
        for año in años:
            # VALIDACIÓN: Solo calcular si el fondo ya existía ese año
            inicio_año = pd.Timestamp(año, 1, 1)
            
            if fecha_inicio_fondo <= inicio_año:
                # El fondo ya existía al inicio del año
                datos_año = precios[precios['Dates'].dt.year == año]
                
                if len(datos_año) > 1:
                    precio_inicio = datos_año.iloc[0, 1]
                    precio_fin = datos_año.iloc[-1, 1]
                    
                    if not pd.isna(precio_inicio) and not pd.isna(precio_fin) and precio_inicio != 0:
                        rentabilidad = ((precio_fin / precio_inicio) - 1) * 100
                        resultado['rentabilidades_anuales'][str(año)] = round(rentabilidad, 2)
                    else:
                        resultado['rentabilidades_anuales'][str(año)] = "-"
                else:
                    resultado['rentabilidades_anuales'][str(año)] = "-"
            else:
                # El fondo no existía ese año
                resultado['rentabilidades_anuales'][str(año)] = "-"
        
        return resultado
        
    except Exception as e:
        return None

def obtener_meses_para_calculo(fecha_actual):
    """Misma función que en anexo_mensual_module.py"""
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
    """Misma función que en anexo_mensual_module.py"""
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
        return np.nan

def calcular_rentabilidad_12_meses(precios, fecha_actual):
    """Misma función que en anexo_mensual_module.py"""
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

def calcular_retornos_mensuales_fondo(precios):
    """
    Replica exactamente la lógica de calcular_retornos_mensuales_completos() en anexo_mensual_module.py
    """
    try:
        if len(precios) == 0:
            return None
            
        fecha_actual = precios['Dates'].max()
        
        # Obtener los meses para calcular
        meses_calculo = obtener_meses_para_calculo(fecha_actual)
        
        resultado = {
            'precio_actual': float(precios.iloc[-1, 1]),
            'fecha_actual': fecha_actual.isoformat(),
            'meses_disponibles': [mes_texto for mes_texto, _, _ in meses_calculo],
            'retornos_mensuales': {}
        }
        
        # Calcular rentabilidad para cada mes
        for mes_texto, año, mes_num in meses_calculo:
            rentabilidad_mes = calcular_rentabilidad_mes(precios, año, mes_num)
            resultado['retornos_mensuales'][mes_texto] = rentabilidad_mes
        
        # Calcular rentabilidad 12 meses
        rent_12m = calcular_rentabilidad_12_meses(precios, fecha_actual)
        resultado['retornos_mensuales']['12_M'] = rent_12m
        
        return resultado
        
    except Exception as e:
        return None

def obtener_años_automaticos(fecha_actual):
    """Misma función que en informe_module.py"""
    año_actual = fecha_actual.year
    return año_actual - 1, año_actual - 2

def calcular_rentabilidad_diaria(precios):
    """Misma función que en informe_module.py"""
    try:
        if len(precios) < 2:
            return np.nan
        
        precio_hoy = precios.iloc[-1, 1]
        precio_ayer = precios.iloc[-2, 1]
        
        if pd.isna(precio_hoy) or pd.isna(precio_ayer) or precio_ayer == 0:
            return np.nan
        
        return ((precio_hoy / precio_ayer) - 1) * 100
        
    except Exception as e:
        return np.nan

def calcular_rentabilidad_mtd(precios, fecha_actual):
    """Misma función que en informe_module.py"""
    try:
        mes_actual = fecha_actual.month
        año_actual = fecha_actual.year
        
        # Obtener mes anterior
        if mes_actual == 1:
            mes_anterior = 12
            año_anterior = año_actual - 1
        else:
            mes_anterior = mes_actual - 1
            año_anterior = año_actual
        
        # Filtrar datos del mes anterior
        datos_mes_anterior = precios[
            (precios['Dates'].dt.year == año_anterior) & 
            (precios['Dates'].dt.month == mes_anterior)
        ]
        
        if len(datos_mes_anterior) == 0:
            return np.nan
        
        precio_inicio_mtd = datos_mes_anterior.iloc[-1, 1]
        precio_actual = precios.iloc[-1, 1]
        
        if pd.isna(precio_inicio_mtd) or pd.isna(precio_actual) or precio_inicio_mtd == 0:
            return np.nan
        
        return ((precio_actual / precio_inicio_mtd) - 1) * 100
        
    except Exception as e:
        return np.nan

def calcular_rentabilidad_ytd_mejorado(precios, fecha_actual):
    """Misma función que en informe_module.py"""
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
    """Misma función que en informe_module.py"""
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
    """Misma función que en informe_module.py"""
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
        fecha_inicio_objetivo = fecha_final - timedelta(days=años_objetivo * 365.25)
        
        # Filtrar datos para obtener el precio más cercano a la fecha objetivo
        datos_periodo = precios[precios['Dates'] >= fecha_inicio_objetivo]
        
        if len(datos_periodo) == 0:
            return np.nan
        
        # Precio inicial del período objetivo y precio final
        precio_inicial = datos_periodo.iloc[0, 1]
        precio_final = precios.iloc[-1, 1]
        
        if pd.isna(precio_inicial) or pd.isna(precio_final) or precio_inicial == 0:
            return np.nan
        
        # Calcular rentabilidad simple del período
        rentabilidad_total = (precio_final / precio_inicial) - 1
        
        # Convertir a rentabilidad anualizada usando exactamente los años objetivo
        rentabilidad_anualizada = (((1 + rentabilidad_total) ** (1/años_objetivo)) - 1) * 100
        
        return rentabilidad_anualizada
        
    except Exception as e:
        return np.nan

def calcular_informe_pdf_completo_fondo(precios):
    """
    Replica exactamente la lógica de calcular_rentabilidades_completas_pdf() en informe_module.py
    """
    try:
        if len(precios) == 0:
            return None
            
        fecha_actual = precios['Dates'].max()
        año_1, año_2 = obtener_años_automaticos(fecha_actual)
        precio_actual = precios.iloc[-1, 1]
        
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
        
        resultado = {
            'precio_actual': float(precio_actual),
            'fecha_actual': fecha_actual.isoformat(),
            'TAC': round(np.random.uniform(0.5, 2.5), 2),  # Simulado
            'diaria': rent_diaria,
            '1_mes': rent_1m,
            '3_meses': rent_3m,
            '12_meses': rent_12m,
            'MTD': rent_mtd,
            'YTD': rent_ytd,
            f'año_{año_1}': rent_año_1,
            f'año_{año_2}': rent_año_2,
            '3_años_anual': rent_3a_anual,
            '5_años_anual': rent_5a_anual
        }
        
        return resultado
        
    except Exception as e:
        return None

# =============================================================================
# FUNCIÓN PARA CARGAR PRE-CÁLCULOS
# =============================================================================

def cargar_precalculos():
    """
    Carga los pre-cálculos desde el archivo pickle
    """
    try:
        if os.path.exists('./data/precalculos_optimizado.pkl'):
            with open('./data/precalculos_optimizado.pkl', 'rb') as f:
                return pickle.load(f)
        else:
            print("⚠️ No se encontró archivo de pre-cálculos")
            return None
    except Exception as e:
        print(f"❌ Error cargando pre-cálculos: {e}")
        return None

def obtener_rentabilidades_acumuladas_precalculadas(moneda, codigos_fondos, nombres_fondos):
    """
    Obtiene rentabilidades acumuladas desde pre-cálculos
    Replica el formato exacto de calcular_rentabilidades() en Pagina.py
    """
    precalculos = cargar_precalculos()
    if not precalculos:
        return None
    
    resultados = []
    
    for i, (codigo, nombre) in enumerate(zip(codigos_fondos, nombres_fondos)):
        if codigo in precalculos[moneda]['rentabilidades_acumuladas']:
            datos = precalculos[moneda]['rentabilidades_acumuladas'][codigo]
            
            # Separar fondo y serie del nombre completo
            partes = nombre.split(' - ')
            fondo = partes[0] if len(partes) > 0 else nombre
            serie = partes[1] if len(partes) > 1 else 'N/A'
            
            resultados.append({
                'Fondo': fondo,
                'Serie': serie,
                'TAC': datos['TAC'],
                '1 Mes': datos['1_mes'],
                '3 Meses': datos['3_meses'],
                '12 Meses': datos['12_meses'],
                'YTD': datos['YTD'],
                '3 Años': datos['3_anos'],
                '5 Años': datos['5_anos']
            })
    
    return pd.DataFrame(resultados).round(2) if resultados else pd.DataFrame()

def obtener_rentabilidades_anualizadas_precalculadas(moneda, codigos_fondos, nombres_fondos):
    """
    Obtiene rentabilidades anualizadas desde pre-cálculos
    Replica el formato exacto de calcular_rentabilidades_anualizadas() en Pagina.py
    """
    precalculos = cargar_precalculos()
    if not precalculos:
        return None
    
    resultados = []
    
    for i, (codigo, nombre) in enumerate(zip(codigos_fondos, nombres_fondos)):
        if codigo in precalculos[moneda]['rentabilidades_anualizadas']:
            datos = precalculos[moneda]['rentabilidades_anualizadas'][codigo]
            
            # Separar fondo y serie del nombre completo
            partes = nombre.split(' - ')
            fondo = partes[0] if len(partes) > 0 else nombre
            serie = partes[1] if len(partes) > 1 else 'N/A'
            
            resultados.append({
                'Fondo': fondo,
                'Serie': serie,
                '1 Año': datos['1_año'],
                '3 Años': datos['3_años'],
                '5 Años': datos['5_años'],
                'ITD': datos['ITD'],
                'Años Historial': datos['años_historial']
            })
    
    return pd.DataFrame(resultados).round(2) if resultados else pd.DataFrame()

def obtener_rentabilidades_por_año_precalculadas(moneda, codigos_fondos, nombres_fondos):
    """
    Obtiene rentabilidades por año desde pre-cálculos
    Replica el formato exacto de calcular_rentabilidades_por_año() en Pagina.py
    """
    precalculos = cargar_precalculos()
    if not precalculos:
        return None
    
    resultados = []
    
    for i, (codigo, nombre) in enumerate(zip(codigos_fondos, nombres_fondos)):
        if codigo in precalculos[moneda]['rentabilidades_por_año']:
            datos = precalculos[moneda]['rentabilidades_por_año'][codigo]
            
            # Separar fondo y serie del nombre completo
            partes = nombre.split(' - ')
            fondo = partes[0] if len(partes) > 0 else nombre
            serie = partes[1] if len(partes) > 1 else 'N/A'
            
            # Crear fila base
            fila_resultado = {
                'Fondo': fondo,
                'Serie': serie
            }
            
            # Agregar rentabilidades anuales
            for año_str, rentabilidad in datos['rentabilidades_anuales'].items():
                fila_resultado[año_str] = rentabilidad
            
            resultados.append(fila_resultado)
    
    return pd.DataFrame(resultados) if resultados else pd.DataFrame()

def obtener_retornos_mensuales_precalculados(moneda, codigos_fondos, nombres_fondos):
    """
    Obtiene retornos mensuales desde pre-cálculos
    Replica el formato exacto de calcular_retornos_mensuales_completos() en anexo_mensual_module.py
    """
    precalculos = cargar_precalculos()
    if not precalculos:
        return None
    
    resultados = []
    
    for i, (codigo, nombre) in enumerate(zip(codigos_fondos, nombres_fondos)):
        if codigo in precalculos[moneda]['retornos_mensuales']:
            datos = precalculos[moneda]['retornos_mensuales'][codigo]
            
            # Separar fondo y serie del nombre completo
            partes = nombre.split(' - ')
            fondo = partes[0] if len(partes) > 0 else nombre
            serie = partes[1] if len(partes) > 1 else 'N/A'
            
            # Crear diccionario base del resultado
            resultado = {
                'Fondo': fondo,
                'Serie': serie
            }
            
            # Agregar retornos mensuales
            for mes, rentabilidad in datos['retornos_mensuales'].items():
                resultado[mes] = rentabilidad
            
            resultados.append(resultado)
    
    return pd.DataFrame(resultados).round(2) if resultados else pd.DataFrame()

def obtener_informe_pdf_completo_precalculado(moneda, codigos_fondos, nombres_fondos):
    """
    Obtiene datos completos para informe PDF desde pre-cálculos
    Replica el formato exacto de calcular_rentabilidades_completas_pdf() en informe_module.py
    """
    precalculos = cargar_precalculos()
    if not precalculos:
        return None
    
    resultados = []
    
    for i, (codigo, nombre) in enumerate(zip(codigos_fondos, nombres_fondos)):
        if codigo in precalculos[moneda]['informe_pdf_completo']:
            datos = precalculos[moneda]['informe_pdf_completo'][codigo]
            
            # Separar fondo y serie del nombre completo
            partes = nombre.split(' - ')
            fondo = partes[0] if len(partes) > 0 else nombre
            serie = partes[1] if len(partes) > 1 else 'N/A'
            
            # Obtener años dinámicamente
            año_1_key = None
            año_2_key = None
            for key in datos.keys():
                if key.startswith('año_'):
                    if año_1_key is None:
                        año_1_key = key
                    else:
                        año_2_key = key
                        break
            
            año_1 = año_1_key.split('_')[1] if año_1_key else 'N/A'
            año_2 = año_2_key.split('_')[1] if año_2_key else 'N/A'
            
            resultados.append({
                'Fondo': fondo,
                'Serie': serie,
                'Valor Cuota': round(datos['precio_actual'], 2),
                'TAC': datos['TAC'],
                'Diaria': datos['diaria'],
                '1 Mes': datos['1_mes'],
                '3 Meses': datos['3_meses'],
                '12 Meses': datos['12_meses'],
                'MTD': datos['MTD'],
                'YTD': datos['YTD'],
                f'Año {año_1}': datos.get(año_1_key),
                f'Año {año_2}': datos.get(año_2_key),
                '3 Años*': datos['3_años_anual'],
                '5 Años**': datos['5_años_anual']
            })
    
    return pd.DataFrame(resultados).round(2) if resultados else pd.DataFrame()

def obtener_valor_cuota_actual_precalculado(moneda, codigo_fondo):
    """
    Obtiene valor cuota actual desde pre-cálculos
    """
    precalculos = cargar_precalculos()
    if not precalculos:
        return None
    
    if codigo_fondo in precalculos[moneda]['valor_cuota_actual']:
        return precalculos[moneda]['valor_cuota_actual'][codigo_fondo]
    
    return None

def verificar_precalculos_vigentes():
    """
    Verifica si los pre-cálculos están vigentes (menos de 24 horas)
    """
    try:
        precalculos = cargar_precalculos()
        if not precalculos:
            return False
        
        fecha_generacion = datetime.fromisoformat(precalculos['timestamp'])
        tiempo_transcurrido = datetime.now() - fecha_generacion
        
        # Considerar vigente si tiene menos de 24 horas
        return tiempo_transcurrido.total_seconds() < 24 * 3600
        
    except Exception as e:
        print(f"❌ Error verificando vigencia: {e}")
        return False

def mostrar_estadisticas_precalculos():
    """Muestra estadísticas de los pre-cálculos generados"""
    precalculos = cargar_precalculos()
    if not precalculos:
        print("❌ No hay pre-cálculos disponibles")
        return
        
    print(f"\n📊 ESTADÍSTICAS DE PRE-CÁLCULOS:")
    print(f"   Fecha generación: {precalculos['fecha_generacion']}")
    print(f"   Total fondos CLP: {precalculos['metadata']['total_fondos_clp']}")
    print(f"   Total fondos USD: {precalculos['metadata']['total_fondos_usd']}")
    print(f"   Fecha datos más reciente: {precalculos['metadata']['fecha_datos_mas_reciente']}")
    
    for moneda in ['CLP', 'USD']:
        print(f"\n   {moneda}:")
        for tipo_calculo, datos in precalculos[moneda].items():
            if isinstance(datos, dict):
                print(f"     {tipo_calculo}: {len(datos)} fondos")

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    print("🚀 INICIANDO GENERACIÓN DE PRE-CÁLCULOS OPTIMIZADOS")
    print("="*60)
    
    # Verificar si hay pre-cálculos vigentes
    if verificar_precalculos_vigentes():
        print("✅ Pre-cálculos vigentes encontrados (menos de 24h)")
        print("¿Desea regenerar? (s/N):", end=" ")
        respuesta = input().strip().lower()
        if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
            print("📊 Mostrando estadísticas de pre-cálculos existentes:")
            mostrar_estadisticas_precalculos()
            print("="*60)
            exit(0)
    
    resultado = generar_precalculos_completos()
    
    if resultado:
        print("\n✅ PRE-CÁLCULOS COMPLETADOS EXITOSAMENTE")
        mostrar_estadisticas_precalculos()
        
        # Verificar integridad
        print("\n🔍 VERIFICANDO INTEGRIDAD...")
        vigentes = verificar_precalculos_vigentes()
        print(f"   Vigencia: {'✅ Vigente' if vigentes else '❌ Expirado'}")
        
    else:
        print("\n❌ ERROR EN LA GENERACIÓN DE PRE-CÁLCULOS")
    
    print("="*60)