import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time

app = Flask(__name__)
CORS(app)

# Disfraces de navegador para que Yahoo no nos detecte como bot
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v3.1 [AUDITOR MODE] - ONLINE"

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Simulación de comportamiento humano
        time.sleep(random.uniform(0.5, 1.5))
        empresa = yf.Ticker(ticker_symbol)
        
        # 2. Descarga de estados financieros
        is_statement = empresa.get_financials()
        bs_statement = empresa.get_balance_sheet()
        info = empresa.info

        if is_statement.empty or bs_statement.empty:
            return jsonify({"error": "Yahoo no liberó los libros contables para este ticker"}), 404

        # --- FUNCIÓN DE AUDITORÍA (Busca por palabras clave) ---
        def buscar_dato(df, palabras_clave):
            for palabra in palabras_clave:
                # Busca coincidencias parciales en los nombres de las filas
                coincidencias = [idx for idx in df.index if palabra.lower() in idx.lower()]
                if coincidencias:
                    return float(df.loc[coincidencias[0]].iloc[0])
            return 0.0

        # --- EXTRACCIÓN DE DATOS ---
        ebit = buscar_dato(is_statement, ['EBIT', 'Operating Income'])
        utilidad_neta = buscar_dato(is_statement, ['Net Income'])
        
        # Buscamos el Patrimonio con varios nombres posibles
        patrimonio = buscar_dato(bs_statement, ['Total Stockholder Equity', 'Stockholders Equity', 'Common Stock Equity'])
        
        # Si el patrimonio sigue en 0, intentamos sacarlo de la 'info' general
        if patrimonio == 0:
            patrimonio = float(info.get('bookValue', 0) * info.get('sharesOutstanding', 0))

        # Deuda Total
        deuda = buscar_dato(bs_statement, ['Total Debt', 'Long Term Debt'])
        if deuda == 0:
            deuda = float(info.get('totalDebt', 0))

        # --- CÁLCULOS FINANCIEROS ---
        tax_rate = 0.27 # Tasa impositiva Chile
        nopat = ebit * (1 - tax_rate)
        capital_invertido = patrimonio + deuda
        
        # Ratios finales
        roic = (nopat / capital_invertido) * 100 if capital_invertido > 0 else 0
        roe = (utilidad_neta / patrimonio) * 100 if patrimonio > 0 else 0

        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "moneda": info.get("financialCurrency", "N/A"),
            "datos_crudos": {
                "ebit": round(ebit, 2),
                "nopat": round(nopat, 2),
                "utilidad_neta": round(utilidad_neta, 2),
                "patrimonio": round(patrimonio, 2),
                "deuda_total": round(deuda, 2)
            },
            "ratios": {
                "roic_percent": round(roic, 2),
                "roe_percent": round(roe, 2),
                "leverage": round(deuda / patrimonio, 2) if patrimonio > 0 else 0
            },
            "msg": "Data auditada exitosamente por Aetherium Engine"
        })

    except Exception as e:
        return jsonify({
            "error": "Fallo en la extracción",
            "detalle": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
