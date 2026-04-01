import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time

app = Flask(__name__)
CORS(app)

# Lista de disfraces (User-Agents) para engañar a Yahoo
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1.2 Mobile/15E148 Safari/604.1"
]

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v3 [STEALTH MODE] - Usa /api/fundamentales?ticker=AAPL"

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Falta el Ticker"}), 400

    try:
        # 1. Elegimos un disfraz al azar
        random_agent = random.choice(USER_AGENTS)
        
        # 2. Pequeño retraso aleatorio para no parecer un robot ultra rápido
        time.sleep(random.uniform(0.5, 1.5))

        # 3. Descargamos usando yfinance de forma "silenciosa"
        empresa = yf.Ticker(ticker_symbol)
        
        # Forzamos la descarga de los fundamentales (Income Statement)
        # Yahoo a veces bloquea si pides mucho a la vez, así que pedimos lo justo
        is_statement = empresa.get_financials()
        bs_statement = empresa.get_balance_sheet()
        info = empresa.info

        if is_statement.empty:
            return jsonify({"error": "Yahoo bloqueó la descarga de estados financieros"}), 429

        # --- EXTRACCIÓN DE DATOS ---
        ebit = is_statement.loc['EBIT'].iloc[0] if 'EBIT' in is_statement.index else 0
        utilidad_neta = is_statement.loc['Net Income'].iloc[0] if 'Net Income' in is_statement.index else 0
        patrimonio = bs_statement.loc['Total Stockholder Equity'].iloc[0] if 'Total Stockholder Equity' in bs_statement.index else 0
        deuda_total = info.get('totalDebt', 0)

        # Ratios
        tax_rate = 0.27
        nopat = float(ebit) * (1 - tax_rate)
        cap_inv = float(patrimonio) + float(deuda_total)
        roic = (nopat / cap_inv) * 100 if cap_inv > 0 else 0

        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol),
            "nopat": round(nopat, 2),
            "roic": round(roic, 2),
            "patrimonio": float(patrimonio),
            "deuda": float(deuda_total),
            "msg": "Data secured by Aetherium Stealth Mode"
        })

    except Exception as e:
        return jsonify({
            "error": "Rate Limit Activo",
            "msg": "La IP de Render sigue quemada. Intenta de nuevo en un rato o usa un VPN.",
            "detalle": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
