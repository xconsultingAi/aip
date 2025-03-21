from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
import os

# def get_vector_store():
#     return Chroma(
#         persist_directory=settings.CHROMA_DIR,
#         embedding_function=OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
#     )
    
def get_organization_vector_store(organization_id: int):
    org_chroma_dir = os.path.join(settings.CHROMA_DIR, str(organization_id))
    return Chroma(
        persist_directory=org_chroma_dir,
        embedding_function=OpenAIEmbeddings()
    )