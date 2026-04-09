import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os
import threading
import pandas as pd

app = Flask(__name__)
CORS(app)

api_lock = threading.Lock()

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v11 [RAW DATA EXTRACTOR] - ONLINE"

@app.route('/api/datos', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    periodo = request.args.get('periodo', '1y') 
    
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        with api_lock:
            # Pausa de seguridad humana
            time.sleep(random.uniform(1.0, 2.5))
            empresa = yf.Ticker(ticker_symbol)
            
            # 1. HISTORIAL DE PRECIOS (Motor Estadístico)
            yf_period = periodo if periodo in ['1mo', '3mo', '6mo', '1y', '5y'] else '5y'
            hist = None
            for intento in range(3):
                try:
                    hist = empresa.history(period=yf_period)
                    if not hist.empty: break
                except Exception:
                    time.sleep(2)
            
            datos_historicos = []
            if hist is not None and not hist.empty:
                for index, row in hist.iterrows():
                    datos_historicos.append({"Fecha": index.strftime('%Y-%m-%d'), "Cierre": float(row['Close'])})

            # 2. DESCARGA DE ESTADOS FINANCIEROS
            is_stmt = pd.DataFrame()
            bs_stmt = pd.DataFrame()
            try:
                is_stmt = empresa.get_financials()
                bs_stmt = empresa.get_balance_sheet()
            except Exception:
                pass

            # BÚSQUEDA INTELIGENTE (Fuzzy Match): Encuentra la fila aunque Yahoo le cambie el nombre
            def find_val(df, keywords):
                if df is None or df.empty: return 0
                for word in keywords:
                    # Busca ignorando mayúsculas y espacios
                    matches = [idx for idx in df.index if word.lower() in str(idx).lower()]
                    if matches:
                        # Si encuentra coincidencias, saca el valor del año más reciente (iloc[0])
                        for match in matches:
                            val = df.loc[match].iloc[0]
                            if pd.notna(val) and str(val).lower() != 'nan' and val != 0:
                                return float(val)
                return 0

            # 3. EXTRACCIÓN DE LAS CUENTAS CONTABLES CRUDAS
            net_income = find_val(is_stmt, ['net income', 'net income common'])
            ebit = find_val(is_stmt, ['ebit', 'operating income'])
            revenue = find_val(is_stmt, ['total revenue', 'operating revenue'])
            
            assets = find_val(bs_stmt, ['total assets'])
            equity = find_val(bs_stmt, ['stockholders equity', 'total equity', 'common stock equity'])
            debt = find_val(bs_stmt, ['total debt', 'long term debt'])

            # 4. CAPA DE RESPALDO (Por si Yahoo oculta los Estados Financieros)
            info = {}
            try:
                info = empresa.info
            except Exception:
                pass

            if isinstance(info, dict):
                if debt == 0: debt = float(info.get('totalDebt', 0))
                if revenue == 0: revenue = float(info.get('totalRevenue', 0))
                if net_income == 0: net_income = float(info.get('netIncome', 0))
                if ebit == 0: ebit = float(info.get('operatingCashflow', 0))
                if equity == 0:
                    try:
                        equity = float(info.get('bookValue', 0)) * float(info.get('sharesOutstanding', 0))
                    except:
                        equity = float(info.get('totalStockholderEquity', 0))

        # RESPUESTA LIMPIA Y DIRECTA AL FRONTEND
        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol) if isinstance(info, dict) else ticker_symbol,
            "datos": datos_historicos,
            "datos_crudos": {
                "ebit": ebit,
                "patrimonio": equity,
                "deuda_total": debt,
                "ventas": revenue,
                "utilidad_neta": net_income,
                "activos_totales": assets
            }
        })

    except Exception as e:
        return jsonify({"error": "Fallo critico en la API", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
