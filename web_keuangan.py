import streamlit as st
import pandas as pd
from datetime import datetime
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import io

# --- 1. KONFIGURASI AWAL ---
st.set_page_config(page_title="Sistem Keuangan Pro", layout="wide")
DB_FILE = "data_keuangan_final.xlsx"

# --- 2. LOGIKA PENYIMPANAN DATA ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            if "Dompet" not in df.columns: df["Dompet"] = "Kas Utama"
            df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors='coerce').fillna(0).astype(int)
            return df
        except:
            return pd.DataFrame(columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Dompet", "Jumlah"])
    return pd.DataFrame(columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Dompet", "Jumlah"])

# Load data awal
df_raw = load_data()

# Ambil list dompet yang unik
list_dompet = df_raw["Dompet"].unique().tolist()
if "Kas Utama" not in list_dompet:
    list_dompet.insert(0, "Kas Utama")

# --- 3. FIX BUG MENTAL (SESSION STATE) ---
if 'dompet_aktif' not in st.session_state:
    st.session_state.dompet_aktif = "Kas Utama"

# --- 4. FUNGSI PDF ---
def generate_pdf(dataframe, judul, nama_dompet):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    elements.append(Paragraph(f"<b>{judul.upper()}</b>", styles['Title']))
    elements.append(Paragraph(f"<center>Sumber Dana: {nama_dompet}</center>", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Tabel Data
    data = [["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo"]]
    saldo_temp = 0
    df_pdf = dataframe.sort_values("Tanggal")
    for _, r in df_pdf.iterrows():
        saldo_temp = saldo_temp + r['Jumlah'] if r['Tipe'] == "Pemasukan" else saldo_temp - r['Jumlah']
        data.append([str(r['Tanggal']), r['Keterangan'], r['Tipe'], r['Metode'], f"{int(r['Jumlah']):,}", f"{int(saldo_temp):,}"])
    
    # Total
    t_in = df_pdf[df_pdf["Tipe"]=="Pemasukan"]["Jumlah"].sum()
    t_out = df_pdf[df_pdf["Tipe"]=="Pengeluaran"]["Jumlah"].sum()
    data.append(["", "TOTAL MASUK", "", "", f"{int(t_in):,}", ""])
    data.append(["", "TOTAL KELUAR", "", "", f"{int(t_out):,}", ""])
    data.append(["", "SALDO AKHIR", "", "", "", f"{int(t_in-t_out):,}"])

    t = Table(data, colWidths=[65, 160, 65, 65, 75, 75])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.dodgerblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(t)

    # Tanda Tangan
    elements.append(Spacer(1, 40))
    st_ttd = ParagraphStyle(name='T', alignment=TA_CENTER, fontSize=10)
    elements.append(Paragraph(f"Jakarta, {datetime.now().strftime('%d %B %Y')}", st_ttd))
    elements.append(Spacer(1, 15))
    ttd_table = [[Paragraph("Yang Menyerahkan,", st_ttd), Paragraph("Yang Menerima,", st_ttd)],
                 ["", ""], [""], [""],
                 [Paragraph("<b>(Yaumil Mubarrok)</b>", st_ttd), Paragraph("<b>(Ustadzah Sofwatunnufus, S.E)</b>", st_ttd)]]
    elements.append(Table(ttd_table, colWidths=[250, 250]))
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- 5. TAMPILAN SIDEBAR ---
with st.sidebar:
    st.header("➕ Input Data")
    with st.form("input_form", clear_on_submit=True):
        f_tgl = st.date_input("Tanggal", datetime.now())
        f_dompet = st.selectbox("Pilih Dompet:", list_dompet)
        f_ket = st.text_input("Keterangan")
        f_tipe = st.selectbox("Tipe", ["Pemasukan", "Pengeluaran"])
        f_metode = st.selectbox("Metode", ["Cash", "Transfer"])
        f_jml = st.number_input("Jumlah (Rp)", min_value=0, step=1000)
        
        if st.form_submit_button("Simpan Transaksi"):
            if f_ket:
                new_row = pd.DataFrame([[f_tgl.strftime("%Y-%m-%d"), f_ket, f_tipe, f_metode, f_dompet, int(f_jml)]], 
                                       columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Dompet", "Jumlah"])
                df_save = pd.concat([df_raw, new_row], ignore_index=True)
                df_save.to_excel(DB_FILE, index=False)
                st.success("Tersimpan!")
                st.rerun()

    st.divider()
    st.header("📂 Dompet Baru")
    nama_baru = st.text_input("Nama Acara/Dompet:")
    if st.button("Tambah"):
        if nama_baru and nama_baru not in list_dompet:
            # Simpan satu baris dummy biar dompetnya terdaftar di Excel
            dummy = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), "Buka Dompet Baru", "Pemasukan", "Cash", nama_baru, 0]], 
                                 columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Dompet", "Jumlah"])
            pd.concat([df_raw, dummy], ignore_index=True).to_excel(DB_FILE, index=False)
            st.success("Berhasil!")
            st.rerun()

# --- 6. TAMPILAN UTAMA ---
st.title("💸 Dashboard Keuangan")

# Pilih Dompet (Gunakan session_state biar gak pindah sendiri)
idx_default = list_dompet.index(st.session_state.dompet_aktif) if st.session_state.dompet_aktif in list_dompet else 0
pilihan_view = st.selectbox("Pilih Dompet yang ingin dilihat:", list_dompet, index=idx_default)
st.session_state.dompet_aktif = pilihan_view

# Filter Data
df_view = df_raw[df_raw["Dompet"] == pilihan_view].copy()
df_view = df_view.sort_values("Tanggal")

# Hitung Saldo Berjalan
saldo_walk = []
s = 0
for _, r in df_view.iterrows():
    s = s + r["Jumlah"] if r["Tipe"] == "Pemasukan" else s - r["Jumlah"]
    saldo_walk.append(s)
df_view["Saldo"] = saldo_walk

# Metrics
t_in = df_view[df_view["Tipe"]=="Pemasukan"]["Jumlah"].sum()
t_out = df_view[df_view["Tipe"]=="Pengeluaran"]["Jumlah"].sum()

c1, c2, c3 = st.columns(3)
c1.metric("Total Masuk", f"Rp {t_in:,}")
c2.metric("Total Keluar", f"Rp {t_out:,}")
c3.metric(f"Saldo {pilihan_view}", f"Rp {t_in - t_out:,}")

st.divider()

# PDF Section
if not df_view.empty:
    st.subheader("🖨️ Cetak PDF")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        judul_pdf = st.text_input("Judul Laporan:", f"Laporan Keuangan {pilihan_view}")
    with col_b:
        st.write(" ")
        pdf_raw = generate_pdf(df_view, judul_pdf, pilihan_view)
        st.download_button("📥 Download", data=pdf_raw, file_name=f"Laporan_{pilihan_view}.pdf")

st.divider()

# Tabel Riwayat
st.subheader(f"📜 Riwayat Transaksi: {pilihan_view}")
if not df_view.empty:
    # Header
    h = st.columns([1.5, 3, 1, 1, 1.5, 1.5, 0.5])
    n = ["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo", "X"]
    for col, txt in zip(h, n): col.markdown(f"**{txt}**")
    
    # Body (Terbaru di atas)
    for i, r in df_view.iloc[::-1].iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 3, 1, 1, 1.5, 1.5, 0.5])
        c1.write(r["Tanggal"]); c2.write(r["Keterangan"]); c3.write(r["Tipe"])
        c4.write(r["Metode"]); c5.write(f"{r['Jumlah']:,}"); c6.write(f"**{r['Saldo']:,}**")
        if c7.button("🗑️", key=f"del_{i}"):
            df_raw.drop(i).to_excel(DB_FILE, index=False)
            st.rerun()
else:
    st.info("Belum ada transaksi di dompet ini.")
