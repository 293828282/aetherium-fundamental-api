import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os
import requests

app = Flask(__name__)
CORS(app)

# Session para simular un navegador real y evitar el "Too Many Requests"
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
})

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v3.4 [ANTI-BLOCK] - ONLINE"

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Sigilo y delay aleatorio
        time.sleep(random.uniform(2, 4))
        
        # 2. Pasamos la session al Ticker (esto es clave para el bloqueo)
        empresa = yf.Ticker(ticker_symbol, session=session)
        
        # 3. Intentamos traer .info primero (es más ligero)
        info = empresa.info
        is_statement = empresa.get_financials()
        bs_statement = empresa.get_balance_sheet()

        # --- TU LÓGICA DE AUDITOR (BUSCAR DATO) ---
        def buscar_dato(df, keywords):
            if df is None or df.empty: return None
            for word in keywords:
                match = [idx for idx in df.index if word.lower() in idx.lower()]
                if match:
                    val = df.loc[match[0]].iloc[0]
                    if val is not None and str(val).lower() != 'nan' and val != 0:
                        return float(val)
            return None

        # --- DATOS PARA EL ROIC ---
        ebit = buscar_dato(is_statement, ['EBIT', 'Operating Income'])
        if ebit is None: ebit = float(info.get('ebitda', 0)) * 0.8

        patrimonio = buscar_dato(bs_statement, ['Total Stockholder Equity', 'Common Stock Equity', 'Total Equity'])
        if patrimonio is None:
            book_v = info.get('bookValue')
            shares = info.get('sharesOutstanding')
            patrimonio = float(book_v * shares) if book_v and shares else float(info.get('totalStockholderEquity', 0))

        deuda = buscar_dato(bs_statement, ['Total Debt', 'Long Term Debt'])
        if deuda is None: deuda = float(info.get('totalDebt', 0))

        # --- CÁLCULOS DE INGENIERÍA COMERCIAL ---
        tax_rate = 0.27
        nopat = (ebit if ebit else 0) * (1 - tax_rate)
        cap_invertido = (patrimonio if patrimonio else 0) + (deuda if deuda else 0)
        roic = (nopat / cap_invertido) * 100 if cap_invertido > 0 else 0

        # --- RESPUESTA JSON CON LAS VARIABLES DE TU COLEGA ---
        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "sector": info.get("sector", "N/A"),
            "analisis": {
                "liquidez": {
                    "razon_corriente": info.get('currentRatio'),
                    "prueba_acida": info.get('quickRatio')
                },
                "rentabilidad": {
                    "roe": round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else None,
                    "roa": round(info.get('returnOnAssets', 0) * 100, 2) if info.get('returnOnAssets') else None,
                    "ros_margen_neto": round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else None,
                    "roic": round(roic, 2)
                },
                "solvencia": {
                    "leverage": round(deuda / patrimonio, 2) if patrimonio and patrimonio > 0 else "N/A",
                    "ebitda": info.get('ebitda')
                },
                "mercado": {
                    "beta": round(info.get('beta', 0), 2) if info.get('beta') else None,
                    "ventas": info.get('totalRevenue')
                }
            }
        })

    except Exception as e:
        # Si Yahoo nos sigue bloqueando, devolvemos un mensaje claro
        if "429" in str(e) or "Too Many Requests" in str(e):
            return jsonify({"error": "Yahoo Rate Limit", "detalle": "La IP de Render está bloqueada temporalmente. Espera 10 minutos."}), 500
        return jsonify({"error": "Fallo crítico", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
