import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os

app = Flask(__name__)
CORS(app)

# Disfraces de navegación para mitigar el Rate Limit de Yahoo en Render
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
        return jsonify({"error": "Ticker no proporcionado"}), 400

    try:
        # Simulación de retardo humano para reducir bloqueos
        time.sleep(random.uniform(1.5, 3))
        empresa = yf.Ticker(ticker_symbol)
        
        # Extraemos el diccionario .info (contiene la mayoría de los ratios procesados)
        info = empresa.info
        
        # Estructura del JSON según los requerimientos del colega
        return jsonify({
            "status": "success",
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "sector": info.get("sector", "N/A"),
            "analisis_fundamental": {
                "liquidez": {
                    "razon_corriente": info.get('currentRatio'),
                    "prueba_acida": info.get('quickRatio'),
                    "ratio_efectivo": info.get('cashRatio') # Si está disponible
                },
                "rentabilidad": {
                    "roe_percent": round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else None,
                    "roa_percent": round(info.get('returnOnAssets', 0) * 100, 2) if info.get('returnOnAssets') else None,
                    "ros_margen_neto": round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else None,
                    "roic_percent": round(info.get('returnOnCapital', 0) * 100, 2) if info.get('returnOnCapital') else None
                },
                "solvencia": {
                    "leverage_de": info.get('debtToEquity'),
                    "deuda_capital": info.get('debtToCapital'), # Si está disponible
                    "cobertura_intereses": info.get('earningsLow') # Fallback o campo específico si existe
                },
                "mercado": {
                    "beta": info.get('beta'),
                    "ebitda": info.get('ebitda'),
                    "revenue_total": info.get('totalRevenue'),
                    "utilidad_neta": info.get('netIncomeToCommon')
                }
            },
            "metadata": {
                "currency": info.get("financialCurrency", "USD"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        })

    except Exception as e:
        # El error "Too Many Requests" suele venir de aquí si Yahoo bloquea la IP
        return jsonify({"error": "Fallo en la extracción", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
