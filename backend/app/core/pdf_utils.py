import os
import unicodedata
from urllib.parse import urlparse
from pathlib import Path
from fpdf import FPDF # type: ignore

def generate_pdf_path(url: str, base_dir: str) -> tuple:
    # Generate PDF path
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '')
    path_segments = [s for s in parsed.path.split('/') if s]
    
    # Output directory structure
    output_dir = os.path.join(base_dir, domain)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate filename options
    filename_options = {
        'full_path': '_'.join([domain] + path_segments)[:200] + '.pdf',
        'domain_only': f'{domain}.pdf',
        'last_segment': f"{path_segments[-1]}.pdf" if path_segments else f'{domain}_index.pdf'
    }
    
    # Return all options and directory
    return {
        'directory': output_dir,
        'filenames': filename_options,
        'recommended': filename_options['full_path']
    }

def save_content_as_pdf(content: str, url: str, base_dir: str) -> str:
    # Save content as PDF and return relative path
    path_info = generate_pdf_path(url, base_dir)
    full_path = os.path.join(path_info['directory'], path_info['recommended'])
    
    # Convert Unicode to ASCII (approximation)
    ascii_content = unicodedata.normalize('NFKD', content)
    ascii_content = ascii_content.encode('ascii', 'ignore').decode('ascii')
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=ascii_content)
    pdf.output(full_path)
    
    return os.path.relpath(full_path, start=base_dir)