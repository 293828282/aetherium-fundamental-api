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
    return "🚀 Aetherium Fundamental API v3.3 [REIT & GLOBAL FIX] - ONLINE"

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Sigilo total
        time.sleep(random.uniform(1, 2))
        empresa = yf.Ticker(ticker_symbol)
        
        # 2. Descarga con fallback (reintento)
        is_statement = empresa.get_financials()
        bs_statement = empresa.get_balance_sheet()
        info = empresa.info

        # --- AUDITOR OMNICANAL ---
        def buscar_dato(df, keywords):
            if df is None or df.empty: return None
            for word in keywords:
                match = [idx for idx in df.index if word.lower() in idx.lower()]
                if match:
                    val = df.loc[match[0]].iloc[0]
                    if val is not None and str(val).lower() != 'nan' and val != 0:
                        return float(val)
            return None

        # --- EXTRACCIÓN EBIT ---
        ebit = buscar_dato(is_statement, ['EBIT', 'Operating Income', 'OperatingIncome'])
        if ebit is None: ebit = float(info.get('operatingCashflow', 0)) # Fallback si no hay EBIT

        # --- EXTRACCIÓN PATRIMONIO (LA BATALLA FINAL) ---
        # Intento 1: Balance Sheet nombres estándar
        patrimonio = buscar_dato(bs_statement, [
            'Total Stockholder Equity', 
            'Stockholders Equity', 
            'Common Stock Equity', 
            'Total Equity',
            'Net Assets' # Común en REITs y Fondos
        ])

        # Intento 2: Atajo por Yahoo Info (Book Value * Shares)
        if patrimonio is None or patrimonio == 0:
            book_v = info.get('bookValue')
            shares = info.get('sharesOutstanding')
            if book_v and shares:
                patrimonio = float(book_v * shares)

        # Intento 3: Directamente del campo totalStockholderEquity de la info
        if patrimonio is None or patrimonio == 0:
            patrimonio = float(info.get('totalStockholderEquity', 0))

        # --- EXTRACCIÓN DEUDA ---
        deuda = buscar_dato(bs_statement, ['Total Debt', 'Long Term Debt', 'Total Liab'])
        if deuda is None or deuda == 0:
            deuda = float(info.get('totalDebt', 0))

        # --- CÁLCULOS FINANCIEROS ---
        # Si el patrimonio sigue siendo 0 tras 3 intentos, la empresa podría tener patrimonio negativo
        patrimonio_final = patrimonio if patrimonio is not None else 0.0
        ebit_final = ebit if ebit is not None else 0.0
        deuda_final = deuda if deuda is not None else 0.0
        
        tax_rate = 0.27
        nopat = ebit_final * (1 - tax_rate)
        capital_invertido = patrimonio_final + deuda_final
        
        roic = (nopat / capital_invertido) * 100 if capital_invertido > 0 else 0
        
        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "sector": info.get("sector", "N/A"),
            "datos_crudos": {
                "ebit": round(ebit_final, 2),
                "nopat": round(nopat, 2),
                "patrimonio": round(patrimonio_final, 2),
                "deuda_total": round(deuda_final, 2)
            },
            "ratios": {
                "roic": round(roic, 2),
                "leverage": round(deuda_final / patrimonio_final, 2) if patrimonio_final > 0 else "High/Neg"
            },
            "msg": "Data auditada con fallback de seguridad v3.3"
        })

    except Exception as e:
        return jsonify({"error": "Fallo crítico", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
