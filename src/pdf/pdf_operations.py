from db.db_models import DbArticle
from s3.s3_client import *
from typing import IO
from model.models import DocumentType
import fitz

COLOR_GOLD = (1, 1, 0)
BASE_DPI = (300, 300)

def get_page_from_stream(body: IO, page: int) -> fitz.Document:
    doc = fitz.Document()
    source_doc = fitz.Document("pdf", body.read())
    doc.insert_pdf(source_doc, from_page=page, to_page=page)
    return doc


def highlight_region(doc: fitz.Document, bounds: tuple[int, int, int, int], page_num=0):
    # assumes a single page document generated via get_page_from_stream
    page = doc[page_num]
    rect : fitz.Annot = page.add_rect_annot(fitz.Rect(*bounds))
    rect.set_colors(fill=COLOR_GOLD)
    rect.update(opacity=0.5)

def get_output_bytes(doc: fitz.Document, content_type: DocumentType) -> bytes:
    if content_type == 'pdf':
        return doc.write()
    elif content_type == 'webp':
        return doc[0].get_pixmap().pil_tobytes(format='WEBP', optimize=True, dpi=BASE_DPI)
    elif content_type == 'svg':
        return doc[0].get_svg_image()

def extract_page(article: DbArticle, page: int, content_type: DocumentType = 'pdf') -> str:
    # Return a cached result if it exists
    bucket = article.bucket_name
    page_path = get_page_path(article.id, page, content_type)

    if not object_exists(bucket, page_path):
        body = get_object_body(bucket, get_article_path(article.id))
        with get_page_from_stream(body, page) as doc:
            put_object(bucket, page_path, get_output_bytes(doc, content_type))

    return get_presigned_url(bucket, page_path)
    
def extract_snippet(article: DbArticle, page: int, bb: tuple[int, int, int, int], content_type: DocumentType = 'pdf') -> str:
    # Return a cached result if it exists
    bucket = article.bucket_name
    snippet_path = get_snippet_path(article.id, page, bb, content_type)

    if not object_exists(bucket, snippet_path):
        body = get_object_body(bucket, get_article_path(article.id))
        with get_page_from_stream(body, page) as doc:
            highlight_region(doc, bb)
            put_object(bucket, snippet_path, get_output_bytes(doc, content_type))

    return get_presigned_url(bucket, snippet_path)
