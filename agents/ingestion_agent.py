"""Data Ingestion Agent: CSV, JSON, and text-based PDF normalization."""
from .shared_agent import ingest, parse_pdf_file, parse_pdf_text

__all__ = ["ingest", "parse_pdf_file", "parse_pdf_text"]
