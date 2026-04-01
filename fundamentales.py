import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

# Ruta de bienvenida para evitar el 404 inicial
@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API [ONLINE] - Usa /api/fundamentales?ticker=AAPL"

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Iniciamos el objeto Ticker
        # NO usamos sesiones complejas esta vez, vamos directo como el código de precios
        empresa = yf.Ticker(ticker_symbol)
        
        # 2. Extraemos la info básica (Ratios ya calculados por Yahoo)
        info = empresa.info
        
        # 3. Extraemos el Balance y el Estado de Resultados
        # Usamos .get_financials() que a veces es más estable que .financials
        is_statement = empresa.get_financials()
        bs_statement = empresa.get_balance_sheet()

        if is_statement.empty or bs_statement.empty:
             return jsonify({"error": "Yahoo no entregó datos contables para este ticker"}), 404

        # --- EXTRACCIÓN DE DATOS PARA RATIOS ---
        # Buscamos las filas por nombre (usamos .get por seguridad)
        ebit = is_statement.loc['EBIT'].iloc[0] if 'EBIT' in is_statement.index else 0
        utilidad_neta = is_statement.loc['Net Income'].iloc[0] if 'Net Income' in is_statement.index else 0
        patrimonio = bs_statement.loc['Total Stockholder Equity'].iloc[0] if 'Total Stockholder Equity' in bs_statement.index else 0
        deuda_total = bs_statement.loc['Total Debt'].iloc[0] if 'Total Debt' in bs_statement.index else info.get('totalDebt', 0)

        # --- CÁLCULOS DE INGENIERÍA COMERCIAL ---
        tax_rate = 0.27
        nopat = float(ebit) * (1 - tax_rate)
        capital_invertido = float(patrimonio) + float(deuda_total)
        
        roic = (nopat / capital_invertido) * 100 if capital_invertido > 0 else 0
        roe = (float(utilidad_neta) / float(patrimonio)) * 100 if patrimonio > 0 else 0

        return jsonify({
            "status": "success",
            "empresa": info.get("longName", ticker_symbol),
            "ticker": ticker_symbol.upper(),
            "datos_crudos": {
                "ebit": float(ebit),
                "utilidad_neta": float(utilidad_neta),
                "patrimonio": float(patrimonio),
                "deuda_total": float(deuda_total)
            },
            "analisis": {
                "nopat": round(nopat, 2),
                "roic_percent": round(roic, 2),
                "roe_percent": round(roe, 2),
                "leverage": round(float(deuda_total)/float(patrimonio), 2) if patrimonio > 0 else 0
            }
        })

    except Exception as e:
        # Si Yahoo nos bloquea la IP de Render, esto nos avisará
        return jsonify({
            "error": "Yahoo Rate Limit",
            "detalle": str(e),
            "msg": "La IP de Render está saturada. Reintenta en 5 min o cambia el ticker."
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
