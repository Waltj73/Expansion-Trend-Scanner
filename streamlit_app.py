# ============================================
# streamlit_app.py
# Narrow → Expansion Trend Scanner
# ============================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

from ta.trend import EMAIndicator
from ta.trend import SMAIndicator
from ta.trend import ADXIndicator

from ta.volatility import AverageTrueRange
from ta.volatility import BollingerBands


# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="Narrow Expansion Scanner",
    layout="wide"
)

st.title("📈 Narrow → Expansion Scanner")

st.markdown("""
This scanner searches for:

✅ Stocks above the 200 SMA  
✅ Rising 20 EMA  
✅ Compression / narrow conditions  
✅ Bullish momentum alignment  
✅ Potential early expansion setups
""")


# ============================================
# INPUTS
# ============================================

scan_group = st.selectbox(
    "Choose Scan Group",
    [
        "NASDAQ 100",
        "S&P 500",
        "Custom"
    ]
)

custom_input = st.text_area(
    "Custom Tickers",
    value="AAPL,NVDA,AMD",
    disabled=(scan_group != "Custom")
)

scan_button = st.button("Run Scan")


# ============================================
# TICKER GROUPS
# ============================================

def get_tickers(group):

    if group == "NASDAQ 100":

        return [
            "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG",
            "TSLA","AVGO","COST","NFLX","AMD","INTC","QCOM",
            "ADBE","AMGN","INTU","PEP","TXN","CSCO","CMCSA",
            "HON","AMAT","BKNG","ISRG","VRTX","SBUX","ADI",
            "LRCX","MU","PANW","MELI","KLAC","SNPS","CDNS",
            "CRWD","ASML","MAR","ADP","FTNT","PYPL","ABNB",
            "TEAM","MRVL","ORLY","WDAY","CTAS","NXPI","KDP"
        ]

    elif group == "S&P 500":

        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )

        return table[0]["Symbol"].tolist()

    else:

        return [
            t.strip().upper()
            for t in custom_input.split(",")
            if t.strip()
        ]


# ============================================
# SCORING
# ============================================

def calculate_score(row):

    score = 0

    if row["Above200"]:
        score += 2

    if row["EMA20 Rising"]:
        score += 2

    if row["Near EMA20"]:
        score += 2

    if row["Compression"]:
        score += 2

    if row["ADX Strong"]:
        score += 1

    if row["Momentum Bull"]:
        score += 1

    return score


# ============================================
# SCANNER
# ============================================

def scan_ticker(ticker):

    try:

        df = yf.download(
            ticker,
            period="1y",
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if len(df) < 250:
            return None

        # ====================================
        # INDICATORS
        # ====================================

        df["EMA20"] = EMAIndicator(
            df["Close"],
            window=20
        ).ema_indicator()

        df["SMA200"] = SMAIndicator(
            df["Close"],
            window=200
        ).sma_indicator()

        atr = AverageTrueRange(
            df["High"],
            df["Low"],
            df["Close"],
            window=14
        )

        df["ATR"] = atr.average_true_range()

        adx = ADXIndicator(
            df["High"],
            df["Low"],
            df["Close"],
            window=14
        )

        df["ADX"] = adx.adx()

        bb = BollingerBands(
            df["Close"],
            window=20,
            window_dev=2
        )

        df["BB_Width"] = (
            bb.bollinger_hband()
            - bb.bollinger_lband()
        ) / df["Close"]

        latest = df.iloc[-1]

        close = latest["Close"]
        ema20 = latest["EMA20"]
        sma200 = latest["SMA200"]

        # ====================================
        # CONDITIONS
        # ====================================

        above200 = close > sma200

        ema20_rising = (
            df["EMA20"].iloc[-1]
            > df["EMA20"].iloc[-5]
        )

        distance_from_ema = abs(close - ema20)

        near_ema20 = (
            distance_from_ema
            < latest["ATR"] * 1.5
        )

        compression = (
            latest["BB_Width"]
            < df["BB_Width"].rolling(20).mean().iloc[-1]
        )

        adx_strong = latest["ADX"] > 20

        momentum_bull = close > ema20

        # ====================================
        # RESULT
        # ====================================

        result = {
            "Ticker": ticker,
            "Close": round(close, 2),
            "EMA20": round(ema20, 2),
            "SMA200": round(sma200, 2),
            "ADX": round(latest["ADX"], 2),
            "Distance From EMA": round(distance_from_ema, 2),
            "Above200": above200,
            "EMA20 Rising": ema20_rising,
            "Near EMA20": near_ema20,
            "Compression": compression,
            "ADX Strong": adx_strong,
            "Momentum Bull": momentum_bull,
        }

        result["Score"] = calculate_score(result)

        return result

    except Exception as e:

        return {
            "Ticker": ticker,
            "Error": str(e)
        }


# ============================================
# RUN SCAN
# ============================================

if scan_button:

    tickers = get_tickers(scan_group)

    results = []

    progress = st.progress(0)

    for i, ticker in enumerate(tickers):

        result = scan_ticker(ticker)

        if result:
            results.append(result)

        progress.progress((i + 1) / len(tickers))

    if results:

        results_df = pd.DataFrame(results)

        # Remove failed scans
        results_df = results_df.dropna(subset=["Score"])

        # Sort best scores first
        results_df = results_df.sort_values(
            by="Score",
            ascending=False
        )

        # ====================================
        # RESULTS TABLE
        # ====================================

        st.subheader("📊 Scan Results")

        st.dataframe(
            results_df,
            use_container_width=True
        )

        # ====================================
        # TOP SETUPS
        # ====================================

        st.subheader("🔥 Top Setups")

        top = results_df[
            results_df["Score"] >= 7
        ]

        if len(top) > 0:

            for _, row in top.iterrows():

                st.markdown(f"""
### {row['Ticker']}

- Score: **{row['Score']}**
- ADX: **{row['ADX']}**
- Above 200: **{row['Above200']}**
- EMA20 Rising: **{row['EMA20 Rising']}**
- Compression: **{row['Compression']}**
- Near EMA20: **{row['Near EMA20']}**
                """)

        else:

            st.info("No strong setups found.")
