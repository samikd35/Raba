"""
Dynamic CSV Statistics Extractor for Market Research Analysis

Implements dynamic field detection and statistical extraction without predefined schemas.
Provides accurate statistical distributions with full traceability and citation generation.
"""

import io
import csv
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
import pandas as pd
import numpy as np
from fastapi import UploadFile, HTTPException

from ..utils.error_handling import (
    DocumentProcessingError, CSVParsingError,
    handle_document_processing_errors, retry_with_exponential_backoff,
    monitor_performance, error_monitor, ErrorCategory, ErrorSeverity
)
from .performance_optimizer import get_streaming_csv_processor
from .caching_optimization_system import get_statistics_cache

logger = logging.getLogger(__name__)


class DynamicCSVStatisticsExtractor:
    """
    Dynamic CSV statistics extractor that automatically detects field types
    and generates comprehensive statistical distributions without predefined schemas.
    
    Key Features:
    - Automatic field type detection (categorical, numerical, text, date)
    - Adaptive processing for any CSV structure
    - Exact statistical distributions for categorical fields
    - Chunk-to-row mapping for accurate percentage calculations
    - Unique citation IDs with verification hashes
    - Persona association support
    """
    
    # Configuration constants
    MAX_CATEGORICAL_UNIQUE_VALUES = 50  # Max unique values to treat as categorical
    MIN_CATEGORICAL_FREQUENCY = 2  # Min frequency to include in distributions
    CHUNK_SIZE = 500  # Default chunk size for processing
    
    def __init__(self):
        """Initialize the dynamic CSV statistics extractor."""
        self.logger = logger
    
    @handle_document_processing_errors
    @monitor_performance("csv_statistics_extraction")
    @retry_with_exponential_backoff(max_retries=2, exceptions=(IOError, OSError))
    async def extract_statistics(
        self, 
        csv_file: UploadFile, 
        project_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dynamically analyze CSV structure and extract all statistical distributions.
        Uses streaming processing for large files to avoid memory limitations.
        
        Args:
            csv_file: Uploaded CSV file
            project_id: Project identifier for citation generation
            persona_id: Optional persona association
            
        Returns:
            Dictionary containing comprehensive statistics and metadata
            
        Raises:
            CSVParsingError: If CSV parsing or analysis fails
        """
        # Check file size to determine processing strategy
        file_size_mb = await self._get_file_size_mb(csv_file)
        
        if file_size_mb > 50:  # Use streaming for files > 50MB
            return await self._extract_statistics_streaming(csv_file, project_id, persona_id)
        else:
            return await self._extract_statistics_standard(csv_file, project_id, persona_id)
    
    async def _get_file_size_mb(self, csv_file: UploadFile) -> float:
        """Get file size in MB."""
        current_pos = csv_file.file.tell()
        csv_file.file.seek(0, 2)  # Seek to end
        size_bytes = csv_file.file.tell()
        csv_file.file.seek(current_pos)  # Reset position
        return size_bytes / (1024 * 1024)
    
    async def _extract_statistics_streaming(
        self, 
        csv_file: UploadFile, 
        project_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract statistics using streaming processing for large files.
        
        Args:
            csv_file: Uploaded CSV file
            project_id: Project identifier
            persona_id: Optional persona association
            
        Returns:
            Dictionary containing aggregated statistics from all chunks
        """
        self.logger.info(f"Using streaming processing for large CSV file: {csv_file.filename}")
        
        streaming_processor = get_streaming_csv_processor()
        
        # Aggregate statistics across chunks
        aggregated_stats = {
            "metadata": None,
            "categorical_distributions": {},
            "numerical_summaries": {},
            "chunk_mapping": {},
            "field_types": {},
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "processing_method": "streaming"
        }
        
        total_rows = 0
        chunk_count = 0
        
        # Process chunks and aggregate results
        async for chunk_result in streaming_processor.process_large_csv_streaming(
            csv_file, project_id, persona_id
        ):
            chunk_stats = chunk_result["chunk_statistics"]
            chunk_count += 1
            total_rows += chunk_stats.get("row_count", 0)
            
            # Aggregate categorical distributions
            for field, stats in chunk_stats.get("categorical_distributions", {}).items():
                if field not in aggregated_stats["categorical_distributions"]:
                    aggregated_stats["categorical_distributions"][field] = {
                        "total_responses": 0,
                        "unique_values": set(),
                        "value_counts": {},
                        "field_type": "categorical"
                    }
                
                # Aggregate counts
                aggregated_stats["categorical_distributions"][field]["total_responses"] += stats["chunk_total"]
                
                for value, count in stats["top_values"].items():
                    if value in aggregated_stats["categorical_distributions"][field]["value_counts"]:
                        aggregated_stats["categorical_distributions"][field]["value_counts"][value] += count
                    else:
                        aggregated_stats["categorical_distributions"][field]["value_counts"][value] = count
            
            # Store chunk mapping
            chunk_id = chunk_stats["chunk_id"]
            aggregated_stats["chunk_mapping"][chunk_id] = {
                "row_numbers": list(range(
                    total_rows - chunk_stats["row_count"], 
                    total_rows
                )),
                "respondent_count": chunk_stats["row_count"],
                "field_coverage": list(chunk_stats.get("field_types", {}).keys())
            }
            
            # Update field types
            aggregated_stats["field_types"].update(chunk_stats.get("field_types", {}))
        
        # Finalize categorical distributions
        for field, stats in aggregated_stats["categorical_distributions"].items():
            total_responses = stats["total_responses"]
            distribution = []
            
            for value, count in stats["value_counts"].items():
                percentage = (count / total_responses) * 100 if total_responses > 0 else 0
                fraction = f"{count}/{total_responses}"
                
                citation_id = self._generate_citation_id(project_id, "csv", field, str(value))
                
                distribution.append({
                    "value": str(value),
                    "count": int(count),
                    "percentage": round(percentage, 2),
                    "fraction": fraction,
                    "citation_id": citation_id
                })
            
            # Sort by count
            distribution.sort(key=lambda x: x["count"], reverse=True)
            
            aggregated_stats["categorical_distributions"][field] = {
                "total_responses": total_responses,
                "unique_values": len(stats["value_counts"]),
                "distribution": distribution,
                "field_type": "categorical"
            }
        
        # Generate metadata
        aggregated_stats["metadata"] = {
            "filename": csv_file.filename,
            "total_rows": total_rows,
            "total_columns": len(aggregated_stats["field_types"]),
            "detected_types": aggregated_stats["field_types"],
            "persona_association": persona_id,
            "processing_timestamp": datetime.utcnow().isoformat(),
            "content_type": "csv",
            "chunks_processed": chunk_count,
            "processing_method": "streaming"
        }
        
        return aggregated_stats
    
    async def _extract_statistics_standard(
        self, 
        csv_file: UploadFile, 
        project_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Standard statistics extraction with caching support.
        
        Args:
            csv_file: Uploaded CSV file
            project_id: Project identifier for citation generation
            persona_id: Optional persona association
            
        Returns:
            Dictionary containing comprehensive statistics and metadata
            
        Raises:
            CSVParsingError: If CSV parsing or analysis fails
        """
        # Generate cache key based on file content and parameters
        cache_key = await self._generate_cache_key(csv_file, project_id, persona_id)
        
        # Try to get from cache first
        cache = get_statistics_cache()
        cached_result = await cache.get(cache_key)
        
        if cached_result is not None:
            self.logger.info(f"Retrieved CSV statistics from cache for {csv_file.filename}")
            return cached_result
        
        # Extract statistics normally
        result = await self._extract_statistics_uncached(csv_file, project_id, persona_id)
        
        # Cache the result
        await cache.set(cache_key, result, ttl_seconds=3600)  # Cache for 1 hour
        
        return result
    
    async def _generate_cache_key(
        self, 
        csv_file: UploadFile, 
        project_id: str, 
        persona_id: Optional[str]
    ) -> str:
        """Generate cache key for CSV statistics."""
        # Read file content for hashing
        content = await csv_file.read()
        await csv_file.seek(0)  # Reset position
        
        # Create hash of content + parameters
        content_hash = hashlib.md5(content).hexdigest()
        params_str = f"{project_id}:{persona_id or 'none'}"
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        
        return f"csv_stats:{content_hash}:{params_hash}"
    
    async def _extract_statistics_uncached(
        self, 
        csv_file: UploadFile, 
        project_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Standard statistics extraction for smaller CSV files.
        
        Args:
            csv_file: Uploaded CSV file
            project_id: Project identifier for citation generation
            persona_id: Optional persona association
            
        Returns:
            Dictionary containing comprehensive statistics and metadata
            
        Raises:
            CSVParsingError: If CSV parsing or analysis fails
        """
        try:
            # Read and validate CSV file
            df = await self._read_and_validate_csv(csv_file)
            
            # Detect field types dynamically
            field_types = self._detect_field_types(df)
            
            # Extract categorical distributions
            categorical_distributions = self._extract_categorical_distributions(
                df, field_types, project_id
            )
            
            # Extract numerical summaries
            numerical_summaries = self._extract_numerical_summaries(
                df, field_types, project_id
            )
            
            # Create chunk-to-row mapping
            chunk_mapping = self._create_chunk_mapping(df)
            
            # Generate metadata
            metadata = self._generate_metadata(csv_file, df, field_types, persona_id)
            
            # Compile final statistics
            statistics = {
                "metadata": metadata,
                "categorical_distributions": categorical_distributions,
                "numerical_summaries": numerical_summaries,
                "chunk_mapping": chunk_mapping,
                "field_types": field_types,
                "extraction_timestamp": datetime.utcnow().isoformat()
            }
            
            self.logger.info(
                f"Successfully extracted statistics from CSV {csv_file.filename}: "
                f"{len(categorical_distributions)} categorical fields, "
                f"{len(numerical_summaries)} numerical fields"
            )
            
            return statistics
            
        except CSVParsingError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error extracting CSV statistics: {e}")
            raise CSVParsingError(
                f"Failed to extract CSV statistics: {str(e)}",
                error_code="CSV_STATISTICS_EXTRACTION_ERROR"
            )
    
    async def _read_and_validate_csv(self, csv_file: UploadFile) -> pd.DataFrame:
        """
        Read and validate CSV file with multiple encoding attempts.
        
        Args:
            csv_file: Uploaded CSV file
            
        Returns:
            Validated pandas DataFrame
            
        Raises:
            CSVParsingError: If CSV cannot be read or validated
        """
        try:
            # Read file content
            content = await csv_file.read()
            await csv_file.seek(0)  # Reset for potential reuse
            
            if len(content) == 0:
                raise CSVParsingError(
                    "CSV file is empty",
                    error_code="CSV_EMPTY_FILE"
                )
            
            # Try different encodings
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
                        "CSV file contains no data",
                        error_code="CSV_NO_DATA"
                    )
                except pd.errors.ParserError as e:
                    parsing_errors.append(f"{encoding}: Parser error - {str(e)}")
                    continue
            
            if df is None:
                raise CSVParsingError(
                    f"Unable to parse CSV with any encoding. Errors: {'; '.join(parsing_errors)}",
                    error_code="CSV_ENCODING_ERROR"
                )
            
            # Validate DataFrame
            if df.empty:
                raise CSVParsingError(
                    "CSV file contains no data rows",
                    error_code="CSV_NO_DATA_ROWS"
                )
            
            if len(df.columns) == 0:
                raise CSVParsingError(
                    "CSV file contains no columns",
                    error_code="CSV_NO_COLUMNS"
                )
            
            # Clean column names
            df.columns = df.columns.astype(str).str.strip()
            
            # Handle duplicate column names
            if df.columns.duplicated().any():
                duplicate_cols = df.columns[df.columns.duplicated()].tolist()
                self.logger.warning(f"Found duplicate column names: {duplicate_cols}")
                df.columns = pd.io.common.dedup_names(df.columns, is_potential_multiindex=False)
            
            self.logger.info(f"Successfully read CSV: {len(df)} rows, {len(df.columns)} columns")
            return df
            
        except CSVParsingError:
            raise
        except Exception as e:
            raise CSVParsingError(
                f"Failed to read CSV file: {str(e)}",
                error_code="CSV_READ_ERROR"
            )
    
    def _detect_field_types(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Dynamically detect field types without predefined schemas.
        
        Args:
            df: Pandas DataFrame to analyze
            
        Returns:
            Dictionary mapping column names to detected types
        """
        field_types = {}
        
        for column in df.columns:
            series = df[column].dropna()  # Remove NaN values for analysis
            
            if len(series) == 0:
                field_types[column] = "empty"
                continue
            
            # Check if numeric
            if pd.api.types.is_numeric_dtype(series):
                if series.dtype in ['int64', 'int32', 'float64', 'float32']:
                    # Check if it's actually categorical (limited unique values)
                    unique_count = series.nunique()
                    if unique_count <= self.MAX_CATEGORICAL_UNIQUE_VALUES:
                        field_types[column] = "categorical_numeric"
                    else:
                        field_types[column] = "numerical"
                else:
                    field_types[column] = "numerical"
            else:
                # Try to convert to datetime
                try:
                    pd.to_datetime(series.head(100), errors='raise')
                    field_types[column] = "date"
                except (ValueError, TypeError):
                    # Check if categorical (limited unique values)
                    unique_count = series.nunique()
                    if unique_count <= self.MAX_CATEGORICAL_UNIQUE_VALUES:
                        field_types[column] = "categorical"
                    else:
                        field_types[column] = "text"
        
        self.logger.info(f"Detected field types: {field_types}")
        return field_types
    
    def _extract_categorical_distributions(
        self, 
        df: pd.DataFrame, 
        field_types: Dict[str, str], 
        project_id: str
    ) -> Dict[str, Any]:
        """
        Extract exact statistical distributions for categorical fields.
        
        Args:
            df: Pandas DataFrame
            field_types: Detected field types
            project_id: Project ID for citation generation
            
        Returns:
            Dictionary of categorical distributions with citations
        """
        categorical_distributions = {}
        
        categorical_fields = [
            col for col, field_type in field_types.items() 
            if field_type in ["categorical", "categorical_numeric"]
        ]
        
        for field in categorical_fields:
            try:
                series = df[field].dropna()
                
                if len(series) == 0:
                    continue
                
                # Calculate value counts
                value_counts = series.value_counts()
                total_responses = len(series)
                
                # Create distribution with exact percentages
                distribution = []
                for value, count in value_counts.items():
                    if count >= self.MIN_CATEGORICAL_FREQUENCY:
                        percentage = (count / total_responses) * 100
                        fraction = f"{count}/{total_responses}"
                        
                        # Generate citation ID
                        citation_id = self._generate_citation_id(
                            project_id, "csv", field, str(value)
                        )
                        
                        distribution.append({
                            "value": str(value),
                            "count": int(count),
                            "percentage": round(percentage, 2),
                            "fraction": fraction,
                            "citation_id": citation_id
                        })
                
                # Sort by count (descending)
                distribution.sort(key=lambda x: x["count"], reverse=True)
                
                categorical_distributions[field] = {
                    "total_responses": int(total_responses),
                    "unique_values": int(len(value_counts)),
                    "distribution": distribution,
                    "field_type": field_types[field]
                }
                
            except Exception as e:
                self.logger.warning(f"Failed to extract distribution for field {field}: {e}")
                continue
        
        return categorical_distributions
    
    def _extract_numerical_summaries(
        self, 
        df: pd.DataFrame, 
        field_types: Dict[str, str], 
        project_id: str
    ) -> Dict[str, Any]:
        """
        Extract numerical summaries for numerical fields.
        
        Args:
            df: Pandas DataFrame
            field_types: Detected field types
            project_id: Project ID for citation generation
            
        Returns:
            Dictionary of numerical summaries with citations
        """
        numerical_summaries = {}
        
        numerical_fields = [
            col for col, field_type in field_types.items() 
            if field_type == "numerical"
        ]
        
        for field in numerical_fields:
            try:
                series = df[field].dropna()
                
                if len(series) == 0:
                    continue
                
                # Calculate summary statistics
                summary = {
                    "count": int(len(series)),
                    "mean": float(series.mean()),
                    "median": float(series.median()),
                    "std": float(series.std()) if len(series) > 1 else 0.0,
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "q25": float(series.quantile(0.25)),
                    "q75": float(series.quantile(0.75))
                }
                
                # Generate citation ID
                citation_id = self._generate_citation_id(
                    project_id, "csv", field, "summary"
                )
                
                summary["citation_id"] = citation_id
                summary["field_type"] = field_types[field]
                
                numerical_summaries[field] = summary
                
            except Exception as e:
                self.logger.warning(f"Failed to extract summary for field {field}: {e}")
                continue
        
        return numerical_summaries
    
    def _create_chunk_mapping(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Create chunk-to-row mapping for accurate percentage calculations.
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            Dictionary mapping chunk IDs to row information
        """
        chunk_mapping = {}
        total_rows = len(df)
        
        # Create chunks of specified size
        for i in range(0, total_rows, self.CHUNK_SIZE):
            chunk_end = min(i + self.CHUNK_SIZE, total_rows)
            chunk_id = f"chunk_{i}_{chunk_end}"
            
            chunk_mapping[chunk_id] = {
                "row_numbers": list(range(i, chunk_end)),
                "respondent_count": int(chunk_end - i),
                "field_coverage": list(df.columns),
                "start_row": int(i),
                "end_row": int(chunk_end - 1)
            }
        
        return chunk_mapping
    
    def _generate_metadata(
        self, 
        csv_file: UploadFile, 
        df: pd.DataFrame, 
        field_types: Dict[str, str],
        persona_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive metadata for the CSV analysis.
        
        Args:
            csv_file: Original uploaded file
            df: Processed DataFrame
            field_types: Detected field types
            persona_id: Optional persona association
            
        Returns:
            Metadata dictionary
        """
        return {
            "filename": csv_file.filename,
            "total_rows": int(len(df)),
            "total_columns": int(len(df.columns)),
            "detected_types": field_types,
            "persona_association": persona_id,
            "null_values_count": int(df.isnull().sum().sum()),
            "processing_timestamp": datetime.utcnow().isoformat(),
            "content_type": "csv",
            "field_type_summary": {
                field_type: int(sum(1 for t in field_types.values() if t == field_type))
                for field_type in set(field_types.values())
            }
        }
    
    def _generate_citation_id(
        self, 
        project_id: str, 
        source_type: str, 
        field_name: str, 
        value_identifier: str
    ) -> str:
        """
        Generate unique citation ID with verification hash.
        
        Args:
            project_id: Project identifier
            source_type: Type of source (csv, pdf)
            field_name: Name of the field
            value_identifier: Identifier for the specific value
            
        Returns:
            Unique citation ID
        """
        # Create base string for hashing
        base_string = f"{project_id}:{source_type}:{field_name}:{value_identifier}:{datetime.utcnow().isoformat()}"
        
        # Generate hash
        hash_object = hashlib.md5(base_string.encode())
        hash_hex = hash_object.hexdigest()[:8]  # Use first 8 characters
        
        # Create citation ID
        citation_id = f"csv_{field_name}_{value_identifier}_{hash_hex}"
        
        return citation_id
    
    def verify_statistics(
        self, 
        statistics: Dict[str, Any], 
        original_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Verify extracted statistics against original data.
        
        Args:
            statistics: Extracted statistics
            original_df: Original DataFrame
            
        Returns:
            Verification results
        """
        verification_results = {
            "verified": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Verify row count
            expected_rows = len(original_df)
            actual_rows = statistics["metadata"]["total_rows"]
            
            if expected_rows != actual_rows:
                verification_results["verified"] = False
                verification_results["errors"].append(
                    f"Row count mismatch: expected {expected_rows}, got {actual_rows}"
                )
            
            # Verify categorical distributions
            for field, distribution in statistics["categorical_distributions"].items():
                if field in original_df.columns:
                    series = original_df[field].dropna()
                    expected_total = len(series)
                    actual_total = distribution["total_responses"]
                    
                    if expected_total != actual_total:
                        verification_results["warnings"].append(
                            f"Field {field}: response count mismatch: expected {expected_total}, got {actual_total}"
                        )
            
            # Verify numerical summaries
            for field, summary in statistics["numerical_summaries"].items():
                if field in original_df.columns:
                    series = original_df[field].dropna()
                    expected_count = len(series)
                    actual_count = summary["count"]
                    
                    if expected_count != actual_count:
                        verification_results["warnings"].append(
                            f"Field {field}: count mismatch: expected {expected_count}, got {actual_count}"
                        )
            
        except Exception as e:
            verification_results["verified"] = False
            verification_results["errors"].append(f"Verification failed: {str(e)}")
        
        return verification_results


# Service instance getter following VMP patterns
_dynamic_csv_extractor: Optional[DynamicCSVStatisticsExtractor] = None

def get_dynamic_csv_extractor() -> DynamicCSVStatisticsExtractor:
    """Get dynamic CSV extractor service singleton."""
    global _dynamic_csv_extractor
    if _dynamic_csv_extractor is None:
        _dynamic_csv_extractor = DynamicCSVStatisticsExtractor()
    return _dynamic_csv_extractor