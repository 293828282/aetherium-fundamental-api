import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os
import threading

app = Flask(__name__)
CORS(app)

# Candado para evitar que Yahoo nos bloquee por exceso de peticiones
api_lock = threading.Lock()

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v9.0 [FULL RATIOS + ANTI-BLOCK] - ONLINE"

@app.route('/api/datos', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    periodo = request.args.get('periodo', '1y') 
    
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        with api_lock:
            # Pausa de seguridad
            time.sleep(random.uniform(1.0, 2.5))
            
            empresa = yf.Ticker(ticker_symbol)
            
            yf_period = periodo
            if periodo not in ['1mo', '3mo', '6mo', '1y', '5y']: 
                yf_period = '5y'

            # 1. EXTRACCIÓN DE HISTORIAL (Para los gráficos y Markowitz)
            hist = None
            for intento in range(3):
                try:
                    hist = empresa.history(period=yf_period)
                    if not hist.empty:
                        break
                except Exception as e:
                    time.sleep(2)
            
            datos_historicos = []
            if hist is not None and not hist.empty:
                for index, row in hist.iterrows():
                    datos_historicos.append({
                        "Fecha": index.strftime('%Y-%m-%d'),
                        "Cierre": float(row['Close'])
                    })

            # 2. EXTRACCIÓN DE FUNDAMENTALES Y RATIOS
            info = {}
            try:
                info = empresa.info
            except Exception as e:
                print(f"Yahoo bloqueó info para {ticker_symbol}: {e}")

            # Variables Base Seguras
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

            # Cálculos Estructurales (NOPAT, ROIC, Leverage)
            tax_rate = 0.27
            nopat = ebit * (1 - tax_rate)
            capital_invertido = patrimonio + deuda
            roic = (nopat / capital_invertido) * 100 if capital_invertido > 0 else 0
            leverage = (deuda / patrimonio) if patrimonio > 0 else 0

            # Extracción del Diccionario Extendido
            if isinstance(info, dict):
                ratios_ext = {
                    "liquidez_corriente": info.get('currentRatio'),
                    "prueba_acida": info.get('quickRatio'),
                    "roe": round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else None,
                    "roa": round(info.get('returnOnAssets', 0) * 100, 2) if info.get('returnOnAssets') else None,
                    "ros": round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else None,
                    "beta": round(info.get('beta', 0), 2) if info.get('beta') else None,
                    "ebitda": info.get('ebitda'),
                    "ventas": info.get('totalRevenue'),
                    "utilidad_neta": info.get('netIncome')
                }
            else:
                ratios_ext = {k: None for k in ["liquidez_corriente", "prueba_acida", "roe", "roa", "ros", "beta", "ebitda", "ventas", "utilidad_neta"]}

        # 3. RESPUESTA JSON COMPLETA
        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol) if isinstance(info, dict) else ticker_symbol,
            "datos": datos_historicos,
            "datos_crudos": {
                "ebit": round(ebit if ebit else 0, 2),
                "nopat": round(nopat, 2),
                "patrimonio": round(patrimonio if patrimonio else 0, 2),
                "deuda_total": round(deuda if deuda else 0, 2),
                "ventas": ratios_ext["ventas"],
                "utilidad_neta": ratios_ext["utilidad_neta"]
            },
            "ratios": {
                "roic": round(roic, 2),
                "leverage": round(leverage, 2) if leverage else "High/Neg",
                "razon_corriente": ratios_ext["liquidez_corriente"],
                "prueba_acida": ratios_ext["prueba_acida"],
                "roe": ratios_ext["roe"],
                "roa": ratios_ext["roa"],
                "ros": ratios_ext["ros"],
                "beta": ratios_ext["beta"],
                "ebitda": ratios_ext["ebitda"]
            }
        })

    except Exception as e:
        return jsonify({"error": "Fallo critico en la API", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
