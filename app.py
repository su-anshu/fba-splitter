import streamlit as st
from PIL import Image
import fitz  # PyMuPDF
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.utils import ImageReader
from concurrent.futures import ThreadPoolExecutor
import os

# Page config
st.set_page_config(
    page_title="PDF Label Splitter",
    layout="centered",
    initial_sidebar_state="auto"
)

# UI Header
st.markdown(
    """
    <h2 style='text-align: center; color: #004080;'>📄 PDF Label Splitter</h2>
    <p style='text-align: center; color: #666;'>Split each PDF page into top and bottom halves, rotate -90°, and export to A5 format</p>
    """,
    unsafe_allow_html=True
)

# Settings
rotation_angle = -90
dpi = 300
page_size = A5
page_width, page_height = page_size
MAX_PREVIEW = 6

st.divider()

uploaded_file = st.file_uploader("📁 Upload your PDF file", type="pdf", help="Only PDF format is supported")

def process_page(page_index, page_data):
    page = page_data.load_page(page_index)
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    mid = img.height // 2
    halves = [img.crop((0, 0, img.width, mid)), img.crop((0, mid, img.width, img.height))]

    processed_halves = []
    for half in halves:
        if rotation_angle:
            half = half.rotate(rotation_angle, expand=True)

        img_buf = BytesIO()
        half.save(img_buf, format='JPEG', quality=95)
        img_buf.seek(0)

        inch_width = page_width / 72
        target_width_px = int(inch_width * dpi)
        scale = target_width_px / half.width
        target_height_px = int(half.height * scale)
        display_height = (target_height_px / dpi) * 72
        y_offset = (page_height - display_height) / 2

        processed_halves.append((img_buf, y_offset, display_height))

    return processed_halves

if uploaded_file:
    # Extract input filename for use in download
    base_name = os.path.splitext(uploaded_file.name)[0]
    output_filename = f"{base_name}_split.pdf"

    with st.spinner("⏳ Splitting, rotating, and formatting your PDF..."):
        pdf_reader = fitz.open(stream=uploaded_file.read(), filetype="pdf")

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_page, i, pdf_reader) for i in range(len(pdf_reader))]
            results = [f.result() for f in futures]

        output_pdf_stream = BytesIO()
        c = canvas.Canvas(output_pdf_stream, pagesize=page_size)
        preview_images = []

        for halves in results:
            for img_buf, y_offset, display_height in halves:
                c.drawImage(ImageReader(img_buf), 0, y_offset, width=page_width, height=display_height)
                c.showPage()
                img_buf.seek(0)
                preview_images.append(Image.open(img_buf).copy())

        c.save()
        output_pdf_stream.seek(0)

    st.success("✅ Your PDF has been processed and is ready to download!")

    # Download button with dynamic file name
    st.download_button(
        label="📥 Download Final PDF",
        data=output_pdf_stream,
        file_name=output_filename,
        mime="application/pdf"
    )

    st.markdown("---")

    st.markdown("### 🔍 Preview of Split Pages")

    for i, img in enumerate(preview_images[:MAX_PREVIEW]):
        st.image(img, caption=f"Page {i + 1}", use_container_width=True)

    if len(preview_images) > MAX_PREVIEW:
        st.info(f"Showing only the first {MAX_PREVIEW} preview pages for performance.")
