# dashboard.py (FINAL fixed Google Sheets gspread by key)

import streamlit as st
import pandas as pd
import bcrypt
from dotenv import load_dotenv
import os
from datetime import datetime
from groq import Groq
import matplotlib.pyplot as plt
import altair as alt
from PIL import Image
import io
import requests
import csv

# ======================
# 🖼️ Konfigurasi Logo & Favicon
# ======================
logo_path = "Logo Findme.png"
logo_url = None

def load_image_bytes(path=None, url=None):
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return f.read()
        except Exception:
            pass
    if url:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
    return None

img_bytes = load_image_bytes(path=logo_path, url=logo_url)

if img_bytes:
    try:
        img = Image.open(io.BytesIO(img_bytes))
        st.set_page_config(page_title="FindMe AI", page_icon=img, layout="wide")
    except Exception:
        st.set_page_config(page_title="FindMe AI", page_icon="💰", layout="wide")
else:
    st.set_page_config(page_title="FindMe AI", page_icon="💰", layout="wide")

def header_with_logo(image_bytes=None, width=120, title="FindMe AI", subtitle="Manajemen Keuangan Pintar"):
    cols = st.columns([0.15, 0.85])
    if image_bytes:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            with cols[0]:
                st.image(img, width=width)
            with cols[1]:
                st.markdown(f"## {title}")
                st.markdown(f"_{subtitle}_")
        except:
            with cols[1]:
                st.markdown(f"## {title}")
                st.markdown(f"_{subtitle}_")
    else:
        with cols[1]:
            st.markdown(f"## {title}")
            st.markdown(f"_{subtitle}_")

header_with_logo(img_bytes)

# ======================
# 🔑 Load API Key
# ======================
api_key = None
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("❌ GROQ_API_KEY tidak ditemukan.")
    st.stop()

client = Groq(api_key=api_key)

# ======================
# 📁 GOOGLE SHEETS DATABASE
# ======================
from google.oauth2.service_account import Credentials
import gspread

EXPECTED_USERS_COLS = ["Email", "Password", "Total_Budget"]
EXPECTED_TRANSACTIONS_COLS = ["User", "Tanggal", "Kategori", "Jumlah"]

SPREADSHEET_ID = st.secrets["google_sheets"]["spreadsheet_id"]

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

gc = gspread.authorize(credentials)
sheet = gc.open_by_key(SPREADSHEET_ID)

def load_or_create_google_sheet(sheet_name, expected_cols):
    try:
        ws = sheet.worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records())
        if df.empty:
            df = pd.DataFrame(columns=expected_cols)
            ws.update([expected_cols])
        return df
    except:
        ws = sheet.add_worksheet(title=sheet_name, rows=1000, cols=len(expected_cols))
        ws.update([expected_cols])
        return pd.DataFrame(columns=expected_cols)

def save_google_sheet(df, sheet_name):
    ws = sheet.worksheet(sheet_name)
    df_converted = df.copy().astype(str)
    ws.clear()
    ws.update([df_converted.columns.values.tolist()] + df_converted.values.tolist())

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# ======================
# ⚙️ Session Init
# ======================
if "page" not in st.session_state:
    st.session_state["page"] = "home"
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

def go_to(page_name: str):
    st.session_state["page"] = page_name
    st.rerun()

# ======================
# 🏠 HOME PAGE
# ======================
if st.session_state["page"] == "home":
    st.markdown("### Selamat datang di aplikasi manajemen keuangan pintar Anda! 💡")
    st.write("Kelola pemasukan, pengeluaran, dan dapatkan saran AI pribadi 🔑")

    col1, col2 = st.columns(2)
    with col1:
        st.button("🔐 Login", use_container_width=True, on_click=lambda: go_to("login"))
    with col2:
        st.button("🆕 Daftar", use_container_width=True, on_click=lambda: go_to("signup"))

# ======================
# 🔐 LOGIN PAGE
# ======================
elif st.session_state["page"] == "login":
    st.title("🔑 Login ke FinSmart AI")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users = load_or_create_google_sheet("Users", EXPECTED_USERS_COLS)
        if email in users["Email"].values:
            user_data = users[users["Email"] == email].iloc[0]
            if verify_password(password, user_data["Password"]):
                st.session_state["logged_in"] = True
                st.session_state["user"] = email
                go_to("dashboard")
            else:
                st.error("❌ Password salah.")
        else:
            st.error("❌ Email tidak ditemukan.")

    st.info("Belum punya akun?")
    st.button("👉 Daftar Sekarang", on_click=lambda: go_to("signup"))
    st.button("⬅ Kembali", on_click=lambda: go_to("home"))

# ======================
# 📝 SIGNUP PAGE
# ======================
elif st.session_state["page"] == "signup":
    st.title("🆕 Daftar Akun Baru")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    total_budget = st.number_input("Total Budget Awal (Rp)", step=1000, value=0)

    if st.button("Daftar"):
        users = load_or_create_google_sheet("Users", EXPECTED_USERS_COLS)
        if not email or not password:
            st.warning("❗ Mohon isi email dan password.")
        elif email in users["Email"].values:
            st.warning("❗ Email sudah terdaftar.")
        else:
            hashed_pw = hash_password(password)
            new_user = pd.DataFrame([[email, hashed_pw, total_budget]], columns=EXPECTED_USERS_COLS)
            users = pd.concat([users, new_user], ignore_index=True)
            save_google_sheet(users, "Users")
            st.success("✅ Akun berhasil dibuat! Silakan login.")

    st.button("⬅ Kembali", on_click=lambda: go_to("home"))

# ======================
# 📊 DASHBOARD + SIDEBAR
# ======================
elif st.session_state["page"] == "dashboard":
    if not st.session_state.get("logged_in", False):
        go_to("login")

    # Sidebar Menu
    with st.sidebar:
        st.image(img, width=120)
        st.title("📌 Menu")
        menu = st.radio("Navigasi", ["Dashboard", "Plot", "Analisis AI", "Download Data"])
        st.write("---")
        if st.button("🚪 Logout"):
            st.session_state["logged_in"] = False
            st.session_state["user"] = None
            go_to("home")

    user = st.session_state["user"]
    st.title(f"💰 Dashboard Keuangan - {user}")

    df = load_or_create_google_sheet("Transactions", EXPECTED_TRANSACTIONS_COLS)
    users_df = load_or_create_google_sheet("Users", EXPECTED_USERS_COLS)
    user_data = df[df["User"] == user]

    try:
        total_budget = float(users_df.loc[users_df["Email"] == user, "Total_Budget"].iloc[0])
    except:
        total_budget = 0

    # =======================
    # DASHBOARD PAGE
    # =======================
    if menu == "Dashboard":
        st.subheader("🧾 Tambah Transaksi")
        with st.form("tambah_transaksi", clear_on_submit=True):
            tanggal = st.date_input("Tanggal", datetime.now())
            kategori = st.selectbox("Kategori", ["Makanan", "Transportasi", "Hiburan", "Tagihan", "Gaji", "Lainnya"])
            jumlah = st.number_input("Jumlah (positif = pengeluaran, negatif = pemasukan)", step=1000)
            submit = st.form_submit_button("💾 Simpan")

        if submit:
            new_row = pd.DataFrame([{ "User": user, "Tanggal": tanggal, "Kategori": kategori, "Jumlah": jumlah }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_google_sheet(df, "Transactions")
            st.success("✅ Transaksi disimpan!")
            st.rerun()

        st.subheader("📋 Riwayat Transaksi")
        st.dataframe(user_data)

       # =======================
    # PLOT DATA
    # =======================
    elif menu == "Plot":
        st.subheader("📊 Tren Transaksi")
        if not user_data.empty:
            pengeluaran = user_data[user_data["Jumlah"] > 0]["Jumlah"].sum()
            pemasukan = abs(user_data[user_data["Jumlah"] < 0]["Jumlah"].sum())
            sisa = pemasukan - pengeluaran

            col1, col2, col3 = st.columns(3)
            col1.metric("Pemasukan", f"Rp {pemasukan:,}")
            col2.metric("Pengeluaran", f"Rp {pengeluaran:,}")
            col3.metric("Sisa", f"Rp {sisa:,}")

            user_data["Tanggal"] = pd.to_datetime(user_data["Tanggal"], errors="coerce")
            daily_summary = user_data.groupby("Tanggal")["Jumlah"].sum().reset_index()

            # =======================
            # PLOT 1 - LINE CHART
            # =======================
            chart = alt.Chart(daily_summary).mark_line(point=True).encode(
                x="Tanggal:T",
                y="Jumlah:Q",
                tooltip=["Tanggal", "Jumlah"]
            ).properties(width=700, height=400)
            st.altair_chart(chart, use_container_width=True)

            # =======================
            # PLOT 2 - PIE CHART
            # =======================
            st.subheader("📉 Distribusi Pengeluaran")
            pengeluaran_kat = user_data[user_data["Jumlah"] > 0].groupby("Kategori")["Jumlah"].sum()

            if not pengeluaran_kat.empty:
                fig, ax = plt.subplots()
                ax.pie(pengeluaran_kat, labels=pengeluaran_kat.index, autopct="%1.1f%%")
                st.pyplot(fig)

            # =======================
            # PLOT 3 - BAR CHART
            # =======================
            st.subheader("📦 Bar Chart Pengeluaran per Kategori")
            bar_data = pengeluaran_kat.reset_index()
            bar_chart = alt.Chart(bar_data).mark_bar().encode(
                x="Kategori:N",
                y="Jumlah:Q",
                tooltip=["Kategori", "Jumlah"]
            ).properties(width=700, height=400)
            st.altair_chart(bar_chart, use_container_width=True)

            # =======================
            # PLOT 4 - AREA CHART
            # =======================
            st.subheader("📈 Area Chart Tren Total Harian")
            area_chart = alt.Chart(daily_summary).mark_area(opacity=0.4).encode(
                x="Tanggal:T",
                y="Jumlah:Q"
            ).properties(width=700, height=400)
            st.altair_chart(area_chart, use_container_width=True)

            # =======================
            # PLOT 5 - SCATTER PLOT
            # =======================
            st.subheader("🎯 Scatter Plot Pemasukan vs Pengeluaran")

            scatter_df = pd.DataFrame({
                "pemasukan": [pemasukan],
                "pengeluaran": [pengeluaran]
            })

            fig_scatter, ax_scatter = plt.subplots()
            ax_scatter.scatter(scatter_df["pemasukan"], scatter_df["pengeluaran"])
            ax_scatter.set_xlabel("Pemasukan")
            ax_scatter.set_ylabel("Pengeluaran")
            ax_scatter.set_title("Korelasi Pendapatan vs Pengeluaran")
            st.pyplot(fig_scatter)

        else:
            st.info("Belum ada data transaksi.")

    # =======================
    # ANALISIS AI
    # =======================
    elif menu == "Analisis AI":
        st.subheader("🤖 Analisis AI")
        if st.button("Analisis Sekarang"):
            pengeluaran = user_data[user_data["Jumlah"] > 0]["Jumlah"].sum()
            pemasukan = abs(user_data[user_data["Jumlah"] < 0]["Jumlah"].sum())
            sisa = pemasukan - pengeluaran

            prompt = f"""
            Analisis keuangan user {user}:
            - Total pemasukan: {pemasukan}
            - Total pengeluaran: {pengeluaran}
            - Sisa budget: {sisa}
            - Total budget awal: {total_budget}
            Berikan 3 saran keuangan.
            """

            with st.spinner("Memproses..."):
                try:
                    response = client.chat.completions.create(
                        model="openai/gpt-oss-20b",
                        messages=[
                            {"role": "system", "content": "Kamu adalah asisten keuangan."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_completion_tokens=800,
                    )
                    hasil = response.choices[0].message.content
                    st.success("Berhasil!")
                    st.write(hasil)
                except Exception as e:
                    st.error("Gagal menganalisis.")
                    st.exception(e)

    # =======================
    # DOWNLOAD DATA
    # =======================
    elif menu == "Download Data":
        st.subheader("📥 Download Spreadsheet Keuangan")
        csv = user_data.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV",
            csv,
            f"riwayat_keuangan_{user}.csv",
            "text/csv"
        )

# =======================
# ⭐ FITUR ULASAN & RATING
# =======================
st.markdown("---")
st.subheader("⭐ Berikan Ulasan Tentang Aplikasi Ini")

REVIEW_COLS = ["Nama", "Email", "Rating", "Ulasan", "Tanggal"]

# Load sheet ulasan (atau buat jika belum ada)
def load_reviews():
    return load_or_create_google_sheet("Reviews", REVIEW_COLS)

def save_reviews(df):
    save_google_sheet(df, "Reviews")

review_df = load_reviews()

# Form input review
with st.form("form_ulasan", clear_on_submit=True):
    nama_ulasan = st.text_input("Nama")
    email_ulasan = st.text_input("Email")
    rating_ulasan = st.slider("Rating", min_value=1, max_value=5, step=1)
    isi_ulasan = st.text_area("Tulis ulasan Anda di sini...")
    kirim_ulasan = st.form_submit_button("Kirim Ulasan")

if kirim_ulasan:
    if nama_ulasan and email_ulasan and isi_ulasan:
        new_review = pd.DataFrame([[
            nama_ulasan,
            email_ulasan,
            rating_ulasan,
            isi_ulasan,
            datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        ]], columns=REVIEW_COLS)

        review_df = pd.concat([review_df, new_review], ignore_index=True)
        save_reviews(review_df)

        st.success("🎉 Terima kasih, ulasan Anda telah dikirim!")
        st.rerun()
    else:
        st.warning("⚠ Mohon isi nama, email, dan ulasan terlebih dahulu.")

# Tampilkan daftar ulasan
st.markdown("### 💬 Ulasan Pengguna")

review_df = load_reviews()

if review_df.empty:
    st.info("Belum ada ulasan, jadilah yang pertama memberikan review ⭐")
else:
    for i in range(len(review_df)-1, -1, -1):   # tampilkan terbaru dulu
        st.markdown(f"""
        **{review_df.iloc[i]['Name']}** ({review_df.iloc[i]['Email']})  
        Rating: {"⭐" * int(review_df.iloc[i]['Rating'])}  
        _"{review_df.iloc[i]['Ulasan']}"_  
        **🕒 {review_df.iloc[i]['Tanggal']}**
        """)
        st.markdown("---")
