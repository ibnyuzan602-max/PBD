# dashboard.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import bcrypt
from dotenv import load_dotenv
import os
from datetime import datetime
from groq import Groq

# ====== 1️⃣ Load API Key (Streamlit Secrets > env) ======
# Jika deploy di Streamlit Cloud, simpan key di st.secrets
api_key = None
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    # fallback ke .env / environment variable lokal
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("GROQ_API_KEY tidak ditemukan. Simpan key di Streamlit Secrets atau .env.")
    st.stop()

client = Groq(api_key=api_key)

# ====== 2️⃣ File Cek ======
if not os.path.exists("users.csv"):
    pd.DataFrame(columns=["email", "password", "total_budget"]).to_csv("users.csv", index=False)
if not os.path.exists("transactions.csv"):
    pd.DataFrame(columns=["user", "tanggal", "kategori", "jumlah"]).to_csv("transactions.csv", index=False)

# ====== 3️⃣ Fungsi Utility ======
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# ====== 4️⃣ Tampilan Login / Signup ======
st.set_page_config(page_title="FinSmart AI", page_icon="💰")
st.title("💰 FinSmart AI - Manajemen Keuangan Pintar")

menu = st.sidebar.selectbox("Navigasi", ["Login", "Sign Up", "Dashboard"])

# ====== Sign Up ======
if menu == "Sign Up":
    st.subheader("🆕 Buat Akun Baru")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    total_budget = st.number_input("Total Budget Awal (Rp)", step=1000, value=0)
    signup_btn = st.button("Daftar")

    if signup_btn:
        users = pd.read_csv("users.csv")
        if email in users["email"].values:
            st.warning("❗ Email sudah terdaftar.")
        else:
            hashed_pw = hash_password(password)
            new_user = pd.DataFrame([[email, hashed_pw, total_budget]], columns=["email", "password", "total_budget"])
            users = pd.concat([users, new_user], ignore_index=True)
            users.to_csv("users.csv", index=False)
            st.success("✅ Akun berhasil dibuat! Silakan login.")

# ====== Login ======
elif menu == "Login":
    st.subheader("🔑 Login ke Akun")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")

    if login_btn:
        users = pd.read_csv("users.csv")
        if email in users["email"].values:
            user_data = users[users["email"] == email].iloc[0]
            if verify_password(password, user_data["password"]):
                st.session_state["logged_in"] = True
                st.session_state["user"] = email
                st.success(f"✅ Selamat datang, {email}!")
            else:
                st.error("❌ Password salah.")
        else:
            st.error("❌ Email tidak ditemukan.")

# ====== Dashboard (Setelah Login) ======
elif menu == "Dashboard":
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.warning("⚠️ Silakan login terlebih dahulu.")
    else:
        user = st.session_state["user"]
        st.subheader(f"📊 Dashboard - {user}")

        # ====== Load Data Transaksi User ======
        df = pd.read_csv("transactions.csv")
        user_data = df[df["user"] == user]

        # ====== Form Tambah Transaksi ======
        st.subheader("🧾 Tambah Transaksi Baru")
        with st.form("tambah_transaksi", clear_on_submit=True):
            tanggal = st.date_input("Tanggal", datetime.now())
            kategori = st.selectbox("Kategori", ["Makanan", "Transportasi", "Hiburan", "Tagihan", "Gaji", "Lainnya"])
            jumlah = st.number_input("Jumlah (positif = pengeluaran, negatif = pemasukan)", step=1000)
            submit = st.form_submit_button("💾 Simpan Transaksi")

        if submit:
            new_row = pd.DataFrame([{
                "user": user,
                "tanggal": tanggal,
                "kategori": kategori,
                "jumlah": jumlah
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv("transactions.csv", index=False)
            st.success("✅ Transaksi berhasil disimpan!")

            # update user_data agar tampilan langsung berubah
            user_data = df[df["user"] == user]

        # ====== Tampilkan Data User ======
        st.subheader("📋 Riwayat Transaksi")
        st.dataframe(user_data)

        if not user_data.empty:
            pengeluaran = user_data[user_data["jumlah"] > 0]["jumlah"].sum()
            pemasukan = abs(user_data[user_data["jumlah"] < 0]["jumlah"].sum())
            sisa = pemasukan - pengeluaran

            st.metric("Total Pemasukan", f"Rp {pemasukan:,.0f}")
            st.metric("Total Pengeluaran", f"Rp {pengeluaran:,.0f}")
            st.metric("Sisa Budget", f"Rp {sisa:,.0f}")

            # ====== Analisis AI ======
            st.subheader("🧠 Analisis Keuangan AI")
            prompt = f"""
Analisis keuangan user {user}:
- Total pemasukan: {pemasukan}
- Total pengeluaran: {pengeluaran}
- Sisa budget: {sisa}

Berikan 3 saran keuangan pribadi untuk minggu depan.
"""

            if st.button("Analisis Sekarang"):
                with st.spinner("AI sedang menganalisis..."):
                    # Panggilan ke Groq: endpoint chat-style (sesuaikan bila SDK berbeda)
                    response = client.chat.completions.create(
                        model="llama3-8b-8192",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.success("✅ Analisis Selesai")
                    st.write(response.choices[0].message.content)
        else:
            st.info("Belum ada transaksi. Tambahkan data untuk analisis AI.")
