import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Configuramos una sesión que "engañe" a Yahoo
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Origin': 'https://finance.yahoo.com',
    'Referer': 'https://finance.yahoo.com/'
})

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Debes ingresar un Ticker"}), 400

    try:
        # Usamos la sesión personalizada para pasar el escudo de Yahoo
        empresa = yf.Ticker(ticker_symbol, session=session)
        
        # Extraer Estados Financieros
        # Intentamos traer los datos anuales (.financials)
        is_statement = empresa.financials
        bs_statement = empresa.balance_sheet
        info = empresa.info
        
        if is_statement.empty or bs_statement.empty:
            return jsonify({"error": "No hay datos contables disponibles para este ticker en Yahoo"}), 404

        # Variables con "Seguro de Fallo"
        ebit = is_statement.loc['EBIT'].iloc[0] if 'EBIT' in is_statement.index else 0
        utilidad_neta = is_statement.loc['Net Income'].iloc[0] if 'Net Income' in is_statement.index else 0
        total_activos = bs_statement.loc['Total Assets'].iloc[0] if 'Total Assets' in bs_statement.index else 0
        patrimonio = bs_statement.loc['Total Stockholder Equity'].iloc[0] if 'Total Stockholder Equity' in bs_statement.index else 0
        deuda_total = bs_statement.loc['Total Debt'].iloc[0] if 'Total Debt' in bs_statement.index else info.get('totalDebt', 0)

        tax_rate = 0.27 # Tasa Chile
        nopat = float(ebit) * (1 - tax_rate)
        capital_invertido = float(patrimonio) + float(deuda_total)
        
        roic = (nopat / capital_invertido) if capital_invertido > 0 else 0
        roe = (float(utilidad_neta) / float(patrimonio)) if patrimonio > 0 else 0

        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", "N/A"),
            "datos_crudos": {
                "ebit": float(ebit),
                "nopat": nopat,
                "utilidad_neta": float(utilidad_neta),
                "patrimonio": float(patrimonio),
                "deuda_total": float(deuda_total)
            },
            "ratios": {
                "roic_anual": round(roic * 100, 2),
                "roe_anual": round(roe * 100, 2),
                "leverage": round(float(deuda_total)/float(patrimonio), 2) if patrimonio > 0 else 0
            }
        })

    except Exception as e:
        return jsonify({"error": f"Yahoo nos bloqueó de nuevo: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
