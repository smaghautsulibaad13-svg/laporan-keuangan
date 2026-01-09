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
st.set_page_config(page_title="Finance Multi-Wallet Pro", layout="wide")
DB_FILE = "data_keuangan_multi_wallet.xlsx"

# --- FUNGSI LOAD DATA ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            # Pastikan kolom Dompet ada
            if "Dompet" not in df.columns:
                df["Dompet"] = "Kas Utama"
            df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors='coerce').fillna(0).astype(int)
            return df
        except:
            return pd.DataFrame(columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Dompet", "Jumlah"])
    return pd.DataFrame(columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Dompet", "Jumlah"])

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
def generate_pdf(dataframe, custom_title, dompet_nama):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph(f"<b>{custom_title.upper()}</b>", styles['Title']))
    elements.append(Paragraph(f"<center>Sumber Dana / Dompet: {dompet_nama}</center>", styles['Normal']))
    elements.append(Spacer(1, 20))

    data_tabel = [["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo"]]
    for _, row in dataframe.iterrows():
        data_tabel.append([str(row['Tanggal']), row['Keterangan'], row['Tipe'], row['Metode'], f"{int(row['Jumlah']):,}", f"{int(row['Saldo']):,}"])
    
    t_in = dataframe[dataframe["Tipe"]=="Pemasukan"]["Jumlah"].sum()
    t_out = dataframe[dataframe["Tipe"]=="Pengeluaran"]["Jumlah"].sum()
    
    data_tabel.append(["", "TOTAL MASUK", "", "", f"{int(t_in):,}", ""])
    data_tabel.append(["", "TOTAL KELUAR", "", "", f"{int(t_out):,}", ""])
    data_tabel.append(["", f"SALDO AKHIR {dompet_nama.upper()}", "", "", "", f"{int(t_in-t_out):,}"])

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
    
    elements.append(Spacer(1, 40))
    style_ttd = ParagraphStyle(name='TTD', fontSize=10, alignment=TA_CENTER)
    tgl_skrg = datetime.now().strftime("%d %B %Y")
    elements.append(Paragraph(f"Jakarta, {tgl_skrg}", style_ttd))
    elements.append(Spacer(1, 15))
    data_ttd = [[Paragraph("Yang Menyerahkan,", style_ttd), Paragraph("Yang Menerima,", style_ttd)],
                ["", ""], [""], [""],
                [Paragraph("<b>(Yaumil Mubarrok)</b>", style_ttd), Paragraph("<b>(Ustadzah Sofwatunnufus, S.E)</b>", style_ttd)]]
    elements.append(Table(data_ttd, colWidths=[250, 250]))
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- LOGIKA APLIKASI ---
df_raw = load_data()

# Ambil daftar dompet yang sudah ada di database
list_dompet_existing = df_raw["Dompet"].unique().tolist() if not df_raw.empty else ["Kas Utama"]
if "Kas Utama" not in list_dompet_existing:
    list_dompet_existing.insert(0, "Kas Utama")

st.title("💰 Finance Multi-Wallet System")

# 1. SIDEBAR: INPUT & MANAJEMEN DOMPET
with st.sidebar:
    st.header("⚙️ Pengaturan Dompet")
    dompet_baru = st.text_input("Tambah Nama Acara/Dompet Baru:")
    if st.button("Tambah Dompet"):
        if dompet_baru and dompet_baru not in list_dompet_existing:
            list_dompet_existing.append(dompet_baru)
            st.success(f"Dompet '{dompet_baru}' siap digunakan!")
        else:
            st.warning("Nama sudah ada atau kosong")

    st.divider()
    st.header("📝 Tambah Transaksi")
    with st.form("form_input", clear_on_submit=True):
        tgl = st.date_input("Tanggal", datetime.now())
        dompet_pilihan = st.selectbox("Pilih Dompet:", list_dompet_existing)
        ket = st.text_input("Keterangan")
        tipe = st.selectbox("Tipe", ["Pemasukan", "Pengeluaran"])
        metode = st.selectbox("Metode", ["Cash", "Transfer"])
        jml = st.number_input("Jumlah (Rp)", min_value=0, step=1000)
        
        if st.form_submit_button("Simpan Transaksi"):
            if ket:
                new_data = pd.DataFrame([[tgl.strftime("%Y-%m-%d"), ket, tipe, metode, dompet_pilihan, int(jml)]], 
                                       columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Dompet", "Jumlah"])
                df_to_save = pd.concat([df_raw, new_data], ignore_index=True)
                df_to_save.to_excel(DB_FILE, index=False)
                st.success(f"Tersimpan di {dompet_pilihan}!")
                st.rerun()

# 2. FILTER TAMPILAN (Dinamis sesuai dompet yang ada)
st.subheader("🔍 Pilih Dompet untuk Dilihat")
view_pilihan = st.selectbox("Lihat Laporan Dompet:", list_dompet_existing)

df_filtered = df_raw[df_raw["Dompet"] == view_pilihan]
df_display = calculate_with_balance(df_filtered)

# 3. DASHBOARD METRICS
t_in = df_display[df_display["Tipe"]=="Pemasukan"]["Jumlah"].sum()
t_out = df_display[df_display["Tipe"]=="Pengeluaran"]["Jumlah"].sum()

c1, c2, c3 = st.columns(3)
c1.metric(f"Total Masuk", f"Rp {t_in:,}")
c2.metric(f"Total Keluar", f"Rp {t_out:,}", delta_color="inverse")
c3.metric(f"Saldo Akhir {view_pilihan}", f"Rp {t_in - t_out:,}")

st.divider()

# 4. CETAK PDF
if not df_display.empty:
    st.subheader(f"🖨️ Cetak Laporan {view_pilihan}")
    col_pdf1, col_pdf2 = st.columns([3, 1])
    with col_pdf1:
        judul_pdf = st.text_input("Judul di PDF:", f"Laporan Keuangan {view_pilihan}")
    with col_pdf2:
        st.write(" ")
        pdf_file = generate_pdf(df_display, judul_pdf, view_pilihan)
        st.download_button(label=f"📥 Download PDF {view_pilihan}", data=pdf_file, 
                           file_name=f"Laporan_{view_pilihan}.pdf", mime="application/pdf")
else:
    st.info(f"Dompet '{view_pilihan}' masih kosong. Belum ada transaksi.")

st.divider()

# 5. TABEL RIWAYAT
st.subheader(f"📜 Detail Transaksi: {view_pilihan}")
if not df_display.empty:
    h = st.columns([1.5, 3, 1, 1, 1.5, 1.5, 0.8])
    for col, name in zip(h, ["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo", "Hapus"]):
        col.markdown(f"**{name}**")
    
    for i, r in df_display.iloc[::-1].iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 3, 1, 1, 1.5, 1.5, 0.8])
        c1.write(r["Tanggal"]); c2.write(r["Keterangan"]); c3.write(r["Tipe"])
        c4.write(r["Metode"]); c5.write(f"{r['Jumlah']:,}"); c6.write(f"**{r['Saldo']:,}**")
        if c7.button("🗑️", key=f"del_{i}_{view_pilihan}"):
            df_raw.drop(i).to_excel(DB_FILE, index=False)
            st.rerun()
