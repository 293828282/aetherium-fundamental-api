import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os
import threading

app = Flask(__name__)
CORS(app)

# EL CANDADO: Obliga al servidor a atender a los clientes de uno en uno
# Esto evita el error 429 (Too Many Requests) si el frontend hace peticiones simultáneas.
api_lock = threading.Lock()

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v8.0 [ANTI-BLOCK & LOCK FIX] - ONLINE"

@app.route('/api/datos', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    periodo = request.args.get('periodo', '1y') 
    
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # Aquí empieza la fila de espera para proteger la conexión
        with api_lock:
            # Pausa obligatoria para simular comportamiento humano
            time.sleep(random.uniform(1.0, 2.5))
            
            # Dejamos que yfinance use su propio sistema curl_cffi internamente
            empresa = yf.Ticker(ticker_symbol)
            
            yf_period = periodo
            if periodo not in ['1mo', '3mo', '6mo', '1y', '5y']: 
                yf_period = '5y'

            # 1. EXTRACCIÓN DE HISTORIAL BLINDADA (Con 3 reintentos)
            hist = None
            for intento in range(3):
                try:
                    hist = empresa.history(period=yf_period)
                    if not hist.empty:
                        break
                except Exception as e:
                    print(f"Fallo historia {ticker_symbol} intento {intento}: {e}")
                    time.sleep(2)
            
            datos_historicos = []
            if hist is not None and not hist.empty:
                for index, row in hist.iterrows():
                    datos_historicos.append({
                        "Fecha": index.strftime('%Y-%m-%d'),
                        "Cierre": float(row['Close'])
                    })

            # 2. EXTRACCIÓN DE INFO BLINDADA (Evita el JSONDecodeError / Expecting value)
            info = {}
            try:
                info = empresa.info
            except Exception as e:
                print(f"Yahoo bloqueó la extracción de info para {ticker_symbol}: {e}")
                # Si falla, info se queda como un diccionario vacío en lugar de romper el servidor

            # Si info viene vacío porque Yahoo bloqueó, asignamos 0 a todo.
            # El Frontend de Aetherium detectará los 0s o el arreglo vacío y activará el Fallback Matemático solo.
            ebit = info.get('operatingCashflow', 0) if isinstance(info, dict) else 0
            deuda = info.get('totalDebt', 0) if isinstance(info, dict) else 0
            
            patrimonio = 0
            if isinstance(info, dict):
                book_v = info.get('bookValue')
                shares = info.get('sharesOutstanding')
                if book_v is not None and shares is not None:
                    try:
                        patrimonio = float(book_v) * float(shares)
                    except ValueError:
                        patrimonio = float(info.get('totalStockholderEquity', 0))

        # RESPUESTA LIMPIA SIEMPRE
        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol) if isinstance(info, dict) else ticker_symbol,
            "datos": datos_historicos,
            "fundamentales": {
                "ebit": round(ebit if ebit else 0, 2),
                "patrimonio": round(patrimonio if patrimonio else 0, 2),
                "deuda_total": round(deuda if deuda else 0, 2)
            }
        })

    except Exception as e:
        # Solo llegará aquí si hay un error real de sintaxis en Python
        return jsonify({"error": "Fallo critico en la API", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
