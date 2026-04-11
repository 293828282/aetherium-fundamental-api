import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- HEADERS DE DISFRAZ ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# 1. MOTOR DE PRECIOS (Tu código original, optimizado para calcular retornos)
def extraccion_silenciosa_precios(ticker, periodo="1y"):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?range={periodo}&interval=1d"
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=10)
        if respuesta.status_code != 200: return None
        
        data = respuesta.json()
        resultado = data['chart']['result'][0]
        precios = resultado['indicators']['quote'][0]['close']
        
        # Limpiamos los None
        precios_limpios = [p for p in precios if p is not None]
        
        if len(precios_limpios) < 2: return None
        
        # Calculamos el retorno del periodo: (Precio Final / Precio Inicial) - 1
        retorno = (precios_limpios[-1] / precios_limpios[0]) - 1
        
        return {
            "precio_actual": round(precios_limpios[-1], 2),
            "retorno": round(retorno, 4)
        }
    except Exception as e:
        print(f"Error en extracción de precios para {ticker}: {e}")
        return None

# 2. MOTOR DE FUNDAMENTALES (La nueva barrera rota)
def extraccion_silenciosa_fundamentales(ticker):
    # Atacamos el endpoint oculto que contiene los EEFF (Income Statement y Balance Sheet)
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=incomeStatementHistory,balanceSheetHistory"
    
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=10)
        if respuesta.status_code != 200: return None
        
        data = respuesta.json()
        result = data.get('quoteSummary', {}).get('result', [])
        if not result: return None
        
        # Navegamos a los reportes más recientes (índice 0)
        bs_data = result[0].get('balanceSheetHistory', {}).get('balanceSheetStatements', [{}])[0]
        is_data = result[0].get('incomeStatementHistory', {}).get('incomeStatementHistory', [{}])[0]
        
        # Función auxiliar para extraer el valor numérico 'raw' de la maraña de Yahoo
        def get_val(diccionario, clave):
            return diccionario.get(clave, {}).get('raw', 0) if clave in diccionario else 0

        # --- EXTRACCIÓN DE CUENTAS ---
        # Balance
        efectivo = get_val(bs_data, 'cash')
        inventarios = get_val(bs_data, 'inventory')
        activo_circulante = get_val(bs_data, 'totalCurrentAssets')
        pasivo_circulante = get_val(bs_data, 'totalCurrentLiabilities')
        pasivos_totales = get_val(bs_data, 'totalLiab')
        deuda_cp = get_val(bs_data, 'shortLongTermDebt')
        deuda_lp = get_val(bs_data, 'longTermDebt')
        patrimonio_neto = get_val(bs_data, 'totalStockholderEquity')
        
        # Estado de Resultados
        ebit = get_val(is_data, 'ebit')
        if ebit == 0: ebit = get_val(is_data, 'operatingIncome') # Fallback
        gastos_intereses = abs(get_val(is_data, 'interestExpense')) # Lo pasamos a positivo
        impuestos = get_val(is_data, 'incomeTaxExpense')
        utilidad_neta = get_val(is_data, 'netIncome')

        # --- CÁLCULO DE COSTO DE DEUDA (Kd) ---
        deuda_total = deuda_cp + deuda_lp
        kd = (gastos_intereses / deuda_total) if deuda_total > 0 else 0

        return {
            "estado_situacion": {
                "efectivo_y_equivalentes": efectivo,
                "inventarios": inventarios,
                "activo_circulante": activo_circulante,
                "pasivo_circulante": pasivo_circulante,
                "pasivos_totales": pasivos_totales,
                "deuda_financiera_cp": deuda_cp,
                "deuda_financiera_lp": deuda_lp,
                "patrimonio_neto": patrimonio_neto
            },
            "estado_resultados": {
                "utilidad_operativa_ebit": ebit,
                "gastos_por_intereses": gastos_intereses,
                "gasto_impuesto_renta": impuestos,
                "utilidad_neta": utilidad_neta
            },
            "variables_calculadas": {
                "tasa_costo_deuda_kd": round(kd, 4)
            }
        }
    except Exception as e:
        print(f"Error en extracción de fundamentales para {ticker}: {e}")
        return None

@app.route('/')
def home():
    return jsonify({"status": "Motor Universal Activo", "metodo": "Extracción Quirúrgica Directa (Precios + EEFF)"})

@app.route('/api/datos', methods=['GET', 'POST'])
def obtener_datos():
    if request.method == 'POST':
        data = request.get_json() or {}
        ticker = data.get('ticker', 'AAPL')
        ticker_mercado = data.get('benchmark', '^GSPC') # S&P 500 por defecto
        ticker_rf = data.get('risk_free', '^TNX') # Bono del Tesoro a 10 años por defecto
        periodo = data.get('periodo', '1y')
    else:
        ticker = request.args.get('ticker', 'AAPL')
        ticker_mercado = request.args.get('benchmark', '^GSPC')
        ticker_rf = request.args.get('risk_free', '^TNX')
        periodo = request.args.get('periodo', '1y')

    ticker = ticker.upper().strip()

    # 1. Extracción de Fundamentales de la Empresa
    fundamentales = extraccion_silenciosa_fundamentales(ticker)
    
    # 2. Extracción de Variables de Mercado
    datos_activo = extraccion_silenciosa_precios(ticker, periodo)
    datos_mercado = extraccion_silenciosa_precios(ticker_mercado, periodo)
    datos_rf = extraccion_silenciosa_precios(ticker_rf, periodo) # ^TNX ya viene en porcentaje directo (ej: 4.2 = 4.2%)

    if not fundamentales or not datos_activo:
        return jsonify({"error": f"Fallo al extraer la data profunda de {ticker}."}), 404

    # Procesamos el Risk Free Rate (si ^TNX es 4.25, significa 4.25% anual, lo pasamos a decimal 0.0425)
    rf_rate = (datos_rf['precio_actual'] / 100) if datos_rf else 0.04

    # Armamos la estructura final exacta que pediste
    payload = {
        "ticker": ticker,
        "cuentas_estado_situacion": fundamentales["estado_situacion"],
        "cuentas_estado_resultados": fundamentales["estado_resultados"],
        "variables_mercado": {
            "retorno_historico_activo_Ri": datos_activo["retorno"],
            "retorno_historico_mercado_Rm": datos_mercado["retorno"] if datos_mercado else 0.10,
            "tasa_libre_riesgo_Rf": round(rf_rate, 4),
            "tasa_costo_deuda_Kd": fundamentales["variables_calculadas"]["tasa_costo_deuda_kd"]
        }
    }

    return jsonify({
        "status": "success",
        "datos": payload
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
