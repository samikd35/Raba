"""
Structured PDF Content Extractor for Market Research Analysis

Implements dynamic theme extraction and structured content processing from interview PDFs.
Provides comprehensive content analysis with full traceability and citation generation.
"""

import io
import re
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime
from collections import Counter, defaultdict
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.chunk import ne_chunk
from nltk.tag import pos_tag
from pypdf import PdfReader
from fastapi import UploadFile

from ..utils.error_handling import (
    DocumentProcessingError, PDFParsingError,
    handle_document_processing_errors, retry_with_exponential_backoff,
    monitor_performance, error_monitor, ErrorCategory, ErrorSeverity
)
from .performance_optimizer import get_batch_pdf_processor, get_intelligent_chunking_strategy

logger = logging.getLogger(__name__)

# Download required NLTK data if not present
def _ensure_nltk_data():
    """Ensure all required NLTK data is available."""
    required_packages = [
        ('tokenizers/punkt', 'punkt'),
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('corpora/stopwords', 'stopwords'),
        ('taggers/averaged_perceptron_tagger', 'averaged_perceptron_tagger'),
        ('taggers/averaged_perceptron_tagger_eng', 'averaged_perceptron_tagger_eng'),
        ('chunkers/maxent_ne_chunker', 'maxent_ne_chunker'),
        ('corpora/words', 'words'),
        ('corpora/wordnet', 'wordnet'),
        ('corpora/omw-1.4', 'omw-1.4')
    ]
    
    for data_path, package_name in required_packages:
        try:
            nltk.data.find(data_path)
        except LookupError:
            try:
                nltk.download(package_name, quiet=True)
            except Exception:
                pass  # Continue if download fails

# Initialize NLTK data
_ensure_nltk_data()


class StructuredPDFExtractor:
    """
    Structured PDF content extractor that dynamically extracts themes, quotes,
    and metadata from interview PDFs without predefined categories.
    
    Key Features:
    - Dynamic theme extraction using NLP and keyword matching
    - Participant profiling with demographics and behavioral insights
    - Page and segment-level traceability for citations
    - Quote extraction with context preservation
    - Sentiment analysis and satisfaction scoring
    """
    
    # Configuration constants
    MIN_THEME_FREQUENCY = 2  # Minimum frequency for theme inclusion
    MAX_THEMES = 20  # Maximum number of themes to extract
    MIN_QUOTE_LENGTH = 10  # Minimum quote length in words
    MAX_QUOTE_LENGTH = 100  # Maximum quote length in words
    SEGMENT_SIZE = 500  # Characters per segment for processing
    
    # Common interview keywords for theme detection
    THEME_KEYWORDS = {
        'pain_points': [
            'problem', 'issue', 'challenge', 'difficulty', 'frustration', 'struggle',
            'pain', 'obstacle', 'barrier', 'concern', 'worry', 'complaint'
        ],
        'solutions': [
            'solution', 'fix', 'resolve', 'solve', 'address', 'handle', 'deal',
            'approach', 'method', 'way', 'strategy', 'tool', 'system'
        ],
        'benefits': [
            'benefit', 'advantage', 'value', 'gain', 'improvement', 'better',
            'help', 'useful', 'effective', 'efficient', 'save', 'time'
        ],
        'emotions': [
            'happy', 'satisfied', 'pleased', 'excited', 'frustrated', 'angry',
            'disappointed', 'confused', 'worried', 'stressed', 'relieved'
        ],
        'frequency': [
            'always', 'often', 'frequently', 'sometimes', 'rarely', 'never',
            'daily', 'weekly', 'monthly', 'regularly', 'occasionally'
        ]
    }
    
    # Sentiment indicators
    POSITIVE_INDICATORS = [
        'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
        'love', 'like', 'enjoy', 'satisfied', 'happy', 'pleased'
    ]
    
    NEGATIVE_INDICATORS = [
        'bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike',
        'frustrated', 'angry', 'disappointed', 'confused', 'difficult'
    ]
    
    def __init__(self):
        """Initialize the structured PDF extractor."""
        self.logger = logger
        self.stop_words = set(stopwords.words('english'))
    
    @handle_document_processing_errors
    @monitor_performance("pdf_content_extraction")
    @retry_with_exponential_backoff(max_retries=2, exceptions=(IOError, OSError))
    async def extract_structured_content(
        self, 
        pdf_file: UploadFile, 
        project_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured insights from interview PDFs with full traceability.
        Uses batch processing for large PDFs to manage memory efficiently.
        
        Args:
            pdf_file: Uploaded PDF file
            project_id: Project identifier for citation generation
            persona_id: Optional persona association
            
        Returns:
            Dictionary containing structured content and metadata
            
        Raises:
            PDFParsingError: If PDF parsing or analysis fails
        """
        # Check file size and page count to determine processing strategy
        file_size_mb = await self._get_file_size_mb(pdf_file)
        
        if file_size_mb > 20:  # Use batch processing for files > 20MB
            return await self._extract_content_batched(pdf_file, project_id, persona_id)
        else:
            return await self._extract_content_standard(pdf_file, project_id, persona_id)
    
    async def _get_file_size_mb(self, pdf_file: UploadFile) -> float:
        """Get file size in MB."""
        current_pos = pdf_file.file.tell()
        pdf_file.file.seek(0, 2)  # Seek to end
        size_bytes = pdf_file.file.tell()
        pdf_file.file.seek(current_pos)  # Reset position
        return size_bytes / (1024 * 1024)
    
    async def _extract_content_batched(
        self, 
        pdf_file: UploadFile, 
        project_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract content using batch processing for large PDFs.
        
        Args:
            pdf_file: Uploaded PDF file
            project_id: Project identifier
            persona_id: Optional persona association
            
        Returns:
            Dictionary containing aggregated content from all batches
        """
        self.logger.info(f"Using batch processing for large PDF file: {pdf_file.filename}")
        
        batch_processor = get_batch_pdf_processor()
        chunking_strategy = get_intelligent_chunking_strategy()
        
        # Aggregate content across batches
        all_page_contents = []
        all_themes = {}
        all_quotes = []
        combined_text = ""
        
        # Process batches and aggregate results
        async for batch_result in batch_processor.process_large_pdf_batched(
            pdf_file, project_id, persona_id
        ):
            batch_pages = batch_result["batch_results"]
            
            for page_result in batch_pages:
                if "error" not in page_result and page_result.get("content"):
                    all_page_contents.append({
                        "page_number": page_result["page_number"],
                        "content": page_result["content"],
                        "word_count": page_result["word_count"],
                        "char_count": page_result["char_count"]
                    })
                    
                    combined_text += f"\n--- Page {page_result['page_number']} ---\n{page_result['content']}\n"
                    
                    # Aggregate themes from page
                    page_themes = page_result.get("themes", [])
                    for theme in page_themes:
                        if theme in all_themes:
                            all_themes[theme] += 1
                        else:
                            all_themes[theme] = 1
        
        # Create optimized segments using intelligent chunking
        segments = await chunking_strategy.create_optimized_chunks(
            combined_text, content_type="pdf"
        )
        
        # Extract comprehensive themes from aggregated content
        themes = self._extract_themes_from_segments(segments, project_id)
        
        # Extract key quotes from segments
        key_quotes = self._extract_key_quotes_from_segments(segments, themes, project_id)
        
        # Extract participant profile from combined text
        participant_profile = self._extract_participant_profile({
            "raw_text": combined_text,
            "page_contents": all_page_contents
        })
        
        # Perform sentiment analysis
        sentiment_analysis = self._analyze_sentiment(combined_text)
        
        # Create chunk mapping from segments
        chunk_mapping = self._create_chunk_mapping_from_segments(segments)
        
        # Generate metadata
        metadata = {
            "filename": pdf_file.filename,
            "total_pages": len(all_page_contents),
            "extracted_pages": len(all_page_contents),
            "failed_pages": [],
            "total_words": sum(page["word_count"] for page in all_page_contents),
            "total_segments": len(segments),
            "persona_association": persona_id,
            "processing_timestamp": datetime.utcnow().isoformat(),
            "content_type": "pdf",
            "processing_method": "batched",
            "extraction_quality": {
                "page_success_rate": 1.0,  # All processed pages were successful
                "estimated_completeness": min(1.0, sum(page["word_count"] for page in all_page_contents) / 1000)
            }
        }
        
        return {
            "metadata": metadata,
            "themes": themes,
            "key_quotes": key_quotes,
            "participant_profile": {
                **participant_profile,
                "sentiment_analysis": sentiment_analysis
            },
            "chunk_mapping": chunk_mapping,
            "extraction_timestamp": datetime.utcnow().isoformat()
        }
    
    def _extract_themes_from_segments(self, segments: List[Dict[str, Any]], project_id: str) -> Dict[str, Any]:
        """Extract themes from intelligent segments."""
        themes = {}
        theme_contexts = defaultdict(list)
        
        # Extract themes using existing methods but with segments
        segment_contents = [segment["content"] for segment in segments]
        keyword_themes = self._extract_keyword_themes_from_segments(segments)
        
        # Combine all text for NLP analysis
        all_text = " ".join(segment_contents)
        nlp_themes = self._extract_nlp_themes(all_text)
        
        # Combine and score themes
        all_themes = {**keyword_themes, **nlp_themes}
        
        # Filter and rank themes
        for theme_name, theme_data in all_themes.items():
            if theme_data["frequency"] >= self.MIN_THEME_FREQUENCY:
                citation_id = self._generate_citation_id(project_id, "pdf", "theme", theme_name)
                
                themes[theme_name] = {
                    "frequency": theme_data["frequency"],
                    "percentage": round((theme_data["frequency"] / len(segments)) * 100, 2),
                    "sources": theme_data["sources"],
                    "citation_id": citation_id,
                    "context_examples": theme_data.get("examples", [])[:3]
                }
        
        # Sort themes by frequency and limit
        sorted_themes = dict(
            sorted(themes.items(), key=lambda x: x[1]["frequency"], reverse=True)[:self.MAX_THEMES]
        )
        
        return sorted_themes
    
    def _extract_keyword_themes_from_segments(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract keyword-based themes from segments."""
        themes = {}
        
        for category, keywords in self.THEME_KEYWORDS.items():
            theme_data = {
                "frequency": 0,
                "sources": [],
                "examples": []
            }
            
            for segment in segments:
                content_lower = segment["content"].lower()
                matches = []
                
                for keyword in keywords:
                    if keyword in content_lower:
                        matches.append(keyword)
                
                if matches:
                    theme_data["frequency"] += 1
                    theme_data["sources"].append({
                        "segment_id": segment["chunk_id"],
                        "matched_keywords": matches
                    })
                    
                    # Extract example sentence
                    sentences = sent_tokenize(segment["content"])
                    for sentence in sentences:
                        if any(keyword in sentence.lower() for keyword in matches):
                            theme_data["examples"].append(sentence.strip())
                            break
            
            if theme_data["frequency"] > 0:
                themes[category] = theme_data
        
        return themes
    
    def _extract_key_quotes_from_segments(
        self, 
        segments: List[Dict[str, Any]], 
        themes: Dict[str, Any], 
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Extract key quotes from segments."""
        quotes = []
        
        for segment in segments:
            sentences = sent_tokenize(segment["content"])
            
            for sentence in sentences:
                words = sentence.split()
                
                if self.MIN_QUOTE_LENGTH <= len(words) <= self.MAX_QUOTE_LENGTH:
                    related_themes = []
                    sentence_lower = sentence.lower()
                    
                    for theme_name, theme_data in themes.items():
                        if any(
                            keyword in sentence_lower 
                            for source in theme_data.get("sources", [])
                            for keyword in source.get("matched_keywords", [])
                        ):
                            related_themes.append(theme_name)
                    
                    is_significant = (
                        any(indicator in sentence_lower for indicator in self.POSITIVE_INDICATORS) or
                        any(indicator in sentence_lower for indicator in self.NEGATIVE_INDICATORS) or
                        '"' in sentence or
                        '!' in sentence or
                        len(related_themes) > 0
                    )
                    
                    if is_significant:
                        citation_id = self._generate_citation_id(project_id, "pdf", "quote", str(len(quotes)))
                        
                        quotes.append({
                            "quote": sentence.strip(),
                            "themes": related_themes,
                            "segment_id": segment["chunk_id"],
                            "context": self._extract_quote_context(sentence, segment["content"]),
                            "citation_id": citation_id,
                            "sentiment": self._analyze_quote_sentiment(sentence)
                        })
        
        # Sort quotes by relevance
        quotes.sort(key=lambda q: len(q["themes"]) + abs(q["sentiment"]), reverse=True)
        return quotes[:20]
    
    def _create_chunk_mapping_from_segments(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create chunk mapping from intelligent segments."""
        chunk_mapping = {}
        
        for segment in segments:
            chunk_id = f"chunk_{segment['chunk_id']}"
            
            chunk_mapping[chunk_id] = {
                "segment_ids": [segment["chunk_id"]],
                "char_range": (segment["start_pos"], segment["end_pos"]),
                "word_count": segment["word_count"],
                "chunk_type": segment["chunk_type"],
                "semantic_score": segment["semantic_score"]
            }
        
        return chunk_mapping
    
    async def _extract_content_standard(
        self, 
        pdf_file: UploadFile, 
        project_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Standard content extraction for smaller PDF files.
        
        Args:
            pdf_file: Uploaded PDF file
            project_id: Project identifier for citation generation
            persona_id: Optional persona association
            
        Returns:
            Dictionary containing structured content and metadata
            
        Raises:
            PDFParsingError: If PDF parsing or analysis fails
        """
        try:
            # Read and parse PDF
            pdf_content = await self._read_and_parse_pdf(pdf_file)
            
            # Extract participant information
            participant_profile = self._extract_participant_profile(pdf_content)
            
            # Segment content for processing
            segments = self._segment_content(pdf_content)
            
            # Extract themes dynamically
            themes = self._extract_themes(segments, project_id)
            
            # Extract key quotes
            key_quotes = self._extract_key_quotes(segments, themes, project_id)
            
            # Perform sentiment analysis
            sentiment_analysis = self._analyze_sentiment(pdf_content["raw_text"])
            
            # Create chunk mapping
            chunk_mapping = self._create_chunk_mapping(segments)
            
            # Generate metadata
            metadata = self._generate_metadata(pdf_file, pdf_content, persona_id)
            
            # Compile structured content
            structured_content = {
                "metadata": metadata,
                "themes": themes,
                "key_quotes": key_quotes,
                "participant_profile": {
                    **participant_profile,
                    "sentiment_analysis": sentiment_analysis
                },
                "chunk_mapping": chunk_mapping,
                "extraction_timestamp": datetime.utcnow().isoformat()
            }
            
            self.logger.info(
                f"Successfully extracted structured content from PDF {pdf_file.filename}: "
                f"{len(themes)} themes, {len(key_quotes)} quotes"
            )
            
            return structured_content
            
        except PDFParsingError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error extracting PDF content: {e}")
            raise PDFParsingError(
                f"Failed to extract structured PDF content: {str(e)}",
                error_code="PDF_CONTENT_EXTRACTION_ERROR"
            )
    
    async def _read_and_parse_pdf(self, pdf_file: UploadFile) -> Dict[str, Any]:
        """
        Read and parse PDF file with comprehensive error handling.
        
        Args:
            pdf_file: Uploaded PDF file
            
        Returns:
            Dictionary containing parsed PDF content
            
        Raises:
            PDFParsingError: If PDF cannot be read or parsed
        """
        try:
            # Read file content
            content = await pdf_file.read()
            await pdf_file.seek(0)  # Reset for potential reuse
            
            if len(content) == 0:
                raise PDFParsingError(
                    "PDF file is empty",
                    error_code="PDF_EMPTY_FILE"
                )
            
            # Parse PDF
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
            page_contents = []
            raw_text = ""
            failed_pages = []
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        page_contents.append({
                            "page_number": page_num,
                            "content": page_text.strip(),
                            "word_count": len(page_text.split()),
                            "char_count": len(page_text)
                        })
                        raw_text += f"\n--- Page {page_num} ---\n{page_text}\n"
                    else:
                        failed_pages.append(page_num)
                except Exception as e:
                    self.logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    failed_pages.append(page_num)
                    continue
            
            # Validate extracted content
            if not raw_text.strip():
                raise PDFParsingError(
                    "No readable text content found in PDF",
                    error_code="PDF_NO_TEXT_CONTENT"
                )
            
            return {
                "raw_text": raw_text.strip(),
                "page_contents": page_contents,
                "total_pages": len(pdf_reader.pages),
                "extracted_pages": len(page_contents),
                "failed_pages": failed_pages,
                "total_words": sum(page["word_count"] for page in page_contents),
                "total_chars": len(raw_text)
            }
            
        except PDFParsingError:
            raise
        except Exception as e:
            raise PDFParsingError(
                f"Failed to read PDF file: {str(e)}",
                error_code="PDF_READ_ERROR"
            )
    
    def _extract_participant_profile(self, pdf_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract participant demographics and characteristics from PDF content.
        
        Args:
            pdf_content: Parsed PDF content
            
        Returns:
            Dictionary containing participant profile information
        """
        text = pdf_content["raw_text"].lower()
        profile = {
            "demographics": {},
            "key_characteristics": [],
            "interview_metadata": {}
        }
        
        try:
            # Extract age information
            age_patterns = [
                r'age[:\s]+(\d+)',
                r'(\d+)\s+years?\s+old',
                r'(\d+)\s*y\.?o\.?'
            ]
            
            for pattern in age_patterns:
                match = re.search(pattern, text)
                if match:
                    profile["demographics"]["age"] = int(match.group(1))
                    break
            
            # Extract gender information
            gender_patterns = [
                r'gender[:\s]+(male|female|m|f|man|woman)',
                r'(male|female|m|f|man|woman)'
            ]
            
            for pattern in gender_patterns:
                match = re.search(pattern, text)
                if match:
                    gender = match.group(1).lower()
                    if gender in ['m', 'man', 'male']:
                        profile["demographics"]["gender"] = "male"
                    elif gender in ['f', 'woman', 'female']:
                        profile["demographics"]["gender"] = "female"
                    break
            
            # Extract occupation/role information
            occupation_patterns = [
                r'occupation[:\s]+([^\n\.]+)',
                r'job[:\s]+([^\n\.]+)',
                r'work[:\s]+as[:\s]+([^\n\.]+)',
                r'role[:\s]+([^\n\.]+)'
            ]
            
            for pattern in occupation_patterns:
                match = re.search(pattern, text)
                if match:
                    profile["demographics"]["occupation"] = match.group(1).strip()
                    break
            
            # Extract experience level
            experience_patterns = [
                r'(\d+)\s+years?\s+of\s+experience',
                r'experience[:\s]+(\d+)\s+years?',
                r'(\d+)\s*\+?\s*years?\s+experience'
            ]
            
            for pattern in experience_patterns:
                match = re.search(pattern, text)
                if match:
                    profile["demographics"]["experience_years"] = int(match.group(1))
                    break
            
            # Extract key characteristics using NLP
            characteristics = self._extract_characteristics(text)
            profile["key_characteristics"] = characteristics
            
            # Extract interview metadata
            profile["interview_metadata"] = {
                "duration_estimated": self._estimate_interview_duration(text),
                "interview_type": self._detect_interview_type(text),
                "topics_covered": self._extract_topics(text)
            }
            
        except Exception as e:
            self.logger.warning(f"Error extracting participant profile: {e}")
        
        return profile
    
    def _segment_content(self, pdf_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Segment PDF content into manageable chunks for processing.
        
        Args:
            pdf_content: Parsed PDF content
            
        Returns:
            List of content segments with metadata
        """
        segments = []
        text = pdf_content["raw_text"]
        
        # Split into segments by character count
        for i in range(0, len(text), self.SEGMENT_SIZE):
            segment_text = text[i:i + self.SEGMENT_SIZE]
            
            # Try to break at sentence boundaries
            if i + self.SEGMENT_SIZE < len(text):
                # Find the last sentence boundary
                last_period = segment_text.rfind('.')
                last_question = segment_text.rfind('?')
                last_exclamation = segment_text.rfind('!')
                
                boundary = max(last_period, last_question, last_exclamation)
                if boundary > self.SEGMENT_SIZE * 0.7:  # Only if boundary is not too early
                    segment_text = segment_text[:boundary + 1]
            
            # Determine which page(s) this segment covers
            page_info = self._determine_segment_pages(i, len(segment_text), pdf_content)
            
            segments.append({
                "segment_id": f"segment_{len(segments)}",
                "content": segment_text.strip(),
                "start_char": i,
                "end_char": i + len(segment_text),
                "word_count": len(segment_text.split()),
                "page_info": page_info
            })
        
        return segments
    
    def _extract_themes(self, segments: List[Dict[str, Any]], project_id: str) -> Dict[str, Any]:
        """
        Extract themes dynamically using NLP and keyword matching.
        
        Args:
            segments: Content segments
            project_id: Project ID for citation generation
            
        Returns:
            Dictionary of extracted themes with frequencies and citations
        """
        themes = {}
        theme_contexts = defaultdict(list)
        
        # Combine all segment text for analysis
        all_text = " ".join([segment["content"] for segment in segments])
        
        # Extract themes using different methods
        keyword_themes = self._extract_keyword_themes(segments)
        nlp_themes = self._extract_nlp_themes(all_text)
        
        # Combine and score themes
        all_themes = {**keyword_themes, **nlp_themes}
        
        # Filter and rank themes
        for theme_name, theme_data in all_themes.items():
            if theme_data["frequency"] >= self.MIN_THEME_FREQUENCY:
                # Generate citation ID
                citation_id = self._generate_citation_id(
                    project_id, "pdf", "theme", theme_name
                )
                
                themes[theme_name] = {
                    "frequency": theme_data["frequency"],
                    "percentage": round((theme_data["frequency"] / len(segments)) * 100, 2),
                    "sources": theme_data["sources"],
                    "citation_id": citation_id,
                    "context_examples": theme_data.get("examples", [])[:3]  # Top 3 examples
                }
        
        # Sort themes by frequency and limit to MAX_THEMES
        sorted_themes = dict(
            sorted(themes.items(), key=lambda x: x[1]["frequency"], reverse=True)[:self.MAX_THEMES]
        )
        
        return sorted_themes
    
    def _extract_keyword_themes(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract themes based on predefined keyword categories.
        
        Args:
            segments: Content segments
            
        Returns:
            Dictionary of keyword-based themes
        """
        themes = {}
        
        for category, keywords in self.THEME_KEYWORDS.items():
            theme_data = {
                "frequency": 0,
                "sources": [],
                "examples": []
            }
            
            for segment in segments:
                content_lower = segment["content"].lower()
                matches = []
                
                for keyword in keywords:
                    if keyword in content_lower:
                        matches.append(keyword)
                
                if matches:
                    theme_data["frequency"] += 1
                    theme_data["sources"].append({
                        "segment_id": segment["segment_id"],
                        "page_info": segment["page_info"],
                        "matched_keywords": matches
                    })
                    
                    # Extract example sentence
                    sentences = sent_tokenize(segment["content"])
                    for sentence in sentences:
                        if any(keyword in sentence.lower() for keyword in matches):
                            theme_data["examples"].append(sentence.strip())
                            break
            
            if theme_data["frequency"] > 0:
                themes[category] = theme_data
        
        return themes
    
    def _extract_nlp_themes(self, text: str) -> Dict[str, Any]:
        """
        Extract themes using NLP techniques (noun phrases, entities).
        
        Args:
            text: Full text content
            
        Returns:
            Dictionary of NLP-extracted themes
        """
        themes = {}
        
        try:
            # Tokenize and tag
            tokens = word_tokenize(text.lower())
            pos_tags = pos_tag(tokens)
            
            # Extract noun phrases
            noun_phrases = []
            current_phrase = []
            
            for word, pos in pos_tags:
                if pos.startswith('NN') or pos.startswith('JJ'):  # Nouns and adjectives
                    if word not in self.stop_words and len(word) > 2:
                        current_phrase.append(word)
                else:
                    if len(current_phrase) >= 2:  # Multi-word phrases
                        phrase = " ".join(current_phrase)
                        noun_phrases.append(phrase)
                    current_phrase = []
            
            # Count phrase frequencies
            phrase_counts = Counter(noun_phrases)
            
            # Convert to theme format
            for phrase, count in phrase_counts.most_common(10):  # Top 10 phrases
                if count >= self.MIN_THEME_FREQUENCY:
                    themes[f"concept_{phrase.replace(' ', '_')}"] = {
                        "frequency": count,
                        "sources": [],  # Would need segment-level analysis for sources
                        "examples": [phrase]
                    }
        
        except Exception as e:
            self.logger.warning(f"Error in NLP theme extraction: {e}")
        
        return themes
    
    def _extract_key_quotes(
        self, 
        segments: List[Dict[str, Any]], 
        themes: Dict[str, Any], 
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract key quotes with context and theme associations.
        
        Args:
            segments: Content segments
            themes: Extracted themes
            project_id: Project ID for citation generation
            
        Returns:
            List of key quotes with metadata
        """
        quotes = []
        
        for segment in segments:
            sentences = sent_tokenize(segment["content"])
            
            for sentence in sentences:
                words = sentence.split()
                
                # Filter by length
                if self.MIN_QUOTE_LENGTH <= len(words) <= self.MAX_QUOTE_LENGTH:
                    # Check if quote relates to any theme
                    related_themes = []
                    sentence_lower = sentence.lower()
                    
                    for theme_name, theme_data in themes.items():
                        # Check if quote contains theme-related keywords
                        if any(
                            keyword in sentence_lower 
                            for source in theme_data.get("sources", [])
                            for keyword in source.get("matched_keywords", [])
                        ):
                            related_themes.append(theme_name)
                    
                    # Check for emotional content or strong statements
                    is_significant = (
                        any(indicator in sentence_lower for indicator in self.POSITIVE_INDICATORS) or
                        any(indicator in sentence_lower for indicator in self.NEGATIVE_INDICATORS) or
                        '"' in sentence or  # Direct quotes
                        '!' in sentence or  # Exclamations
                        len(related_themes) > 0  # Theme-related
                    )
                    
                    if is_significant:
                        # Generate citation ID
                        citation_id = self._generate_citation_id(
                            project_id, "pdf", "quote", str(len(quotes))
                        )
                        
                        quotes.append({
                            "quote": sentence.strip(),
                            "themes": related_themes,
                            "page_info": segment["page_info"],
                            "segment_id": segment["segment_id"],
                            "context": self._extract_quote_context(sentence, segment["content"]),
                            "citation_id": citation_id,
                            "sentiment": self._analyze_quote_sentiment(sentence)
                        })
        
        # Sort quotes by relevance (number of themes + sentiment strength)
        quotes.sort(
            key=lambda q: len(q["themes"]) + abs(q["sentiment"]), 
            reverse=True
        )
        
        # Return top quotes (limit to reasonable number)
        return quotes[:20]
    
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of the entire text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        text_lower = text.lower()
        
        # Count positive and negative indicators
        positive_count = sum(1 for indicator in self.POSITIVE_INDICATORS if indicator in text_lower)
        negative_count = sum(1 for indicator in self.NEGATIVE_INDICATORS if indicator in text_lower)
        
        total_indicators = positive_count + negative_count
        
        if total_indicators == 0:
            return {
                "overall_sentiment": 0.0,
                "positive_score": 0.0,
                "negative_score": 0.0,
                "neutral_score": 1.0
            }
        
        positive_ratio = positive_count / total_indicators
        negative_ratio = negative_count / total_indicators
        
        # Calculate overall sentiment (-1 to 1)
        overall_sentiment = positive_ratio - negative_ratio
        
        return {
            "overall_sentiment": round(overall_sentiment, 2),
            "positive_score": round(positive_ratio, 2),
            "negative_score": round(negative_ratio, 2),
            "neutral_score": round(1.0 - positive_ratio - negative_ratio, 2)
        }
    
    def _analyze_quote_sentiment(self, quote: str) -> float:
        """
        Analyze sentiment of a single quote.
        
        Args:
            quote: Quote text
            
        Returns:
            Sentiment score (-1 to 1)
        """
        quote_lower = quote.lower()
        
        positive_count = sum(1 for indicator in self.POSITIVE_INDICATORS if indicator in quote_lower)
        negative_count = sum(1 for indicator in self.NEGATIVE_INDICATORS if indicator in quote_lower)
        
        if positive_count == 0 and negative_count == 0:
            return 0.0
        
        return (positive_count - negative_count) / (positive_count + negative_count)
    
    def _create_chunk_mapping(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create chunk mapping for segments with page and location information.
        
        Args:
            segments: Content segments
            
        Returns:
            Dictionary mapping chunk IDs to segment information
        """
        chunk_mapping = {}
        
        for segment in segments:
            chunk_id = f"chunk_{segment['segment_id']}"
            
            chunk_mapping[chunk_id] = {
                "page_range": self._get_page_range(segment["page_info"]),
                "segment_ids": [segment["segment_id"]],
                "themes_covered": [],  # Would be populated after theme extraction
                "char_range": (segment["start_char"], segment["end_char"]),
                "word_count": segment["word_count"]
            }
        
        return chunk_mapping
    
    def _generate_metadata(
        self, 
        pdf_file: UploadFile, 
        pdf_content: Dict[str, Any], 
        persona_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive metadata for the PDF analysis.
        
        Args:
            pdf_file: Original uploaded file
            pdf_content: Parsed PDF content
            persona_id: Optional persona association
            
        Returns:
            Metadata dictionary
        """
        return {
            "filename": pdf_file.filename,
            "total_pages": pdf_content["total_pages"],
            "extracted_pages": pdf_content["extracted_pages"],
            "failed_pages": pdf_content["failed_pages"],
            "total_words": pdf_content["total_words"],
            "total_segments": len(pdf_content.get("segments", [])),
            "persona_association": persona_id,
            "processing_timestamp": datetime.utcnow().isoformat(),
            "content_type": "pdf",
            "extraction_quality": {
                "page_success_rate": pdf_content["extracted_pages"] / pdf_content["total_pages"],
                "estimated_completeness": min(1.0, pdf_content["total_words"] / 1000)  # Rough estimate
            }
        }
    
    def _generate_citation_id(
        self, 
        project_id: str, 
        source_type: str, 
        content_type: str, 
        identifier: str
    ) -> str:
        """
        Generate unique citation ID with verification hash.
        
        Args:
            project_id: Project identifier
            source_type: Type of source (csv, pdf)
            content_type: Type of content (theme, quote, etc.)
            identifier: Unique identifier for the content
            
        Returns:
            Unique citation ID
        """
        # Create base string for hashing
        base_string = f"{project_id}:{source_type}:{content_type}:{identifier}:{datetime.utcnow().isoformat()}"
        
        # Generate hash
        hash_object = hashlib.md5(base_string.encode())
        hash_hex = hash_object.hexdigest()[:8]
        
        # Create citation ID
        citation_id = f"pdf_{content_type}_{identifier}_{hash_hex}"
        
        return citation_id
    
    # Helper methods
    
    def _extract_characteristics(self, text: str) -> List[str]:
        """Extract key characteristics from text using keyword analysis."""
        characteristics = []
        
        # Define characteristic patterns
        patterns = {
            "tech_savvy": ["technology", "digital", "app", "software", "online"],
            "experienced": ["experience", "years", "veteran", "senior", "expert"],
            "budget_conscious": ["cost", "price", "budget", "expensive", "cheap", "affordable"],
            "time_pressed": ["time", "busy", "quick", "fast", "urgent", "deadline"],
            "collaborative": ["team", "group", "collaborate", "together", "share"],
            "detail_oriented": ["detail", "precise", "accurate", "thorough", "careful"]
        }
        
        for characteristic, keywords in patterns.items():
            if any(keyword in text for keyword in keywords):
                characteristics.append(characteristic)
        
        return characteristics
    
    def _estimate_interview_duration(self, text: str) -> Optional[int]:
        """Estimate interview duration based on content length."""
        word_count = len(text.split())
        # Rough estimate: 150-200 words per minute of speech
        estimated_minutes = word_count / 175
        return int(estimated_minutes) if estimated_minutes > 5 else None
    
    def _detect_interview_type(self, text: str) -> str:
        """Detect the type of interview based on content patterns."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["user", "customer", "experience", "product"]):
            return "user_interview"
        elif any(word in text_lower for word in ["market", "research", "survey", "study"]):
            return "market_research"
        elif any(word in text_lower for word in ["expert", "professional", "industry"]):
            return "expert_interview"
        else:
            return "general_interview"
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics discussed in the interview."""
        # This is a simplified implementation
        # In practice, you might use more sophisticated topic modeling
        
        topic_keywords = {
            "product_features": ["feature", "functionality", "capability"],
            "user_experience": ["experience", "usability", "interface"],
            "pricing": ["price", "cost", "budget", "payment"],
            "competition": ["competitor", "alternative", "comparison"],
            "workflow": ["process", "workflow", "procedure", "steps"]
        }
        
        topics = []
        text_lower = text.lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _determine_segment_pages(
        self, 
        start_char: int, 
        segment_length: int, 
        pdf_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine which pages a segment covers."""
        # This is a simplified implementation
        # In practice, you'd need to track character positions per page
        
        total_chars = pdf_content["total_chars"]
        total_pages = pdf_content["total_pages"]
        
        # Rough estimate of page coverage
        chars_per_page = total_chars / total_pages if total_pages > 0 else total_chars
        
        start_page = int(start_char / chars_per_page) + 1
        end_page = int((start_char + segment_length) / chars_per_page) + 1
        
        return {
            "start_page": min(start_page, total_pages),
            "end_page": min(end_page, total_pages),
            "estimated": True  # Mark as estimated since we don't have exact page boundaries
        }
    
    def _get_page_range(self, page_info: Dict[str, Any]) -> Tuple[int, int]:
        """Get page range tuple from page info."""
        return (page_info.get("start_page", 1), page_info.get("end_page", 1))
    
    def _extract_quote_context(self, quote: str, segment_content: str) -> str:
        """Extract context around a quote."""
        sentences = sent_tokenize(segment_content)
        
        for i, sentence in enumerate(sentences):
            if quote.strip() in sentence:
                # Get surrounding sentences for context
                start_idx = max(0, i - 1)
                end_idx = min(len(sentences), i + 2)
                context_sentences = sentences[start_idx:end_idx]
                return " ".join(context_sentences)
        
        return segment_content[:200] + "..." if len(segment_content) > 200 else segment_content


# Service instance getter following VMP patterns
_structured_pdf_extractor: Optional[StructuredPDFExtractor] = None

def get_structured_pdf_extractor() -> StructuredPDFExtractor:
    """Get structured PDF extractor service singleton."""
    global _structured_pdf_extractor
    if _structured_pdf_extractor is None:
        _structured_pdf_extractor = StructuredPDFExtractor()
    return _structured_pdf_extractor