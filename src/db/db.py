from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from os import environ
import urllib.parse
from uuid import UUID
from fastapi import HTTPException
from .db_models import Base, DbArticle, DbApiKey, DbArticleExtraction
from .article_query import build_article_query
from model.api_models import Article, DatabaseMetrics, ArticleQuery, ArticleExtraction

def setup_engine():
    """ Create a new postgres connection based on environment variables """
    return create_engine(f'postgresql://{environ["PG_USER"]}:{urllib.parse.quote_plus(environ["PG_PASSWORD"])}@{environ["PG_HOST"]}:{environ["PG_PORT"]}/{environ["PG_DATABASE"]}')

engine = setup_engine()

# Create tables if they don't exist
Base.metadata.create_all(engine)
DbSession = sessionmaker(bind=engine)

def validate_api_key(session: Session, api_key: str):
    """ Check the API key exists and is enabled, raising an exception if not """
    if not session.scalars(select(DbApiKey).filter_by(api_key=api_key, enabled=True)).first():
        raise HTTPException(status_code=403, detail="Invalid API key")

def validate_write_access(session: Session, api_key: str):
    """ Check the API key exists and is allows DB writes, raising an exception if not """
    if not session.scalars(select(DbApiKey).filter_by(api_key=api_key, enabled=True, write_enabled=True)).first():
        raise HTTPException(status_code=403, detail="Invalid API key")

def get_article_with_api_key(session: Session, article_id: str, api_key: str, auth_required: bool = True, modifying = False) -> DbArticle:
    article = session.get(DbArticle, article_id)
    if article is None:
        raise HTTPException(404, "Article matching query criteria not found")
    if modifying:
        validate_write_access(session, api_key)
    elif auth_required and not article.is_public:
        validate_api_key(session, api_key)
    return article

def add_article(article: DbArticle, api_key: str) -> DbArticle:
    """ Add an article to the database if given a valid API key """
    with DbSession() as session:
        validate_write_access(session, api_key)

        article.registrant = api_key
        session.add(article)
        session.commit()
        return article

def get_article_list(page_number: int, per_page: int) -> list[Article]:
    """ Retrieve a paginated list of article summaries """
    with DbSession() as session:
        articles = session.scalars(select(DbArticle)
            .order_by(DbArticle.title).limit(per_page).offset(page_number * per_page)).all()
        return [Article.from_db_article(a) for a in articles]

def get_article(article_id: UUID, api_key: str, auth_required: bool = True) -> DbArticle:
    """ Retrieve an article's metadata, then optionally ensure the requesting user has permissions to access the document """
    with DbSession() as session:
        return get_article_with_api_key(session, article_id, api_key, auth_required)

def get_db_metrics() -> DatabaseMetrics:
    """ Retrieve miscellaneous metadata about the state of the database """
    with DbSession() as session:
        document_count = session.query(func.count(DbArticle.id)).scalar()
        extraction_count = session.query(func.count(DbArticleExtraction.id)).scalar()
        return DatabaseMetrics(document_count=document_count, extraction_count=extraction_count)

def query_articles(query: ArticleQuery) -> DbArticle:
    """ Find an article based on its xdd id or doi """
    with DbSession() as session:
        article = session.scalar(build_article_query(query))
        if article is None:
            raise HTTPException(404, "Article matching query criteria not found")
        return Article.from_db_article(article)

def delete_article(article_id: UUID, api_key: str) -> DbArticle:
    """ Delete an article from the database """
    with DbSession() as session:
        article = get_article_with_api_key(session, article_id, api_key)
        if article.registrant != api_key:
            raise HTTPException(status_code=403, detail="Must own article")

        session.delete(article)
        session.commit()
        return article

def get_article_extractions(article_id: UUID, extraction_type: str = None, api_key: str = None) -> list[ArticleExtraction]:
    """ Get the extractions associated with an article """
    with DbSession() as session:
        article = get_article_with_api_key(session, article_id, api_key)

        extractions = [e for e in article.extractions if extraction_type is None or e.extraction_type == extraction_type]
        return [ArticleExtraction.from_db_extraction(e) for e in extractions]

def add_article_extraction(article_id: UUID, extraction: ArticleExtraction, api_key: str):
    """ Add an extraction to an article """
    with DbSession() as session:
        validate_write_access(session, api_key)
        db_extraction = extraction.to_db_extraction(article_id)
        db_extraction.registrant = api_key
        session.add(db_extraction)
        session.commit()


def delete_article_extraction(article_id: UUID, extraction_id: UUID, api_key: str):
    """ Remove an extraction from an article """
    with DbSession() as session:
        to_delete = session.get(DbArticleExtraction, extraction_id)
        if to_delete.registrant != api_key:
            raise HTTPException(status_code=403, detail="Must own article extraction")
        session.delete(to_delete)
        session.commit()

