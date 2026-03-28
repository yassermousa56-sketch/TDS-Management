import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import hashlib
import json
from datetime import datetime, date
import warnings
warnings.filterwarnings("ignore")

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

# ─────────────────────────────────────────────
# BRAND CONFIG
# ─────────────────────────────────────────────
BRAND = {
    "name":       "Design Show",
    "tagline":    "Egypt's Premier Design & Décor Exhibition",
    "edition":    "2026 Edition",
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

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1iM_LIul_5_1CoKarEWu7WqohkgsuHWYgIHje4DUjd9I"
WS_EXHIBITORS   = "Exhibitors"   # worksheet name in Google Sheet
WS_PAYMENTS     = "Payments"     # worksheet name in Google Sheet
USERS_FILE      = "design_show_users.json"

COLUMNS = [
    "Company Name", "Category", "Booth Size Category", "Booth Area (m²)",
    "Price per m²", "Total Booth Price", "Paid Amount", "Remaining Amount",
    "Payment Status", "Contract Date", "Edition", "Hall / Zone",
    "Sales Person", "Contact Person", "Contact Phone", "Notes",
]
PAYMENT_COLUMNS = ["Company Name", "Payment Date", "Amount", "Method", "Reference", "Notes"]

BOOTH_SIZES      = ["Small (≤18m²)", "Medium (18–36m²)", "Large (36–72m²)", "XL (72m²+)"]
PAYMENT_STATUSES = ["Unpaid", "Partial", "Fully Paid"]
PAYMENT_METHODS  = ["Cash", "Bank Transfer", "Cheque", "Credit Card", "Installment", "Other"]
EDITIONS         = ["Design Show 2026"]
HALLS = [
    "Hall A — Premium", "Hall B — Standard", "Hall C — Emerging Brands",
    "Hall D — International", "Outdoor Pavilion", "VIP Lounge Area",
]
CATEGORIES = [
    "Interior Design & Décor", "Furniture & Upholstery", "Lighting & Electrical",
    "Kitchens & Bathrooms", "Flooring & Wall Coverings", "Art & Sculptures",
    "Smart Home & Technology", "Textiles & Curtains", "Outdoor & Landscape",
    "Architecture & Contracting", "Paint & Finishing", "Accessories & Gifts", "Other",
]

C = {
    "bg": "#0A0A0A", "bg_card": "#111111", "bg_panel": "#181818",
    "gold": "#C9A84C", "gold_lt": "#E8C87A", "gold_dk": "#8B6914",
    "white": "#F0EDE8", "grey": "#8A8A8A", "border": "#2A2A2A",
    "green": "#4CAF7D", "red": "#E05252", "blue": "#5B9BD5", "purple": "#9B72CF",
}

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Montserrat:wght@300;400;500;600;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] {{
        background-color:{C['bg']}; color:{C['white']}; font-family:'Montserrat',sans-serif;
    }}
    [data-testid="stSidebar"] {{
        background:linear-gradient(180deg,#0A0A0A 0%,#111111 100%) !important;
        border-right:1px solid {C['gold_dk']};
    }}
    [data-testid="stSidebar"] * {{ color:{C['white']} !important; }}
    .ds-logo {{ text-align:center; padding:24px 0 16px 0; border-bottom:1px solid {C['gold_dk']}; margin-bottom:20px; }}
    .ds-logo-icon {{ font-size:38px; line-height:1; margin-bottom:8px; }}
    .ds-logo-name {{ font-family:'Cormorant Garamond',serif; font-size:20px; font-weight:700; color:{C['gold']} !important; letter-spacing:2px; text-transform:uppercase; }}
    .ds-logo-tagline {{ font-size:9px; color:{C['grey']} !important; letter-spacing:1.5px; text-transform:uppercase; margin-top:4px; }}
    .ds-logo-edition {{ font-size:10px; color:{C['gold_dk']} !important; font-weight:600; margin-top:6px; letter-spacing:1px; }}

    /* ── KPI CARDS (FIX: no nested conditional HTML) ── */
    .ds-kpi {{ background:{C['bg_card']}; border:1px solid {C['border']}; border-top:2px solid {C['gold_dk']}; border-radius:8px; padding:18px 16px; transition:border-top-color .2s, box-shadow .2s; margin-bottom:4px; }}
    .ds-kpi:hover {{ border-top-color:{C['gold']}; box-shadow:0 4px 20px rgba(201,168,76,.12); }}
    .ds-kpi-label {{ font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:2px; color:{C['grey']}; margin-bottom:8px; }}
    .ds-kpi-value {{ font-family:'Cormorant Garamond',serif; font-size:28px; font-weight:700; color:{C['white']}; line-height:1.1; }}
    .ds-kpi-sub {{ font-size:11px; color:{C['grey']}; margin-top:5px; }}
    .c-gold  {{ color:{C['gold']}; }}
    .c-green {{ color:{C['green']}; }}
    .c-red   {{ color:{C['red']}; }}

    .page-header {{ padding:0 0 20px 0; border-bottom:1px solid {C['border']}; margin-bottom:28px; }}
    .page-title {{ font-family:'Cormorant Garamond',serif; font-size:32px; font-weight:700; color:{C['white']}; letter-spacing:1px; margin-bottom:4px; }}
    .page-subtitle {{ font-size:12px; color:{C['grey']}; letter-spacing:1px; text-transform:uppercase; }}
    .section-title {{ font-family:'Cormorant Garamond',serif; font-size:20px; font-weight:700; color:{C['gold']}; margin:30px 0 14px 0; padding-bottom:8px; border-bottom:1px solid {C['border']}; letter-spacing:1px; }}
    .gold-line {{ height:1px; background:linear-gradient(90deg,transparent,{C['gold']},transparent); margin:20px 0; border:none; }}

    /* ── LIVE CALC BOX ── */
    .calc-box {{ background:{C['bg_panel']}; border:1px solid {C['gold_dk']}; border-radius:8px; padding:16px 18px; margin:4px 0; }}
    .calc-label {{ font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:2px; color:{C['grey']}; margin-bottom:6px; }}
    .calc-value {{ font-family:'Cormorant Garamond',serif; font-size:26px; font-weight:700; color:{C['gold']}; }}
    .calc-value-green {{ font-family:'Cormorant Garamond',serif; font-size:26px; font-weight:700; color:{C['green']}; }}
    .calc-value-red {{ font-family:'Cormorant Garamond',serif; font-size:26px; font-weight:700; color:{C['red']}; }}

    .pay-row {{ background:{C['bg_panel']}; border:1px solid {C['border']}; border-left:3px solid {C['gold']}; border-radius:6px; padding:12px 16px; margin-bottom:8px; }}
    .pay-amount {{ font-family:'Cormorant Garamond',serif; font-size:20px; font-weight:700; color:{C['gold']}; }}
    .pay-meta {{ font-size:11px; color:{C['grey']}; margin-top:3px; letter-spacing:.5px; }}
    .insight-card {{ background:{C['bg_panel']}; border:1px solid {C['border']}; border-left:3px solid {C['gold']}; border-radius:8px; padding:16px 20px; margin-bottom:12px; }}
    .insight-title {{ font-weight:700; font-size:13px; color:{C['gold']}; margin-bottom:6px; letter-spacing:.5px; }}
    .insight-body {{ font-size:12px; color:{C['grey']}; line-height:1.7; }}

    .stButton > button {{
        background:linear-gradient(135deg,{C['gold_dk']},{C['gold']}); color:#000; border:none;
        border-radius:6px; font-weight:700; font-size:13px; letter-spacing:.5px;
        padding:9px 22px; transition:opacity .2s,box-shadow .2s;
    }}
    .stButton > button:hover {{ opacity:.9; box-shadow:0 4px 14px rgba(201,168,76,.3); }}
    div[data-testid="stForm"] {{
        background:{C['bg_card']}; border:1px solid {C['border']};
        border-top:2px solid {C['gold_dk']}; border-radius:10px; padding:26px;
    }}
    .stSelectbox label,.stTextInput label,.stNumberInput label,
    .stDateInput label,.stTextArea label,.stMultiSelect label {{
        color:{C['grey']} !important; font-size:11px !important;
        font-weight:600 !important; letter-spacing:1px !important; text-transform:uppercase !important;
    }}
    .stDataFrame {{ border-radius:8px; overflow:hidden; }}
    div[data-testid="metric-container"] {{
        background:{C['bg_card']}; border:1px solid {C['border']};
        border-top:2px solid {C['gold_dk']}; border-radius:8px; padding:14px;
    }}
    .stAlert {{ border-radius:8px; }}
    hr {{ border-color:{C['border']}; }}
    .stTabs [data-baseweb="tab"] {{ color:{C['grey']}; font-weight:600; font-size:13px; letter-spacing:.5px; }}
    .stTabs [aria-selected="true"] {{ color:{C['gold']} !important; border-bottom-color:{C['gold']} !important; }}
    .hall-badge {{ display:inline-block; background:rgba(201,168,76,.12); border:1px solid {C['gold_dk']}; border-radius:4px; padding:2px 8px; font-size:11px; color:{C['gold']}; font-weight:600; letter-spacing:.5px; }}

    /* ── LOGIN PAGE ── */
    .login-wrapper {{
        min-height:100vh;
        display:flex;
        align-items:center;
        justify-content:center;
        background: radial-gradient(ellipse at 50% 0%, rgba(201,168,76,.10) 0%, transparent 70%),
                    radial-gradient(ellipse at 80% 100%, rgba(139,105,20,.08) 0%, transparent 60%),
                    {C['bg']};
    }}
    .login-card {{
        background:{C['bg_card']};
        border:1px solid {C['border']};
        border-top:3px solid {C['gold']};
        border-radius:16px;
        padding:52px 48px 44px 48px;
        width:100%;
        max-width:420px;
        box-shadow:0 32px 80px rgba(0,0,0,.6), 0 0 60px rgba(201,168,76,.06);
        animation: fadeUp .6s ease both;
    }}
    @keyframes fadeUp {{
        from {{ opacity:0; transform:translateY(28px); }}
        to   {{ opacity:1; transform:translateY(0); }}
    }}
    .login-logo-wrap {{
        text-align:center;
        margin-bottom:32px;
    }}
    .login-icon {{
        font-size:52px;
        display:block;
        margin-bottom:12px;
        animation: pulse 3s ease-in-out infinite;
    }}
    @keyframes pulse {{
        0%,100% {{ transform:scale(1);   filter:drop-shadow(0 0 0px {C['gold']}); }}
        50%      {{ transform:scale(1.08); filter:drop-shadow(0 0 16px {C['gold']}); }}
    }}
    .login-brand {{
        font-family:'Cormorant Garamond',serif;
        font-size:26px;
        font-weight:700;
        color:{C['gold']};
        letter-spacing:3px;
        text-transform:uppercase;
        line-height:1.1;
    }}
    .login-tagline {{
        font-size:10px;
        color:{C['grey']};
        letter-spacing:2px;
        text-transform:uppercase;
        margin-top:6px;
    }}
    .login-divider {{
        height:1px;
        background:linear-gradient(90deg,transparent,{C['gold_dk']},transparent);
        margin:24px 0;
    }}
    .login-title {{
        font-family:'Cormorant Garamond',serif;
        font-size:18px;
        font-weight:600;
        color:{C['white']};
        text-align:center;
        margin-bottom:24px;
        letter-spacing:1px;
    }}
    .login-error {{
        background:rgba(224,82,82,.12);
        border:1px solid rgba(224,82,82,.3);
        border-radius:8px;
        padding:10px 14px;
        font-size:12px;
        color:{C['red']};
        text-align:center;
        margin-top:12px;
        animation: shake .3s ease;
    }}
    @keyframes shake {{
        0%,100% {{ transform:translateX(0); }}
        25%      {{ transform:translateX(-6px); }}
        75%      {{ transform:translateX(6px); }}
    }}
    .login-footer {{
        text-align:center;
        font-size:10px;
        color:{C['grey']};
        margin-top:28px;
        letter-spacing:1px;
    }}
    /* hide sidebar on login */
    .login-hide-sidebar [data-testid="stSidebar"] {{ display:none !important; }}
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# KPI CARD HELPER  (FIX: no nested conditional inside f-string)
# ─────────────────────────────────────────────
def kpi_card(label: str, value: str, sub: str = "", color: str = "c-gold") -> str:
    sub_part = f'<div class="ds-kpi-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="ds-kpi">'
        f'<div class="ds-kpi-label">{label}</div>'
        f'<div class="ds-kpi-value {color}">{value}</div>'
        f'{sub_part}'
        f'</div>'
    )


# ─────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────
def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_users() -> dict:
    """Load users from JSON file. Creates default admin/admin if not exists."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Default credentials
    default = {
        "admin": {
            "password_hash": _hash("admin"),
            "role": "Admin",
            "display_name": "Administrator",
            "created_at": str(datetime.now().date()),
        }
    }
    save_users(default)
    return default

def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def check_credentials(username: str, password: str) -> bool:
    users = load_users()
    if username in users:
        return users[username]["password_hash"] == _hash(password)
    return False

def get_user_info(username: str) -> dict:
    users = load_users()
    return users.get(username, {})

def is_logged_in() -> bool:
    return st.session_state.get("authenticated", False)

def do_logout():
    st.session_state.authenticated = False
    st.session_state.current_user  = ""
    st.session_state.page          = "analytics"


# ─────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────
def page_login():
    # Hide sidebar completely on login screen
    st.markdown("""
    <style>
    [data-testid="stSidebar"]          { display:none !important; }
    [data-testid="collapsedControl"]   { display:none !important; }
    .block-container { padding:0 !important; max-width:100% !important; }
    footer { display:none !important; }
    header { display:none !important; }
    </style>
    """, unsafe_allow_html=True)

    # Decorative particle background
    st.markdown("""
    <style>
    @keyframes float1 { 0%,100%{transform:translate(0,0) rotate(0deg);opacity:.3;} 50%{transform:translate(20px,-30px) rotate(180deg);opacity:.7;} }
    @keyframes float2 { 0%,100%{transform:translate(0,0) rotate(0deg);opacity:.2;} 50%{transform:translate(-15px,25px) rotate(-120deg);opacity:.5;} }
    @keyframes float3 { 0%,100%{transform:translate(0,0);opacity:.15;} 50%{transform:translate(30px,15px);opacity:.4;} }
    .particle {position:fixed;border-radius:50%;pointer-events:none;z-index:0;}
    .p1{width:300px;height:300px;background:radial-gradient(circle,rgba(201,168,76,.08),transparent);top:-80px;left:-80px;animation:float1 12s ease-in-out infinite;}
    .p2{width:200px;height:200px;background:radial-gradient(circle,rgba(201,168,76,.06),transparent);bottom:60px;right:-40px;animation:float2 15s ease-in-out infinite;}
    .p3{width:150px;height:150px;background:radial-gradient(circle,rgba(139,105,20,.1),transparent);bottom:200px;left:100px;animation:float3 10s ease-in-out infinite;}
    </style>
    <div class="particle p1"></div>
    <div class="particle p2"></div>
    <div class="particle p3"></div>
    """, unsafe_allow_html=True)

    # Center the login card
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

        # Brand card
        st.markdown(f"""
        <div class="login-card">
            <div class="login-logo-wrap">
                <span class="login-icon">{BRAND['logo_emoji']}</span>
                <div class="login-brand">{BRAND['name']}</div>
                <div class="login-tagline">{BRAND['tagline']}</div>
                <div style="font-size:10px;color:{C['gold_dk']};margin-top:4px;letter-spacing:1px;">{BRAND['edition']}</div>
            </div>
            <div class="login-divider"></div>
            <div class="login-title">Management System Access</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Login form inside a styled container
        with st.container():
            username = st.text_input(
                "Username", placeholder="Enter your username",
                key="login_user",
                label_visibility="visible",
            )
            password = st.text_input(
                "Password", placeholder="Enter your password",
                type="password", key="login_pass",
                label_visibility="visible",
            )

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            login_btn = st.button("🔑 LOG IN", use_container_width=True, key="login_btn")

            if login_btn:
                if not username.strip() or not password.strip():
                    st.error("Please enter both username and password.")
                elif check_credentials(username.strip(), password.strip()):
                    st.session_state.authenticated = True
                    st.session_state.current_user  = username.strip()
                    st.session_state.page          = "analytics"
                    st.rerun()
                else:
                    st.markdown(
                        '<div class="login-error">❌ Invalid username or password. Please try again.</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown(f"""
        <div class="login-footer">
            © {datetime.now().year} {BRAND['name']} · All rights reserved<br>
            Unauthorized access is strictly prohibited
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PAGE: SECURITY
# ─────────────────────────────────────────────
def page_security():
    page_header("🔐 Security & Access Control",
                f"{BRAND['name']} · manage users, passwords, and access permissions")

    users = load_users()
    current = st.session_state.get("current_user", "")

    # ── Current Users Table ──
    st.markdown('<div class="section-title">👥 User Accounts</div>', unsafe_allow_html=True)
    user_rows = []
    for uname, udata in users.items():
        user_rows.append({
            "Username":     uname,
            "Display Name": udata.get("display_name", uname),
            "Role":         udata.get("role", "User"),
            "Created":      udata.get("created_at", "—"),
            "Status":       "🟢 Active",
        })
    user_df = pd.DataFrame(user_rows)
    st.dataframe(user_df, use_container_width=True, hide_index=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    tab_pw, tab_add, tab_del = st.tabs(["🔑 Change Password", "➕ Add New User", "🗑️ Remove User"])

    # ── TAB 1: CHANGE PASSWORD ──
    with tab_pw:
        st.markdown(f'<div style="font-size:12px;color:{C["grey"]};margin-bottom:16px;">Change password for any existing account.</div>', unsafe_allow_html=True)
        with st.form("change_pw_form", clear_on_submit=True):
            target_user = st.selectbox("Select User", list(users.keys()))
            c1, c2 = st.columns(2)
            with c1:
                new_pw  = st.text_input("New Password *",     type="password", placeholder="At least 4 characters")
            with c2:
                conf_pw = st.text_input("Confirm Password *", type="password", placeholder="Repeat new password")
            # Admin must verify own password when changing others
            own_pw = st.text_input("Your Current Password (required) *", type="password")
            do_change = st.form_submit_button("✅ Update Password", use_container_width=True)

            if do_change:
                if not check_credentials(current, own_pw):
                    st.error("❌ Your current password is incorrect.")
                elif len(new_pw) < 4:
                    st.error("❌ New password must be at least 4 characters.")
                elif new_pw != conf_pw:
                    st.error("❌ Passwords do not match.")
                else:
                    users[target_user]["password_hash"] = _hash(new_pw)
                    save_users(users)
                    st.success(f"✅ Password updated for **{target_user}**.")

    # ── TAB 2: ADD USER ──
    with tab_add:
        st.markdown(f'<div style="font-size:12px;color:{C["grey"]};margin-bottom:16px;">Create a new user account.</div>', unsafe_allow_html=True)
        with st.form("add_user_form", clear_on_submit=True):
            a1, a2 = st.columns(2)
            with a1:
                new_uname   = st.text_input("Username *",     placeholder="e.g. sales_01")
                new_display = st.text_input("Display Name *", placeholder="e.g. Ahmed Sales")
            with a2:
                new_role    = st.selectbox("Role", ["Viewer", "Sales", "Manager", "Admin"])
                new_upass   = st.text_input("Password *", type="password", placeholder="At least 4 characters")
            do_add = st.form_submit_button("➕ Create User", use_container_width=True)

            if do_add:
                if not new_uname.strip():
                    st.error("❌ Username is required.")
                elif new_uname.strip() in users:
                    st.error(f"❌ Username '{new_uname}' already exists.")
                elif len(new_upass) < 4:
                    st.error("❌ Password must be at least 4 characters.")
                elif not new_display.strip():
                    st.error("❌ Display Name is required.")
                else:
                    users[new_uname.strip()] = {
                        "password_hash": _hash(new_upass),
                        "role":          new_role,
                        "display_name":  new_display.strip(),
                        "created_at":    str(date.today()),
                    }
                    save_users(users)
                    st.success(f"✅ User **{new_uname}** created successfully with role **{new_role}**.")
                    st.rerun()

    # ── TAB 3: REMOVE USER ──
    with tab_del:
        st.markdown(f'<div style="font-size:12px;color:{C["grey"]};margin-bottom:16px;">Remove a user account. You cannot delete your own account.</div>', unsafe_allow_html=True)
        removable = [u for u in users.keys() if u != current]
        if not removable:
            st.info("No other users to remove.")
        else:
            with st.form("del_user_form", clear_on_submit=True):
                del_user = st.selectbox("Select User to Remove", removable)
                confirm  = st.text_input(f"Type the username to confirm deletion")
                do_del   = st.form_submit_button("🗑️ Remove User", use_container_width=True)
                if do_del:
                    if confirm.strip() != del_user:
                        st.error(f"❌ Type '{del_user}' exactly to confirm.")
                    else:
                        del users[del_user]
                        save_users(users)
                        st.success(f"✅ User **{del_user}** removed.")
                        st.rerun()

    # ── Security Tips ──
    st.markdown('<div class="section-title">🛡️ Security Recommendations</div>', unsafe_allow_html=True)
    tips = [
        ("🔑 Change default password", "The default admin/admin password should be changed immediately after first login."),
        ("👥 Principle of least privilege", "Assign the minimum required role to each user. Use 'Viewer' for read-only staff."),
        ("🔒 Strong passwords", "Use passwords with 8+ characters, mixing letters, numbers, and symbols."),
        ("📋 Audit user list", "Regularly review active user accounts and remove accounts for staff who have left."),
        ("🚪 Always log out", "Always use the Logout button when leaving the system, especially on shared computers."),
    ]
    for icon_title, body in tips:
        st.markdown(
            f'<div class="insight-card">'
            f'<div class="insight-title">{icon_title}</div>'
            f'<div class="insight-body">{body}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# SAFE DATE HELPER  (FIX: NaTType error)
# ─────────────────────────────────────────────
def safe_date(val) -> date:
    """Convert any value to a date, returning today if conversion fails."""
    try:
        ts = pd.Timestamp(val)
        if pd.isna(ts):
            return date.today()
        return ts.date()
    except Exception:
        return date.today()


# ─────────────────────────────────────────────
# GSHEETS — CLIENT & WORKSHEET HELPERS
# ─────────────────────────────────────────────
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource(ttl=3600)
def _get_client():
    """Build and cache a gspread client from secrets.toml credentials."""
    # Convert AttrDict → plain dict (required by google-auth)
    raw = st.secrets["gcp_service_account"]
    info = {
        "type":                        raw["type"],
        "project_id":                  raw["project_id"],
        "private_key_id":              raw["private_key_id"],
        "private_key":                 raw["private_key"].replace("\\n", "\n"),
        "client_email":                raw["client_email"],
        "client_id":                   raw["client_id"],
        "auth_uri":                    raw.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
        "token_uri":                   raw.get("token_uri", "https://oauth2.googleapis.com/token"),
        "auth_provider_x509_cert_url": raw.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
        "client_x509_cert_url":        raw.get("client_x509_cert_url", ""),
    }
    creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    return gspread.authorize(creds)

def _get_or_create_ws(title: str, headers: list) -> "gspread.Worksheet":
    """Open worksheet by name; create it with headers if it doesn't exist."""
    client = _get_client()
    sh = client.open_by_url(SPREADSHEET_URL)
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=2000, cols=max(len(headers), 10))
        ws.append_row(headers, value_input_option="RAW")
        return ws
    # If sheet exists but is empty, write headers
    if not ws.row_values(1):
        ws.append_row(headers, value_input_option="RAW")
    return ws

def _check_connection() -> bool:
    """Return True if GSheets is reachable, show error otherwise."""
    if not GSHEETS_AVAILABLE:
        st.error("❌ gspread / google-auth غير مثبتين. شغّل: `pip install gspread google-auth`")
        return False
    if "gcp_service_account" not in st.secrets:
        st.error("❌ مفيش `[gcp_service_account]` في ملف `.streamlit/secrets.toml`. راجع إعداد الـ credentials.")
        return False
    try:
        _get_client()
        return True
    except Exception as e:
        st.error(f"❌ فشل الاتصال بـ Google Sheets: {e}")
        return False


# ─────────────────────────────────────────────
# DATA HELPERS — EXHIBITORS  (Google Sheets)
# ─────────────────────────────────────────────
@st.cache_data(ttl=8)
def load_data() -> pd.DataFrame:
    try:
        ws      = _get_or_create_ws(WS_EXHIBITORS, COLUMNS)
        records = ws.get_all_records(expected_headers=COLUMNS, default_blank="")
        df      = pd.DataFrame(records) if records else pd.DataFrame(columns=COLUMNS)
    except Exception as e:
        st.warning(f"⚠️ Could not load exhibitors: {e}")
        df = pd.DataFrame(columns=COLUMNS)
    for col in ["Booth Area (m²)", "Price per m²", "Total Booth Price", "Paid Amount", "Remaining Amount"]:
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)
    df["Contract Date"] = pd.to_datetime(df.get("Contract Date"), errors="coerce")
    for col in ["Edition", "Hall / Zone", "Contact Person", "Contact Phone", "Notes"]:
        if col not in df.columns: df[col] = ""
        else:                     df[col] = df[col].fillna("")
    return df

def save_data(df: pd.DataFrame):
    ws = _get_or_create_ws(WS_EXHIBITORS, COLUMNS)
    for col in COLUMNS:
        if col not in df.columns: df[col] = ""
    rows = [COLUMNS] + df[COLUMNS].fillna("").astype(str).values.tolist()
    ws.clear()
    ws.update(rows, value_input_option="USER_ENTERED")
    st.cache_data.clear()

def detect_status(paid: float, total: float) -> str:
    if total <= 0 or paid <= 0: return "Unpaid"
    if paid >= total:           return "Fully Paid"
    return "Partial"

def add_record(rec: dict):
    df = load_data()
    save_data(pd.concat([df, pd.DataFrame([rec])], ignore_index=True))

def update_record(idx: int, rec: dict):
    df = load_data()
    for k, v in rec.items(): df.at[idx, k] = v
    save_data(df)

def delete_record(idx: int):
    df = load_data()
    save_data(df.drop(index=idx).reset_index(drop=True))


# ─────────────────────────────────────────────
# DATA HELPERS — PAYMENTS  (Google Sheets)
# ─────────────────────────────────────────────
@st.cache_data(ttl=8)
def load_payments() -> pd.DataFrame:
    try:
        ws      = _get_or_create_ws(WS_PAYMENTS, PAYMENT_COLUMNS)
        records = ws.get_all_records(expected_headers=PAYMENT_COLUMNS, default_blank="")
        pf      = pd.DataFrame(records) if records else pd.DataFrame(columns=PAYMENT_COLUMNS)
    except Exception as e:
        st.warning(f"⚠️ Could not load payments: {e}")
        pf = pd.DataFrame(columns=PAYMENT_COLUMNS)
    pf["Amount"]       = pd.to_numeric(pf.get("Amount", 0), errors="coerce").fillna(0)
    pf["Payment Date"] = pd.to_datetime(pf.get("Payment Date"), errors="coerce")
    for col in ["Reference", "Notes", "Method"]:
        if col not in pf.columns: pf[col] = ""
        else:                     pf[col] = pf[col].fillna("")
    return pf

def save_payments(pf: pd.DataFrame):
    ws = _get_or_create_ws(WS_PAYMENTS, PAYMENT_COLUMNS)
    for col in PAYMENT_COLUMNS:
        if col not in pf.columns: pf[col] = ""
    rows = [PAYMENT_COLUMNS] + pf[PAYMENT_COLUMNS].fillna("").astype(str).values.tolist()
    ws.clear()
    ws.update(rows, value_input_option="USER_ENTERED")
    st.cache_data.clear()

def _recalc(company: str):
    df = load_data(); pf = load_payments()
    idx_list = df[df["Company Name"] == company].index.tolist()
    if not idx_list: return
    idx        = idx_list[0]
    total_paid = pf[pf["Company Name"] == company]["Amount"].sum()
    total_val  = float(df.at[idx, "Total Booth Price"])
    df.at[idx, "Paid Amount"]      = total_paid
    df.at[idx, "Remaining Amount"] = max(total_val - total_paid, 0)
    df.at[idx, "Payment Status"]   = detect_status(total_paid, total_val)
    save_data(df)

def log_payment(company: str, pay_date: date, amount: float, method: str, ref: str, notes: str):
    pf = load_payments()
    save_payments(pd.concat([pf, pd.DataFrame([{
        "Company Name": company, "Payment Date": str(pay_date),
        "Amount": amount, "Method": method, "Reference": ref, "Notes": notes,
    }])], ignore_index=True))
    _recalc(company)

def delete_payment_entry(pay_idx: int, company: str):
    pf = load_payments()
    save_payments(pf.drop(index=pay_idx).reset_index(drop=True))
    _recalc(company)


# ─────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────
PL = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Montserrat", color=C["white"]),
    margin=dict(t=40, b=20, l=10, r=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
)
GOLD_SEQ = ["#8B6914", "#C9A84C", "#E8C87A", "#F5E4A8"]

def al(fig, title="", height=320):
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, family="Cormorant Garamond", color=C["gold"]), x=0),
        height=height, **PL,
    )
    fig.update_xaxes(gridcolor=C["border"], zeroline=False)
    fig.update_yaxes(gridcolor=C["border"], zeroline=False)
    return fig

def chart_revenue_by_category(df):
    if df.empty: return go.Figure()
    g = df.groupby("Category")["Total Booth Price"].sum().reset_index().sort_values("Total Booth Price", ascending=False)
    fig = px.bar(g, x="Category", y="Total Booth Price", color="Total Booth Price", color_continuous_scale=GOLD_SEQ)
    fig.update_coloraxes(showscale=False); fig.update_xaxes(tickangle=-35)
    return al(fig, "💰 Revenue by Category")

def chart_exhibitors_by_category(df):
    if df.empty: return go.Figure()
    g = df["Category"].value_counts().reset_index(); g.columns = ["Category","Count"]
    fig = px.pie(g, names="Category", values="Count",
                 color_discrete_sequence=["#C9A84C","#E8C87A","#8B6914","#5B9BD5","#9B72CF",
                                          "#4CAF7D","#E05252","#F0EDE8","#8A8A8A","#D4A017","#6B8E9F","#C17F24","#A0522D"])
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return al(fig, "🏢 Exhibitors by Category")

def chart_payment_status(df):
    if df.empty: return go.Figure()
    g = df["Payment Status"].value_counts().reset_index(); g.columns = ["Status","Count"]
    cmap = {"Fully Paid":C["green"],"Partial":C["gold"],"Unpaid":C["red"]}
    fig = px.pie(g, names="Status", values="Count", color="Status", color_discrete_map=cmap, hole=0.60)
    fig.update_traces(textposition="outside", textinfo="label+percent")
    return al(fig, "📊 Payment Status")

def chart_gauge(value, title=""):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"suffix":"%","font":{"size":34,"color":C["gold"],"family":"Cormorant Garamond"}},
        gauge={
            "axis":{"range":[0,100],"tickcolor":C["grey"],"tickfont":{"color":C["grey"]}},
            "bar":{"color":C["gold"]},"bgcolor":C["bg_card"],"bordercolor":C["border"],
            "steps":[{"range":[0,40],"color":"rgba(224,82,82,.15)"},
                     {"range":[40,75],"color":"rgba(201,168,76,.12)"},
                     {"range":[75,100],"color":"rgba(76,175,125,.12)"}],
            "threshold":{"line":{"color":C["gold_lt"],"width":3},"thickness":.75,"value":value},
        },
    ))
    return al(fig, title, height=290)

def chart_by_hall(df):
    if df.empty or "Hall / Zone" not in df.columns: return go.Figure()
    g = df.groupby("Hall / Zone").agg(Revenue=("Total Booth Price","sum"),Count=("Company Name","count")).reset_index()
    fig = px.bar(g, x="Hall / Zone", y="Revenue", color="Count", color_continuous_scale=GOLD_SEQ, text="Count")
    fig.update_traces(textposition="outside"); fig.update_coloraxes(showscale=False)
    return al(fig, "🏛️ Revenue by Hall / Zone")

def chart_trend(df):
    if df.empty or df["Contract Date"].isna().all(): return go.Figure()
    tmp = df.dropna(subset=["Contract Date"]).copy()
    tmp["Month"] = tmp["Contract Date"].dt.to_period("M").dt.to_timestamp()
    g = tmp.groupby("Month").agg(Total=("Total Booth Price","sum"),Paid=("Paid Amount","sum")).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["Month"],y=g["Total"],name="Contracted",fill="tozeroy",line=dict(color=C["gold"],width=2)))
    fig.add_trace(go.Scatter(x=g["Month"],y=g["Paid"],name="Collected",fill="tozeroy",line=dict(color=C["green"],width=2)))
    return al(fig, "📈 Collection Trend", height=300)

def chart_top_exhibitors(df, n=10):
    if df.empty: return go.Figure()
    top = df.nlargest(n,"Total Booth Price")[["Company Name","Total Booth Price","Paid Amount"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=top["Company Name"],x=top["Total Booth Price"],name="Total",orientation="h",marker_color=C["gold"]))
    fig.add_trace(go.Bar(y=top["Company Name"],x=top["Paid Amount"],name="Paid",orientation="h",marker_color=C["green"]))
    fig.update_layout(barmode="overlay",height=380)
    return al(fig, "🏆 Top Exhibitors by Value", height=380)

def chart_remaining(df):
    if df.empty: return go.Figure()
    g = df.groupby("Payment Status")["Remaining Amount"].sum().reset_index()
    cmap = {"Fully Paid":C["green"],"Partial":C["gold"],"Unpaid":C["red"]}
    fig = px.bar(g, x="Payment Status", y="Remaining Amount", color="Payment Status", color_discrete_map=cmap)
    fig.update_layout(showlegend=False)
    return al(fig, "💸 Outstanding by Status")

def chart_payment_timeline(company: str):
    pf = load_payments()
    cp = pf[pf["Company Name"] == company].dropna(subset=["Payment Date"]).copy()
    if cp.empty: return None
    cp["Month"] = cp["Payment Date"].dt.to_period("M").dt.to_timestamp()
    g = cp.groupby("Month")["Amount"].sum().reset_index()
    fig = px.bar(g, x="Month", y="Amount", color_discrete_sequence=[C["gold"]])
    fig.update_layout(showlegend=False)
    return al(fig, f"📅 Monthly Payments — {company}", height=240)

def chart_forecast(df):
    if df.empty or df["Contract Date"].isna().all(): return go.Figure()
    tmp = df.dropna(subset=["Contract Date"]).copy()
    tmp["Month"] = tmp["Contract Date"].dt.to_period("M").dt.to_timestamp()
    g = tmp.groupby("Month")["Total Booth Price"].sum().reset_index().sort_values("Month")
    if len(g) < 2: return go.Figure()
    x = np.arange(len(g)); y = g["Total Booth Price"].values; c = np.polyfit(x, y, 1)
    fd = [g["Month"].iloc[-1] + pd.DateOffset(months=i+1) for i in range(3)]
    fy = [max(np.polyval(c, len(g)+i), 0) for i in range(3)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["Month"],y=y,name="Historical",line=dict(color=C["gold"],width=2)))
    fig.add_trace(go.Scatter(x=fd,y=fy,name="Forecast",line=dict(color=C["purple"],width=2,dash="dot")))
    return al(fig, "🔮 3-Month Revenue Forecast", height=300)

def chart_edition_compare(df):
    if df.empty or "Edition" not in df.columns: return go.Figure()
    g = df.groupby("Edition").agg(Revenue=("Total Booth Price","sum"),Collected=("Paid Amount","sum"),Exhibitors=("Company Name","count")).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=g["Edition"],y=g["Revenue"],name="Contracted",marker_color=C["gold"]))
    fig.add_trace(go.Bar(x=g["Edition"],y=g["Collected"],name="Collected",marker_color=C["green"]))
    fig.update_layout(barmode="group")
    return al(fig, "📋 Edition Comparison")


# ─────────────────────────────────────────────
# AI / INSIGHTS
# ─────────────────────────────────────────────
def compute_risk(row) -> tuple:
    s = 0
    if row["Payment Status"] == "Unpaid":    s += 40
    elif row["Payment Status"] == "Partial": s += 20
    if row["Remaining Amount"] > 50000: s += 20
    elif row["Remaining Amount"] > 20000: s += 10
    if pd.notna(row["Contract Date"]):
        try:
            days = (pd.Timestamp.now() - row["Contract Date"]).days
            s += 20 if days > 180 else (10 if days > 90 else 0)
        except Exception:
            pass
    t   = row["Total Booth Price"]
    pct = (row["Paid Amount"]/t*100) if t > 0 else 0
    s  += 20 if pct < 25 else (10 if pct < 50 else 0)
    s   = min(s, 100)
    return s, ("High" if s >= 60 else ("Medium" if s >= 30 else "Low"))

def ai_insights(df: pd.DataFrame) -> list:
    if df.empty: return [{"title":"No Data","body":"Add exhibitors to unlock insights.","type":"info"}]
    ins   = []
    total = df["Total Booth Price"].sum(); col = df["Paid Amount"].sum()
    rem   = df["Remaining Amount"].sum();  rate = (col/total*100) if total > 0 else 0
    up    = df[df["Payment Status"]=="Unpaid"]; pa = df[df["Payment Status"]=="Partial"]
    if rate < 50:
        ins.append({"title":"⚠️ Low Collection Rate","body":f"Only {rate:.1f}% collected. EGP {rem:,.0f} outstanding. Immediate follow-up required.","type":"red"})
    elif rate < 75:
        ins.append({"title":"📌 Collection Needs Attention","body":f"{rate:.1f}% collected. {len(pa)} partial payers owe EGP {pa['Remaining Amount'].sum():,.0f}.","type":"yellow"})
    else:
        ins.append({"title":"✅ Strong Collection Rate","body":f"Excellent {rate:.1f}% collection rate. EGP {rem:,.0f} remaining.","type":"green"})
    if not up.empty:
        names = ", ".join(up.nlargest(3,"Total Booth Price")["Company Name"].tolist())
        ins.append({"title":f"🚨 {len(up)} Fully Unpaid Exhibitors","body":f"At risk: EGP {up['Total Booth Price'].sum():,.0f}. Top: {names}.","type":"red"})
    if "Category" in df.columns:
        tc  = df.groupby("Category")["Total Booth Price"].sum().idxmax()
        trv = df.groupby("Category")["Total Booth Price"].sum().max()
        ins.append({"title":"📊 Category Performance","body":f"'{tc}' leads at EGP {trv:,.0f}. Allocate premium hall space to top revenue categories.","type":"info"})
    if "Hall / Zone" in df.columns and df["Hall / Zone"].notna().any():
        hall_rev = df.groupby("Hall / Zone")["Total Booth Price"].sum()
        if not hall_rev.empty:
            ins.append({"title":"🏛️ Hall Performance","body":f"'{hall_rev.idxmax()}' is the highest revenue hall. Consider increasing booth density for next edition.","type":"info"})
    if df["Booth Area (m²)"].sum() > 0:
        avg_ppm = df["Total Booth Price"].sum() / df["Booth Area (m²)"].sum()
        ins.append({"title":"💡 Pricing Strategy","body":f"Avg EGP {avg_ppm:,.0f}/m². Offer 5% early-bird discount for contracts signed 6+ months ahead.","type":"info"})
    if not pa.empty:
        names = ", ".join(pa.nlargest(5,"Remaining Amount")["Company Name"].tolist())
        ins.append({"title":"📞 Follow-Up Priority","body":f"Contact: {names} within 48 hrs.","type":"yellow"})
    return ins


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(f"""<div class="ds-logo">
            <div class="ds-logo-icon">{BRAND['logo_emoji']}</div>
            <div class="ds-logo-name">{BRAND['name']}</div>
            <div class="ds-logo-tagline">{BRAND['tagline']}</div>
            <div class="ds-logo-edition">{BRAND['edition']}</div>
        </div>""", unsafe_allow_html=True)

        pages = {
            f"{BRAND['logo_emoji']} Data Entry":  "data_entry",
            "📊 Analytics Dashboard":             "analytics",
            "🤖 AI Intelligence":                 "ai",
            "🔍 Records & Search":                "records",
            "⚙️ Settings":                        "settings",
            "🔐 Security":                        "security",
        }
        if "page" not in st.session_state: st.session_state.page = "analytics"
        for label, key in pages.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key; st.rerun()

        st.markdown("<hr class='gold-line'/>", unsafe_allow_html=True)
        df = load_data(); pf = load_payments()
        rate = (df["Paid Amount"].sum()/df["Total Booth Price"].sum()*100) if df["Total Booth Price"].sum() > 0 else 0
        st.markdown(f"""<div style='font-size:11px;color:{C['grey']};padding:4px 0;line-height:2.2;'>
            <div>🏢 <b style='color:{C['white']};'>{len(df)}</b> Exhibitors</div>
            <div>💳 <b style='color:{C['white']};'>{len(pf)}</b> Payments logged</div>
            <div>💰 <b style='color:{C['gold']};'>EGP {df['Total Booth Price'].sum():,.0f}</b> contracted</div>
            <div>✅ <b style='color:{C['green']};'>EGP {df['Paid Amount'].sum():,.0f}</b> collected</div>
            <div>📈 <b style='color:{C['gold']};'>{rate:.1f}%</b> collection rate</div>
        </div>""", unsafe_allow_html=True)

        # ── User info + Logout ──
        st.markdown("<hr class='gold-line'/>", unsafe_allow_html=True)
        current_user = st.session_state.get("current_user", "")
        user_info    = get_user_info(current_user)
        display_name = user_info.get("display_name", current_user)
        role         = user_info.get("role", "User")
        st.markdown(
            f'<div style="font-size:11px;color:{C["grey"]};margin-bottom:10px;line-height:1.8;">'
            f'<div>👤 <b style="color:{C["white"]};">{display_name}</b></div>'
            f'<div>🎖️ <span style="color:{C["gold"]};">{role}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("🚪 Log Out", key="logout_btn", use_container_width=True):
            do_logout()
            st.rerun()

    return st.session_state.page

def page_header(title, subtitle=""):
    sub_html = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="page-header"><div class="page-title">{title}</div>{sub_html}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PAGE: DATA ENTRY  (FIX: removed st.form → live auto-calc)
# ─────────────────────────────────────────────
def page_data_entry():
    page_header(f"{BRAND['logo_emoji']} Exhibitor Registration",
                f"{BRAND['name']} · {BRAND['edition']} · Register a new exhibitor")

    if "edit_mode" not in st.session_state: st.session_state.edit_mode = False
    if "edit_idx"  not in st.session_state: st.session_state.edit_idx  = None

    df = load_data(); default = {}
    if st.session_state.edit_mode and st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        if idx < len(df):
            default = df.iloc[idx].to_dict()
            st.info(f"✏️ Editing: **{default.get('Company Name','')}**")

    # ── Company Details ──
    st.markdown('<div class="section-title">🏢 Company Details</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        company      = st.text_input("Company Name *", value=str(default.get("Company Name","")), key="de_company")
        category     = st.selectbox("Category *", CATEGORIES,
                           index=CATEGORIES.index(default["Category"]) if default.get("Category") in CATEGORIES else 0)
        hall         = st.selectbox("Hall / Zone", HALLS,
                           index=HALLS.index(default["Hall / Zone"]) if default.get("Hall / Zone") in HALLS else 0)
    with c2:
        edition      = st.selectbox("Exhibition Edition", EDITIONS,
                           index=EDITIONS.index(default["Edition"]) if default.get("Edition") in EDITIONS else 1)
        contact_name = st.text_input("Contact Person", value=str(default.get("Contact Person","")))
        contact_tel  = st.text_input("Contact Phone",  value=str(default.get("Contact Phone","")))
    with c3:
        sales_person = st.text_input("Sales Person", value=str(default.get("Sales Person","")))
        cdate        = st.date_input("Contract Date", value=safe_date(default.get("Contract Date")))

    # ── Booth & Pricing (LIVE CALC) ──
    st.markdown('<div class="section-title">📐 Booth & Pricing</div>', unsafe_allow_html=True)
    p1, p2, p3, p4, p5 = st.columns(5)
    with p1:
        booth_size = st.selectbox("Booth Size *", BOOTH_SIZES,
                         index=BOOTH_SIZES.index(default["Booth Size Category"]) if default.get("Booth Size Category") in BOOTH_SIZES else 0)
    with p2:
        area = st.number_input("Booth Area (m²) *", min_value=0.0, step=0.5,
                               value=float(default.get("Booth Area (m²)", 0.0)), key="de_area")
    with p3:
        ppm  = st.number_input("Price per m² (EGP) *", min_value=0.0, step=50.0,
                               value=float(default.get("Price per m²", 0.0)), key="de_ppm")
    # Live calculation from session_state
    live_area  = st.session_state.get("de_area", area)
    live_ppm   = st.session_state.get("de_ppm", ppm)
    total_price = live_area * live_ppm
    with p4:
        st.markdown(f'<div class="calc-box"><div class="calc-label">Total Booth Price</div><div class="calc-value">EGP {total_price:,.0f}</div></div>', unsafe_allow_html=True)
    with p5:
        st.markdown(f'<div class="calc-box"><div class="calc-label">Area × Price/m²</div><div class="calc-value" style="font-size:16px;">{live_area:.1f} × {live_ppm:,.0f}</div></div>', unsafe_allow_html=True)

    # ── Payment (LIVE CALC) ──
    st.markdown('<div class="section-title">💳 Payment</div>', unsafe_allow_html=True)
    fp1, fp2, fp3, fp4, fp5 = st.columns(5)
    with fp1:
        paid = st.number_input("Initial Paid Amount (EGP)", min_value=0.0, step=500.0,
                               value=float(default.get("Paid Amount", 0.0)), key="de_paid")
    live_paid    = st.session_state.get("de_paid", paid)
    live_remain  = max(total_price - live_paid, 0)
    auto_status  = detect_status(live_paid, total_price)
    with fp2:
        st.markdown(f'<div class="calc-box"><div class="calc-label">Remaining Amount</div><div class="{"calc-value-red" if live_remain > 0 else "calc-value-green"}">EGP {live_remain:,.0f}</div></div>', unsafe_allow_html=True)
    with fp3:
        pstatus = st.selectbox("Payment Status", PAYMENT_STATUSES, index=PAYMENT_STATUSES.index(auto_status))
    with fp4:
        pay_method_init = st.selectbox("Initial Payment Method", PAYMENT_METHODS)
    with fp5:
        pct_paid = (live_paid / total_price * 100) if total_price > 0 else 0
        st.markdown(f'<div class="calc-box"><div class="calc-label">% Paid</div><div class="{"calc-value-green" if pct_paid >= 100 else "calc-value"}">{ pct_paid:.1f}%</div></div>', unsafe_allow_html=True)

    notes = st.text_area("Internal Notes", value=str(default.get("Notes", "")), height=80)

    col_save, col_cancel = st.columns([3, 1])
    with col_save:
        do_save = st.button(f"💾 Register Exhibitor — {BRAND['name']}", use_container_width=True)
    with col_cancel:
        if st.session_state.edit_mode:
            if st.button("❌ Cancel Edit", use_container_width=True):
                st.session_state.edit_mode = False; st.session_state.edit_idx = None; st.rerun()

    if do_save:
        if not company.strip():    st.error("❌ Company Name is required.")
        elif live_area <= 0:       st.error("❌ Booth Area must be > 0.")
        elif live_ppm  <= 0:       st.error("❌ Price per m² must be > 0.")
        else:
            rec = {
                "Company Name":company.strip(), "Category":category,
                "Booth Size Category":booth_size, "Booth Area (m²)":live_area,
                "Price per m²":live_ppm, "Total Booth Price":total_price,
                "Paid Amount":live_paid, "Remaining Amount":live_remain,
                "Payment Status":pstatus, "Contract Date":str(cdate),
                "Edition":edition, "Hall / Zone":hall,
                "Sales Person":sales_person.strip(),
                "Contact Person":contact_name.strip(),
                "Contact Phone":contact_tel.strip(),
                "Notes":notes.strip(),
            }
            if st.session_state.edit_mode and st.session_state.edit_idx is not None:
                with st.spinner("☁️ Syncing to Google Sheet..."):
                    update_record(st.session_state.edit_idx, rec)
                st.success("✅ Record updated & synced to Google Sheet!")
                st.session_state.edit_mode = False; st.session_state.edit_idx = None
            else:
                with st.spinner("☁️ Saving to Google Sheet..."):
                    add_record(rec)
                    if live_paid > 0:
                        log_payment(company.strip(), cdate, live_paid, pay_method_init, "", "Initial payment at registration")
                st.success(f"✅ **{company}** saved to Google Sheet! Total: EGP {total_price:,.0f} · Remaining: EGP {live_remain:,.0f}")
            st.rerun()


# ─────────────────────────────────────────────
# PAGE: ANALYTICS  (FIX: kpi_card helper — no </div> leak)
# ─────────────────────────────────────────────
def page_analytics():
    page_header("📊 Analytics Dashboard",
                f"{BRAND['name']} · {BRAND['edition']} · Real-time performance overview")
    df = load_data()
    if df.empty: st.warning("No exhibitors registered yet."); return

    total = df["Total Booth Price"].sum(); col = df["Paid Amount"].sum()
    rem   = df["Remaining Amount"].sum();  rate = (col/total*100) if total > 0 else 0
    uc    = int((df["Payment Status"]=="Unpaid").sum())
    pc    = int((df["Payment Status"]=="Partial").sum())
    fc    = int((df["Payment Status"]=="Fully Paid").sum())
    n     = len(df)
    halls = int(df["Hall / Zone"].nunique()) if "Hall / Zone" in df.columns else 0
    tc    = df.groupby("Category")["Total Booth Price"].sum().idxmax()

    # Row 1
    cs = st.columns(4)
    with cs[0]: st.markdown(kpi_card("Total Exhibitors",   str(n),                    f"across {halls} halls"),            unsafe_allow_html=True)
    with cs[1]: st.markdown(kpi_card("Contracted Revenue", f"EGP {total:,.0f}",       ""),                                  unsafe_allow_html=True)
    with cs[2]: st.markdown(kpi_card("Collected Revenue",  f"EGP {col:,.0f}",         f"{rate:.1f}% of total", "c-green"),  unsafe_allow_html=True)
    with cs[3]: st.markdown(kpi_card("Outstanding",        f"EGP {rem:,.0f}",         f"{uc} unpaid · {pc} partial", "c-red"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    # Row 2
    cs2 = st.columns(4)
    with cs2[0]: st.markdown(kpi_card("Fully Paid",         str(fc),                   f"{fc/n*100:.0f}% of exhibitors", "c-green"), unsafe_allow_html=True)
    with cs2[1]: st.markdown(kpi_card("Avg Booth Area",     f"{df['Booth Area (m²)'].mean():.1f} m2", "per exhibitor"),    unsafe_allow_html=True)
    with cs2[2]: st.markdown(kpi_card("Avg Price / m2",     f"EGP {df['Price per m²'].mean():,.0f}", "per square meter"),  unsafe_allow_html=True)
    with cs2[3]: st.markdown(kpi_card("Top Revenue Category", tc, ""),                 unsafe_allow_html=True)

    st.markdown('<div class="section-title">Revenue & Collections</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1.4, 1.6])
    with c1: st.plotly_chart(chart_revenue_by_category(df), use_container_width=True, config={"displayModeBar":False})
    with c2: st.plotly_chart(chart_gauge(rate,"💳 Collection Progress"), use_container_width=True, config={"displayModeBar":False})
    with c3: st.plotly_chart(chart_payment_status(df), use_container_width=True, config={"displayModeBar":False})

    c4, c5 = st.columns(2)
    with c4: st.plotly_chart(chart_trend(df), use_container_width=True, config={"displayModeBar":False})
    with c5: st.plotly_chart(chart_forecast(df), use_container_width=True, config={"displayModeBar":False})

    c6, c7 = st.columns(2)
    with c6: st.plotly_chart(chart_exhibitors_by_category(df), use_container_width=True, config={"displayModeBar":False})
    with c7: st.plotly_chart(chart_by_hall(df), use_container_width=True, config={"displayModeBar":False})

    c8, c9 = st.columns([2, 1])
    with c8: st.plotly_chart(chart_top_exhibitors(df), use_container_width=True, config={"displayModeBar":False})
    with c9: st.plotly_chart(chart_remaining(df), use_container_width=True, config={"displayModeBar":False})

    st.plotly_chart(chart_edition_compare(df), use_container_width=True, config={"displayModeBar":False})


# ─────────────────────────────────────────────
# PAGE: AI INTELLIGENCE
# ─────────────────────────────────────────────
def page_ai():
    page_header("🤖 AI Intelligence",
                f"{BRAND['name']} · smart analytics and strategic recommendations")
    df = load_data()
    if df.empty: st.warning("No data available."); return

    for ins in ai_insights(df):
        bc = {"red":C["red"],"yellow":C["gold"],"green":C["green"],"info":C["blue"]}.get(ins["type"],C["blue"])
        st.markdown(f'<div class="insight-card" style="border-left-color:{bc};"><div class="insight-title" style="color:{bc};">{ins["title"]}</div><div class="insight-body">{ins["body"]}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">🎯 Exhibitor Risk Assessment</div>', unsafe_allow_html=True)
    rows = []
    for _, r in df.iterrows():
        s, lv = compute_risk(r)
        rows.append({"Company":r["Company Name"],"Hall":r.get("Hall / Zone","—"),
                     "Risk Score":s,"Risk Level":lv,
                     "Remaining (EGP)":r["Remaining Amount"],"Status":r["Payment Status"]})
    rdf = pd.DataFrame(rows).sort_values("Risk Score", ascending=False)
    def cr(v):
        if v=="High":   return f"color:{C['red']};font-weight:bold;"
        if v=="Medium": return f"color:{C['gold']};font-weight:bold;"
        return f"color:{C['green']};font-weight:bold;"
    st.dataframe(rdf.style.applymap(cr, subset=["Risk Level"]), use_container_width=True, hide_index=True)

    total = df["Total Booth Price"].sum(); col_ = df["Paid Amount"].sum()
    pa    = df[df["Payment Status"]=="Partial"]
    pred  = col_ + pa["Remaining Amount"].sum() * 0.75
    ar    = rdf[rdf["Risk Level"]=="High"]["Remaining (EGP)"].sum()
    st.markdown('<div class="section-title">📈 Revenue Completion Prediction</div>', unsafe_allow_html=True)
    cs = st.columns(3)
    with cs[0]: st.markdown(kpi_card("Current Collection",       f"EGP {col_:,.0f}",  f"{col_/total*100:.1f}% of contracted", "c-green"), unsafe_allow_html=True)
    with cs[1]: st.markdown(kpi_card("Predicted (75% partials)", f"EGP {pred:,.0f}",  f"{pred/total*100:.1f}% of contracted", "c-gold"),  unsafe_allow_html=True)
    with cs[2]: st.markdown(kpi_card("High Risk Outstanding",    f"EGP {ar:,.0f}",    "Requires urgent action",               "c-red"),   unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PAGE: RECORDS / SEARCH  (FIX: NaT safe_date everywhere)
# ─────────────────────────────────────────────
def page_records():
    page_header("🔍 Exhibitor Records",
                f"{BRAND['name']} · search, filter, manage payments, and edit records")
    df = load_data()
    if df.empty: st.warning("No records yet. Register exhibitors first."); return

    # ── FILTERS ──
    with st.expander("🔎 Search & Filters", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            search  = st.text_input("🔍 Company Name")
            cats    = st.multiselect("Category", sorted(df["Category"].dropna().unique().tolist()))
        with fc2:
            bsizes  = st.multiselect("Booth Size", BOOTH_SIZES)
            statuses= st.multiselect("Payment Status", PAYMENT_STATUSES)
        with fc3:
            halls_f = st.multiselect("Hall / Zone", sorted(df["Hall / Zone"].dropna().unique().tolist()))
            eds_f   = st.multiselect("Edition",     sorted(df["Edition"].dropna().unique().tolist()))
        with fc4:
            sp_f    = st.multiselect("Sales Person", sorted(df["Sales Person"].dropna().unique().tolist()))
            valid_dates = df["Contract Date"].dropna()
            if not valid_dates.empty:
                d1 = valid_dates.min().date()
                d2 = valid_dates.max().date()
                dr = st.date_input("Contract Date Range", value=(d1, d2))
            else:
                dr = None
        fr1, fr2 = st.columns(2)
        with fr1:
            paid_mn = st.number_input("Min Paid",      min_value=0.0, value=0.0, step=1000.0)
            paid_mx = st.number_input("Max Paid",      min_value=0.0, value=float(df["Paid Amount"].max())+1, step=1000.0)
        with fr2:
            rem_mn  = st.number_input("Min Remaining", min_value=0.0, value=0.0, step=1000.0)
            rem_mx  = st.number_input("Max Remaining", min_value=0.0, value=float(df["Remaining Amount"].max())+1, step=1000.0)
        reset = st.button("🔄 Reset All Filters")

    filt = df.copy()
    if not reset:
        if search:     filt = filt[filt["Company Name"].str.contains(search, case=False, na=False)]
        if cats:       filt = filt[filt["Category"].isin(cats)]
        if bsizes:     filt = filt[filt["Booth Size Category"].isin(bsizes)]
        if statuses:   filt = filt[filt["Payment Status"].isin(statuses)]
        if halls_f:    filt = filt[filt["Hall / Zone"].isin(halls_f)]
        if eds_f:      filt = filt[filt["Edition"].isin(eds_f)]
        if sp_f:       filt = filt[filt["Sales Person"].isin(sp_f)]
        if dr and len(dr)==2:
            filt = filt[filt["Contract Date"].notna() &
                        (filt["Contract Date"].dt.date >= dr[0]) &
                        (filt["Contract Date"].dt.date <= dr[1])]
        filt = filt[(filt["Paid Amount"]>=paid_mn)&(filt["Paid Amount"]<=paid_mx)&
                    (filt["Remaining Amount"]>=rem_mn)&(filt["Remaining Amount"]<=rem_mx)]

    # Summary
    f_total = filt["Total Booth Price"].sum()
    f_paid  = filt["Paid Amount"].sum()
    f_rem   = filt["Remaining Amount"].sum()
    st.markdown(
        '<div style="display:flex;gap:14px;margin-bottom:16px;flex-wrap:wrap;">'
        + kpi_card("Filtered",    str(len(filt)),        "")
        + kpi_card("Contracted",  f"EGP {f_total:,.0f}", "")
        + kpi_card("Collected",   f"EGP {f_paid:,.0f}",  "", "c-green")
        + kpi_card("Outstanding", f"EGP {f_rem:,.0f}",   "", "c-red")
        + '</div>',
        unsafe_allow_html=True,
    )

    def hl(val):
        if val=="Fully Paid": return f"background:rgba(76,175,125,.15);color:{C['green']};font-weight:bold;"
        if val=="Partial":    return f"background:rgba(201,168,76,.12);color:{C['gold']};font-weight:bold;"
        if val=="Unpaid":     return f"background:rgba(224,82,82,.15);color:{C['red']};font-weight:bold;"
        return ""

    disp = filt.copy()
    disp["Contract Date"] = disp["Contract Date"].apply(
        lambda v: pd.Timestamp(v).strftime("%d %b %Y") if pd.notna(v) else ""
    )
    st.dataframe(disp.reset_index(drop=True).style.applymap(hl, subset=["Payment Status"]),
                 use_container_width=True, height=340, hide_index=False)

    csv_bytes = filt.assign(**{"Contract Date":filt["Contract Date"].astype(str)}).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export Filtered CSV", data=csv_bytes,
                       file_name=f"DesignShow_exhibitors_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

    st.markdown("<hr class='gold-line'/>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏢 Manage Company</div>', unsafe_allow_html=True)

    selected = st.selectbox("Select a company", ["— Select —"] + df["Company Name"].tolist(), key="rec_sel")
    if selected == "— Select —":
        st.info("👆 Select a company to manage payments, log new payments, or edit details.")
        return

    idx = df[df["Company Name"] == selected].index[0]
    row = df.iloc[idx]

    # Company info strip
    hall_badge = f'<span class="hall-badge">{row.get("Hall / Zone","")}</span>' if row.get("Hall / Zone") else ""
    st.markdown(
        f'<div style="background:{C["bg_panel"]};border:1px solid {C["border"]};border-radius:8px;padding:14px 18px;margin-bottom:16px;">'
        f'<div style="font-family:Cormorant Garamond,serif;font-size:18px;font-weight:700;color:{C["gold"]};">{selected} {hall_badge}</div>'
        f'<div style="font-size:11px;color:{C["grey"]};margin-top:4px;">'
        f'{row.get("Category","—")} · {row.get("Edition","—")} · '
        f'👤 {row.get("Contact Person","—")} · 📞 {row.get("Contact Phone","—")} · 🤝 {row.get("Sales Person","—")}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    tab_hist, tab_log, tab_edit = st.tabs(["💳 Payment History", "➕ Log New Payment", "✏️ Edit / Delete Record"])

    # ── TAB 1: HISTORY ──
    with tab_hist:
        pf = load_payments(); cp = pf[pf["Company Name"]==selected].copy()
        c1, c2, c3 = st.columns(3)
        c1.metric("Contract Value",    f"EGP {row['Total Booth Price']:,.0f}")
        c2.metric("Total Paid",        f"EGP {row['Paid Amount']:,.0f}")
        c3.metric("Remaining Balance", f"EGP {row['Remaining Amount']:,.0f}")
        pct = (row["Paid Amount"]/row["Total Booth Price"]*100) if row["Total Booth Price"] > 0 else 0
        st.progress(min(int(pct),100), text=f"💳 {pct:.1f}% collected")
        if cp.empty:
            st.info("No payments logged yet. Use the 'Log New Payment' tab.")
        else:
            cp_s = cp.sort_values("Payment Date", ascending=False).reset_index()
            st.markdown(f"**{len(cp_s)} payment(s) · Total: EGP {cp_s['Amount'].sum():,.0f}**")
            for _, pr in cp_s.iterrows():
                orig_idx = int(pr["index"])
                pd_str   = pd.Timestamp(pr["Payment Date"]).strftime("%d %b %Y") if pd.notna(pr["Payment Date"]) else "—"
                ref_txt  = str(pr.get("Reference","")).strip()
                note_txt = str(pr.get("Notes","")).strip()
                meta     = f'📅 {pd_str} &nbsp;·&nbsp; 💳 {pr.get("Method","—")}'
                if ref_txt:  meta += f' &nbsp;·&nbsp; 🔖 {ref_txt}'
                if note_txt: meta += f' &nbsp;·&nbsp; 📝 {note_txt}'
                col_a, col_b = st.columns([8,1])
                with col_a:
                    st.markdown(f'<div class="pay-row"><div class="pay-amount">EGP {pr["Amount"]:,.0f}</div><div class="pay-meta">{meta}</div></div>', unsafe_allow_html=True)
                with col_b:
                    if st.button("🗑️", key=f"dp_{orig_idx}_{selected}", help="Delete payment"):
                        delete_payment_entry(orig_idx, selected); st.success("Payment deleted."); st.rerun()
            fig = chart_payment_timeline(selected)
            if fig: st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            pay_csv = cp.assign(**{"Payment Date":cp["Payment Date"].astype(str)}).to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Export Payment History", data=pay_csv, mime="text/csv",
                               file_name=f"DesignShow_payments_{selected.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.csv")

    # ── TAB 2: LOG PAYMENT ──
    with tab_log:
        rem_now = float(row["Remaining Amount"])
        st.markdown(
            f'<div class="insight-card" style="border-left-color:{C["gold"]};">'
            f'<div class="insight-title">💳 Log Payment for {selected}</div>'
            f'<div class="insight-body">Contract: <b>EGP {row["Total Booth Price"]:,.0f}</b> &nbsp;·&nbsp; '
            f'Paid: <b style="color:{C["green"]};">EGP {row["Paid Amount"]:,.0f}</b> &nbsp;·&nbsp; '
            f'Remaining: <b style="color:{C["gold"]};">EGP {rem_now:,.0f}</b></div></div>',
            unsafe_allow_html=True,
        )
        if rem_now <= 0:
            st.success("✅ Fully paid — no outstanding balance.")
        else:
            with st.form(f"log_{selected}", clear_on_submit=True):
                lc1, lc2 = st.columns(2)
                with lc1:
                    pay_amount = st.number_input("Payment Amount (EGP) *", min_value=1.0,
                                                 max_value=float(rem_now), step=500.0,
                                                 value=min(5000.0, float(rem_now)))
                    pay_date   = st.date_input("Payment Date *", value=date.today())
                with lc2:
                    pay_method = st.selectbox("Payment Method", PAYMENT_METHODS)
                    pay_ref    = st.text_input("Reference / Cheque #", placeholder="Bank ref, cheque number...")
                pay_notes = st.text_input("Notes (optional)")
                do_save   = st.form_submit_button("✅ Save Payment", use_container_width=True)
                if do_save:
                    if pay_amount <= 0:
                        st.error("Amount must be > 0.")
                    elif pay_amount > rem_now + 0.01:
                        st.error(f"Exceeds remaining balance of EGP {rem_now:,.0f}.")
                    else:
                        log_payment(selected, pay_date, pay_amount, pay_method, pay_ref, pay_notes)
                        st.success(f"✅ EGP {pay_amount:,.0f} logged via {pay_method}! Remaining: EGP {max(rem_now-pay_amount,0):,.0f}")
                        st.rerun()

    # ── TAB 3: EDIT / DELETE  (FIX: safe_date for NaT) ──
    with tab_edit:
        st.markdown(f'<div style="font-size:11px;color:{C["grey"]};margin-bottom:14px;letter-spacing:.5px;">Edit exhibitor details directly — all changes saved immediately.</div>', unsafe_allow_html=True)
        with st.form(f"edit_{selected}", clear_on_submit=False):
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                e_comp = st.text_input("Company Name *", value=str(row["Company Name"]))
                e_cat  = st.selectbox("Category *", CATEGORIES,
                             index=CATEGORIES.index(row["Category"]) if row["Category"] in CATEGORIES else 0)
                e_hall = st.selectbox("Hall / Zone", HALLS,
                             index=HALLS.index(row.get("Hall / Zone","")) if row.get("Hall / Zone","") in HALLS else 0)
            with ec2:
                e_ed  = st.selectbox("Edition", EDITIONS,
                            index=EDITIONS.index(row.get("Edition","")) if row.get("Edition","") in EDITIONS else 1)
                e_cp  = st.text_input("Contact Person", value=str(row.get("Contact Person","")))
                e_ct  = st.text_input("Contact Phone",  value=str(row.get("Contact Phone","")))
            with ec3:
                e_sp    = st.text_input("Sales Person", value=str(row.get("Sales Person","")))
                # FIX: use safe_date to avoid NaTType error
                e_cdate = st.date_input("Contract Date", value=safe_date(row.get("Contract Date")))
                e_stat  = st.selectbox("Payment Status (override)", PAYMENT_STATUSES,
                              index=PAYMENT_STATUSES.index(row["Payment Status"]) if row["Payment Status"] in PAYMENT_STATUSES else 0)

            bp1, bp2, bp3 = st.columns(3)
            with bp1:
                e_bsize = st.selectbox("Booth Size", BOOTH_SIZES,
                              index=BOOTH_SIZES.index(row["Booth Size Category"]) if row["Booth Size Category"] in BOOTH_SIZES else 0)
            with bp2:
                e_area  = st.number_input("Booth Area (m²) *", min_value=0.0, step=0.5, value=float(row["Booth Area (m²)"]))
            with bp3:
                e_ppm   = st.number_input("Price per m² (EGP) *", min_value=0.0, step=50.0, value=float(row["Price per m²"]))

            e_total = e_area * e_ppm
            st.caption(f"New total price: EGP {e_total:,.0f}")
            e_notes = st.text_area("Notes", value=str(row.get("Notes","")), height=70)

            pf_now     = load_payments()
            cp_now     = pf_now[pf_now["Company Name"]==selected]
            paid_total = float(cp_now["Amount"].sum()) if not cp_now.empty else float(row["Paid Amount"])
            e_rem      = max(e_total - paid_total, 0)
            st.caption(f"Paid (from log): EGP {paid_total:,.0f} → Remaining: EGP {e_rem:,.0f}")

            sc, dc = st.columns([3,1])
            with sc: do_save_e  = st.form_submit_button("💾 Update Record", use_container_width=True)
            with dc: do_delete  = st.form_submit_button("🗑️ Delete",        use_container_width=True)

            if do_save_e:
                if not e_comp.strip():  st.error("Company Name required.")
                elif e_area <= 0:       st.error("Area must be > 0.")
                elif e_ppm  <= 0:       st.error("Price must be > 0.")
                else:
                    update_record(idx, {
                        "Company Name":e_comp.strip(),"Category":e_cat,
                        "Booth Size Category":e_bsize,"Booth Area (m²)":e_area,
                        "Price per m²":e_ppm,"Total Booth Price":e_total,
                        "Paid Amount":paid_total,"Remaining Amount":e_rem,
                        "Payment Status":e_stat,"Contract Date":str(e_cdate),
                        "Edition":e_ed,"Hall / Zone":e_hall,
                        "Sales Person":e_sp.strip(),"Contact Person":e_cp.strip(),
                        "Contact Phone":e_ct.strip(),"Notes":e_notes.strip(),
                    })
                    st.success(f"✅ Updated {e_comp}!"); st.rerun()

            if do_delete:
                delete_record(idx)
                pf_d = load_payments()
                save_payments(pf_d[pf_d["Company Name"]!=selected].reset_index(drop=True))
                st.success(f"🗑️ Deleted {selected} and all payment records."); st.rerun()


# ─────────────────────────────────────────────
# PAGE: SETTINGS
# ─────────────────────────────────────────────
def page_settings():
    page_header("⚙️ Settings & Data Management",
                f"{BRAND['name']} · import, export, and system configuration")
    df = load_data(); pf = load_payments()

    st.markdown('<div class="section-title">📤 Export Data</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇️ Export Exhibitors CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"DesignShow_exhibitors_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)
    with c2:
        st.download_button("⬇️ Export Payments Log CSV",
            data=pf.to_csv(index=False).encode("utf-8"),
            file_name=f"DesignShow_payments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)
    with c3:
        rate = (df["Paid Amount"].sum()/df["Total Booth Price"].sum()*100) if df["Total Booth Price"].sum()>0 else 0
        st.markdown(
            kpi_card(BRAND["name"],
                     f"{rate:.1f}% collected",
                     f"{len(df)} exhibitors · {len(pf)} payments"),
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">📥 Import from CSV (bulk upload)</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload Exhibitors CSV → pushes to Google Sheet", type=["csv"])
    if uploaded:
        try:
            new_df  = pd.read_csv(uploaded)
            core    = ["Company Name","Category","Booth Size Category","Booth Area (m²)","Price per m²","Total Booth Price","Paid Amount","Remaining Amount","Payment Status"]
            missing = [c for c in core if c not in new_df.columns]
            if missing: st.error(f"Missing required columns: {missing}")
            else:
                mode = st.radio("Import Mode", ["Append to existing data","Replace all data"])
                if st.button("✅ Confirm Import → Push to Google Sheet"):
                    save_data(new_df if mode=="Replace all data" else pd.concat([df, new_df], ignore_index=True))
                    st.success(f"✅ {len(new_df)} records pushed to Google Sheet."); st.rerun()
        except Exception as e: st.error(f"Import failed: {e}")

    st.markdown('<div class="section-title">🗑️ Danger Zone</div>', unsafe_allow_html=True)
    with st.expander("⚠️ Destructive Actions — Irreversible"):
        st.warning("This will clear ALL rows from the Google Sheet worksheets.")
        confirm = st.text_input("Type DELETE ALL to confirm")
        if st.button("🗑️ Clear All Exhibitors & Payments from Google Sheet"):
            if confirm == "DELETE ALL":
                save_data(pd.DataFrame(columns=COLUMNS))
                save_payments(pd.DataFrame(columns=PAYMENT_COLUMNS))
                st.success("✅ All data cleared from Google Sheet."); st.rerun()
            else: st.error("Type 'DELETE ALL' exactly.")

    st.markdown('<div class="section-title">☁️ Google Sheets Connection</div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        gs_ok = GSHEETS_AVAILABLE
        try:
            _get_client()
            conn_status = "✅ Connected & Active"
            conn_color  = C["green"]
        except Exception as e:
            conn_status = f"❌ {e}"
            conn_color  = C["red"]
        st.markdown(
            f'<div class="insight-card"><div class="insight-title">🔗 Connection Status</div>'
            f'<div class="insight-body">'
            f'Library (gspread): <b>{"✅ Installed" if gs_ok else "❌ Run: pip install gspread google-auth"}</b><br>'
            f'Status: <b style="color:{conn_color};">{conn_status}</b><br>'
            f'Spreadsheet: <code style="font-size:10px;word-break:break-all;">{SPREADSHEET_URL}</code><br>'
            f'Exhibitors sheet: <b>{WS_EXHIBITORS}</b><br>'
            f'Payments sheet: <b>{WS_PAYMENTS}</b><br>'
            f'Live rows: <b>{len(df)}</b> exhibitors · <b>{len(pf)}</b> payments'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="insight-card"><div class="insight-title">⚙️ .streamlit/secrets.toml Setup</div>'
            f'<div class="insight-body" style="font-size:11px;">'
            f'<code>[connections.gsheets]<br>'
            f'type = "service_account"<br>'
            f'project_id = "your-project-id"<br>'
            f'private_key_id = "..."<br>'
            f'private_key = "-----BEGIN RSA..."<br>'
            f'client_email = "your@sa.iam.gserviceaccount.com"<br>'
            f'client_id = "..."<br>'
            f'token_uri = "https://oauth2.googleapis.com/token"</code><br><br>'
            f'📌 Share the Sheet with <b>client_email</b> as <b>Editor</b>.'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">ℹ️ System Information</div>', unsafe_allow_html=True)
    c5, c6 = st.columns(2)
    with c5:
        st.markdown(
            f'<div class="insight-card"><div class="insight-title">Users File (local)</div>'
            f'<div class="insight-body">'
            f'Path: <code>{os.path.abspath(USERS_FILE)}</code><br>'
            f'Status: {"✅ Exists" if os.path.exists(USERS_FILE) else "⚠️ Will be created on first login"}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    with c6:
        st.markdown(
            f'<div class="insight-card"><div class="insight-title">{BRAND["name"]} — {BRAND["edition"]}</div>'
            f'<div class="insight-body">'
            f'{BRAND["tagline"]}<br><br>'
            f'Exhibitors: <b>{len(df)}</b> · Payment entries: <b>{len(pf)}</b><br>'
            f'Halls tracked: <b>{df["Hall / Zone"].nunique()}</b><br>'
            f'Editions: <b>{df["Edition"].nunique()}</b><br>'
            f'Categories: <b>{df["Category"].nunique()}</b>'
            f'</div></div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    inject_css()

    # Init auth session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = ""

    # ── AUTH GATE ──
    if not is_logged_in():
        page_login()
        return

    # ── GSHEETS CONNECTION CHECK ──
    if not _check_connection():
        st.stop()

    # ── APP (only if authenticated + connected) ──
    page = render_sidebar()
    if   page == "data_entry": page_data_entry()
    elif page == "analytics":  page_analytics()
    elif page == "ai":         page_ai()
    elif page == "records":    page_records()
    elif page == "settings":   page_settings()
    elif page == "security":   page_security()

if __name__ == "__main__":
    main()
