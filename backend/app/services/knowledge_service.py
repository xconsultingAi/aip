import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.exceptions import openai_exception

embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

def process_file(file_path: str, content_type: str) -> int:
    try:
        if content_type == "application/pdf":
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path)
        
        documents = loader.load()
        chunks = text_splitter.split_documents(documents)
        
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=settings.CHROMA_DIR
        )
        
        return len(chunks)
    except Exception as e:
        raise openai_exception(f"File processing error: {str(e)}")