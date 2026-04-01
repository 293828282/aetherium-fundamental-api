import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os

app = Flask(__name__)
CORS(app)

# Rotación de identidades para mitigar el bloqueo de IP en Render
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]

@app.route('/')
def home():
    return "🚀 Aetherium Financial Engine v4.0 [INTEGRATED] - ONLINE"

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Sigilo total (Pausa aleatoria ligeramente más larga para evitar el 429)
        time.sleep(random.uniform(2, 4))
        empresa = yf.Ticker(ticker_symbol)
        
        # 2. Descarga de datos (Mantenemos tu lógica de fallback)
        is_statement = empresa.get_financials()
        bs_statement = empresa.get_balance_sheet()
        info = empresa.info

        # --- AUDITOR OMNICANAL (Tu lógica original) ---
        def buscar_dato(df, keywords):
            if df is None or df.empty: return None
            for word in keywords:
                match = [idx for idx in df.index if word.lower() in idx.lower()]
                if match:
                    val = df.loc[match[0]].iloc[0]
                    if val is not None and str(val).lower() != 'nan' and val != 0:
                        return float(val)
            return None

        # Extracción de EBIT
        ebit = buscar_dato(is_statement, ['EBIT', 'Operating Income', 'OperatingIncome'])
        if ebit is None: ebit = float(info.get('ebitda', 0)) * 0.8 

        # Extracción de Patrimonio
        patrimonio = buscar_dato(bs_statement, ['Total Stockholder Equity', 'Stockholders Equity', 'Common Stock Equity', 'Total Equity', 'Net Assets'])
        if patrimonio is None or patrimonio == 0:
            book_v = info.get('bookValue')
            shares = info.get('sharesOutstanding')
            patrimonio = float(book_v * shares) if book_v and shares else float(info.get('totalStockholderEquity', 0))

        # Extracción de Deuda
        deuda = buscar_dato(bs_statement, ['Total Debt', 'Long Term Debt', 'Total Liab'])
        if deuda is None or deuda == 0:
            deuda = float(info.get('totalDebt', 0))

        # --- CÁLCULOS ROIC ---
        tax_rate = 0.27
        nopat = (ebit if ebit else 0) * (1 - tax_rate)
        capital_invertido = (patrimonio if patrimonio else 0) + (deuda if deuda else 0)
        roic = (nopat / capital_invertido) * 100 if capital_invertido > 0 else 0

        # --- RESPUESTA JSON COMPLETA (Lo que pidió tu colega) ---
        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "sector": info.get("sector", "N/A"),
            "datos_financieros": {
                "ebit": round(ebit if ebit else 0, 2),
                "nopat": round(nopat, 2),
                "patrimonio": round(patrimonio if patrimonio else 0, 2),
                "deuda_total": round(deuda if deuda else 0, 2),
                "revenue": info.get('totalRevenue'),
                "net_income": info.get('netIncome')
            },
            "ratios": {
                "liquidez": {
                    "razon_corriente": info.get('currentRatio'),
                    "prueba_acida": info.get('quickRatio'),
                    "ratio_efectivo": info.get('cashRatio')
                },
                "rentabilidad": {
                    "roic": round(roic, 2),
                    "roe": round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else None,
                    "roa": round(info.get('returnOnAssets', 0) * 100, 2) if info.get('returnOnAssets') else None,
                    "ros": round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else None
                },
                "solvencia": {
                    "leverage": round(deuda / patrimonio, 2) if patrimonio and patrimonio > 0 else "N/A",
                    "ebitda": info.get('ebitda')
                },
                "mercado": {
                    "beta": round(info.get('beta', 0), 2) if info.get('beta') else None
                }
            },
            "msg": "Aetherium Full-Stack Intelligence Unit"
        })

    except Exception as e:
        return jsonify({"error": "Fallo crítico", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
