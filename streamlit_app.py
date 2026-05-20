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
✅ EMA separation states  
✅ Bullish momentum alignment  
✅ Compression → Expansion environments
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
# CHECKMARK FORMATTER
# ============================================

def checkmark(value):

    if value:
        return "✅"
    else:
        return "❌"


# ============================================
# STATE DETECTION
# ============================================

def determine_state(ema_distance_ratio):

    if ema_distance_ratio < 2:
        return "NARROW"

    elif ema_distance_ratio < 6:
        return "HEALTHY"

    else:
        return "WIDE"


# ============================================
# SCORE FUNCTION
# ============================================

def calculate_score(row):

    score = 0

    if row["Above200"]:
        score += 2

    if row["EMA20 Rising"]:
        score += 2

    if row["Compression"]:
        score += 2

    if row["ADX Strong"]:
        score += 1

    if row["Momentum Bull"]:
        score += 1

    # Favor Narrow / Healthy
    if row["State"] == "NARROW":
        score += 2

    elif row["State"] == "HEALTHY":
        score += 1

    return score


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
        # FIX DIMENSIONS
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

        compression = (
            latest_bb_width
            < bb_width.rolling(20).mean().iloc[-1]
        )

        adx_strong = latest_adx > 20

        momentum_bull = latest_close > latest_ema20

        # ====================================
        # EMA DISTANCE STATE
        # ====================================

        ema_distance = abs(
            latest_ema20 - latest_sma200
        )

        ema_distance_ratio = (
            ema_distance / latest_atr
        )

        state = determine_state(
            ema_distance_ratio
        )

        # ====================================
        # PRICE DISTANCE FROM EMA
        # ====================================

        price_distance = abs(
            latest_close - latest_ema20
        )

        price_distance_ratio = (
            price_distance / latest_atr
        )

        # ====================================
        # RESULT
        # ====================================

        result = {
            "Ticker": ticker,

            "Close": round(latest_close, 2),
            "EMA20": round(latest_ema20, 2),
            "SMA200": round(latest_sma200, 2),

            "ADX": round(latest_adx, 2),

            "State": state,

            "EMA Dist Ratio": round(
                ema_distance_ratio, 2
            ),

            "Price Dist Ratio": round(
                price_distance_ratio, 2
            ),

            "Above200": above200,
            "EMA20 Rising": ema20_rising,
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

    if len(results) == 0:
        st.error("No results returned.")
        st.stop()

    results_df = pd.DataFrame(results)

    if "Score" not in results_df.columns:
        st.error("No valid scan results returned.")
        st.dataframe(results_df)
        st.stop()

    # ====================================
    # REMOVE FAILURES
    # ====================================

    results_df = results_df[
        results_df["Score"].notna()
    ]

    # ====================================
    # CHECKMARKS
    # ====================================

    bool_cols = [
        "Above200",
        "EMA20 Rising",
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
    # STYLE FUNCTIONS
    # ====================================

    def highlight_score(val):

        if val >= 9:
            return "background-color: green; color: white"

        elif val >= 7:
            return "background-color: orange; color: black"

        else:
            return "background-color: red; color: white"


    def highlight_state(val):

        if val == "NARROW":
            return (
                "background-color: #1E90FF;"
                "color: white;"
                "font-weight: bold"
            )

        elif val == "HEALTHY":
            return (
                "background-color: green;"
                "color: white;"
                "font-weight: bold"
            )

        elif val == "WIDE":
            return (
                "background-color: red;"
                "color: white;"
                "font-weight: bold"
            )

        return ""


    styled_df = (
        results_df.style
        .map(highlight_score, subset=["Score"])
        .map(highlight_state, subset=["State"])
    )

    # ====================================
    # DISPLAY
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

- State: **{row['State']}**
- Score: **{row['Score']}**
- ADX: **{row['ADX']}**
- EMA Distance Ratio: **{row['EMA Dist Ratio']}**
- Price Distance Ratio: **{row['Price Dist Ratio']}**
""")

    else:

        st.info("No strong setups found.")
