import logging
from langchain_community.document_loaders import(
    PyPDFLoader, 
    TextLoader,
    UnstructuredWordDocumentLoader,  # DOCX
    UnstructuredHTMLLoader,  # HTML
    CSVLoader,
    UnstructuredExcelLoader  # XLS/XLSX
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.exceptions import openai_exception
from app.core.vector_store import get_organization_vector_store
import chardet # type: ignore
from typing import Optional
from app.models.knowledge_base import KnowledgeURL
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.url_processing import URLProcessor
from app.core.pdf_utils import save_content_as_pdf
from app.db.repository.knowledge_base import create_url_knowledge
import os

logger= logging.getLogger(__name__)

#SH: Initialize OpenAI Embeddings using API key
embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)

#SH: Setup text splitter: splits large documents into smaller overlapping chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

def detect_file_encoding(file_path: str, sample_size: int = 10000) -> Optional[str]:
    # More robust encoding detection with fallback
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
            result = chardet.detect(raw_data)
            
            # Only return encoding if confidence is high enough
            if result['confidence'] > 0.7:
                return result['encoding']
            return None
    except Exception as e:
        logger.warning(f"Encoding detection failed: {str(e)}")
        return None

def get_safe_loader(file_path: str, content_type: str):
    """Handle file loading with proper encoding fallbacks"""
    encoding = None
    loader = None

    # Try with detected encoding first
    if content_type in ["text/plain", "text/html", "text/csv"]:
        encoding = detect_file_encoding(file_path) or 'utf-8'

    try:
        if content_type == "application/pdf":
            loader = PyPDFLoader(file_path)
        elif content_type == "text/plain":
            loader = TextLoader(file_path, encoding=encoding)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            loader = UnstructuredWordDocumentLoader(file_path)
        elif content_type == "text/html":
            loader = UnstructuredHTMLLoader(file_path, encoding=encoding)
        elif content_type == "text/csv":
            loader = CSVLoader(file_path, encoding=encoding)
        elif content_type in ["application/vnd.ms-excel", 
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            loader = UnstructuredExcelLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {content_type}")

        return loader
    except UnicodeDecodeError:
        # Fallback to different encodings if initial attempt fails
        fallback_encodings = ['utf-8-sig', 'latin-1', 'windows-1252']
        for enc in fallback_encodings:
            try:
                if content_type == "text/plain":
                    return TextLoader(file_path, encoding=enc)
                elif content_type == "text/html":
                    return UnstructuredHTMLLoader(file_path, encoding=enc)
                elif content_type == "text/csv":
                    return CSVLoader(file_path, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode file with any supported encoding")

#SH: Main function to process a file and store its embeddings
def process_file(file_path: str, content_type: str, organization_id: int) -> int:
    try:
        #SH: Get vector store instance for a specific organization
        vector_store = get_organization_vector_store(organization_id)
        loader = get_safe_loader(file_path, content_type)

        try:
            #SH: Load the file's content into LangChain Document format
            documents = loader.load()
            #SH: Split content into chunks
            chunks = text_splitter.split_documents(documents)
            #SH: Add the processed chunks into the organization’s vector store
            vector_store.add_documents(chunks)
            #SH: Return number of chunks created
            return len(chunks)
        except Exception as load_error:
            logger.error(f"Failed to process file {file_path}: {str(load_error)}")
            raise openai_exception(f"File processing failed: {str(load_error)}")

    except Exception as e:
        #SH: Raise a custom exception if anything fails
        logger.error(f"File processing error for {file_path}: {str(e)}", exc_info=True)
        raise openai_exception(f"Could not process file: {str(e)}")
# For Url Scraping
async def process_url(url_data: KnowledgeURL, organization_id: int, db: AsyncSession):
    try:
        # Validate URL
        if not str(url_data.url).startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        processor = URLProcessor()
        content = processor.fetch_url(str(url_data.url))
        
        if len(content) < 50:
            raise ValueError("Insufficient content extracted (min 50 chars required)")

        # First split the content into chunks for vector storage
        chunks = text_splitter.split_text(content)
        chunk_count = len(chunks)
        
        # Store in vector store
        vector_store = get_organization_vector_store(organization_id)
        await vector_store.aadd_texts(chunks)

        # Save PDF and get relative path
        pdf_relative_path = save_content_as_pdf(
            content=content,
            url=str(url_data.url),
            base_dir=os.path.join(settings.KNOWLEDGE_BASE_DIR, settings.SCRAPED_PDFS_SUBDIR)
        )

        # Get full path to calculate file size
        full_pdf_path = os.path.join(
            settings.KNOWLEDGE_BASE_DIR, 
            settings.SCRAPED_PDFS_SUBDIR, 
            pdf_relative_path
        )

        # Calculate required fields
        filename = os.path.basename(pdf_relative_path)
        content_type = "application/pdf"
        file_size = os.path.getsize(full_pdf_path)

        # Store metadata in database with all required fields
        await create_url_knowledge(
            db=db,
            name=url_data.name,
            url=str(url_data.url),
            organization_id=organization_id,
            file_path=pdf_relative_path,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            chunk_count=chunk_count,
            crawl_depth=url_data.depth,
            include_links=url_data.include_links
        )

        return {
            "url": url_data.url,
            "chunk_count": chunk_count,
            "pdf_path": pdf_relative_path,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"URL Processing Error: {str(e)}", exc_info=True)
        raise