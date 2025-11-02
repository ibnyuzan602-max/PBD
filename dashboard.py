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

# ====== 2️⃣ File Cek + Normalisasi Kolom ======
EXPECTED_USERS_COLS = ["Email", "Password", "Total_Budget"]
EXPECTED_TRANSACTIONS_COLS = ["User", "Tanggal", "Kategori", "Jumlah"]

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalisasi nama kolom: trim, ganti spasi->underscore, ubah huruf sesuai pola
    Lalu sesuaikan beberapa variasi umum seperti 'Total Budget' -> 'Total_Budget'.
    """
    cols = []
    for c in df.columns:
        c2 = c.strip()
        # ganti spasi ke underscore, hapus double underscore
        c2 = c2.replace(" ", "_")
        # beberapa penyesuaian kapitalisasi: kita ingin PascalCase/Exact as expected
        # buat variasi umum menjadi standar:
        # contoh: totalbudget, total_budget, Total_Budget -> Total_Budget
        low = c2.lower()
        if low in ("totalbudget", "total_budget", "total_budget"):
            cols.append("Total_Budget")
        elif low in ("email",):
            cols.append("Email")
        elif low in ("password",):
            cols.append("Password")
        elif low in ("user",):
            cols.append("User")
        elif low in ("tanggal", "date"):
            cols.append("Tanggal")
        elif low in ("kategori", "category"):
            cols.append("Kategori")
        elif low in ("jumlah", "amount"):
            cols.append("Jumlah")
        else:
            # fallback: capitalize first letter, keep underscores
            cols.append(c2[0].upper() + c2[1:] if len(c2) > 0 else c2)
    df.columns = cols
    return df

# Pastikan file ada; buat jika belum
if not os.path.exists("users.csv"):
    pd.DataFrame(columns=EXPECTED_USERS_COLS).to_csv("users.csv", index=False)
if not os.path.exists("transactions.csv"):
    pd.DataFrame(columns=EXPECTED_TRANSACTIONS_COLS).to_csv("transactions.csv", index=False)

# Baca dan normalisasi users.csv
try:
    users_df = pd.read_csv("users.csv")
    users_df = normalize_columns(users_df)
    # pastikan kolom ada sesuai expected (jika kolom hilang, tambahkan)
    for col in EXPECTED_USERS_COLS:
        if col not in users_df.columns:
            users_df[col] = ""
    users_df = users_df[EXPECTED_USERS_COLS]
    users_df.to_csv("users.csv", index=False)
except Exception:
    # jika csv korup atau kosong, buat ulang
    users_df = pd.DataFrame(columns=EXPECTED_USERS_COLS)
    users_df.to_csv("users.csv", index=False)

# Baca dan normalisasi transactions.csv
try:
    trans_df = pd.read_csv("transactions.csv")
    trans_df = normalize_columns(trans_df)
    for col in EXPECTED_TRANSACTIONS_COLS:
        if col not in trans_df.columns:
            trans_df[col] = ""
    trans_df = trans_df[EXPECTED_TRANSACTIONS_COLS]
    trans_df.to_csv("transactions.csv", index=False)
except Exception:
    trans_df = pd.DataFrame(columns=EXPECTED_TRANSACTIONS_COLS)
    trans_df.to_csv("transactions.csv", index=False)

# ====== 3️⃣ Fungsi Utility ======
def hash_password(password: str) -> str:
    """Hash password dengan bcrypt dan return decoded string."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password plaintext terhadap hashed bcrypt."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

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
        users = normalize_columns(users)
        # pastikan kolom tetap sesuai
        for col in EXPECTED_USERS_COLS:
            if col not in users.columns:
                users[col] = ""
        users = users[EXPECTED_USERS_COLS]

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

# ====== Login ======
elif menu == "Login":
    st.subheader("🔑 Login ke Akun")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")

    if login_btn:
        users = pd.read_csv("users.csv")
        users = normalize_columns(users)
        # pastikan kolom ada
        for col in EXPECTED_USERS_COLS:
            if col not in users.columns:
                users[col] = ""
        users = users[EXPECTED_USERS_COLS]

        if email in users["Email"].values:
            user_data = users[users["Email"] == email].iloc[0]
            if verify_password(password, user_data["Password"]):
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
        df = normalize_columns(df)
        for col in EXPECTED_TRANSACTIONS_COLS:
            if col not in df.columns:
                df[col] = ""
        df = df[EXPECTED_TRANSACTIONS_COLS]

        user_data = df[df["User"] == user]

        # ====== Form Tambah Transaksi ======
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

            # update user_data agar tampilan langsung berubah
            user_data = df[df["User"] == user]

        # ====== Tampilkan Data User ======
        st.subheader("📋 Riwayat Transaksi")
        st.dataframe(user_data)

        if not user_data.empty:
            pengeluaran = user_data[user_data["Jumlah"] > 0]["Jumlah"].sum()
            pemasukan = abs(user_data[user_data["Jumlah"] < 0]["Jumlah"].sum())
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
                    # tampilkan isi jawaban
                    # (jika struktur response berbeda, adjust access path)
                    try:
                        st.write(response.choices[0].message.content)
                    except Exception:
                        st.write(response)

        else:
            st.info("Belum ada transaksi. Tambahkan data untuk analisis AI.")
