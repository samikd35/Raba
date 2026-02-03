"""
PDF Extractor Service

Extracts text content from uploaded PDF files for bootstrap context generation.
"""

import logging
import os
import tempfile
from typing import Dict, Any, List, Optional
import asyncio

logger = logging.getLogger(__name__)


class PDFExtractorService:
    """
    Service for extracting text content from PDF files.
    
    Uses PyPDF2 as primary extractor with pdfplumber as fallback.
    """
    
    def __init__(self):
        """Initialize PDF extractor."""
        self._check_dependencies()
        logger.info("PDF Extractor Service initialized")
    
    def _check_dependencies(self):
        """Check if PDF extraction libraries are available."""
        try:
            import PyPDF2
            self.has_pypdf2 = True
        except ImportError:
            self.has_pypdf2 = False
            logger.warning("PyPDF2 not installed, PDF extraction may be limited")
        
        try:
            import pdfplumber
            self.has_pdfplumber = True
        except ImportError:
            self.has_pdfplumber = False
            logger.warning("pdfplumber not installed, fallback extraction unavailable")
    
    async def extract_text_from_pdf(
        self,
        file_path: str,
        max_pages: int = 50
    ) -> Dict[str, Any]:
        """
        Extract text from a single PDF file.
        
        Args:
            file_path: Path to the PDF file
            max_pages: Maximum number of pages to extract
            
        Returns:
            Dict with extracted text and metadata
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            
            # Try PyPDF2 first
            if self.has_pypdf2:
                result = await self._extract_with_pypdf2(file_path, max_pages)
                if result["success"]:
                    return result
            
            # Fallback to pdfplumber
            if self.has_pdfplumber:
                result = await self._extract_with_pdfplumber(file_path, max_pages)
                if result["success"]:
                    return result
            
            raise Exception("No PDF extraction library available")
            
        except Exception as e:
            logger.error(f"❌ Error extracting PDF {file_path}: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "file_path": file_path
            }
    
    async def _extract_with_pypdf2(
        self,
        file_path: str,
        max_pages: int
    ) -> Dict[str, Any]:
        """Extract text using PyPDF2."""
        try:
            import PyPDF2
            
            def _extract():
                text_parts = []
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    total_pages = len(reader.pages)
                    pages_to_extract = min(total_pages, max_pages)
                    
                    for i in range(pages_to_extract):
                        page = reader.pages[i]
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    
                    return {
                        "text": "\n\n".join(text_parts),
                        "total_pages": total_pages,
                        "extracted_pages": pages_to_extract,
                        "extractor": "pypdf2"
                    }
            
            # Run in thread pool to not block async
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _extract)
            
            return {
                "success": True,
                "file_path": file_path,
                **result
            }
            
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_with_pdfplumber(
        self,
        file_path: str,
        max_pages: int
    ) -> Dict[str, Any]:
        """Extract text using pdfplumber (better for complex layouts)."""
        try:
            import pdfplumber
            
            def _extract():
                text_parts = []
                with pdfplumber.open(file_path) as pdf:
                    total_pages = len(pdf.pages)
                    pages_to_extract = min(total_pages, max_pages)
                    
                    for i in range(pages_to_extract):
                        page = pdf.pages[i]
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    
                    return {
                        "text": "\n\n".join(text_parts),
                        "total_pages": total_pages,
                        "extracted_pages": pages_to_extract,
                        "extractor": "pdfplumber"
                    }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _extract)
            
            return {
                "success": True,
                "file_path": file_path,
                **result
            }
            
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def extract_from_storage(
        self,
        file_key: str,
        bucket: str = "bootstrap-uploads"
    ) -> Dict[str, Any]:
        """
        Download file from Supabase storage and extract text.
        
        Args:
            file_key: Storage key for the file
            bucket: Storage bucket name
            
        Returns:
            Dict with extracted text and metadata
        """
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            supabase = get_service_role_client()
            
            # Download file to temp location
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = tmp.name
                
                try:
                    # Download from Supabase storage
                    response = supabase.client.storage.from_(bucket).download(file_key)
                    tmp.write(response)
                    tmp.flush()
                    
                    # Extract text
                    result = await self.extract_text_from_pdf(tmp_path)
                    result["file_key"] = file_key
                    result["bucket"] = bucket
                    
                    return result
                    
                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                        
        except Exception as e:
            logger.error(f"❌ Error extracting from storage {file_key}: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "file_key": file_key
            }
    
    async def extract_text_from_files(
        self,
        file_keys: List[str],
        bucket: str = "bootstrap-uploads"
    ) -> List[Dict[str, Any]]:
        """
        Extract text from multiple files in storage.
        
        Args:
            file_keys: List of storage keys
            bucket: Storage bucket name
            
        Returns:
            List of extraction results
        """
        results = []
        
        for file_key in file_keys:
            # Determine file type from extension
            if file_key.lower().endswith('.pdf'):
                result = await self.extract_from_storage(file_key, bucket)
            else:
                # For non-PDF files, try to read as text
                result = await self._extract_text_file(file_key, bucket)
            
            results.append(result)
        
        logger.info(f"✅ Extracted text from {len(results)} files")
        return results
    
    async def _extract_text_file(
        self,
        file_key: str,
        bucket: str
    ) -> Dict[str, Any]:
        """Extract content from a plain text file."""
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            supabase = get_service_role_client()
            response = supabase.client.storage.from_(bucket).download(file_key)
            
            # Try to decode as UTF-8
            try:
                text = response.decode('utf-8')
            except UnicodeDecodeError:
                text = response.decode('latin-1')
            
            return {
                "success": True,
                "text": text,
                "file_key": file_key,
                "bucket": bucket,
                "extractor": "text"
            }
            
        except Exception as e:
            logger.error(f"❌ Error extracting text file {file_key}: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "file_key": file_key
            }


def get_pdf_extractor_service() -> PDFExtractorService:
    """Factory function for PDFExtractorService."""
    return PDFExtractorService()
