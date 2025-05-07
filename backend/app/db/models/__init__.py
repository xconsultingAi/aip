from app.db.models.user import User
from app.db.models.agent import Agent
from app.db.models.organization import Organization
from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.widget import WidgetSession

def __init__(self, filename, content_type, organization_id, file_size, chunk_count):
    self.filename = filename
    self.content_type = content_type
    self.organization_id = organization_id
    self.file_size = file_size
    self.chunk_count = chunk_count