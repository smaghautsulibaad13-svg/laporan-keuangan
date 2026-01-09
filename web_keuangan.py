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
st.set_page_config(page_title="MyFinance Pro v2.4", layout="wide")
DB_FILE = "data_keuangan_web.xlsx"

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        for col in ["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah"]:
            if col not in df.columns: df[col] = ""
        df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors='coerce').fillna(0).astype(int)
        saldo_list = []
        curr = 0
        for _, r in df.iterrows():
            curr = curr + r["Jumlah"] if r["Tipe"] == "Pemasukan" else curr - r["Jumlah"]
            saldo_list.append(curr)
        df["Saldo"] = saldo_list
        return df
    return pd.DataFrame(columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo"])

# --- FUNGSI GENERATE PDF DENGAN TANDA TANGAN ---
def generate_pdf(dataframe, custom_title):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Judul & Info
    elements.append(Paragraph(f"<b>{custom_title.upper()}</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # 1. Tabel Utama + Summary
    total_in = dataframe[dataframe["Tipe"] == "Pemasukan"]["Jumlah"].sum()
    total_out = dataframe[dataframe["Tipe"] == "Pengeluaran"]["Jumlah"].sum()
    saldo_akhir = total_in - total_out

    data_tabel = [["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo"]]
    for _, row in dataframe.iterrows():
        data_tabel.append([str(row['Tanggal']), row['Keterangan'], row['Tipe'], row['Metode'], f"{int(row['Jumlah']):,}", f"{int(row['Saldo']):,}"])
    
    data_tabel.append(["", "TOTAL PEMASUKAN", "", "", f"{int(total_in):,}", ""])
    data_tabel.append(["", "TOTAL PENGELUARAN", "", "", f"{int(total_out):,}", ""])
    data_tabel.append(["", "SALDO AKHIR", "", "", "", f"{int(saldo_akhir):,}"])
    
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

    # 2. BAGIAN TANDA TANGAN
    # Setting Style Tanda Tangan
    style_ttd = ParagraphStyle(name='TTD', fontSize=10, alignment=TA_CENTER)
    
    # Tanggal di atas tanda tangan
    tgl_skrg = datetime.now().strftime("%d %B %Y")
    elements.append(Paragraph(f"Jakarta, {tgl_skrg}", ParagraphStyle(name='Tgl', fontSize=10, alignment=TA_CENTER)))
    elements.append(Spacer(1, 15))

    # Struktur Tanda Tangan (Gunakan Tabel tanpa border)
    data_ttd = [
        [Paragraph("Yang Menyerahkan,", style_ttd), Paragraph("Yang Menerima,", style_ttd)],
        ["", ""], # Ruang Tanda Tangan
        ["", ""], 
        ["", ""],
        [Paragraph("<b>(Yaumil Mubarrok)</b>", style_ttd), Paragraph("<b>(Ustadzah Sofwatunnufus, S.E)</b>", style_ttd)]
    ]
    
    table_ttd = Table(data_ttd, colWidths=[250, 250])
    table_ttd.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table_ttd)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- TAMPILAN WEB ---
df = load_data()
st.title("💰 LAPORAN ADMINISTRASI KEUANGAN PPGI")

with st.sidebar:
    st.header("Input Transaksi")
    with st.form("input_form", clear_on_submit=True):
        tgl = st.date_input("Tanggal", datetime.now())
        ket = st.text_input("Keterangan")
        tipe = st.selectbox("Tipe", ["Pemasukan", "Pengeluaran"])
        metode = st.selectbox("Metode", ["Cash", "Transfer"])
        jml = st.number_input("Jumlah (Rp)", min_value=0, step=1000)
        if st.form_submit_button("Simpan"):
            if ket:
                new_row = pd.DataFrame([[tgl.strftime("%Y-%m-%d"), ket, tipe, metode, int(jml)]], columns=["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah"])
                df_to_save = pd.concat([df.drop(columns=['Saldo'], errors='ignore'), new_row], ignore_index=True)
                df_to_save.to_excel(DB_FILE, index=False)
                st.rerun()

# Metrics Dashboard
t_in, t_out = df[df["Tipe"]=="Pemasukan"]["Jumlah"].sum(), df[df["Tipe"]=="Pengeluaran"]["Jumlah"].sum()
c1, c2, c3 = st.columns(3)
c1.metric("Pemasukan", f"Rp {t_in:,}")
c2.metric("Pengeluaran", f"Rp {t_out:,}", delta_color="inverse")
c3.metric("Saldo", f"Rp {t_in-t_out:,}")

st.divider()

# Download PDF
st.subheader("🖨️ Cetak Laporan Resmi")
judul_pdf = st.text_input("Judul Laporan:", "Laporan Keuangan Harian")
if not df.empty:
    pdf_file = generate_pdf(df, judul_pdf)
    st.download_button("📥 Download PDF Ber-Tanda Tangan", pdf_file, file_name=f"{judul_pdf}.pdf")

st.divider()

# Tabel
st.subheader("📊 Riwayat Transaksi")
if not df.empty:
    header = st.columns([1.5, 3, 1, 1, 1.5, 1.5, 0.5])
    for c, f in zip(header, ["Tanggal", "Keterangan", "Tipe", "Metode", "Jumlah", "Saldo", "Hapus"]):
        c.markdown(f"**{f}**")
    for i, r in df.iloc[::-1].iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 3, 1, 1, 1.5, 1.5, 0.5])
        c1.write(r["Tanggal"]); c2.write(r["Keterangan"]); c3.write(r["Tipe"])
        c4.write(r["Metode"]); c5.write(f"{r['Jumlah']:,}"); c6.write(f"**{r['Saldo']:,}**")
        if c7.button("🗑️", key=f"d_{i}"):
            df.drop(i).drop(columns=['Saldo'], errors='ignore').to_excel(DB_FILE, index=False)

            st.rerun()
