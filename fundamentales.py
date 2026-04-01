import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os

app = Flask(__name__)
CORS(app)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v3.2 [OMEGA] - ONLINE"

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Sigilo
        time.sleep(random.uniform(1, 2))
        empresa = yf.Ticker(ticker_symbol)
        
        # 2. Descarga de datos
        is_statement = empresa.get_financials()
        bs_statement = empresa.get_balance_sheet()
        info = empresa.info

        # --- FUNCIÓN AUDITORA SUPREMA ---
        def buscar_valor(df, keywords):
            if df is None or df.empty: return 0.0
            for word in keywords:
                # Buscamos en los índices de las filas
                match = [idx for idx in df.index if word.lower() in idx.lower()]
                if match:
                    val = df.loc[match[0]].iloc[0]
                    # Si el valor es nulo o NaN, seguimos buscando
                    if val is not None and str(val) != 'nan':
                        return float(val)
            return 0.0

        # --- EXTRACCIÓN ---
        ebit = buscar_valor(is_statement, ['EBIT', 'Operating Income', 'OperatingIncome'])
        utilidad_neta = buscar_valor(is_statement, ['Net Income', 'NetIncome'])
        
        # Lista extendida de nombres para el Patrimonio
        patrimonio = buscar_valor(bs_statement, [
            'Total Stockholder Equity', 
            'Stockholders Equity', 
            'Common Stock Equity', 
            'Total Equity'
        ])
        
        # Si sigue en 0, usamos el multiplicador de Yahoo Info
        if patrimonio == 0:
            patrimonio = float(info.get('bookValue', 0) * info.get('sharesOutstanding', 0))
            if patrimonio == 0: patrimonio = float(info.get('totalStockholderEquity', 0))

        # Deuda
        deuda = buscar_valor(bs_statement, ['Total Debt', 'Long Term Debt'])
        if deuda == 0: deuda = float(info.get('totalDebt', 0))

        # --- MATEMÁTICA FINANCIERA ---
        tax_rate = 0.27
        nopat = ebit * (1 - tax_rate)
        
        # ROIC = NOPAT / (Patrimonio + Deuda)
        capital_invertido = patrimonio + deuda
        roic = (nopat / capital_invertido) * 100 if capital_invertido > 0 else 0
        roe = (utilidad_neta / patrimonio) * 100 if patrimonio > 0 else 0

        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "datos_crudos": {
                "ebit": round(ebit, 2),
                "nopat": round(nopat, 2),
                "patrimonio": round(patrimonio, 2),
                "deuda_total": round(deuda, 2)
            },
            "ratios": {
                "roic": round(roic, 2),
                "roe": round(roe, 2),
                "leverage": round(deuda / patrimonio, 2) if patrimonio > 0 else 0
            },
            "msg": "Data secured & audited by Aetherium Omega Engine"
        })

    except Exception as e:
        return jsonify({"error": "Error interno", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
