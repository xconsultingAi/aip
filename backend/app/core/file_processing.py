from fastapi import UploadFile
import PyPDF2  # type: ignore
import io

#SH: Asynchronously extract text content from an uploaded PDF file
async def extract_text_from_pdf(file: UploadFile) -> str:
    #SH: Read the binary content of the uploaded file
    contents = await file.read()
    reader = PyPDF2.PdfReader(io.BytesIO(contents))
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    return text
