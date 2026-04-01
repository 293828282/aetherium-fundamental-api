import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os

app = Flask(__name__)
CORS(app)

# Disfraces de navegación para evitar bloqueos de IP
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

@app.route('/')
def home():
    return "🚀 Aetherium Financial Engine v4.0 [FULL-STACK] - ONLINE"

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Sigilo y simulación humana
        time.sleep(random.uniform(1, 2))
        empresa = yf.Ticker(ticker_symbol)
        
        # 2. Acceso a los diccionarios de datos
        info = empresa.info
        # Traemos también los estados financieros crudos por si acaso
        is_statement = empresa.financials 

        # --- EXTRACCIÓN DE RATIOS SOLICITADOS (Directo desde .info) ---
        # Estos son los que te pidió tu colega para completar la tabla
        ratios_info = {
            "razon_corriente": info.get('currentRatio'),
            "prueba_acida": info.get('quickRatio'),
            "roe": info.get('returnOnEquity'),
            "roa": info.get('returnOnAssets'),
            "ros_margen_neto": info.get('profitMargins'),
            "beta": info.get('beta'),
            "ebitda": info.get('ebitda'),
            "revenue_total": info.get('totalRevenue'),
            "net_income": info.get('netIncome'),
            "dividend_yield": info.get('dividendYield'),
            "payout_ratio": info.get('payoutRatio')
        }

        # --- FALLBACK PARA DATOS CRUDOS (Auditoría) ---
        def buscar_en_tabla(df, keywords):
            if df is None or df.empty: return 0.0
            for word in keywords:
                match = [idx for idx in df.index if word.lower() in idx.lower()]
                if match:
                    val = df.loc[match[0]].iloc[0]
                    return float(val) if val and str(val) != 'nan' else 0.0
            return 0.0

        # EBIT y NOPAT (Para el ROIC que ya tenías funcionando)
        ebit = buscar_en_tabla(is_statement, ['EBIT', 'Operating Income'])
        if ebit == 0: ebit = float(info.get('ebitda', 0)) * 0.8 # Estimación si falla todo

        tax_rate = 0.27
        nopat = ebit * (1 - tax_rate)
        
        # Patrimonio y Deuda (Cálculo de Leverage)
        patrimonio = float(info.get('totalStockholderEquity') or (info.get('bookValue', 0) * info.get('sharesOutstanding', 0)))
        deuda = float(info.get('totalDebt', 0))
        
        capital_invertido = patrimonio + deuda
        roic_calculado = (nopat / capital_invertido) * 100 if capital_invertido > 0 else 0

        # 3. Respuesta JSON Maestra
        return jsonify({
            "status": "success",
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "sector": info.get("sector", "N/A"),
            "industria": info.get("industry", "N/A"),
            # Bloque de Ratios (Lo que pidió tu colega)
            "ratios_principales": {
                "liquidez": {
                    "corriente": ratios_info["razon_corriente"],
                    "acida": ratios_info["prueba_acida"]
                },
                "rentabilidad": {
                    "roe_percent": round(ratios_info["roe"] * 100, 2) if ratios_info["roe"] else None,
                    "roa_percent": round(ratios_info["roa"] * 100, 2) if ratios_info["roa"] else None,
                    "ros_percent": round(ratios_info["ros_margen_neto"] * 100, 2) if ratios_info["ros_margen_neto"] else None,
                    "roic_percent": round(roic_calculado, 2)
                },
                "solvencia": {
                    "leverage": round(deuda / patrimonio, 2) if patrimonio > 0 else None,
                    "deuda_capital": round(deuda / capital_invertido, 2) if capital_invertido > 0 else None
                },
                "mercado": {
                    "beta": round(ratios_info["beta"], 2) if ratios_info["beta"] else None,
                    "ebitda": ratios_info["ebitda"]
                }
            },
            # Datos crudos para respaldo
            "datos_financieros": {
                "ventas": ratios_info["revenue_total"],
                "utilidad_neta": ratios_info["net_income"],
                "ebit": ebit,
                "nopat": nopat,
                "patrimonio": patrimonio,
                "deuda_total": deuda
            }
        })

    except Exception as e:
        return jsonify({"error": "Fallo en la extracción", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
