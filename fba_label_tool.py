
import streamlit as st
import pandas as pd
import re
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import inch
from reportlab.lib.units import inch as unit_inch
from io import BytesIO
import pdfplumber

st.title("FBA Label Modifier")

# Upload files
pdf_file = st.file_uploader("Upload FBA Label PDF", type=["pdf"])
csv_file = st.file_uploader("Upload SKU Lookup CSV", type=["csv"])

if pdf_file and csv_file:
    # Load SKU-to-YBS name mapping
    df = pd.read_csv(csv_file)
    sku_to_ybs = df[['SKU', 'YBS Name']].dropna()
    sku_to_ybs_dict = dict(zip(sku_to_ybs['SKU'].astype(str).str.strip(), sku_to_ybs['YBS Name'].astype(str).str.strip()))

    # Patterns
    fba_pattern = re.compile(r"(FBA\d+[A-Z0-9]*([A-Z0-9]{2})U00(\d+))")
    sku_pattern = re.compile(r"Single SKU\s*\n([^\n]+)")
    qty_pattern = re.compile(r"Qty\s+(\d+)")

    output = BytesIO()
    writer = PdfWriter()

    with pdfplumber.open(pdf_file) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            fba_match = fba_pattern.search(text or "")
            sku_match = sku_pattern.search(text or "")
            qty_match = qty_pattern.search(text or "")

            overlay = BytesIO()
            c = canvas.Canvas(overlay, pagesize=(4 * inch, 6 * inch))

            # ID Code and Box
            if fba_match:
                id_code = fba_match.group(2)
                box_number = str(int(fba_match.group(3)))  # remove leading zeros
                label = f"{id_code} - Box {box_number}"
                c.setFont("Helvetica-Bold", 36)
                c.drawString(0.4 * inch, 2.4 * inch, label)

            # SKU
            if sku_match:
                sku = sku_match.group(1).strip()
                c.setFont("Helvetica", 24)
                c.drawString(0.4 * inch, 2.0 * inch, sku)
                ybs_name = sku_to_ybs_dict.get(sku)
                if ybs_name:
                    c.drawString(0.4 * inch, 1.6 * inch, ybs_name)

            # Quantity
            if qty_match:
                qty = qty_match.group(1)
                c.setFont("Helvetica", 24)
                c.drawString(0.4 * inch, 1.2 * inch, f"Qty {qty}")

            # Black line
            c.setLineWidth(1)
            c.line(0.2 * inch, 2.85 * inch, 3.8 * inch, 2.85 * inch)

            c.save()
            overlay.seek(0)

            original_page = PdfReader(pdf_file).pages[i]
            overlay_page = PdfReader(overlay).pages[0]
            original_page.merge_page(overlay_page)
            writer.add_page(original_page)

    writer.write(output)
    output.seek(0)

    st.success("PDF processing complete.")
    st.download_button(label="Download Modified PDF", data=output, file_name="Modified_FBA_Labels.pdf", mime="application/pdf")
