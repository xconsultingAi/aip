import logging
from fastapi import HTTPException
from langchain_community.document_loaders import(
    PyPDFLoader, 
    TextLoader,
    UnstructuredWordDocumentLoader,  # DOCX
    UnstructuredHTMLLoader,  # HTML
    CSVLoader,
    UnstructuredExcelLoader  # XLS/XLSX
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select
from app.core import vector_store
from app.core.config import settings
from app.core.exceptions import openai_exception
from app.core.vector_store import get_organization_vector_store
import chardet # type: ignore
from typing import Optional, List
from app.models.knowledge_base import KnowledgeSearchRequest, KnowledgeURL, TextKnowledgeRequest, YouTubeKnowledgeRequest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.url_processer import URLProcessor
from app.core.pdf_utils import save_content_as_pdf
from app.db.repository.knowledge_base import create_category, create_tag, create_text_knowledge, create_url_knowledge, create_youtube_knowledge, delete_category, delete_tag, get_categories, get_category, get_category_tree, get_knowledge_by_category, get_knowledge_by_tag, get_tag, get_tags, search_knowledge, update_category, update_knowledge_categories_tags, update_tag
import os
from app.core.youtube_processer import YouTubeProcessor
import hashlib
from app.db.models.knowledge_base import TextKnowledge, YouTubeKnowledge
from app.models.knowledge_base import (
    CategoryCreate, CategoryOut, CategoryTree, 
    TagCreate, TagOut, KnowledgeUpdate, KnowledgeBaseOut
)

logger = logging.getLogger(__name__)

#SH: Initialize OpenAI Embeddings using API key
embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)

#SH: Setup text splitter: splits large documents into smaller overlapping chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

#SH: Detect file encoding
def detect_file_encoding(file_path: str, sample_size: int = 10000) -> Optional[str]:
    #SH: More robust encoding detection with fallback
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
            result = chardet.detect(raw_data)
            
            #SH: Only return encoding if confidence is high enough
            if result['confidence'] > 0.7:
                return result['encoding']
            return None
    except Exception as e:
        logger.warning(f"Encoding detection failed: {str(e)}")
        return None

#SH: Get safe loader    
def get_safe_loader(file_path: str, content_type: str):
    #SH: Handle file loading with proper encoding fallbacks
    encoding = None
    loader = None

    #SH: Try with detected encoding first
    if content_type in ["text/plain", "text/html", "text/csv"]:
        encoding = detect_file_encoding(file_path) or 'utf-8'

    try:
        #SH: Load the file based on its content type
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
        #SH: Fallback to different encodings if initial attempt fails
        fallback_encodings = ['utf-8-sig', 'latin-1', 'windows-1252']
        for enc in fallback_encodings:
            try:
                #SH: Try with fallback encoding
                if content_type == "text/plain":
                    return TextLoader(file_path, encoding=enc)
                elif content_type == "text/html":
                    return UnstructuredHTMLLoader(file_path, encoding=enc)
                elif content_type == "text/csv":
                    return CSVLoader(file_path, encoding=enc)
            except UnicodeDecodeError:
                #SH: Continue with next encoding if current one fails
                continue
        raise ValueError(f"Could not decode file with any supported encoding")

#SH: Main function to process a file and store its embeddings
def process_file(file_path: str, content_type: str, organization_id: int, knowledge_base_id: int) -> int:
    try:
        # SH: Get vector store instance for a specific organization
        vector_store = get_organization_vector_store(organization_id)
        loader = get_safe_loader(file_path, content_type)

        try:
            # SH: Load the file's content into LangChain Document format
            documents = loader.load()

            # SH: Split content into chunks
            chunks = text_splitter.split_documents(documents)

            # SH: Add the processed chunks into the organization's vector store with metadata
            for i, chunk in enumerate(chunks):
                vector_store.add_texts(
                    texts=[chunk.page_content],
                    metadatas=[{
                        "chunk_index": i,
                        "knowledge_id": knowledge_base_id,
                        "organization_id": organization_id,
                        "source": file_path
                    }]
                )

            # SH: Return number of chunks created
            return len(chunks)

        except Exception as load_error:
            logger.error(f"Failed to process file {file_path}: {str(load_error)}")
            raise openai_exception(f"File processing failed: {str(load_error)}")

    except Exception as e:
        # SH: Raise a custom exception if anything fails
        logger.error(f"File processing error for {file_path}: {str(e)}", exc_info=True)
        raise openai_exception(f"Could not process file: {str(e)}")

#SH: For Url Scraping
async def process_url(url_data: KnowledgeURL, organization_id: int, db: AsyncSession):
    try:
        #SH: Validate URL
        if not str(url_data.url).startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        #SH: Case-insensitive format validation
        if url_data.format.lower() not in [fmt.lower() for fmt in settings.ALLOWED_URL_FORMATS]:
            raise ValueError(f"Invalid URL format. Allowed: {settings.ALLOWED_URL_FORMATS}")

        processor = URLProcessor()
        content = processor.fetch_url(str(url_data.url))
        
        if len(content) < 50:
            raise ValueError("Insufficient content extracted (min 50 chars required)")

        #SH: Split the content into chunks for vector storage
        chunks = text_splitter.split_text(content)
        chunk_count = len(chunks)
        
        #SH: Store in vector store
        vector_store = get_organization_vector_store(organization_id)
        await vector_store.aadd_texts(chunks)

        #SH: Save PDF in domain-specific subfolder
        pdf_relative_path = save_content_as_pdf(
            content=content,
            source_type="url",
            identifier=str(url_data.url),
            base_dir=settings.KNOWLEDGE_BASE_DIR
        )

        #SH: Get full path to calculate file size
        full_pdf_path = os.path.join(settings.KNOWLEDGE_BASE_DIR, pdf_relative_path)
        if not os.path.exists(full_pdf_path):
            raise ValueError("Failed to generate PDF")

        #SH: Calculate required fields
        filename = os.path.basename(pdf_relative_path)
        content_type = "application/pdf"
        file_size = os.path.getsize(full_pdf_path)

        #SH: Store metadata in database
        url_knowledge = await create_url_knowledge(
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
            include_links=url_data.include_links,
            format=url_data.format
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

# SH: Process YouTube
async def process_youtube(
    youtube_data: YouTubeKnowledgeRequest,
    organization_id: int,
    db: AsyncSession
):
    processor = YouTubeProcessor()
    video_id = processor.extract_video_id(str(youtube_data.video_url))
    logger.info(f"Processing YouTube video {video_id}: {youtube_data.video_url}")

    try:
        #SH: Check for existing video
        existing = await db.execute(
            select(YouTubeKnowledge).where(YouTubeKnowledge.video_id == video_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"YouTube video {video_id} already exists")

        #SH: Use fallback method for transcript (text + speech-to-text)
        transcript, error = processor.get_transcript_with_fallback(video_id)
        logger.info(f"Transcript result for {video_id}: length={len(transcript) if transcript else 0}, error={error}")

        #SH: Get metadata early so it can be reused in both success and fail cases
        metadata = processor.get_video_metadata(str(youtube_data.video_url))
        logger.info(f"Metadata for {video_id}: {metadata}")

        if not transcript:
            if not metadata.get('retrieved_successfully', True):
                raise ValueError(
                    f"Could not access video metadata: {metadata.get('error', 'Unknown error')}. "
                    "The video may be private, age-restricted, or unavailable."
                )
            return {
                "status": "skipped",
                "message": f"Cannot process video '{metadata.get('title', '')}': {error}",
                "reason": "no_transcript",
                "video_id": video_id,
                "title": metadata.get('title', ''),
                "url": youtube_data.video_url
            }

        #SH: Validate transcript length
        if len(transcript.strip()) < 100:
            raise ValueError(
                "Transcript is too short (less than 100 characters). "
                "Please ensure the video has sufficient spoken content."
            )

        if not metadata.get('retrieved_successfully', True):
            raise ValueError(
                f"Could not access video metadata: {metadata.get('error', 'Unknown error')}"
            )

        #SH: Save transcript to PDF
        pdf_relative_path = save_content_as_pdf(
            content=transcript,
            source_type="youtube",
            identifier=video_id,
            base_dir=settings.KNOWLEDGE_BASE_DIR
        )

        #SH: Chunk text and store in vector DB
        chunks = text_splitter.split_text(transcript)
        chunk_count = len(chunks)
        logger.info(f"Created {chunk_count} chunks for video {video_id}")

        if chunk_count > 0:
            vector_store = get_organization_vector_store(organization_id)
            await vector_store.aadd_texts(chunks)

        #SH: Save to database
        filename = os.path.basename(pdf_relative_path)
        await create_youtube_knowledge(
            db=db,
            name=youtube_data.name or metadata.get('title', 'YouTube Video'),
            video_url=str(youtube_data.video_url),
            organization_id=organization_id,
            file_path=pdf_relative_path,
            transcript=transcript,
            filename=filename,
            format=youtube_data.format
        )

        return {
            "status": "success",
            "message": "YouTube video transcript added successfully",
            "video_id": video_id,
            "chunk_count": chunk_count,
            "pdf_path": pdf_relative_path,
            "content_source": "transcript",
            "title": metadata.get('title', ''),
            "url": youtube_data.video_url
        }
    #SH: Handle exceptions
    except ValueError as ve:
        logger.error(f"ValueError processing YouTube video {video_id}: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"YouTube Processing Error for {video_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process YouTube video. Please try again later."
        )

#SH: Process Text   
async def process_text(
    text_data: TextKnowledgeRequest,
    organization_id: int,
    db: AsyncSession
):
    try:
        #SH: Generate content hash to prevent duplicates
        content_hash = hashlib.sha256(text_data.text_content.encode()).hexdigest()
        
        #SH: Check for existing content
        existing = await db.execute(
            select(TextKnowledge)
            .where(TextKnowledge.content_hash == content_hash)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Duplicate text content detected")
        
        #SH: Save PDF
        pdf_relative_path = save_content_as_pdf(
            content=text_data.text_content,
            source_type="text",
            identifier=content_hash,
            base_dir=settings.KNOWLEDGE_BASE_DIR
        )
        
        #SH: Process chunks
        chunks = text_splitter.split_text(text_data.text_content)
        chunk_count = len(chunks)
        vector_store = get_organization_vector_store(organization_id)
        await vector_store.aadd_texts(chunks)
        
        #SH: Create database entry
        filename = os.path.basename(pdf_relative_path)
        await create_text_knowledge(
            db=db,
            name=text_data.name,
            text_content=text_data.text_content,
            organization_id=organization_id,
            file_path=pdf_relative_path,
            filename=filename,
            content_hash=content_hash,
            format=text_data.format 
        )
        
        return {
            "content_hash": content_hash,
            "chunk_count": chunk_count,
            "pdf_path": pdf_relative_path
        }
    except Exception as e:
        logger.error(f"Text Processing Error: {str(e)}", exc_info=True)
        raise
    
# SH: Category Services

# SH: Create a new category and return it after validation
async def create_category_service(
    db: AsyncSession,
    category_data: CategoryCreate
) -> CategoryOut:
    try:
        category = await create_category(db, category_data.model_dump())
        return CategoryOut.model_validate(category)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create category: {str(e)}"
        )

# SH: Get a specific category by ID for the given organization
async def get_category_service(
    db: AsyncSession,
    category_id: int,
    organization_id: int
) -> CategoryOut:
    category = await get_category(db, category_id, organization_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryOut.model_validate(category)

# SH: Get all categories for the given organization
async def get_categories_service(
    db: AsyncSession,
    organization_id: int
) -> List[CategoryOut]:
    categories = await get_categories(db, organization_id)
    return [CategoryOut.model_validate(c) for c in categories]

# SH: Get category tree structure (parent-child hierarchy)
async def get_category_tree_service(
    db: AsyncSession,
    organization_id: int
) -> List[CategoryTree]:
    tree = await get_category_tree(db, organization_id)
    return [CategoryTree.model_validate(c) for c in tree]

# SH: Update a category by ID with given update data
async def update_category_service(
    db: AsyncSession,
    category_id: int,
    organization_id: int,
    update_data: dict
) -> CategoryOut:
    category = await update_category(db, category_id, organization_id, update_data)
    return CategoryOut.model_validate(category)

# SH: Delete a category by ID
async def delete_category_service(
    db: AsyncSession,
    category_id: int,
    organization_id: int
) -> bool:
    return await delete_category(db, category_id, organization_id)

# SH: Tag Services

# SH: Create a new tag and return it after validation
async def create_tag_service(
    db: AsyncSession,
    tag_data: TagCreate
) -> TagOut:
    try:
        tag = await create_tag(db, tag_data.model_dump())
        return TagOut.model_validate(tag)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create tag: {str(e)}"
        )

# SH: Get a tag by ID for the given organization
async def get_tag_service(
    db: AsyncSession,
    tag_id: int,
    organization_id: int
) -> TagOut:
    tag = await get_tag(db, tag_id, organization_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return TagOut.model_validate(tag)

# SH: Get list of tags for the organization, optional search filter
async def get_tags_service(
    db: AsyncSession,
    organization_id: int,
    search: str = None
) -> List[TagOut]:
    tags = await get_tags(db, organization_id, search)
    return [TagOut.model_validate(t) for t in tags]

# SH: Update the name of a tag by ID
async def update_tag_service(
    db: AsyncSession,
    tag_id: int,
    organization_id: int,
    name: str
) -> TagOut:
    tag = await update_tag(db, tag_id, organization_id, name)
    return TagOut.model_validate(tag)

# SH: Delete a tag by ID
async def delete_tag_service(
    db: AsyncSession,
    tag_id: int,
    organization_id: int
) -> bool:
    return await delete_tag(db, tag_id, organization_id)

# SH: Update categories and tags assigned to a knowledge base item
async def update_knowledge_categories_tags_service(
    db: AsyncSession,
    knowledge_id: int,
    organization_id: int,
    update_data: KnowledgeUpdate
) -> KnowledgeBaseOut:
    try:
        kb = await update_knowledge_categories_tags(
            db=db,
            knowledge_id=knowledge_id,
            organization_id=organization_id,
            category_id=update_data.category_id,
            tag_ids=update_data.tag_ids
        )
        return KnowledgeBaseOut.model_validate(kb)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update knowledge base: {str(e)}"
        )

# SH: Get knowledge base items filtered by category, including subcategories optionally
async def get_knowledge_by_category_service(
    db: AsyncSession,
    organization_id: int,
    category_id: Optional[int] = None,
    include_subcategories: bool = False
) -> List[KnowledgeBaseOut]:
    try:
        kbs = await get_knowledge_by_category(
            db=db,
            organization_id=organization_id,
            category_id=category_id,
            include_subcategories=include_subcategories
        )
        return [KnowledgeBaseOut.model_validate(kb) for kb in kbs]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get knowledge bases: {str(e)}"
        )

# SH: Get knowledge base items associated with a specific tag
async def get_knowledge_by_tag_service(
    db: AsyncSession,
    organization_id: int,
    tag_id: int
) -> List[KnowledgeBaseOut]:
    try:
        kbs = await get_knowledge_by_tag(
            db=db,
            organization_id=organization_id,
            tag_id=tag_id
        )
        return [KnowledgeBaseOut.model_validate(kb) for kb in kbs]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get knowledge bases: {str(e)}"
        )

# SH: Generate a text snippet from vector store based on query for a knowledge item
def generate_snippet(query: str, knowledge_base_id: int, organization_id: int) -> str:
    try:
        # SH: Search vector store for most relevant chunk
        results = vector_store.similarity_search(
            query=query,
            k=1,
            filter={
                "knowledge_id": knowledge_base_id,
                "organization_id": organization_id
            }
        )
        
        if results:
            # SH: Return first 200 chars as snippet
            content = results[0].page_content
            return (content[:200] + '...') if len(content) > 200 else content
        
        return f"Relevant content containing '{query}'"
        
    except Exception as e:
        logger.error(f"Snippet generation failed: {str(e)}")
        return f"Document related to '{query}'"

# SH: Perform knowledge base search based on filters, generate highlighted snippets
async def search_knowledge_service(
    db: AsyncSession,
    search_request: KnowledgeSearchRequest,
    organization_id: int
) -> dict:
    # SH: Search knowledge base using filters like query, file types, dates, category, tags
    knowledge_bases, total = await search_knowledge(
        db=db,
        query=search_request.query,
        organization_id=organization_id,
        file_types=search_request.file_types,
        start_date=search_request.start_date,
        end_date=search_request.end_date,
        category_id=search_request.category_id,
        tag_id=search_request.tag_id
    )
    
    # SH: Format results with content snippets and highlight terms
    results = []
    for kb in knowledge_bases:
        snippet = generate_snippet(
            query=search_request.query,
            knowledge_base_id=kb.id,
            organization_id=organization_id
        )

        if search_request.query:
            for term in search_request.query.split():
                snippet = snippet.replace(term, f"<mark>{term}</mark>")

        results.append({
            "id": kb.id,
            "name": kb.name,
            "filename": kb.filename,
            "content_type": kb.content_type,
            "format": kb.format,
            "uploaded_at": kb.uploaded_at,
            "file_size": kb.file_size,
            "snippet": snippet,
            "category": kb.category,
            "tags": kb.tags
        })
    
    return {
        "results": results,
        "total": total
    }

