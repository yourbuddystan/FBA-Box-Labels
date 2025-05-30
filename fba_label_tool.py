
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

pdf_file = st.file_uploader("Upload FBA Label PDF", type=["pdf"])
csv_file = st.file_uploader("Upload SKU Lookup CSV", type=["csv"])

if pdf_file and csv_file:
    try:
        df = pd.read_csv(csv_file)
        sku_to_ybs = df[['SKU', 'YBS Name']].dropna()
        sku_to_ybs_dict = dict(zip(sku_to_ybs['SKU'].astype(str).str.strip(), sku_to_ybs['YBS Name'].astype(str).str.strip()))

        fba_pattern = re.compile(r"(FBA\d+[A-Z0-9]*([A-Z0-9]{2})U00(\d+))")
        sku_pattern = re.compile(r"Single SKU\s*\n([^\n]+)")
        qty_pattern = re.compile(r"Qty\s+(\d+)")

        output = BytesIO()
        writer = PdfWriter()

        # Read original PDF bytes into memory
        pdf_bytes = pdf_file.read()
        pdf_file.seek(0)
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            original_reader = PdfReader(BytesIO(pdf_bytes))
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                fba_match = fba_pattern.search(text)
                sku_match = sku_pattern.search(text)
                qty_match = qty_pattern.search(text)

                overlay = BytesIO()
                c = canvas.Canvas(overlay, pagesize=(4 * inch, 6 * inch))

                # ID + Box Number
                if fba_match:
                    id_code = fba_match.group(2)
                    box_number = str(int(fba_match.group(3)))  # strip leading zeros
                    label = f"{id_code} - Box {box_number}"
                    c.setFont("Helvetica-Bold", 36)
                    c.drawString(0.4 * inch, 2.4 * inch, label)

                # SKU and YBS
                sku = sku_match.group(1).strip() if sku_match else None
                if sku:
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

                # Line at 2.85 inches
                c.setLineWidth(1)
                c.line(0.2 * inch, 2.85 * inch, 3.8 * inch, 2.85 * inch)

                c.save()
                overlay.seek(0)

                # Merge overlays
                base_page = original_reader.pages[i]
                overlay_page = PdfReader(overlay).pages[0]
                base_page.merge_page(overlay_page)
                writer.add_page(base_page)

        writer.write(output)
        output.seek(0)

        st.success("PDF processing complete.")
        st.download_button("Download Modified PDF", data=output, file_name="Modified_FBA_Labels.pdf", mime="application/pdf")
    except Exception as e:
        st.error(f"Something went wrong: {str(e)}")
