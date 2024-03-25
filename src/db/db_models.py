from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column
from uuid import uuid4

# TODO don't hardcode which bucket is public
PUBLIC_PDF_BUCKET = "public-pdfs"

class Base(DeclarativeBase):
    pass

class DbArticle(Base):
    """ ORM Mapping for articles in the document store """
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String)
    xdd_doc_id = Column(String, unique=True, default=None)
    doi = Column(String, unique=True, default=None)
    bucket_name = Column(String)

    page_width = Column(Integer, default=None)
    page_height = Column(Integer, default=None)
    page_count = Column(Integer, default=None)

    ingest_date = Column(DateTime, nullable=False, server_default=func.now())
    ingest_batch = Column(String, default=None)
    registrant = Column(String, default=None) # Currently, the API key that uploaded the article, if any

    extractions: Mapped[list["DbArticleExtraction"]] = relationship(cascade="delete")

    @property
    def doi_link(self):
        return f"https://doi.org/{self.doi}" if self.doi else None

    @property
    def xdd_link(self):
        return f"https://xdd.wisc.edu/api/articles?docid={self.xdd_doc_id}"

    @property
    def is_public(self):
        return self.bucket_name == PUBLIC_PDF_BUCKET

class DbArticleExtraction(Base):
    """ ORM Mapping for a (relatively) agnostic piece of metadata extracted from an article.
    Assumes the extraction correlates to a rectangular location within the document """
    __tablename__ = "article_extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(ForeignKey('articles.id'))

    # Category of the extraction
    extraction_type = Column(String, nullable=False)
    # Classification of the extraction within its category
    label = Column(String, default=None)
    # Confidence score of the extraction
    score = Column(Float, default=True)
    # Extra metadata about the extraction within its category
    extra_data = Column(JSONB, default=None)
    # If the extraction is hosted locally, its path in S3
    s3_path = Column(String, default=None)
    # If the extraction is hosted remotely, its url
    url = Column(String, default=None)

    # Location of extraction within its parent PDF
    page = Column(Integer, default=None)
    x0   = Column(Float, default=None)
    x1   = Column(Float, default=None)
    y0   = Column(Float, default=None)
    y1   = Column(Float, default=None)

    # Ownership info 
    extraction_date = Column(DateTime, nullable=False, server_default=func.now())
    registrant = Column(String, default=None)

    def __init__(self, article_id, extraction_type, label, score, extra_data, url, page, bounds):
        self.article_id = article_id
        self.extraction_type = extraction_type
        self.label = label
        self.score = score
        self.extra_data = extra_data
        self.url = url
        self.page = page
        self.x0, self.y0, self.x1, self.y1 = bounds or [None] * 4


class DbApiKey(Base):
    """ ORM Mapping for simple API key based authorization to access copyright-protected documents """
    __tablename__ = "api_keys"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    api_key = Column(String, nullable=False, unique=True)
    # Name associated with the API key
    contact_name = Column(String, nullable=False)
    # Email associated with the API key
    contact_email = Column(String, nullable=False, unique=True)
    enabled = Column(Boolean, default=True)
    write_enabled = Column(Boolean, default=False) # Whether the API key enables put/post/delete operations

