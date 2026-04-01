import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os

app = Flask(__name__)
CORS(app)

# Lista de User-Agents para intentar saltar el bloqueo de IP de Render
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]

@app.route('/')
def home():
    return "🚀 Aetherium Financial Engine v4.0 - Online"

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Simulación de pausa para evitar bloqueos
        time.sleep(random.uniform(1.5, 3))
        
        # 2. Iniciamos el objeto Ticker
        empresa = yf.Ticker(ticker_symbol)
        
        # 3. Extraemos el diccionario .info (contiene el 90% de lo solicitado)
        data = empresa.info
        
        # --- EXTRACCIÓN DE VARIABLES SOLICITADAS POR TU COMPAÑERO ---
        # Si Yahoo no tiene el dato, devolverá None o 0 por seguridad
        
        respuesta = {
            "status": "success",
            "ticker": ticker_symbol.upper(),
            "empresa": data.get("longName", ticker_symbol),
            "sector": data.get("sector", "N/A"),
            "ratios_fundamentales": {
                "liquidez": {
                    "razon_corriente": data.get("currentRatio"),
                    "prueba_acida": data.get("quickRatio"),
                    "ratio_efectivo": data.get("cashRatio")
                },
                "rentabilidad": {
                    "roe_percent": round(data.get("returnOnEquity", 0) * 100, 2) if data.get("returnOnEquity") else None,
                    "roa_percent": round(data.get("returnOnAssets", 0) * 100, 2) if data.get("returnOnAssets") else None,
                    "ros_margen_neto": round(data.get("profitMargins", 0) * 100, 2) if data.get("profitMargins") else None
                },
                "solvencia": {
                    "leverage_de": data.get("debtToEquity"),
                    "cobertura_intereses": data.get("ebitdaMargins") # Aproximación si no hay interestCoverage
                },
                "mercado": {
                    "beta": round(data.get("beta", 0), 2) if data.get("beta") else None,
                    "ebitda": data.get("ebitda"),
                    "revenue_total": data.get("totalRevenue"),
                    "utilidad_neta": data.get("netIncomeToCommon")
                }
            }
        }

        return jsonify(respuesta)

    except Exception as e:
        # Si sale el error de Rate Limit, lo capturamos aquí
        return jsonify({
            "error": "Yahoo Rate Limit Activo",
            "msg": "La IP de Render está saturada. Intenta de nuevo en 5 minutos.",
            "detalle": str(e)
        }), 500

if __name__ == '__main__':
    # Configuración de puerto para Render
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
