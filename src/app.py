from os import environ
from fastapi import FastAPI, APIRouter, Header, Depends, UploadFile, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import select
from db import db
from uuid import UUID, uuid4
from typing import Optional, Annotated
from model.api_models import Article, DocumentType, DatabaseMetrics, ArticleQuery
from pdf.pdf_operations import PdfDbArticleConverter, PdfOperator, PdfPageOperator, PdfPageSnippetOperator
from util.openapi_reverse_proxy_util import add_openapi_route

api_prefix = environ['API_PREFIX']

app = FastAPI(title="xDD Article Store", docs_url=f"{api_prefix}/docs")
app.add_middleware(GZipMiddleware)

prefix_router = APIRouter(prefix=api_prefix)

add_openapi_route(prefix_router)

@prefix_router.post("/documents")
def add_document(pdf: UploadFile, 
        title: Annotated[str, Form()], bucket: Annotated[str, Form()], doi: Annotated[Optional[str], Form()] = None, 
        x_api_key: Annotated[str, Header()] = None) -> Article:
    """ Upload a new document to the document store """
    if not (title and pdf.file and bucket):
        raise HTTPException("Required parameter missing!")

    data = pdf.file.read()
    
    article_converter = PdfDbArticleConverter(data, title, bucket, doi)
    db.add_article(article_converter.convert(), x_api_key)
    db_article = db.get_article(article_converter.article_id, x_api_key)
    PdfOperator(db_article).upsert(data)
    
    return Article.from_db_article(db_article)



@prefix_router.get("/documents")
def get_documents(page: int = 0, per_page: int = 25) -> list[Article]:
    """ Return a paginated list of alphabetically-sorted documents """
    return db.get_article_list(page, per_page)

@prefix_router.get("/documents/{document_id}")
def get_document(document_id: UUID) -> Article:
    """ Return the metadata for the given document """
    return Article.from_db_article(db.get_article(document_id, None, False))

@prefix_router.delete("/documents/{document_id}")
def delete_document(document_id: UUID, x_api_key: Annotated[str, Header()]):
    """ Delete an article. Requires a write-enabled API key """
    to_delete = db.get_article(document_id, x_api_key)
    db.delete_article(document_id, x_api_key)
    PdfOperator(to_delete).delete()


@prefix_router.get("/documents/{document_id}/content")
def get_document_contents(document_id: UUID, x_api_key: Annotated[Optional[str], Header()] = None) -> RedirectResponse:
    """ Return a redirect to the full PDF contents of the given document """
    article = db.get_article(document_id, x_api_key)
    operator = PdfOperator(article)
    return RedirectResponse(operator.get_presigned_document())

@prefix_router.get("/documents/{document_id}/page/{page_num}")
def get_document_page(
        document_id: UUID, page_num: int, content_type: DocumentType = 'pdf', 
        x_api_key: Optional[str] = Header()) -> RedirectResponse:
    """ Return a redirect to the contents of a single page of the given document
    in the specified output format
    """
    article = db.get_article(document_id, x_api_key)
    operator = PdfPageOperator(article, page_num, content_type)
    return RedirectResponse(operator.get_presigned_document())

@prefix_router.get("/documents/{document_id}/page/{page_num}/snippet/{snippet}")
def get_document_snippet(
        document_id: UUID, page_num: int, snippet: str, x_api_key: Annotated[Optional[str], Header()] = None, 
        content_type: DocumentType = 'pdf') -> RedirectResponse:
    """ Return a redirect to the contents of a single page of the given document
    in the specified output format, with the region given by the comma-separated
    list of bounds highlighted
    """
    snippet_bb = [int(s) for s in snippet.split(',')]
    article = db.get_article(document_id, x_api_key)
    operator = PdfPageSnippetOperator(article, page_num, snippet_bb, content_type)
    return RedirectResponse(operator.get_presigned_document())

@prefix_router.get("/metrics")
def get_metrics() -> DatabaseMetrics:
    return db.get_db_metrics()

@prefix_router.get("/query")
def query_articles(query: Annotated[ArticleQuery, Depends()]) -> Article:
    """ Query an article based on an external ID (xdd id or doi)"""
    return db.query_articles(query)

app.include_router(prefix_router)
