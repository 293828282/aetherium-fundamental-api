import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os
import threading

app = Flask(__name__)
CORS(app)

# EL TRUCO MÁGICO: El Candado (Lock) se mantiene para ordenar las peticiones
# Esto obliga al servidor a atender a los clientes de uno en uno, evitando el error 429.
api_lock = threading.Lock()

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v7.0 [YFINANCE NATIVE FIX] - ONLINE"

@app.route('/api/datos', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    periodo = request.args.get('periodo', '1y') 
    
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # Hacemos fila con el candado
        with api_lock:
            
            # Pausa obligatoria de 1.5 a 3 segundos ANTES de ir a Yahoo
            time.sleep(random.uniform(1.5, 3.0))
            
            # FIX CRÍTICO: Eliminamos el parametro 'session=session'
            # Dejamos que yfinance use su propio sistema interno antibloqueo (curl_cffi)
            empresa = yf.Ticker(ticker_symbol)
            
            yf_period = periodo
            if periodo not in ['1mo', '3mo', '6mo', '1y', '5y']: 
                yf_period = '5y'

            # SISTEMA DE REINTENTOS
            hist = None
            for intento in range(3):
                try:
                    hist = empresa.history(period=yf_period)
                    if not hist.empty:
                        break # Si trajo datos, rompemos el ciclo y avanzamos
                except:
                    time.sleep(2) # Si falla, descansa 2 segundos y vuelve a intentar
            
            datos_historicos = []
            if hist is not None and not hist.empty:
                for index, row in hist.iterrows():
                    datos_historicos.append({
                        "Fecha": index.strftime('%Y-%m-%d'),
                        "Cierre": float(row['Close'])
                    })

            info = empresa.info

            # Extracción segura de fundamentales
            ebit = info.get('operatingCashflow', 0)
            deuda = info.get('totalDebt', 0)
            
            patrimonio = 0
            book_v = info.get('bookValue')
            shares = info.get('sharesOutstanding')
            if book_v is not None and shares is not None:
                try:
                    patrimonio = float(book_v) * float(shares)
                except ValueError:
                    patrimonio = float(info.get('totalStockholderEquity', 0))

        # --- AQUÍ SE ABRE EL CANDADO PARA LA SIGUIENTE PETICIÓN ---

        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "datos": datos_historicos,
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
