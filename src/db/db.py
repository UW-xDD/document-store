from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from os import environ
import urllib.parse
from uuid import UUID
from fastapi import HTTPException
from .db_models import Base, DbArticle, DbApiKey
from .article_query import build_article_query
from model.api_models import Article, DatabaseMetrics, ArticleQuery

def setup_engine():
    """ Create a new postgres connection based on environment variables """
    return create_engine(f'postgresql://{environ["PG_USER"]}:{urllib.parse.quote_plus(environ["PG_PASSWORD"])}@{environ["PG_HOST"]}:{environ["PG_PORT"]}/{environ["PG_DATABASE"]}')

engine = setup_engine()

# Create tables if they don't exist
Base.metadata.create_all(engine)
DbSession = sessionmaker(bind=engine)

def _api_key_valid(session: Session, api_key: str):
    """ Check the API key exists and is enabled """
    return session.scalars(select(DbApiKey).filter_by(api_key=api_key, enabled=True)).first() is not None

def _api_key_write_enabled(session: Session, api_key: str):
    """ Check the API key exists and is enabled """
    return session.scalars(select(DbApiKey).filter_by(api_key=api_key, enabled=True, write_enabled=True)).first() is not None


def add_article(article: DbArticle, api_key: str) -> DbArticle:
    """ Add an article to the database if given a valid API key """
    with DbSession() as session:
        if not _api_key_write_enabled(session, api_key):
            raise HTTPException(status_code=403, detail="Invalid API key")
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
        article = session.get(DbArticle, article_id)
        if article is None:
            raise HTTPException(404, "Article matching query criteria not found")
        if auth_required and not article.is_public and not _api_key_valid(session, api_key):
            raise HTTPException(status_code=403, detail="Invalid API key")
        return article

def get_db_metrics() -> DatabaseMetrics:
    """ Retrieve miscellaneous metadata about the state of the database """
    with DbSession() as session:
        document_count = session.query(func.count(DbArticle.id)).scalar()
        return DatabaseMetrics(document_count=document_count)

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
        article = session.get(DbArticle, article_id)
        if article is None:
            raise HTTPException(404, "Article matching query criteria not found")
        if not _api_key_write_enabled(session, api_key) or article.registrant != api_key:
            raise HTTPException(status_code=403, detail="Invalid API key")

        session.delete(article)
        session.commit()
        return article
