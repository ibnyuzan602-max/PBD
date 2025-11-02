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

# ====== 1️⃣ Load API Key (Streamlit Secrets > env) ======
api_key = None
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
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
    cols = []
    for c in df.columns:
        c2 = c.strip().replace(" ", "_")
        low = c2.lower()
        if low in ("totalbudget", "total_budget"):
            cols.append("Total_Budget")
        elif low == "email":
            cols.append("Email")
        elif low == "password":
            cols.append("Password")
        elif low == "user":
            cols.append("User")
        elif low in ("tanggal", "date"):
            cols.append("Tanggal")
        elif low in ("kategori", "category"):
            cols.append("Kategori")
        elif low in ("jumlah", "amount"):
            cols.append("Jumlah")
        else:
            cols.append(c2[0].upper() + c2[1:] if len(c2) > 0 else c2)
    df.columns = cols
    return df

# Pastikan file CSV ada
if not os.path.exists("users.csv"):
    pd.DataFrame(columns=EXPECTED_USERS_COLS).to_csv("users.csv", index=False)
if not os.path.exists("transactions.csv"):
    pd.DataFrame(columns=EXPECTED_TRANSACTIONS_COLS).to_csv("transactions.csv", index=False)

# Load + normalisasi CSV
def load_or_create_csv(filename, expected_cols):
    try:
        df = pd.read_csv(filename)
        df = normalize_columns(df)
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        df = df[expected_cols]
        df.to_csv(filename, index=False)
        return df
    except Exception:
        df = pd.DataFrame(columns=expected_cols)
        df.to_csv(filename, index=False)
        return df

users_df = load_or_create_csv("users.csv", EXPECTED_USERS_COLS)
trans_df = load_or_create_csv("transactions.csv", EXPECTED_TRANSACTIONS_COLS)

# ====== 3️⃣ Utility Functions ======
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
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

# ====== Login ======
elif menu == "Login":
    st.subheader("🔑 Login ke Akun")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")

    if login_btn:
        users = load_or_create_csv("users.csv", EXPECTED_USERS_COLS)
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

# ====== Dashboard ======
elif menu == "Dashboard":
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.warning("⚠️ Silakan login terlebih dahulu.")
    else:
        user = st.session_state["user"]
        st.subheader(f"📊 Dashboard - {user}")

        # Load data transaksi user
        df = load_or_create_csv("transactions.csv", EXPECTED_TRANSACTIONS_COLS)
        user_data = df[df["User"] == user]

        # Tambah transaksi
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
            user_data = df[df["User"] == user]

        # Tampilkan data
        st.subheader("📋 Riwayat Transaksi")
        st.dataframe(user_data)

        # Tombol ekspor
        if not user_data.empty:
            csv = user_data.to_csv(index=False).encode('utf-8')
            st.download_button("📤 Ekspor ke CSV", csv, file_name="riwayat_transaksi.csv", mime="text/csv")

            # Hitung data keuangan
            pengeluaran = user_data[user_data["Jumlah"] > 0]["Jumlah"].sum()
            pemasukan = abs(user_data[user_data["Jumlah"] < 0]["Jumlah"].sum())
            sisa = pemasukan - pengeluaran

            st.metric("Total Pemasukan", f"Rp {pemasukan:,.0f}")
            st.metric("Total Pengeluaran", f"Rp {pengeluaran:,.0f}")
            st.metric("Sisa Budget", f"Rp {sisa:,.0f}")

            # Ambil total budget user
            total_budget = users_df.loc[users_df["Email"] == user, "Total_Budget"].iloc[0]
            if isinstance(total_budget, str) and total_budget.strip() == "":
                total_budget = 0
            try:
                total_budget = float(total_budget)
            except:
                total_budget = 0

            # 🔔 Notifikasi overspending
            if pengeluaran > 0.8 * total_budget and total_budget > 0:
                st.warning("⚠️ Pengeluaran Anda sudah melebihi 80% dari total budget!")

            # ====== 📊 Grafik ======
            st.subheader("📈 Grafik Pengeluaran per Kategori")
            pengeluaran_kategori = user_data[user_data["Jumlah"] > 0].groupby("Kategori")["Jumlah"].sum()
            if not pengeluaran_kategori.empty:
                fig, ax = plt.subplots()
                pengeluaran_kategori.plot(kind="bar", ax=ax)
                ax.set_ylabel("Jumlah (Rp)")
                ax.set_xlabel("Kategori")
                ax.set_title("Pengeluaran per Kategori")
                st.pyplot(fig)
            else:
                st.info("Belum ada data pengeluaran untuk ditampilkan dalam grafik.")

            # ====== 🧠 Analisis AI ======
            st.subheader("🧠 Analisis Keuangan AI")
            kategori_terbanyak = (
                pengeluaran_kategori.idxmax() if not pengeluaran_kategori.empty else "Belum ada"
            )
            prompt = f"""
Analisis keuangan user {user}:
- Total pemasukan: {pemasukan}
- Total pengeluaran: {pengeluaran}
- Sisa budget: {sisa}
- Kategori pengeluaran terbesar: {kategori_terbanyak}
Berikan 3 saran keuangan pribadi dan langkah konkret untuk minggu depan.
"""

            if st.button("Analisis Sekarang 🧩"):
                with st.spinner("AI sedang menganalisis..."):
                    try:
                        response = client.chat.completions.create(
                            model="openai/gpt-oss-20b",
                            messages=[
                                {"role": "system", "content": "Kamu adalah asisten keuangan pribadi yang memberi saran cerdas dan praktis."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.7,
                            max_tokens=500
                        )
                        hasil = response.choices[0].message.content
                        st.success("✅ Analisis Selesai")
                        st.write(hasil)
                    except Exception as e:
                        st.error("❌ Gagal menganalisis dengan Groq API.")
                        st.exception(e)
        else:
            st.info("Belum ada transaksi. Tambahkan data untuk analisis AI.")
