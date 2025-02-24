import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.exceptions import OpenAIException

class KnowledgeProcessor:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

    def process_file(self, file_path: str, content_type: str):
        try:
            # Load document based on file type
            if content_type == "application/pdf":
                loader = PyPDFLoader(file_path)
            else:  # text/plain
                loader = TextLoader(file_path)
                
            documents = loader.load()
            
            # Split documents
            chunks = self.text_splitter.split_documents(documents)
            
            # Create Chroma vector store
            Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=settings.CHROMA_DIR
            )
            
            return len(chunks)
            
        except Exception as e:
            raise OpenAIException(f"File processing error: {str(e)}")