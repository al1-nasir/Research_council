"""
POST /upload — upload and process PDF papers.

Allows users to upload PDF papers which are then parsed and stored
for searching within the app.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from api.models import UploadResponse
from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.chunker import chunk_text
from ingestion.embedding_pipeline import store_chunks

logger = logging.getLogger(__name__)
router = APIRouter()

# Upload directory
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a PDF file, extract text, chunk it, and store in vector DB.
    
    Returns the document ID and statistics about the processing.
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Generate unique ID
    doc_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{doc_id}.pdf"

    try:
        # Save uploaded file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Uploaded file: {file.filename} ({len(content)} bytes)")

        # Extract text
        try:
            text = extract_text_from_pdf(file_path)
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"Failed to extract text from PDF: {str(e)}"
            )

        if not text or len(text.strip()) < 100:
            raise HTTPException(
                status_code=422,
                detail="PDF appears to be empty or unreadable"
            )

        # Chunk the text
        chunks = chunk_text(text, source_id=doc_id)

        # Store in vector DB
        n_stored = store_chunks(chunks)

        # Get file size
        file_size = os.path.getsize(file_path)

        return UploadResponse(
            document_id=doc_id,
            filename=file.filename,
            file_size=file_size,
            text_length=len(text),
            chunks_created=len(chunks),
            chunks_stored=n_stored,
            status="success",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF upload failed: {e}", exc_info=True)
        # Cleanup on failure
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/upload/{document_id}")
async def delete_uploaded_pdf(document_id: str) -> JSONResponse:
    """
    Delete an uploaded PDF and its stored chunks.
    """
    file_path = UPLOAD_DIR / f"{document_id}.pdf"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        file_path.unlink()
        logger.info(f"Deleted uploaded file: {document_id}")
        return JSONResponse(content={"status": "deleted", "document_id": document_id})
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
