# xDD-supplemented Document Store for CriticalMAAS

This service provides full-document context over a set of PDFs stored
in a document store. It responds to needs of the CriticalMAAS program for designing
workflows linking machine-reading capabilities with human evaluation and
verification, over large sets of internal documents.

The system serves a key role as a PDF document store component of the
"CriticalMAAS Data Repository". It also fills a more general capability gap
for linking xDD to external workflows that can be relevant outside of
CriticalMAAS.

The APIs atop this store provide:

- A standardized data service for accessing PDF document sets for ML pipeline
  development, and storing document extractions produced by ML processing pipelines.
- Contextual page snippets of PDFs for use in _"human-in-the-loop"_ applications

The system is integrated with xDD capabilities for search, discovery, and
filtering (e.g.,
[the xDD snippets API](https://xdd.wisc.edu/api/snippets?term=Belle%20Fourche%20Formation&set=dolomites))
but can be managed independently (e.g., by USGS as part of the CriticalMAAS program). 

Work is ongoing to integrate the system into the CriticalMAAS CDR, beginning by porting the model into the 
[central CriticalMAAS CDR schemas](https://github.com/DARPA-CRITICALMAAS/cdr_schemas)
maintained by Jataware.

**xDD will not provide or integrate capabilities for
accessing full-text documents as part of its core services.**

## Access control

> [!warning] Copyright safety This application provides full text access to
> PDFs, which is often reserved to the original publisher. It is designed for
> internal use for testing and validation, except in unusual cases where all
> documents can be verified to be in the public domain.
>
> **Attestation that document access follows legal requirements** is the
> responsibility of the maintainer of the PDF document store, not xDD. When
> legal obligations preclude such access, or are ambiguous, xDD core services
> should be used without this application.

### Document store

Access to PDFs is controlled at the document store level. Each document
store must contain only PDFs with copyright status appropriate to its level of
public access. Examples:

- A public S3 bucket for documents that we know are in the public domain
- A secure S3 bucket with "USGS internal" access for work products associated
  with CriticalMAAS with more ambiguous copyright (e.g., `geoarchive` set, or
  some subset of that)

### API layer

API access controls will require access limitations corresponding
to those for the document PDFs (except for metadata routes, which will have
only basic information). At present, API key authentication is used to limit
access to the system.

## Components

- **Document store**: An unstructured set of PDF documents stored an S3 bucket
- **Metadata database**: PostgreSQL database containing PDF links, 
  xDD ID, source document link, page counts and sizes, document extractions,
  and other metadata
- **Metadata API**: API providing read and write access to document metadata
- **Document API**: API providing authenticated access to full document
  content and page-level document content
- **Extractions API**: API providing read and write access to the results of
  external metadata extraction workflows. This API is designed around storing
  [COSMOS](https://github.com/UW-COSMOS/Cosmos) figure extractions but is extensible for other extraction types.

A stable ID is assigned to each document upon ingest. This is distinct from the
xDD ID, to allow for the upload of documents not contained in xDD. 

### Future Components

> [!todo] OCR text, ElasticSearch, and other services
> Providing access and search over the OCR text layer of PDFs
> will require significant backend infrastructure beyond a simple collection of
> PDFs, but it might be worthwhile to drive certain extraction tasks.

## API structure

An [OpenAPI specification](https://xdd.wisc.edu/documentstore-api/docs) for the 
Document Store API is maintained as part of the development process. A summary
of the endpoints provided is as follows:

### Metadata

- `GET /documents`: Paginated list of all documents in the store
- `GET /document/<stable-id>`: Document metadata for an individual document
- `GET /query`: Search for documents by xDD ID or DOI
- `POST /documents`: Upload a new document and its metadata

### Full-text PDFs

- `GET /document/<stable-id>/content`: The full-text PDF associated with an xDD ID

### Page extraction images

- `GET /document/<stable-id>/page/<n>?content_type={pdf|webp|svg}`: Page PDF thumbnail
- `GET /document/<stable-id>/page/<n>/snippet/<x1>,<y1>,<x2>,<y2>?content_type={pdf|webp|svg}`: Page PDF thumbnail with the given snippet highlighted

### External Document Extractions

- `GET /document/<stable-id>/extractions`: List all extractions associated with a document
- `POST /document/<stable-id>/extractions`: Add a new extraction with location metadata to a document

## Usage

### Application Flow

- Documents with full-text PDFs available can be listed
- Clients should integrate with xDD's API for search and discovery capabilities
- No documents in an xDD set is guaranteed to be part of a full-text document
  store
- _Applications should fail gracefully for documents where full-text PDFs cannot
  be found._

### Working with documents not in xDD

If PDF context is desired for documents not in xDD, the ideal approach will be
to integrate with the "bring your own documents" flow currently being tested by
xDD (November 2023). So new documents would be added to xDD and their full-text
contents retained in this system, in tandem.


### Future Work

Documents uploaded to the document store but not xDD are currently excluded from
other potentially useful services provided by xDD (e.g., OCR processing, ElasticSearch). 
It remains an open question how many services provided by xDD should be
replicated independently in this framework.


### Future Usage Patterns

> [!todo] A staging area for xDD ingestion?
> If this store contained documents not in xDD, this application could
> serve as a "staging area" for bringing documents into the system, if the
> metadata database contained the requisite information (e.g., citations, links to the source) for
> successful ingestion into xDD.

