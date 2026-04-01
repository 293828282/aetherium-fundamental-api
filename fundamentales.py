import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os

app = Flask(__name__)
CORS(app)

# Lista de agentes para mantener el "Stealth Mode" y evitar bloqueos
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v4.0 [INTEGRATED] - ONLINE"

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Sigilo total para evitar el "Too Many Requests"
        time.sleep(random.uniform(1.5, 3))
        empresa = yf.Ticker(ticker_symbol)
        
        # 2. Descarga de datos
        is_statement = empresa.get_financials()
        bs_statement = empresa.get_balance_sheet()
        info = empresa.info

        # --- AUDITOR OMNICANAL PARA DATOS CRUDOS ---
        def buscar_dato(df, keywords):
            if df is None or df.empty: return None
            for word in keywords:
                match = [idx for idx in df.index if word.lower() in idx.lower()]
                if match:
                    val = df.loc[match[0]].iloc[0]
                    if val is not None and str(val).lower() != 'nan' and val != 0:
                        return float(val)
            return None

        # Extracción de EBIT (Dato base para NOPAT)
        ebit = buscar_dato(is_statement, ['EBIT', 'Operating Income', 'OperatingIncome'])
        if ebit is None: ebit = float(info.get('ebitda', 0)) * 0.8 # Fallback

        # Extracción de Patrimonio
        patrimonio = buscar_dato(bs_statement, [
            'Total Stockholder Equity', 'Stockholders Equity', 'Common Stock Equity', 'Total Equity', 'Net Assets'
        ])
        if patrimonio is None or patrimonio == 0:
            book_v = info.get('bookValue')
            shares = info.get('sharesOutstanding')
            patrimonio = float(book_v * shares) if book_v and shares else float(info.get('totalStockholderEquity', 0))

        # Extracción de Deuda
        deuda = buscar_dato(bs_statement, ['Total Debt', 'Long Term Debt', 'Total Liab'])
        if deuda is None or deuda == 0:
            deuda = float(info.get('totalDebt', 0))

        # --- CÁLCULOS OPERATIVOS ---
        patrimonio_final = patrimonio if patrimonio is not None else 0.0
        ebit_final = ebit if ebit is not None else 0.0
        deuda_final = deuda if deuda is not None else 0.0
        
        tax_rate = 0.27
        nopat = ebit_final * (1 - tax_rate)
        capital_invertido = patrimonio_final + deuda_final
        roic = (nopat / capital_invertido) * 100 if capital_invertido > 0 else 0

        # --- RESPUESTA JSON EXTENDIDA (LO QUE PIDIÓ EL COLEGA) ---
        return jsonify({
            "status": "success",
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "sector": info.get("sector", "N/A"),
            "datos_crudos": {
                "ebit": round(ebit_final, 2),
                "nopat": round(nopat, 2),
                "patrimonio": round(patrimonio_final, 2),
                "deuda_total": round(deuda_final, 2),
                "ventas_totales": info.get('totalRevenue'),
                "utilidad_neta": info.get('netIncome')
            },
            "ratios": {
                "liquidez": {
                    "razon_corriente": info.get('currentRatio'),
                    "prueba_acida": info.get('quickRatio')
                },
                "rentabilidad": {
                    "roic": round(roic, 2),
                    "roe": round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else None,
                    "roa": round(info.get('returnOnAssets', 0) * 100, 2) if info.get('returnOnAssets') else None,
                    "ros": round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else None
                },
                "solvencia": {
                    "leverage": round(deuda_final / patrimonio_final, 2) if patrimonio_final > 0 else "High/Neg",
                    "ebitda": info.get('ebitda')
                },
                "mercado": {
                    "beta": round(info.get('beta', 0), 2) if info.get('beta') else None
                }
            },
            "msg": "Aetherium Full-Stack JSON v4.0"
        })

    except Exception as e:
        return jsonify({"error": "Fallo crítico", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
