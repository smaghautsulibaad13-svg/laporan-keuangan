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

# --- 1. KONFIGURASI ---
st.set_page_config(page_title="Sistem Keuangan Pro v6.1", layout="wide")
DB_FILE = "data_keuangan_final.xlsx"

# --- 2. FUNGSI LOAD DATA ---
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

df_raw = load_data()

# --- 3. INISIALISASI SESSION STATE (Kunci Agar Tidak Nge-reset) ---
# Simpan daftar dompet di session agar tidak hilang saat refresh
if 'list_dompet' not in st.session_state:
    existing = df_raw["Dompet"].unique().tolist() if not df_raw.empty else []
    if "Kas Utama" not in existing:
        existing.insert(0, "Kas Utama")
    st.session_state.list_dompet = existing

if 'dompet_aktif' not in st.session_state:
    st.session_state.dompet_aktif = "Kas Utama"

# --- 4. FUNGSI PDF ---
def generate_pdf(dataframe, judul, nama_dompet):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph(f"<b>{judul.upper()}</b>", styles['Title']))
    elements.append(Paragraph(f"<center>Sumber Dana: {nama_dompet}</center>", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo"]]
    saldo_temp = 0
    df_pdf = dataframe.sort_values("Tanggal")
    for _, r in df_pdf.iterrows():
        saldo_temp = saldo_temp + r['Jumlah'] if r['Tipe'] == "Pemasukan" else saldo_temp - r['Jumlah']
        data.append([str(r['Tanggal']), r['Keterangan'], r['Tipe'], r['Metode'], f"{int(r['Jumlah']):,}", f"{int(saldo_temp):,}"])
    
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

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("📂 Kelola Dompet")
    nama_baru = st.text_input("Nama Dompet/Acara Baru:")
    if st.button("Tambah Dompet"):
        if nama_baru and nama_baru not in st.session_state.list_dompet:
            st.session_state.list_dompet.append(nama_baru)
            st.success(f"Dompet {nama_baru} Ditambahkan!")
            st.rerun()
    
    st.divider()
    st.header("➕ Input Transaksi")
    with st.form("input_form", clear_on_submit=True):
        f_tgl = st.date_input("Tanggal", datetime.now())
        # Dropdown input ngambil dari session_state
        f_dompet = st.selectbox("Pilih Dompet:", st.session_state.list_dompet)
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
                st.success(f"Berhasil simpan ke {f_dompet}!")
                st.rerun()

# --- 6. TAMPILAN UTAMA ---
st.title("💸 Dashboard Keuangan Multi-Dompet")

# Sinkronisasi pilihan dompet agar tidak "mental"
idx_def = st.session_state.list_dompet.index(st.session_state.dompet_aktif) if st.session_state.dompet_aktif in st.session_state.list_dompet else 0
pilihan_view = st.selectbox("Pilih Laporan Dompet:", st.session_state.list_dompet, index=idx_def)
st.session_state.dompet_aktif = pilihan_view

# Filter Data
df_view = df_raw[df_raw["Dompet"] == pilihan_view].copy()
df_view = df_view.sort_values("Tanggal")

# Hitung Saldo
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
c3.metric(f"Saldo Akhir", f"Rp {t_in - t_out:,}")

st.divider()

# PDF Section
if not df_view.empty:
    st.subheader("🖨️ Cetak PDF Resmi")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        judul_pdf = st.text_input("Judul Laporan:", f"Laporan Keuangan {pilihan_view}")
    with col_b:
        st.write(" ")
        pdf_raw = generate_pdf(df_view, judul_pdf, pilihan_view)
        st.download_button("📥 Download PDF", data=pdf_raw, file_name=f"Laporan_{pilihan_view}.pdf")
else:
    st.info(f"Dompet {pilihan_view} masih kosong. Silakan input transaksi di sidebar.")

st.divider()

# Tabel Riwayat
st.subheader(f"📜 Riwayat Transaksi: {pilihan_view}")
if not df_view.empty:
    h = st.columns([1.5, 3, 1, 1, 1.5, 1.5, 0.5])
    for col, txt in zip(h, ["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo", "X"]):
        col.markdown(f"**{txt}**")
    
    for i, r in df_view.iloc[::-1].iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 3, 1, 1, 1.5, 1.5, 0.5])
        c1.write(r["Tanggal"]); c2.write(r["Keterangan"]); c3.write(r["Tipe"])
        c4.write(r["Metode"]); c5.write(f"{r['Jumlah']:,}"); c6.write(f"**{r['Saldo']:,}**")
        if c7.button("🗑️", key=f"del_{i}"):
            df_raw.drop(i).to_excel(DB_FILE, index=False)
            st.rerun()
