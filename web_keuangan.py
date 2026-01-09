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

# --- KONFIGURASI ---
st.set_page_config(page_title="Finance System v4.1", layout="wide")
DB_FILE = "data_keuangan_pro.xlsx"

# --- FUNGSI LOAD DATA ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            if "Kategori" not in df.columns:
                df["Kategori"] = "Kas"
            df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors='coerce').fillna(0).astype(int)
            return df
        except:
            return pd.DataFrame(columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Kategori", "Jumlah"])
    return pd.DataFrame(columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Kategori", "Jumlah"])

# --- FUNGSI HITUNG SALDO BERJALAN ---
def calculate_with_balance(df_filtered):
    if df_filtered.empty:
        return df_filtered
    df_res = df_filtered.copy().sort_values(by="Tanggal", ascending=True)
    saldo_list = []
    curr = 0
    for _, r in df_res.iterrows():
        curr = curr + r["Jumlah"] if r["Tipe"] == "Pemasukan" else curr - r["Jumlah"]
        saldo_list.append(curr)
    df_res["Saldo"] = saldo_list
    return df_res

# --- FUNGSI GENERATE PDF ---
def generate_pdf(dataframe, custom_title, kategori_nama):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header PDF
    elements.append(Paragraph(f"<b>{custom_title.upper()}</b>", styles['Title']))
    elements.append(Paragraph(f"<center>Kategori Laporan: {kategori_nama}</center>", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Data Tabel
    data_tabel = [["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo"]]
    for _, row in dataframe.iterrows():
        data_tabel.append([
            str(row['Tanggal']), 
            row['Keterangan'], 
            row['Tipe'], 
            row['Metode'], 
            f"{int(row['Jumlah']):,}", 
            f"{int(row['Saldo']):,}"
        ])
    
    # Perhitungan Total
    t_in = dataframe[dataframe["Tipe"]=="Pemasukan"]["Jumlah"].sum()
    t_out = dataframe[dataframe["Tipe"]=="Pengeluaran"]["Jumlah"].sum()
    
    data_tabel.append(["", "TOTAL MASUK", "", "", f"{int(t_in):,}", ""])
    data_tabel.append(["", "TOTAL KELUAR", "", "", f"{int(t_out):,}", ""])
    data_tabel.append(["", f"SALDO AKHIR {kategori_nama.upper()}", "", "", "", f"{int(t_in-t_out):,}"])

    t = Table(data_tabel, colWidths=[65, 160, 65, 65, 75, 75])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.dodgerblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, -3), (-1, -1), colors.whitesmoke),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    
    # Bagian Tanda Tangan
    elements.append(Spacer(1, 40))
    style_ttd = ParagraphStyle(name='TTD', fontSize=10, alignment=TA_CENTER)
    tgl_skrg = datetime.now().strftime("%d %B %Y")
    elements.append(Paragraph(f"Jakarta, {tgl_skrg}", style_ttd))
    elements.append(Spacer(1, 15))
    
    data_ttd = [
        [Paragraph("Yang Menyerahkan,", style_ttd), Paragraph("Yang Menerima,", style_ttd)],
        ["", ""], [""], [""],
        [Paragraph("<b>(Yaumil Mubarrok)</b>", style_ttd), Paragraph("<b>(Ustadzah Sofwatunnufus, S.E)</b>", style_ttd)]
    ]
    elements.append(Table(data_ttd, colWidths=[250, 250]))
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- LOGIKA APLIKASI ---
df_raw = load_data()

st.title("💰 Finance System (Multi-Kategori)")

# 1. Filter Kategori
view_kategori = st.radio("Pilih Tampilan Laporan:", ["Kas", "Acara"], horizontal=True)

# Filter dan Hitung Saldo
df_filtered = df_raw[df_raw["Kategori"] == view_kategori]
df_display = calculate_with_balance(df_filtered)

# Sidebar Input
with st.sidebar:
    st.header("Tambah Data Baru")
    with st.form("input_form", clear_on_submit=True):
        tgl = st.date_input("Tanggal", datetime.now())
        kat_input = st.selectbox("Simpan ke Kategori:", ["Kas", "Acara"])
        ket = st.text_input("Keterangan")
        tipe = st.selectbox("Tipe", ["Pemasukan", "Pengeluaran"])
        metode = st.selectbox("Metode", ["Cash", "Transfer"])
        jml = st.number_input("Jumlah (Rp)", min_value=0, step=1000)
        
        if st.form_submit_button("Simpan"):
            if ket:
                new_row = pd.DataFrame([[tgl.strftime("%Y-%m-%d"), ket, tipe, metode, kat_input, int(jml)]], 
                                       columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Kategori", "Jumlah"])
                df_to_save = pd.concat([df_raw, new_row], ignore_index=True)
                df_to_save.to_excel(DB_FILE, index=False)
                st.success("Data Berhasil Disimpan!")
                st.rerun()

# Dashboard Metrics
t_in = df_display[df_display["Tipe"]=="Pemasukan"]["Jumlah"].sum()
t_out = df_display[df_display["Tipe"]=="Pengeluaran"]["Jumlah"].sum()

st.subheader(f"📊 Ringkasan Saldo {view_kategori}")
c1, c2, c3 = st.columns(3)
c1.metric("Pemasukan", f"Rp {t_in:,}")
c2.metric("Pengeluaran", f"Rp {t_out:,}", delta_color="inverse")
c3.metric("Saldo Akhir", f"Rp {t_in - t_out:,}")

st.divider()

# --- BAGIAN PDF (DIPERBAIKI) ---
st.subheader(f"🖨️ Cetak Laporan {view_kategori}")
if not df_display.empty:
    col_pdf1, col_pdf2 = st.columns([3, 1])
    with col_pdf1:
        judul_pdf = st.text_input("Judul di PDF:", f"Laporan Keuangan {view_kategori}", key="judul_pdf")
    with col_pdf2:
        st.write(" ") # Spasi agar sejajar
        pdf_data = generate_pdf(df_display, judul_pdf, view_kategori)
        st.download_button(
            label=f"📥 Download PDF {view_kategori}",
            data=pdf_data,
            file_name=f"Laporan_{view_kategori}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
else:
    st.warning(f"Belum ada transaksi di kategori {view_kategori}. Masukkan data dulu biar tombol cetak muncul!")

st.divider()

# Tabel Riwayat
st.subheader(f"📜 Riwayat Transaksi {view_kategori}")
if not df_display.empty:
    # Header Tabel
    h = st.columns([1.5, 3, 1, 1, 1.5, 1.5, 0.8])
    for col, name in zip(h, ["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo", "Hapus"]):
        col.markdown(f"**{name}**")
    
    # Baris Tabel (Data terbaru di atas)
    for i, r in df_display.iloc[::-1].iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 3, 1, 1, 1.5, 1.5, 0.8])
        c1.write(r["Tanggal"])
        c2.write(r["Keterangan"])
        c3.write(r["Tipe"])
        c4.write(r["Metode"])
        c5.write(f"{r['Jumlah']:,}")
        c6.write(f"**{r['Saldo']:,}**")
        if c7.button("🗑️", key=f"del_{i}_{view_kategori}"):
            # Cari index asli di df_raw untuk dihapus
            df_raw = df_raw.drop(i)
            df_raw.to_excel(DB_FILE, index=False)
            st.rerun()
