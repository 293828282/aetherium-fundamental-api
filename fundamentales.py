import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time
import os
import threading
import pandas as pd

app = Flask(__name__)
CORS(app)

api_lock = threading.Lock()

@app.route('/')
def home():
    return "🚀 Aetherium Fundamental API v10 [FINANCIAL STATEMENTS ENGINE] - ONLINE"

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
            
            # 1. EXTRACCIÓN DE HISTORIAL (Ya comprobamos que esto funciona perfecto)
            yf_period = periodo if periodo in ['1mo', '3mo', '6mo', '1y', '5y'] else '5y'
            hist = None
            for intento in range(3):
                try:
                    hist = empresa.history(period=yf_period)
                    if not hist.empty: break
                except Exception:
                    time.sleep(2)
            
            datos_historicos = []
            if hist is not None and not hist.empty:
                for index, row in hist.iterrows():
                    datos_historicos.append({"Fecha": index.strftime('%Y-%m-%d'), "Cierre": float(row['Close'])})

            # 2. LA NUEVA VÍA: EXTRACCIÓN DE ESTADOS FINANCIEROS (Income Statement & Balance Sheet)
            is_stmt = pd.DataFrame()
            bs_stmt = pd.DataFrame()
            try:
                is_stmt = empresa.get_financials()
                bs_stmt = empresa.get_balance_sheet()
            except Exception as e:
                print(f"Fallo al descargar EEFF para {ticker_symbol}: {e}")

            # Función para extraer el valor más reciente de una fila contable
            def get_accounting_value(df, possible_keys):
                if df is None or df.empty: return 0
                for key in possible_keys:
                    if key in df.index:
                        # Tomamos la columna 0 (el año más reciente reportado)
                        val = df.loc[key].iloc[0]
                        if pd.notna(val) and val != 0:
                            return float(val)
                return 0

            # 3. EXTRACCIÓN DE COMPONENTES CONTABLES BASE
            net_income = get_accounting_value(is_stmt, ['Net Income', 'Net Income Common Stockholders'])
            ebit = get_accounting_value(is_stmt, ['EBIT', 'Operating Income'])
            total_revenue = get_accounting_value(is_stmt, ['Total Revenue', 'Operating Revenue'])
            
            total_assets = get_accounting_value(bs_stmt, ['Total Assets'])
            total_equity = get_accounting_value(bs_stmt, ['Stockholders Equity', 'Total Equity Gross Minority Interest', 'Total Stockholder Equity'])
            total_debt = get_accounting_value(bs_stmt, ['Total Debt', 'Long Term Debt'])
            current_assets = get_accounting_value(bs_stmt, ['Current Assets', 'Total Current Assets'])
            current_liab = get_accounting_value(bs_stmt, ['Current Liabilities', 'Total Current Liabilities'])

            # 4. CÁLCULO MANUAL DE RATIOS (Tu estrategia)
            roe = round((net_income / total_equity) * 100, 2) if total_equity > 0 else None
            roa = round((net_income / total_assets) * 100, 2) if total_assets > 0 else None
            ros = round((net_income / total_revenue) * 100, 2) if total_revenue > 0 else None
            
            leverage = round((total_debt / total_equity), 2) if total_equity > 0 else None
            current_ratio = round((current_assets / current_liab), 2) if current_liab > 0 else None
            
            tax_rate = 0.27 # Tasa impositiva asumida (Chile)
            nopat = ebit * (1 - tax_rate)
            invested_capital = total_debt + total_equity
            roic = round((nopat / invested_capital) * 100, 2) if invested_capital > 0 else None

            # Extraemos el nombre e intentamos rescatar el Beta del Info si nos dejan
            info = {}
            try:
                info = empresa.info
            except Exception:
                pass

            beta = round(info.get('beta', 0), 2) if isinstance(info, dict) and info.get('beta') else None

        # RESPUESTA JSON CON RATIOS CALCULADOS
        return jsonify({
            "ticker": ticker_symbol.upper(),
            "empresa": info.get("longName", ticker_symbol) if isinstance(info, dict) else ticker_symbol,
            "datos": datos_historicos,
            "datos_crudos": {
                "ebit": ebit,
                "nopat": nopat,
                "patrimonio": total_equity,
                "deuda_total": total_debt,
                "ventas": total_revenue,
                "utilidad_neta": net_income,
                "activos_totales": total_assets
            },
            "ratios": {
                "roic": roic,
                "leverage": leverage if leverage is not None else "High/Neg",
                "razon_corriente": current_ratio,
                "roe": roe,
                "roa": roa,
                "ros": ros,
                "beta": beta
            }
        })

    except Exception as e:
        return jsonify({"error": "Fallo critico en la API", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
