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

st.title("📈 Narrow → Expansion Trend Scanner")

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

        try:

            table = pd.read_html(
                "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            )

            return table[0]["Symbol"].tolist()

        except:

            st.error("Failed to load S&P 500 list.")
            return []

    else:

        return [
            t.strip().upper()
            for t in custom_input.split(",")
            if t.strip()
        ]


# ============================================
# SCORE FUNCTION
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
# CHECKMARK FORMATTER
# ============================================

def checkmark(value):

    if value:
        return "✅"
    else:
        return "❌"


# ============================================
# SCAN FUNCTION
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

        if df.empty:
            return None

        if len(df) < 250:
            return None

        # ====================================
        # FIX DATA DIMENSIONS
        # ====================================

        close = df["Close"].squeeze()
        high = df["High"].squeeze()
        low = df["Low"].squeeze()

        # ====================================
        # INDICATORS
        # ====================================

        ema20_series = EMAIndicator(
            close=close,
            window=20
        ).ema_indicator()

        sma200_series = SMAIndicator(
            close=close,
            window=200
        ).sma_indicator()

        atr_series = AverageTrueRange(
            high=high,
            low=low,
            close=close,
            window=14
        ).average_true_range()

        adx_series = ADXIndicator(
            high=high,
            low=low,
            close=close,
            window=14
        ).adx()

        bb = BollingerBands(
            close=close,
            window=20,
            window_dev=2
        )

        bb_width = (
            bb.bollinger_hband()
            - bb.bollinger_lband()
        ) / close

        # ====================================
        # LATEST VALUES
        # ====================================

        latest_close = close.iloc[-1]
        latest_ema20 = ema20_series.iloc[-1]
        latest_sma200 = sma200_series.iloc[-1]
        latest_atr = atr_series.iloc[-1]
        latest_adx = adx_series.iloc[-1]
        latest_bb_width = bb_width.iloc[-1]

        # ====================================
        # CONDITIONS
        # ====================================

        above200 = latest_close > latest_sma200

        ema20_rising = (
            ema20_series.iloc[-1]
            > ema20_series.iloc[-5]
        )

        distance_from_ema = abs(
            latest_close - latest_ema20
        )

        near_ema20 = (
            distance_from_ema
            < latest_atr * 1.5
        )

        compression = (
            latest_bb_width
            < bb_width.rolling(20).mean().iloc[-1]
        )

        adx_strong = latest_adx > 20

        momentum_bull = latest_close > latest_ema20

        # ====================================
        # RESULT
        # ====================================

        result = {
            "Ticker": ticker,
            "Close": round(latest_close, 2),
            "EMA20": round(latest_ema20, 2),
            "SMA200": round(latest_sma200, 2),
            "ADX": round(latest_adx, 2),
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

    if len(tickers) == 0:
        st.error("No tickers loaded.")
        st.stop()

    results = []

    progress = st.progress(0)

    for i, ticker in enumerate(tickers):

        result = scan_ticker(ticker)

        if result is not None:
            results.append(result)

        progress.progress((i + 1) / len(tickers))

    # ====================================
    # RESULTS
    # ====================================

    if len(results) == 0:
        st.error("No results returned.")
        st.stop()

    results_df = pd.DataFrame(results)

    if "Score" not in results_df.columns:
        st.error("No valid scan results returned.")
        st.dataframe(results_df)
        st.stop()

    # Remove failed rows
    results_df = results_df[
        results_df["Score"].notna()
    ]

    # ====================================
    # CHECKMARK COLUMNS
    # ====================================

    bool_cols = [
        "Above200",
        "EMA20 Rising",
        "Near EMA20",
        "Compression",
        "ADX Strong",
        "Momentum Bull"
    ]

    for col in bool_cols:
        results_df[col] = results_df[col].apply(checkmark)

    # ====================================
    # SORT
    # ====================================

    results_df = results_df.sort_values(
        by="Score",
        ascending=False
    )

    # ====================================
    # DATAFRAME STYLING
    # ====================================

    def highlight_score(val):

        if val >= 8:
            return "background-color: green; color: white"

        elif val >= 6:
            return "background-color: orange; color: black"

        else:
            return "background-color: red; color: white"

    styled_df = results_df.style.map(
        highlight_score,
        subset=["Score"]
    )

    # ====================================
    # RESULTS TABLE
    # ====================================

    st.subheader("📊 Scan Results")

    st.dataframe(
        styled_df,
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
