import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.exceptions import openai_exception
from app.core.vector_store import get_organization_vector_store

#SH: Initialize OpenAI Embeddings using API key
embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)

#SH: Setup text splitter: splits large documents into smaller overlapping chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

#SH: Main function to process a file and store its embeddings
def process_file(file_path: str, content_type: str, organization_id: int) -> int:
    try:
        #SH: Get vector store instance for a specific organization
        vector_store = get_organization_vector_store(organization_id)

        #SH: Choose appropriate loader based on file type
        if content_type == "application/pdf":
            loader = PyPDFLoader(file_path)   # For PDF files
        else:
            loader = TextLoader(file_path)    # For plain text files
        #SH: Load the file's content into LangChain Document format
        documents = loader.load()
        #SH: Split content into chunks
        chunks = text_splitter.split_documents(documents)
        #SH: Add the processed chunks into the organization’s vector store
        vector_store.add_documents(chunks)
        #SH: Return number of chunks created
        return len(chunks)

    except Exception as e:
        #SH: Raise a custom exception if anything fails
        raise openai_exception(f"File processing error: {str(e)}")
