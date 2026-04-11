import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import pandas as pd
import yfinance as yf

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Candado para proteger las peticiones de yfinance
api_lock = threading.Lock()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

# 1. MOTOR DE PRECIOS Y RETORNOS (Tu método infalible con Requests)
def extraccion_silenciosa_precios(ticker, periodo="1y"):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?range={periodo}&interval=1d"
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=10)
        if respuesta.status_code != 200: return None
        
        data = respuesta.json()
        resultado = data['chart']['result'][0]
        precios = [p for p in resultado['indicators']['quote'][0]['close'] if p is not None]
        
        if len(precios) < 2: return None
        retorno = (precios[-1] / precios[0]) - 1
        return {"precio_actual": round(precios[-1], 2), "retorno": round(retorno, 4)}
    except:
        return None

# 2. MOTOR CONTABLE (El método de la V11 que ya te funcionó)
def extraer_fundamentales_yfinance(ticker_symbol):
    try:
        empresa = yf.Ticker(ticker_symbol)
        is_stmt = pd.DataFrame()
        bs_stmt = pd.DataFrame()
        try:
            is_stmt = empresa.get_financials()
            bs_stmt = empresa.get_balance_sheet()
        except:
            pass

        def find_val(df, keywords):
            if df is None or df.empty: return 0
            for word in keywords:
                matches = [idx for idx in df.index if word.lower() in str(idx).lower()]
                if matches:
                    for match in matches:
                        val = df.loc[match].iloc[0]
                        if pd.notna(val) and str(val).lower() != 'nan' and val != 0:
                            return float(val)
            return 0

        # Mapeo exacto a las cuentas que solicitaste
        return {
            "estado_situacion": {
                "efectivo_y_equivalentes": find_val(bs_stmt, ['cash', 'cash equivalents']),
                "inventarios": find_val(bs_stmt, ['inventory']),
                "activo_circulante": find_val(bs_stmt, ['total current assets', 'current assets']),
                "pasivo_circulante": find_val(bs_stmt, ['total current liabilities', 'current liabilities']),
                "pasivos_totales": find_val(bs_stmt, ['total liabilities', 'total liab']),
                "deuda_financiera_cp": find_val(bs_stmt, ['current debt', 'short term debt']),
                "deuda_financiera_lp": find_val(bs_stmt, ['long term debt']),
                "patrimonio_neto": find_val(bs_stmt, ['stockholders equity', 'total equity', 'common stock equity'])
            },
            "estado_resultados": {
                "utilidad_operativa_ebit": find_val(is_stmt, ['ebit', 'operating income']),
                "gastos_por_intereses": abs(find_val(is_stmt, ['interest expense'])),
                "gasto_impuesto_renta": find_val(is_stmt, ['tax provision', 'income tax']),
                "utilidad_neta": find_val(is_stmt, ['net income', 'net income common'])
            }
        }
    except Exception as e:
        print(f"Error extrayendo contabilidad: {e}")
        return None

@app.route('/')
def home():
    return jsonify({"status": "Motor Híbrido Activo", "metodo": "Precios(Requests) + EEFF(yFinance)"})

@app.route('/api/datos', methods=['GET', 'POST'])
def obtener_datos():
    if request.method == 'POST':
        data = request.get_json() or {}
        ticker = data.get('ticker', 'AAPL')
        ticker_mercado = data.get('benchmark', '^GSPC')
        ticker_rf = data.get('risk_free', '^TNX')
        periodo = data.get('periodo', '1y')
    else:
        ticker = request.args.get('ticker', 'AAPL')
        ticker_mercado = request.args.get('benchmark', '^GSPC')
        ticker_rf = request.args.get('risk_free', '^TNX')
        periodo = request.args.get('periodo', '1y')

    ticker = ticker.upper().strip()

    # Extracción contable blindada
    with api_lock:
        fundamentales = extraer_fundamentales_yfinance(ticker)
    
    # Extracción de mercado veloz
    datos_activo = extraccion_silenciosa_precios(ticker, periodo)
    datos_mercado = extraccion_silenciosa_precios(ticker_mercado, periodo)
    datos_rf = extraccion_silenciosa_precios(ticker_rf, periodo)

    if not fundamentales or not datos_activo:
        return jsonify({"error": f"Fallo al extraer la data profunda de {ticker}."}), 404

    # Tratamiento de tasas (El tesoro ^TNX viene como 4.5, lo pasamos a 0.045)
    rf_rate = (datos_rf['precio_actual'] / 100) if datos_rf else 0.04
    
    # Cálculo del Costo de la Deuda
    deuda_total = fundamentales["estado_situacion"]["deuda_financiera_cp"] + fundamentales["estado_situacion"]["deuda_financiera_lp"]
    kd = (fundamentales["estado_resultados"]["gastos_por_intereses"] / deuda_total) if deuda_total > 0 else 0

    return jsonify({
        "status": "success",
        "datos": {
            "ticker": ticker,
            "cuentas_estado_situacion": fundamentales["estado_situacion"],
            "cuentas_estado_resultados": fundamentales["estado_resultados"],
            "variables_mercado": {
                "retorno_historico_activo_Ri": datos_activo["retorno"],
                "retorno_historico_mercado_Rm": datos_mercado["retorno"] if datos_mercado else 0.10,
                "tasa_libre_riesgo_Rf": round(rf_rate, 4),
                "tasa_costo_deuda_Kd": round(kd, 4)
            }
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
