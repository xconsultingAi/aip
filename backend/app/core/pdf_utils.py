import os
import unicodedata
from urllib.parse import urlparse
from pathlib import Path
from fpdf import FPDF # type: ignore
from app.core.config import settings

def generate_pdf_path(url: str, base_dir: str) -> tuple:
    #SH: Generate PDF path
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '')
    path_segments = [s for s in parsed.path.split('/') if s]
    
    #SH: Output directory structure
    output_dir = os.path.join(base_dir, domain)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    #SH: Generate filename options
    filename_options = {
        'full_path': '_'.join([domain] + path_segments)[:200] + '.pdf',
        'domain_only': f'{domain}.pdf',
        'last_segment': f"{path_segments[-1]}.pdf" if path_segments else f'{domain}_index.pdf'
    }
    
    #SH: Return all options and directory
    return {
        'directory': output_dir,
        'filenames': filename_options,
        'recommended': filename_options['full_path']
    }

def save_content_as_pdf(content: str, source_type: str, identifier: str, base_dir: str) -> str:
    # Save content as PDF and return relative path
    path_info = generate_pdf_path(source_type, identifier, base_dir)
    full_path = path_info['full_path']
    
    #SH: Convert Unicode to ASCII (approximation)
    ascii_content = unicodedata.normalize('NFKD', content)
    ascii_content = ascii_content.encode('ascii', 'ignore').decode('ascii')
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=ascii_content)
    pdf.output(full_path)
    
    return os.path.relpath(full_path, start=base_dir)


def generate_pdf_path(source_type: str, identifier: str, base_dir: str) -> dict:
    #SH: Handle different source types (url|youtube|text)
    if source_type == "youtube":
        #SH: YouTube PDF path structure
        filename = f"youtube_{identifier[:100]}.pdf"
        output_dir = os.path.join(base_dir, settings.YOUTUBE_PDFS_SUBDIR)
    elif source_type == "text":
        #SH: Text PDF path structure
        filename = f"text_{identifier[:50]}.pdf"
        output_dir = os.path.join(base_dir, settings.TEXT_PDFS_SUBDIR)
    else:  # url
        parsed = urlparse(identifier)
        domain = parsed.netloc.replace('www.', '')
        filename = '_'.join([domain] + [s for s in parsed.path.split('/') if s])[:200] + '.pdf'
        output_dir = os.path.join(base_dir, settings.SCRAPED_PDFS_SUBDIR)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    return {
        'directory': output_dir,
        'filename': filename,
        'full_path': os.path.join(output_dir, filename)
    }

def save_content_as_pdf(content: str, source_type: str, identifier: str, base_dir: str) -> str:
    #SH: Generic PDF saver for different source types
    path_info = generate_pdf_path(source_type, identifier, base_dir)
    full_path = path_info['full_path']
    
    #SH: Convert Unicode to ASCII
    ascii_content = unicodedata.normalize('NFKD', content).encode('ascii', 'ignore').decode('ascii')
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=ascii_content)
    pdf.output(full_path)
    
    return os.path.relpath(full_path, start=base_dir)