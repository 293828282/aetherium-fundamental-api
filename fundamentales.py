import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os

app = Flask(__name__)
CORS(app)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v4.1 [OFFICIAL FIX] - ONLINE"

# --- RUTA CORREGIDA: Ahora es /api/datos para conectar con el Frontend ---
@app.route('/api/datos', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    # Manejo de la variable 'periodo' para compatibilidad con el frontend, aunque yfinance usa periodos propios
    periodo = request.args.get('periodo', '1y') 
    
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Sigilo total para evitar bloqueos
        time.sleep(random.uniform(1.0, 2.5))
        empresa = yf.Ticker(ticker_symbol)
        
        # 2. Descarga de datos históricos de precios (Crucial para el Dashboard)
        # Mapeamos el periodo del frontend al formato de yfinance
        yf_period = periodo
        if periodo == '1mo': yf_period = '1mo'
        elif periodo == '3mo': yf_period = '3mo'
        elif periodo == '6mo': yf_period = '6mo'
        elif periodo == '1y': yf_period = '1y'
        elif periodo == '3y': yf_period = '5y' # Descargamos más por seguridad
        elif periodo == '5y': yf_period = '5y'
        else: yf_period = '5y' # Por defecto forzamos 5y para el LOCF del frontend

        hist = empresa.history(period=yf_period)
        
        datos_historicos = []
        if not hist.empty:
            for index, row in hist.iterrows():
                datos_historicos.append({
                    "Fecha": index.strftime('%Y-%m-%d'),
                    "Cierre": float(row['Close'])
                })

        # 3. Descarga de Fundamentales (Mantenemos tu lógica original por si la usas en otro lado)
        info = empresa.info
        try:
            is_statement = empresa.get_financials()
            bs_statement = empresa.get_balance_sheet()
        except:
            is_statement = None
            bs_statement = None

        # Función de búsqueda de datos
        def buscar_dato(df, keywords):
            if df is None or df.empty: return None
            for word in keywords:
                match = [idx for idx in df.index if word.lower() in str(idx).lower()]
                if match:
                    val = df.loc[match[0]].iloc[0]
                    if val is not None and str(val).lower() != 'nan' and val != 0:
                        return float(val)
            return None

        # Extracción EBIT
        ebit = buscar_dato(is_statement, ['EBIT', 'Operating Income', 'OperatingIncome'])
        if ebit is None: ebit = float(info.get('operatingCashflow', 0))

        # Extracción Patrimonio con blindaje
        patrimonio = buscar_dato(bs_statement, ['Total Stockholder Equity', 'Stockholders Equity', 'Common Stock Equity', 'Total Equity', 'Net Assets'])
        if patrimonio is None or patrimonio == 0:
            book_v = info.get('bookValue')
            shares = info.get('sharesOutstanding')
            if book_v is not None and shares is not None:
                try:
                    patrimonio = float(book_v) * float(shares)
                except ValueError:
                    patrimonio = 0.0
        if patrimonio is None or patrimonio == 0:
            patrimonio = float(info.get('totalStockholderEquity', 0))

        # Extracción Deuda
        deuda = buscar_dato(bs_statement, ['Total Debt', 'Long Term Debt', 'Total Liab'])
        if deuda is None or deuda == 0:
            deuda = float(info.get('totalDebt', 0))

        # --- RESPUESTA ESTRUCTURADA ---
        # El frontend Aetherium busca la llave "datos" que contiene el arreglo de precios
        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "datos": datos_historicos,  # <--- ESTO ES LO QUE LEE EL DASHBOARD HTML/REACT
            "fundamentales": {
                "ebit": round(ebit if ebit else 0, 2),
                "patrimonio": round(patrimonio if patrimonio else 0, 2),
                "deuda_total": round(deuda if deuda else 0, 2)
            }
        })

    except Exception as e:
        return jsonify({"error": "Fallo critico en la API", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
