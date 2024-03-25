from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal, Any
from uuid import UUID
from db.db_models import DbArticle, DbArticleExtraction

DocumentType = Literal['pdf', 'webp', 'svg']

class Article(BaseModel):
    """ JSON model for user-facing document metadata """
    id: UUID = Field(..., description="The internal ID of the document")
    title: str = Field(..., description="Title of the document")
    is_public: bool = Field(..., description="Whether the full content of the PDF can be downloaded without authorization")

    xdd_id: Optional[str] = Field(None, description="The XDD Canonical ID of the document, if present")
    doi: Optional[str] = Field(None, description="The digital object identifier of the document, if present")
    pages: Optional[int] = Field(None, description="Document page count")
    page_width: Optional[int] = Field(None, description="Width of a page in the document")
    page_height: Optional[int] = Field(None, description="Height of a page in the document")
    ingest_date: Optional[Any] = Field(None, description="Article ingest date")
    ingest_batch: Optional[Any] = Field(None, description="Article ingest batch")

    xdd_link: Optional[str] = Field(None, description="xdd api link to the article")
    doi_link: Optional[str] = Field(None, description="doi.org link to the article")



    @staticmethod
    def from_db_article(db_article: DbArticle) -> "Article":
        return Article(
            id = db_article.id,
            title = db_article.title,
            xdd_id = db_article.xdd_doc_id,
            doi = db_article.doi,
            pages = db_article.page_count,
            page_width = db_article.page_width,
            page_height = db_article.page_height,
            xdd_link = db_article.xdd_link,
            doi_link = db_article.doi_link,
            ingest_date = db_article.ingest_date,
            ingest_batch = db_article.ingest_batch,
            is_public=db_article.is_public
        )


class DatabaseMetrics(BaseModel):
    """ JSON model for database metrics """
    document_count: int = Field(..., description="The count of documents in the database")
    extraction_count: int = Field(..., description="The count of document extractions in the database")


class ArticleQuery(BaseModel):
    """ Query parameters model for searching articles """
    xdd_id: Optional[str] = Field(None, description="The XDD Canonical ID of the document to search")
    doi: Optional[str] = Field(None, description="The digital object identifier of the document to search")

    @model_validator(mode='after')
    def check_not_empty(self):
        assert self.xdd_id or self.doi, "Must provide at least one query parameter"


class ArticleExtraction(BaseModel):
    """ JSON model for article extractions obtained via an external service """
    id: UUID | None = Field(None, description="The internal ID of the xtraction")
    extraction_type: str = Field(..., description="The type of model that produced the extraction")
    extraction_label: str = Field(..., description="The classification of the extraction within its model")
    score: float | None = Field(None, description="The confidence of the extraction")
    bbox: tuple[float, float, float, float] | None = Field(None, description="The bounding box of the extraction")
    page_num: int | None = Field(None, description="The page number of the extraction")
    external_link: str | None = Field(None, description="A link to the extraction")
    data: dict | None = Field(None, description="Extra information about the extraction")

    @staticmethod
    def from_db_extraction(db_extraction: DbArticleExtraction) -> "ArticleExtraction":
        return ArticleExtraction(
            id = db_extraction.id,
            extraction_type=db_extraction.extraction_type,
            extraction_label=db_extraction.label,
            page_num=db_extraction.page,
            score=db_extraction.score,
            bbox=[db_extraction.x0, db_extraction.y0, db_extraction.x1, db_extraction.y1],
            external_link=db_extraction.url,
            data = db_extraction.extra_data
        )

    def to_db_extraction(self, article_id: UUID) -> DbArticleExtraction:
        return DbArticleExtraction(
            article_id,
            self.extraction_type,
            self.extraction_label,
            self.score,
            self.data,
            self.external_link,
            self.page_num,
            self.bbox)
