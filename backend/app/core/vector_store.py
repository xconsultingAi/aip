from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

def get_vector_store():
    return Chroma(
        persist_directory=settings.CHROMA_DIR,
        embedding_function=OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
    )