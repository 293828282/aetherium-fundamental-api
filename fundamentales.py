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

api_lock = threading.Lock()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def extraccion_silenciosa_precios(ticker, periodo="1y"):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?range={periodo}&interval=1d"
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=10)
        if respuesta.status_code != 200: return None
        
        data = respuesta.json()
        resultado = data['chart']['result'][0]
        fechas = resultado['timestamp']
        precios_raw = resultado['indicators']['quote'][0]['close']
        
        historial = []
        for t, p in zip(fechas, precios_raw):
            if p is not None:
                fecha_real = datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')
                historial.append({"Fecha": fecha_real, "Cierre": round(p, 4)})
                
        if len(historial) < 2: return None
        retorno = (historial[-1]["Cierre"] / historial[0]["Cierre"]) - 1
        
        return {
            "precio_actual": historial[-1]["Cierre"], 
            "retorno": round(retorno, 4),
            "historial_diario": historial
        }
    except Exception as e:
        print(f"Error en extraccion de precios para {ticker}: {e}")
        return None

def extraer_fundamentales_yfinance(ticker_symbol):
    try:
        empresa = yf.Ticker(ticker_symbol)
        info = {}
        try: info = empresa.info
        except: pass

        is_stmt = pd.DataFrame()
        bs_stmt = pd.DataFrame()
        try:
            is_stmt = empresa.financials
            bs_stmt = empresa.balance_sheet
        except: pass

        def find_val(df, keywords):
            if df is None or df.empty: return 0
            for word in keywords:
                matches = [idx for idx in df.index if word.lower() in str(idx).lower()]
                for match in matches:
                    fila = df.loc[match]
                    if isinstance(fila, pd.DataFrame): fila = fila.iloc[0]
                    for val in fila.values:
                        if pd.notna(val) and str(val).lower() != 'nan' and val != 0:
                            return float(val)
            return 0

        efectivo = find_val(bs_stmt, ['cash', 'cash equivalents']) or float(info.get('totalCash', 0))
        inventarios = find_val(bs_stmt, ['inventory'])
        activo_circulante = find_val(bs_stmt, ['total current assets', 'current assets'])
        pasivo_circulante = find_val(bs_stmt, ['total current liabilities', 'current liabilities'])
        pasivos_totales = find_val(bs_stmt, ['total liabilities', 'total liab']) or float(info.get('totalLiabilitiesNetMinorityInterest', 0))
        deuda_cp = find_val(bs_stmt, ['current debt', 'short term debt'])
        deuda_lp = find_val(bs_stmt, ['long term debt'])
        
        patrimonio = find_val(bs_stmt, ['stockholders equity', 'total equity', 'common stock equity'])
        if patrimonio == 0: 
            patrimonio = float(info.get('totalStockholderEquity', info.get('bookValue', 0) * info.get('sharesOutstanding', 0)))

        ebit = find_val(is_stmt, ['ebit', 'operating income']) or float(info.get('operatingCashflow', 0))
        gastos_int = abs(find_val(is_stmt, ['interest expense', 'interest income expense']))
        impuestos = find_val(is_stmt, ['tax provision', 'income tax'])
        utilidad_neta = find_val(is_stmt, ['net income', 'net income common stockholders']) or float(info.get('netIncome', 0))

        return {
            "estado_situacion": {
                "efectivo_y_equivalentes": efectivo, "inventarios": inventarios, "activo_circulante": activo_circulante,
                "pasivo_circulante": pasivo_circulante, "pasivos_totales": pasivos_totales,
                "deuda_financiera_cp": deuda_cp, "deuda_financiera_lp": deuda_lp, "patrimonio_neto": patrimonio
            },
            "estado_resultados": {
                "utilidad_operativa_ebit": ebit, "gastos_por_intereses": gastos_int,
                "gasto_impuesto_renta": impuestos, "utilidad_neta": utilidad_neta
            }
        }
    except Exception as e:
        print(f"Error en extraccion contable para {ticker_symbol}: {e}")
        return None

@app.route('/')
def home():
    return jsonify({"status": "Motor Hibrido Activo", "metodo": "Analisis Cuantitativo y Fundamental"})

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

    with api_lock:
        fundamentales = extraer_fundamentales_yfinance(ticker)
    
    # Protocolo de contingencia para datos contables inexistentes o iliquidos
    if not fundamentales:
        fundamentales = {
            "estado_situacion": {
                "efectivo_y_equivalentes": 0, "inventarios": 0, "activo_circulante": 0, 
                "pasivo_circulante": 0, "pasivos_totales": 0, "deuda_financiera_cp": 0, 
                "deuda_financiera_lp": 0, "patrimonio_neto": 0
            },
            "estado_resultados": {
                "utilidad_operativa_ebit": 0, "gastos_por_intereses": 0, 
                "gasto_impuesto_renta": 0, "utilidad_neta": 0
            }
        }

    datos_activo = extraccion_silenciosa_precios(ticker, periodo)
    datos_mercado = extraccion_silenciosa_precios(ticker_mercado, periodo)
    datos_rf = extraccion_silenciosa_precios(ticker_rf, periodo)

    if not datos_activo:
        return jsonify({"error": f"El ticker {ticker} no posee un historial de precios valido en el periodo seleccionado."}), 404

    rf_rate = (datos_rf['precio_actual'] / 100) if datos_rf else 0.04
    deuda_total = fundamentales["estado_situacion"]["deuda_financiera_cp"] + fundamentales["estado_situacion"]["deuda_financiera_lp"]
    kd = (fundamentales["estado_resultados"]["gastos_por_intereses"] / deuda_total) if deuda_total > 0 else 0

    return jsonify({
        "status": "success",
        "datos": {
            "ticker": ticker,
            "historial_precios": datos_activo["historial_diario"],
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
