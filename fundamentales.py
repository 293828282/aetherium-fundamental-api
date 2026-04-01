import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Fundamental para que tu HTML pueda leer la API

@app.route('/api/fundamentales', methods=['GET'])
def analizar_eeff():
    ticker_symbol = request.args.get('ticker')
    if not ticker_symbol:
        return jsonify({"error": "Debes ingresar un Ticker"}), 400

    try:
        empresa = yf.Ticker(ticker_symbol)
        
        # 1. Extraer Estados Financieros (Último reporte anual)
        is_statement = empresa.financials  # Income Statement
        bs_statement = empresa.balance_sheet # Balance Sheet
        info = empresa.info # Datos generales y ratios ya calculados
        
        # 2. Variables para Ratios (Manejamos errores si no existen datos)
        ebit = is_statement.loc['EBIT'].iloc[0] if 'EBIT' in is_statement.index else 0
        utilidad_neta = is_statement.loc['Net Income'].iloc[0] if 'Net Income' in is_statement.index else 0
        total_activos = bs_statement.loc['Total Assets'].iloc[0] if 'Total Assets' in bs_statement.index else 0
        patrimonio = bs_statement.loc['Total Stockholder Equity'].iloc[0] if 'Total Stockholder Equity' in bs_statement.index else 0
        deuda_total = bs_statement.loc['Total Debt'].iloc[0] if 'Total Debt' in bs_statement.index else (info.get('totalDebt', 0))

        # 3. Cálculos de Ingeniería Comercial
        tax_rate = 0.27 # Tasa impositiva en Chile
        nopat = ebit * (1 - tax_rate)
        capital_invertido = patrimonio + deuda_total
        
        roic = (nopat / capital_invertido) if capital_invertido > 0 else 0
        roe = (utilidad_neta / patrimonio) if patrimonio > 0 else 0
        leverage = (deuda_total / patrimonio) if patrimonio > 0 else 0

        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", "N/A"),
            "moneda": info.get("financialCurrency", "USD"),
            "datos_crudos": {
                "ebit": float(ebit),
                "nopat": float(nopat),
                "utilidad_neta": float(utilidad_neta),
                "patrimonio": float(patrimonio),
                "deuda_total": float(deuda_total)
            },
            "ratios": {
                "roic_anual": round(float(roic) * 100, 2),
                "roe_anual": round(float(roe) * 100, 2),
                "leverage_ratio": round(float(leverage), 2),
                "margen_ebit": round(info.get("operatingMargins", 0) * 100, 2)
            }
        })

    except Exception as e:
        return jsonify({"error": f"Error al procesar: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
