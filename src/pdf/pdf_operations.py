from fitz.fitz import Document
from db.db_models import DbArticle
from s3.s3_client import *
from typing import Optional
from model.api_models import DocumentType
from uuid import uuid4
import fitz

COLOR_GOLD = (1, 1, 0)
BASE_DPI = (300, 300)

class PdfDbArticleConverter:
    """ Utility class for creating a DbArticle from extracted PyMuPDF metadata """
    data: bytes
    title: str
    bucket: str
    doi: str

    article_id: str

    def __init__(self, data, title, bucket, doi):
        self.article_id = str(uuid4())
        self.data = data
        self.title = title
        self.doi = doi
        self.bucket = bucket

    def convert(self):
        article = DbArticle()
        article.id = self.article_id
        article.bucket_name = self.bucket
        article.doi = self.doi
        article.title = self.title

        doc = fitz.Document("pdf", self.data)
        article.page_count = doc.page_count
        article.page_width = int(doc[0].rect.width)
        article.page_height = int(doc[0].rect.height)

        return article
    


class PdfOperator:
    """ Base level Pdf operator. Defines the skeleton for performing the following operation on a source PDF:
    - Check if the expected output for the operation is cached
    - If not, retrieve the source PDF, perform modifications, then write it to a temporary destination path in s3
    - Return a presigned url for temporary read access to the output document

    The base implementation is a no-op that returns a link to the source PDF without performing any modifications
    """
    article: DbArticle
    content_type: DocumentType = "pdf"

    def __init__(self, article: DbArticle):
        self.article = article

    @property
    def source_path(self):
        """ Path to the input document """
        return f"documents/{self.article.id}.pdf"

    @property
    def dest_path(self):
        """ Temporary storage location for the destination document """
        return self.source_path

    def _generate_output(self, source_doc: fitz.Document) -> Optional[fitz.Document]:
        """ Perform modifications on the input document """
        pass # By default, don't generate any secondary artifacts

    def _get_output_bytes(self, doc: fitz.Document) -> bytes:
        """ Helper to call various PyMuPDF output generation methods """
        if self.content_type == 'pdf':
            return doc.write()
        elif self.content_type == 'webp':
            return doc[0].get_pixmap().pil_tobytes(format='WEBP', optimize=True, dpi=BASE_DPI)
        elif self.content_type == 'svg':
            return doc[0].get_svg_image()

    def get_presigned_document(self) -> str:
        """ Check if a cached version of the output document exists, and generate it if it doesn't.
        Then, return a presigned URL to the cached location of the output document
        """
        if not self.exists():
            # Get the source document and perform modifications
            source_doc = get_object_body(self.article.bucket_name, self.source_path)
            source_pdf = fitz.Document("pdf", source_doc.read())
            dest_doc = self._generate_output(source_pdf)
            if dest_doc:
                # quick sanity check here to prevent overwrites of the source document
                assert self.source_path != self.dest_path
                output_bytes = self._get_output_bytes(dest_doc)
                self.upsert(output_bytes)

        return get_presigned_url(self.article.bucket_name, self.dest_path)

    
    def exists(self):
        """ Return whether this PDF exists in S3 """
        return object_exists(self.article.bucket_name, self.dest_path)

    def upsert(self, body: bytes) -> str:
        """ Add or update this PDF in S3 """
        put_object(self.article.bucket_name, self.source_path, body)

    def delete(self) -> str:
        """ Delete the PDF from S3 """
        delete_object(self.article.bucket_name, self.source_path)


class PdfPageOperator(PdfOperator):
    """ PdfOperator that extracts a single page from the source PDF """
    page: int

    @property
    def dest_path(self):
        return f"pages/{self.article.id}/{self.page}.{self.content_type}"

    def __init__(self, article: DbArticle, page: int, content_type: DocumentType = "pdf"):
        super().__init__(article)
        self.page = page
        self.content_type = content_type

    def _generate_output(self, source_doc: fitz.Document) -> Optional[Document]:
        # create a new document, then insert the given page from the source doc into it
        dest_doc = fitz.Document()
        dest_doc.insert_pdf(source_doc, from_page=self.page, to_page=self.page)
        return dest_doc


class PdfPageSnippetOperator(PdfPageOperator):
    """ PdfOperator that extracts a single page from the source PDF, then highlights a segment """
    bounds: tuple[int, int, int, int]

    @property
    def dest_path(self):
        bb = self.bounds
        return f"snippets/{self.article.id}/{self.page}_{bb[0]}_{bb[1]}_{bb[2]}_{bb[3]}.{self.content_type}"

    def __init__(self, article: DbArticle, page: int, bounds: tuple[int, int, int, int], content_type: DocumentType = "pdf"):
        super().__init__(article, page, content_type)
        self.bounds = bounds

    def _highlight_region(self, doc: fitz.Document, bounds: tuple[int, int, int, int], page_num=0):
        # assumes a single page document generated via get_page_from_stream
        page = doc[page_num]
        rect : fitz.Annot = page.add_rect_annot(fitz.Rect(*bounds))
        rect.set_colors(fill=COLOR_GOLD)
        rect.update(opacity=0.5)

    def _generate_output(self, source_doc: Document) -> Optional[Document]:
        doc = super()._generate_output(source_doc)
        self._highlight_region(doc, self.bounds)
        return doc
