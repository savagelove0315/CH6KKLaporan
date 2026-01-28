import io
import requests
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from reportlab.lib import colors
from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl

# ==============================================================================
# 1. HELPER: NETWORK & FILE HANDLING
# ==============================================================================

def extract_drive_id(url):
    """Extract File ID from various Google Drive URL formats."""
    if not url or not isinstance(url, str):
        return None
    
    # Pattern 1: /file/d/ID/view
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match: return match.group(1)
    
    # Pattern 2: id=ID
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match: return match.group(1)
    
    return None

def download_file(url):
    """
    Robust file downloader.
    Returns: (bytes_content, content_type) or (None, None)
    """
    if not url or len(str(url)) < 5:
        return None, None
        
    file_id = extract_drive_id(url)
    target_url = url
    if file_id:
        target_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
    try:
        response = requests.get(target_url, timeout=15)
        if response.status_code == 200:
            return response.content, response.headers.get('Content-Type', '')
    except Exception as e:
        pass
        
    return None, None

# ==============================================================================
# 2. HELPER: RENDERING
# ==============================================================================

def render_pdf_page(c, pdf_bytes, page_idx=0):
    """
    Render a specific page from a PDF bytes object onto the ReportLab canvas.
    Scales to fit A4 while preserving aspect ratio.
    """
    try:
        # Wrap bytes in BytesIO for pdfrw
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        
        if page_idx >= len(reader.pages):
            return False
            
        page = reader.pages[page_idx]
        page_obj = pagexobj(page)
        
        # Get page bounding box
        # page.MediaBox is usually [x, y, w, h]
        bbox = page.MediaBox
        if not bbox:
            return False
            
        x, y, w, h = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        if w == 0 or h == 0: return False
        
        # Target area (A4 with margins)
        page_w, page_h = A4
        margin = 15*mm
        target_w = page_w - 2*margin
        target_h = page_h - 2*margin
        
        # Calculate scale
        scale = min(target_w/w, target_h/h)
        
        # Center position
        final_w = w * scale
        final_h = h * scale
        pos_x = (page_w - final_w) / 2
        pos_y = (page_h - final_h) / 2
        
        # Draw on canvas
        c.saveState()
        c.translate(pos_x, pos_y)
        c.scale(scale, scale)
        c.doForm(makerl(c, page_obj))
        c.restoreState()
        return True
        
    except Exception as e:
        return False
        return False

def render_image(c, img_bytes, max_h=None):
    """
    Render image bytes onto canvas.
    """
    try:
        img_buffer = io.BytesIO(img_bytes)
        img = ImageReader(img_buffer)
        iw, ih = img.getSize()
        
        page_w, page_h = A4
        margin = 20*mm
        
        target_w = page_w - 2*margin
        target_h = max_h if max_h else (page_h - 2*margin)
        
        scale = min(target_w/iw, target_h/ih)
        dw, dh = iw*scale, ih*scale
        
        x = (page_w - dw) / 2
        y = (page_h - dh) / 2 if not max_h else (max_h - dh) # If max_h provided, assume it's top-aligned area or specific logic
        
        # For full page centering (Sijil/Surat)
        y = (page_h - dh) / 2
        
        c.drawImage(img, x, y, width=dw, height=dh)
        return True
    except Exception as e:
        return False
        return False

# ==============================================================================
# 3. CORE: GENERATOR
# ==============================================================================

def generate_pdf(data_dict):
    """
    Generate PDF with fix data mapping and mixed content support.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 25*mm
    
    # -------------------------------------------------------------------------
    # PART 1: DATA MAPPING (CRITICAL FIX)
    # -------------------------------------------------------------------------
    def get_val(keys, default='-'):
        """Safely retrieve value from dict using multiple potential keys."""
        for k in keys:
            if k in data_dict:
                val = data_dict[k]
                if val is not None and str(val).strip() != '':
                    return str(val).strip()
        return default

    # Mapped Fields
    nama = get_val(['Nama Pelajar', 'Nama'])
    kelas = get_val(['Kelas'])
    
    # Date Fix: Critical for datetime objects
    raw_date = data_dict.get('Tarikh') or data_dict.get('str(Tarikh)') or data_dict.get('Tarikh Program')
    if hasattr(raw_date, 'strftime'):
        tarikh = raw_date.strftime('%Y-%m-%d')
    else:
        tarikh = str(raw_date) if raw_date and str(raw_date).strip() else '-'
    
    # Title Fix: Prefer 'Tajuk Pertandingan'
    tajuk = get_val(['Tajuk Pertandingan', 'Tajuk Activity', 'Tajuk'])
    
    penganjur = get_val(['Penganjur'])
    tempat = get_val(['Tempat'])
    peringkat = get_val(['Peringkat'])
    pencapaian = get_val(['Pencapaian'])

    # -------------------------------------------------------------------------
    # PAGE 1: INFO UTAMA
    # -------------------------------------------------------------------------
    c.setTitle(f"Laporan - {nama}")
    
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 40*mm, "LAPORAN PENCAPAIAN KOKURIKULUM")
    c.line(margin, height - 45*mm, width - margin, height - 45*mm)
    
    fields = [
        ("Nama Pelajar", nama),
        ("Kelas", kelas),
        ("Tarikh Program", tarikh),
        ("Tajuk Aktiviti", tajuk),
        ("Penganjur", penganjur),
        ("Tempat", tempat),
        ("Peringkat", peringkat),
        ("Pencapaian", pencapaian),
    ]
    
    start_y = height - 70*mm
    line_height = 12*mm
    
    c.setFont("Helvetica", 12)
    for idx, (label, value) in enumerate(fields):
        y = start_y - (idx * line_height)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, f"{label}:")
        c.setFont("Helvetica", 12)
        # Handle simple truncation for overflow
        c.drawString(margin + 50*mm, y, value[:75] + ("..." if len(value)>75 else ""))
        
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width/2, 15*mm, "Dijana oleh Sistem Laporan Kokurikulum © Antigravity")
    
    c.showPage()

    # -------------------------------------------------------------------------
    # PAGE 2: SIJIL (Mixed Content)
    # -------------------------------------------------------------------------
    # Mapped Correctly to 'Sijil_Link'
    sijil_url = get_val(['Sijil_Link', 'Sijil'], default=None)
    
    if sijil_url and len(sijil_url) > 5:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, height - 20*mm, "SIJIL PENCAPAIAN")
        
        content, ctype = download_file(sijil_url)
        if content:
            if 'application/pdf' in ctype:
                # Render PDF Page 1
                success = render_pdf_page(c, content, 0)
                if not success:
                    c.drawString(margin, height/2, "[Ralat Memaparkan PDF Sijil]")
            elif 'image' in ctype:
                # Render Image
                render_image(c, content)
            else:
                c.drawString(margin, height/2, "[Format fail tidak disokong]")
        else:
            c.drawString(margin, height/2, "[Gagal memuat turun Sijil]")
            
        c.showPage()

    # -------------------------------------------------------------------------
    # PAGE 3+: SURAT (Multiple Possible)
    # -------------------------------------------------------------------------
    # Mapped Correctly to 'Surat_Link'
    surat_url = get_val(['Surat_Link', 'Surat Jemputan'], default=None)
    
    if surat_url and len(surat_url) > 5:
        # If there are multiple links separated by comma or newlines
        urls = [u.strip() for u in re.split(r'[,\n]', surat_url) if len(u.strip()) > 5]
        
        for idx, s_url in enumerate(urls):
            c.setFont("Helvetica-Bold", 14)
            title = "SURAT JEMPUTAN"
            if len(urls) > 1: title += f" ({idx+1})"
            c.drawString(margin, height - 20*mm, title)
            
            content, ctype = download_file(s_url)
            if content:
                if 'application/pdf' in ctype:
                    render_pdf_page(c, content, 0)
                elif 'image' in ctype:
                    render_image(c, content)
                else:
                    c.drawString(margin, height/2, "[Format fail tidak disokong]")
            else:
                 c.drawString(margin, height/2, "[Gagal memuat turun Surat]")
            
            c.showPage()

    # -------------------------------------------------------------------------
    # PAGE N: GAMBAR (Grid - Images Only)
    # -------------------------------------------------------------------------
    # Collect all image inputs from specific columns
    img_urls = []
    # Explicitly check Link_Foto1 to Link_Foto4
    target_cols = ['Link_Foto1', 'Link_Foto2', 'Link_Foto3', 'Link_Foto4']
    
    for col in target_cols:
        val = data_dict.get(col)
        if val and isinstance(val, str) and len(val.strip()) > 5:
            img_urls.append(val.strip())
            
    if img_urls:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, height - 20*mm, "LAMPIRAN: GAMBAR AKTIVITI")
        
        # Grid Props
        grid_w = (width - 2*margin) / 2
        grid_h = (height - 50*mm) / 2
        
        valid_img_count = 0
        
        for i, url in enumerate(img_urls):
            # Download first to check type (Skip PDFs in Image Grid)
            content, ctype = download_file(url)
            if not content or 'image' not in ctype:
                continue
                
            # New Page Logic
            if valid_img_count > 0 and valid_img_count % 4 == 0:
                c.showPage()
                c.setFont("Helvetica-Bold", 14)
                c.drawString(margin, height - 20*mm, "LAMPIRAN: GAMBAR (Sambungan)")
                
            # Calc Position
            pos_on_page = valid_img_count % 4
            row = pos_on_page // 2
            col = pos_on_page % 2
            
            x_pos = margin + (col * grid_w)
            y_pos = height - 40*mm - ((row + 1) * grid_h) # Bottom of cell
            
            # Draw Image in Box
            try:
                img_io = io.BytesIO(content)
                img = ImageReader(img_io)
                iw, ih = img.getSize()
                
                # Fit to cell (with padding)
                pad = 5*mm
                avail_w = grid_w - 2*pad
                avail_h = grid_h - 2*pad
                
                scale = min(avail_w/iw, avail_h/ih)
                dw, dh = iw*scale, ih*scale
                
                # Center in cell
                final_x = x_pos + pad + (avail_w - dw)/2
                final_y = y_pos + pad + (avail_h - dh)/2
                
                c.drawImage(img, final_x, final_y, width=dw, height=dh)
                
            except Exception as e:
                pass
                
            valid_img_count += 1
            
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer
