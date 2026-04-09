import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os
import threading

app = Flask(__name__)
CORS(app)

api_lock = threading.Lock()

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v8.0 [ANTI-HTML-BLOCK FIX] - ONLINE"

@app.route('/api/datos', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    periodo = request.args.get('periodo', '1y') 
    
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        with api_lock:
            time.sleep(random.uniform(1.0, 2.5))
            
            empresa = yf.Ticker(ticker_symbol)
            
            yf_period = periodo
            if periodo not in ['1mo', '3mo', '6mo', '1y', '5y']: 
                yf_period = '5y'

            # 1. EXTRACCIÓN DE HISTORIAL BLINDADA
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

            # 2. EXTRACCIÓN DE INFO BLINDADA (Aquí ocurría el error "Expecting value")
            info = {}
            try:
                info = empresa.info
            except Exception as e:
                print(f"Yahoo bloqueó la extracción de info para {ticker_symbol}: {e}")
                # Si falla, info se queda como un diccionario vacío en lugar de romper el servidor

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

        # RESPUESTA LIMPIA SIEMPRE (Si viene vacío, el Frontend Aetherium activará su simulación)
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
        # Solo llegará aquí si hay un error real de Python, no de red.
        return jsonify({"error": "Fallo critico en la API", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
