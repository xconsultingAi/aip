from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
import os

#SH: This function returns a Chroma vector store for a specific organization
def get_organization_vector_store(organization_id: int):
    #SH: directory path for storing vectors for this organization
    org_chroma_dir = os.path.join(settings.CHROMA_DIR, str(organization_id))
    
    return Chroma(
        persist_directory=org_chroma_dir,
        embedding_function=OpenAIEmbeddings()
    )
