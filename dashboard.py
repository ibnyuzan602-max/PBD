# dashboard.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import bcrypt
from dotenv import load_dotenv
import os
from datetime import datetime
from groq import Groq
import matplotlib.pyplot as plt
import altair as alt

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
    st.error("❌ GROQ_API_KEY tidak ditemukan. Simpan key di Streamlit Secrets atau .env.")
    st.stop()

client = Groq(api_key=api_key)

# ======================
# 🧱 Setup & File
# ======================
EXPECTED_USERS_COLS = ["Email", "Password", "Total_Budget"]
EXPECTED_TRANSACTIONS_COLS = ["User", "Tanggal", "Kategori", "Jumlah"]

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().replace(" ", "_").capitalize() for c in df.columns]
    return df

def load_or_create_csv(filename, expected_cols):
    if not os.path.exists(filename):
        pd.DataFrame(columns=expected_cols).to_csv(filename, index=False)
    df = pd.read_csv(filename)
    df = normalize_columns(df)
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    return df[expected_cols]

users_df = load_or_create_csv("users.csv", EXPECTED_USERS_COLS)
trans_df = load_or_create_csv("transactions.csv", EXPECTED_TRANSACTIONS_COLS)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# ======================
# ⚙️ Konfigurasi Halaman
# ======================
st.set_page_config(page_title="FinSmart AI", page_icon="💰")

# Inisialisasi session state
if "page" not in st.session_state:
    st.session_state["page"] = "login"
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# ======================
# 🧭 Navigasi Otomatis
# ======================
def go_to(page_name: str):
    st.session_state["page"] = page_name
    st.rerun()

# ======================
# 🔐 HALAMAN LOGIN
# ======================
if st.session_state["page"] == "login":
    st.title("🔑 Login ke FinSmart AI")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users = load_or_create_csv("users.csv", EXPECTED_USERS_COLS)
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

# ======================
# 📝 HALAMAN SIGN UP
# ======================
elif st.session_state["page"] == "signup":
    st.title("🆕 Daftar Akun Baru FinSmart AI")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    total_budget = st.number_input("Total Budget Awal (Rp)", step=1000, value=0)

    if st.button("Daftar"):
        users = load_or_create_csv("users.csv", EXPECTED_USERS_COLS)
        if not email or not password:
            st.warning("❗ Mohon isi email dan password.")
        elif email in users["Email"].values:
            st.warning("❗ Email sudah terdaftar.")
        else:
            hashed_pw = hash_password(password)
            new_user = pd.DataFrame([[email, hashed_pw, total_budget]], columns=EXPECTED_USERS_COLS)
            users = pd.concat([users, new_user], ignore_index=True)
            users.to_csv("users.csv", index=False)
            st.success("✅ Akun berhasil dibuat! Silakan login.")
            st.button("⬅ Kembali ke Login", on_click=lambda: go_to("login"))

# ======================
# 📊 HALAMAN DASHBOARD
# ======================
elif st.session_state["page"] == "dashboard":
    if not st.session_state["logged_in"]:
        go_to("login")

    user = st.session_state["user"]
    st.title(f"💰 Dashboard Keuangan - {user}")

    if st.button("🚪 Logout"):
        st.session_state["logged_in"] = False
        st.session_state["user"] = None
        go_to("login")

    # Load data
    df = normalize_columns(pd.read_csv("transactions.csv"))
    users_df = normalize_columns(pd.read_csv("users.csv"))
    df = df[EXPECTED_TRANSACTIONS_COLS]
    users_df = users_df[EXPECTED_USERS_COLS]

    user_data = df[df["User"] == user]
    user_budget_row = users_df.loc[users_df["Email"] == user]
    total_budget = user_budget_row["Total_Budget"].iloc[0] if not user_budget_row.empty else 0

    # ===== Tambah transaksi =====
    st.subheader("🧾 Tambah Transaksi Baru")
    with st.form("tambah_transaksi", clear_on_submit=True):
        tanggal = st.date_input("Tanggal", datetime.now())
        kategori = st.selectbox("Kategori", ["Makanan", "Transportasi", "Hiburan", "Tagihan", "Gaji", "Lainnya"])
        jumlah = st.number_input("Jumlah (positif = pengeluaran, negatif = pemasukan)", step=1000)
        submit = st.form_submit_button("💾 Simpan Transaksi")

    if submit:
        new_row = pd.DataFrame([{
            "User": user,
            "Tanggal": tanggal,
            "Kategori": kategori,
            "Jumlah": jumlah
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv("transactions.csv", index=False)
        st.success("✅ Transaksi berhasil disimpan!")
        st.experimental_rerun()

    # ===== Tampilkan data =====
    st.subheader("📋 Riwayat Transaksi")
    st.dataframe(user_data)

    if not user_data.empty:
        # Ringkasan
        pengeluaran = user_data[user_data["Jumlah"] > 0]["Jumlah"].sum()
        pemasukan = abs(user_data[user_data["Jumlah"] < 0]["Jumlah"].sum())
        sisa = pemasukan - pengeluaran

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pemasukan", f"Rp {pemasukan:,.0f}")
        col2.metric("Pengeluaran", f"Rp {pengeluaran:,.0f}")
        col3.metric("Sisa", f"Rp {sisa:,.0f}")
        col4.metric("Budget Awal", f"Rp {total_budget:,.0f}")

        # ===== Grafik Time Series =====
        st.subheader("📆 Tren Transaksi dari Waktu ke Waktu")

        user_data["Tanggal"] = pd.to_datetime(user_data["Tanggal"], errors="coerce")
        daily_summary = user_data.groupby("Tanggal")["Jumlah"].sum().reset_index()

        line_chart = alt.Chart(daily_summary).mark_line(point=True).encode(
            x="Tanggal:T",
            y="Jumlah:Q",
            tooltip=["Tanggal", "Jumlah"]
        ).properties(
            width=700, height=400, title="Tren Harian Pengeluaran & Pemasukan"
        )
        st.altair_chart(line_chart, use_container_width=True)

        # ===== Pie Chart =====
        st.subheader("📉 Distribusi Pengeluaran per Kategori")
        pengeluaran_per_kategori = user_data[user_data["Jumlah"] > 0].groupby("Kategori")["Jumlah"].sum()
        if not pengeluaran_per_kategori.empty:
            fig, ax = plt.subplots()
            ax.pie(pengeluaran_per_kategori, labels=pengeluaran_per_kategori.index, autopct="%1.1f%%")
            st.pyplot(fig)

        # ===== Analisis AI =====
        st.subheader("🤖 Analisis Keuangan AI")
        prompt = f"""
Analisis keuangan user {user}:
- Total pemasukan: {pemasukan}
- Total pengeluaran: {pengeluaran}
- Sisa budget: {sisa}
- Total budget awal: {total_budget}

Berikan 3 saran keuangan pribadi untuk minggu depan.
"""
        if st.button("Analisis Sekarang"):
            with st.spinner("AI sedang menganalisis..."):
                try:
                    response = client.chat.completions.create(
                        model="openai/gpt-oss-20b",
                        messages=[
                            {"role": "system", "content": "Kamu adalah asisten keuangan pribadi yang memberi saran berdasarkan data pengguna."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_completion_tokens=800,
                    )
                    hasil = response.choices[0].message.content
                    st.success("✅ Analisis Selesai")
                    st.write(hasil)
                except Exception as e:
                    st.error("❌ Gagal menganalisis dengan Groq API.")
                    st.exception(e)
    else:
        st.info("Belum ada transaksi. Tambahkan data untuk melihat grafik & analisis.")
