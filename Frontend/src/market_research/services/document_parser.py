"""
Document Parser Service for Data Analysis Agent

Handles PDF and CSV document parsing with comprehensive error handling
and validation following VMP service patterns.
"""

import io
import csv
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
from pypdf import PdfReader
from fastapi import UploadFile, HTTPException

from ..utils.error_handling import (
    DocumentProcessingError, PDFParsingError, CSVParsingError,
    handle_document_processing_errors, retry_with_exponential_backoff,
    monitor_performance, error_monitor, ErrorCategory, ErrorSeverity
)

from .quantitative_analyzer import QuantitativeAnalyzer


logger = logging.getLogger(__name__)


class DocumentParserService:
    """
    Service for parsing PDF and CSV documents for market research analysis.
    
    Provides robust parsing with comprehensive error handling and validation
    following VMP service patterns.
    """
    
    # File size limits (in bytes)
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_CSV_SIZE = 20 * 1024 * 1024  # 20MB
    
    # Supported file types
    SUPPORTED_PDF_TYPES = ['application/pdf']
    SUPPORTED_CSV_TYPES = ['text/csv', 'application/csv', 'text/plain']
    
    def __init__(self):
        """Initialize the document parser service"""
        self.quantitative_analyzer = QuantitativeAnalyzer()
    
    @handle_document_processing_errors
    @monitor_performance("pdf_parsing")
    @retry_with_exponential_backoff(max_retries=2, exceptions=(IOError, OSError))
    async def parse_pdf(self, file: UploadFile) -> Dict[str, Any]:
        """
        Parse PDF file and extract text content with comprehensive error handling.
        
        Args:
            file: Uploaded PDF file
            
        Returns:
            Dictionary containing parsed content and metadata
            
        Raises:
            PDFParsingError: If PDF parsing fails
            HTTPException: For validation errors
        """
        try:
            # Validate file
            await self._validate_pdf_file(file)
            
            # Read file content
            content = await file.read()
            
            # Reset file pointer for potential reuse
            await file.seek(0)
            
            # Parse PDF content with specific error handling
            try:
                pdf_reader = PdfReader(io.BytesIO(content))
            except Exception as e:
                if "password" in str(e).lower():
                    raise PDFParsingError(
                        "PDF is password-protected and cannot be processed",
                        error_code="PDF_PASSWORD_PROTECTED"
                    )
                elif "corrupt" in str(e).lower() or "invalid" in str(e).lower():
                    raise PDFParsingError(
                        "PDF file appears to be corrupted or invalid",
                        error_code="PDF_CORRUPTED"
                    )
                else:
                    raise PDFParsingError(
                        f"Unable to read PDF file: {str(e)}",
                        error_code="PDF_READ_ERROR"
                    )
            
            # Check if PDF has pages
            if not pdf_reader.pages:
                raise PDFParsingError(
                    "PDF file contains no pages",
                    error_code="PDF_NO_PAGES"
                )
            
            # Extract text from all pages
            text_content = ""
            page_contents = []
            failed_pages = []
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():  # Only add non-empty pages
                        text_content += f"\n--- Page {page_num} ---\n{page_text}\n"
                        page_contents.append({
                            "page_number": page_num,
                            "content": page_text.strip(),
                            "word_count": len(page_text.split())
                        })
                    else:
                        failed_pages.append(page_num)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    failed_pages.append(page_num)
                    continue
            
            # Check if we extracted any meaningful content
            if not text_content.strip():
                if len(failed_pages) == len(pdf_reader.pages):
                    raise PDFParsingError(
                        "PDF appears to contain only images or unreadable content. No text could be extracted.",
                        error_code="PDF_NO_TEXT_CONTENT",
                        details={"total_pages": len(pdf_reader.pages), "failed_pages": failed_pages}
                    )
                else:
                    raise PDFParsingError(
                        "No readable text content found in PDF",
                        error_code="PDF_EMPTY_CONTENT"
                    )
            
            # Log warnings for failed pages
            if failed_pages:
                logger.warning(f"Failed to extract text from {len(failed_pages)} pages in {file.filename}: {failed_pages}")
            
            # Create metadata
            metadata = {
                "filename": file.filename,
                "file_size": len(content),
                "total_pages": len(pdf_reader.pages),
                "extracted_pages": len(page_contents),
                "failed_pages": failed_pages,
                "total_words": sum(page["word_count"] for page in page_contents),
                "parsed_at": datetime.utcnow().isoformat(),
                "content_type": "pdf"
            }
            
            # Record successful parsing
            error_monitor.record_error(
                Exception(f"Successfully parsed PDF with {len(page_contents)} pages"),
                ErrorCategory.DOCUMENT_PROCESSING,
                ErrorSeverity.LOW,
                {"filename": file.filename, "pages": len(page_contents)}
            )
            
            return {
                "raw_text": text_content.strip(),
                "page_contents": page_contents,
                "metadata": metadata
            }
            
        except PDFParsingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing PDF {file.filename}: {e}")
            raise PDFParsingError(
                f"Unexpected error during PDF parsing: {str(e)}",
                error_code="PDF_UNEXPECTED_ERROR"
            )
    
    @handle_document_processing_errors
    @monitor_performance("csv_parsing")
    @retry_with_exponential_backoff(max_retries=2, exceptions=(IOError, OSError))
    async def parse_csv(self, file: UploadFile) -> Dict[str, Any]:
        """
        Parse CSV file and convert to analyzable text format with comprehensive error handling.
        
        Args:
            file: Uploaded CSV file
            
        Returns:
            Dictionary containing parsed content and metadata
            
        Raises:
            CSVParsingError: If CSV parsing fails
            HTTPException: For validation errors
        """
        try:
            # Validate file
            await self._validate_csv_file(file)
            
            # Read file content
            content = await file.read()
            
            # Reset file pointer for potential reuse
            await file.seek(0)
            
            # Try different encodings with specific error handling
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            used_encoding = None
            parsing_errors = []
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(io.BytesIO(content), encoding=encoding)
                    used_encoding = encoding
                    break
                except UnicodeDecodeError as e:
                    parsing_errors.append(f"{encoding}: {str(e)}")
                    continue
                except pd.errors.EmptyDataError:
                    raise CSVParsingError(
                        "CSV file is empty or contains no data",
                        error_code="CSV_EMPTY_FILE"
                    )
                except pd.errors.ParserError as e:
                    parsing_errors.append(f"{encoding}: Parser error - {str(e)}")
                    continue
                except Exception as e:
                    parsing_errors.append(f"{encoding}: {str(e)}")
                    continue
            
            if df is None:
                raise CSVParsingError(
                    f"Unable to parse CSV with any supported encoding. Tried: {', '.join(encodings)}",
                    error_code="CSV_ENCODING_ERROR",
                    details={"encoding_errors": parsing_errors}
                )
            
            # Validate DataFrame content
            if df.empty:
                raise CSVParsingError(
                    "CSV file contains no data rows",
                    error_code="CSV_NO_DATA"
                )
            
            # Check for reasonable column count
            if len(df.columns) > 100:
                logger.warning(f"CSV has many columns ({len(df.columns)}), this may impact processing performance")
            
            # Check for reasonable row count
            if len(df) > 10000:
                logger.warning(f"CSV has many rows ({len(df)}), this may impact processing performance")
            
            # Validate column names
            if df.columns.duplicated().any():
                duplicate_cols = df.columns[df.columns.duplicated()].tolist()
                logger.warning(f"CSV contains duplicate column names: {duplicate_cols}")
            
            # Convert DataFrame to structured text
            try:
                processed_text = self._convert_dataframe_to_text(df)
            except Exception as e:
                raise CSVParsingError(
                    f"Failed to convert CSV data to text format: {str(e)}",
                    error_code="CSV_TEXT_CONVERSION_ERROR"
                )
            
            quantitative_summary = self.quantitative_analyzer.analyze_dataframe(df)

            # Create metadata
            metadata = {
                "filename": file.filename,
                "file_size": len(content),
                "encoding": used_encoding,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": list(df.columns),
                "null_values_count": df.isnull().sum().sum(),
                "parsed_at": datetime.utcnow().isoformat(),
                "content_type": "csv"
            }
            
            # Record successful parsing
            error_monitor.record_error(
                Exception(f"Successfully parsed CSV with {len(df)} rows and {len(df.columns)} columns"),
                ErrorCategory.DOCUMENT_PROCESSING,
                ErrorSeverity.LOW,
                {"filename": file.filename, "rows": len(df), "columns": len(df.columns)}
            )
            
            return {
                "raw_data": df.to_dict('records'),  # Store original data
                "processed_text": processed_text,
                "metadata": metadata,
                "quantitative_summary": quantitative_summary,
            }
            
        except CSVParsingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing CSV {file.filename}: {e}")
            raise CSVParsingError(
                f"Unexpected error during CSV parsing: {str(e)}",
                error_code="CSV_UNEXPECTED_ERROR"
            )
    
    @monitor_performance("document_combination")
    async def combine_documents(
        self, 
        pdf_content: Optional[Dict[str, Any]] = None, 
        csv_content: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Combine PDF and CSV content into a single text for analysis.
        
        Args:
            pdf_content: Parsed PDF content dictionary
            csv_content: Parsed CSV content dictionary
            
        Returns:
            Combined text content for analysis
            
        Raises:
            DocumentProcessingError: If no content provided or combination fails
        """
        try:
            if not pdf_content and not csv_content:
                raise DocumentProcessingError(
                    "At least one document must be provided for combination",
                    error_code="NO_DOCUMENTS_PROVIDED"
                )
            
            combined_text = ""
            
            # Add PDF content
            if pdf_content:
                pdf_text = pdf_content.get("raw_text", "")
                if not pdf_text.strip():
                    logger.warning("PDF content is empty during combination")
                else:
                    combined_text += "=== PDF DOCUMENT CONTENT ===\n\n"
                    combined_text += pdf_text
                    combined_text += "\n\n"
            
            # Add CSV content
            if csv_content:
                csv_text = csv_content.get("processed_text", "")
                if not csv_text.strip():
                    logger.warning("CSV content is empty during combination")
                else:
                    combined_text += "=== CSV SURVEY DATA ===\n\n"
                    combined_text += csv_text
                    combined_text += "\n\n"
            
            final_text = combined_text.strip()
            
            if not final_text:
                raise DocumentProcessingError(
                    "Combined document content is empty",
                    error_code="EMPTY_COMBINED_CONTENT"
                )
            
            logger.info(f"Successfully combined documents. Total length: {len(final_text)} characters")
            return final_text
            
        except DocumentProcessingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error combining documents: {e}")
            raise DocumentProcessingError(
                f"Failed to combine documents: {str(e)}",
                error_code="DOCUMENT_COMBINATION_ERROR"
            )
    
    async def _validate_pdf_file(self, file: UploadFile) -> None:
        """
        Validate PDF file before processing.
        
        Args:
            file: Uploaded file to validate
            
        Raises:
            HTTPException: If validation fails
        """
        # Check file size
        content = await file.read()
        await file.seek(0)  # Reset for later reading
        
        if len(content) > self.MAX_PDF_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"PDF file too large. Maximum size: {self.MAX_PDF_SIZE // (1024*1024)}MB"
            )
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="PDF file is empty")
        
        # Basic PDF file type validation (check for PDF header)
        if not content.startswith(b'%PDF-'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF files are supported."
            )
    
    async def _validate_csv_file(self, file: UploadFile) -> None:
        """
        Validate CSV file before processing.
        
        Args:
            file: Uploaded file to validate
            
        Raises:
            HTTPException: If validation fails
        """
        # Check file size
        content = await file.read()
        await file.seek(0)  # Reset for later reading
        
        if len(content) > self.MAX_CSV_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"CSV file too large. Maximum size: {self.MAX_CSV_SIZE // (1024*1024)}MB"
            )
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        # Basic CSV format validation - try to detect if it's actually CSV-like
        try:
            # Try to read first few lines as CSV
            text_content = content.decode('utf-8', errors='ignore')
            lines = text_content.split('\n')[:5]  # Check first 5 lines
            
            # Check if it looks like CSV (has commas or semicolons)
            has_delimiters = any(',' in line or ';' in line for line in lines if line.strip())
            
            if not has_delimiters:
                raise HTTPException(
                    status_code=400,
                    detail="File does not appear to be a valid CSV format"
                )
                
        except Exception:
            # If we can't even decode it, it's probably not a valid CSV
            raise HTTPException(
                status_code=400,
                detail="Invalid CSV file format"
            )
    
    def _convert_dataframe_to_text(self, df: pd.DataFrame) -> str:
        """
        Convert pandas DataFrame to structured text for analysis.
        
        Args:
            df: Pandas DataFrame to convert
            
        Returns:
            Structured text representation
        """
        text_parts = []
        
        # Add column information
        text_parts.append(f"Survey Data with {len(df)} responses and {len(df.columns)} questions:")
        text_parts.append(f"Columns: {', '.join(df.columns)}")
        text_parts.append("")
        
        # Convert each row to readable format
        for idx, row in df.iterrows():
            text_parts.append(f"--- Response {idx + 1} ---")
            
            for column in df.columns:
                value = row[column]
                
                # Handle different data types
                if pd.isna(value):
                    value_str = "[No response]"
                elif isinstance(value, (int, float)):
                    value_str = str(value)
                else:
                    value_str = str(value).strip()
                
                text_parts.append(f"{column}: {value_str}")
            
            text_parts.append("")  # Empty line between responses
        
        # Add summary statistics for numeric columns
        numeric_columns = df.select_dtypes(include=['number']).columns
        if len(numeric_columns) > 0:
            text_parts.append("=== NUMERIC SUMMARY ===")
            for col in numeric_columns:
                if not df[col].isna().all():  # Only if column has data
                    mean_val = df[col].mean()
                    median_val = df[col].median()
                    text_parts.append(f"{col}: Mean={mean_val:.2f}, Median={median_val:.2f}")
            text_parts.append("")
        
        return "\n".join(text_parts)


# Service instance getter following VMP patterns
_document_parser_service: Optional[DocumentParserService] = None

def get_document_parser_service() -> DocumentParserService:
    """Get document parser service singleton."""
    global _document_parser_service
    if _document_parser_service is None:
        _document_parser_service = DocumentParserService()
    return _document_parser_service