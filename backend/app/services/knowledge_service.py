import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.exceptions import OpenAIException
from app.core.vector_store import get_organization_vector_store

embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

class KnowledgeProcessor:
    @staticmethod
    def process_file(file_path: str, content_type: str, organization_id: int) -> int:
        try:
            print(f"Processing file for organization ID: {organization_id}")
            # Organization-specific vector store
            vector_store = get_organization_vector_store(organization_id)

            # Load and process file
            if content_type == "application/pdf":
                loader = PyPDFLoader(file_path)
            else:
                loader = TextLoader(file_path)

            documents = loader.load()
            chunks = text_splitter.split_documents(documents)

            # Add documents to the organization-specific vector store
            vector_store.add_documents(chunks)

            return len(chunks)
        except Exception as e:
            raise OpenAIException(f"File processing error: {str(e)}")
