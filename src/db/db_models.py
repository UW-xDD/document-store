from sqlalchemy import Column, String, Boolean, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
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

    @property
    def doi_link(self):
        return f"https://doi.org/{self.doi}" if self.doi else None

    @property
    def xdd_link(self):
        return f"https://xdd.wisc.edu/api/articles?docid={self.xdd_doc_id}"

    @property
    def is_public(self):
        return self.bucket_name == PUBLIC_PDF_BUCKET

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



