from fastapi import UploadFile
import PyPDF2
import io

async def extract_text_from_pdf(file: UploadFile) -> str:
    contents = await file.read()
    reader = PyPDF2.PdfReader(io.BytesIO(contents))
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text