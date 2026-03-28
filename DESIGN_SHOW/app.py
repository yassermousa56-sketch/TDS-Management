import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import hashlib
import json
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection
import warnings

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# BRAND CONFIG
# ─────────────────────────────────────────────
BRAND = {
    "name":       "The Design Show",
    "tagline":    "Egypt's Premier Design & Décor Exhibition",
    "edition":    "2025 Edition",
    "currency":   "EGP",
    "logo_emoji": "🎨",
    "favicon":    "🎨",
}

st.set_page_config(
    page_title=f"{BRAND['name']} — Management System",
    page_icon=BRAND["favicon"],
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# GOOGLE SHEETS CONFIG
# ─────────────────────────────────────────────
# تأكد أن هذا الرابط هو الصحيح في الـ Secrets
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1iM_LIul_5_1CoKarEWu7WqohkgsuHWYgIHje4DUjd9I/edit?usp=sharing"
WS_EXHIBITORS   = "Exhibitors"
WS_PAYMENTS     = "Payments"

COLUMNS = [
    "Company Name", "Category", "Booth Size Category", "Booth Area (m²)",
    "Price per m²", "Total Booth Price", "Paid Amount", "Remaining Amount",
    "Payment Status", "Contract Date", "Edition", "Hall / Zone",
    "Sales Person", "Contact Person", "Contact Phone", "Notes",
]

PAYMENT_COLUMNS = ["Company Name", "Payment Date", "Amount", "Method", "Reference", "Notes"]

# ─────────────────────────────────────────────
# CONNECTION INITIALIZATION
# ─────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)

# ─────────────────────────────────────────────
# DATA HELPERS (LOAD & SAVE)
# ─────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=WS_EXHIBITORS, ttl="5s")
        # تنظيف البيانات والتأكد من العواميد
        if df.empty:
            return pd.DataFrame(columns=COLUMNS)
        for col in COLUMNS:
            if col not in df.columns: df[col] = ""
        # تحويل الأرقام
        num_cols = ["Booth Area (m²)", "Price per m²", "Total Booth Price", "Paid Amount", "Remaining Amount"]
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except Exception as e:
        return pd.DataFrame(columns=COLUMNS)

def save_data(df: pd.DataFrame):
    conn.update(spreadsheet=SPREADSHEET_URL, worksheet=WS_EXHIBITORS, data=df)
    st.cache_data.clear()

def load_payments() -> pd.DataFrame:
    try:
        pf = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=WS_PAYMENTS, ttl="5
