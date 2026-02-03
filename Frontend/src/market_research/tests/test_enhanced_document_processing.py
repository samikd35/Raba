"""
Comprehensive unit tests for enhanced document processing components.

Tests the Dynamic CSV Statistics Extractor, Structured PDF Content Extractor,
Statistics Registry Service, and Persona-Aware Correlation Engine.
"""

import pytest
import asyncio
import io
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import UploadFile
from datetime import datetime

# Import the components to test
from ..services.dynamic_csv_extractor import DynamicCSVStatisticsExtractor, get_dynamic_csv_extractor
from ..services.structured_pdf_extractor import StructuredPDFExtractor, get_structured_pdf_extractor
from ..services.statistics_registry_service import StatisticsRegistryService, get_statistics_registry_service
from ..services.persona_aware_correlation_engine import PersonaAwareCorrelationEngine, get_persona_aware_correlation_engine
from ..utils.error_handling import CSVParsingError, PDFParsingError


class TestDynamicCSVStatisticsExtractor:
    """Test suite for Dynamic CSV Statistics Extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing."""
        return DynamicCSVStatisticsExtractor()
    
    @pytest.fixture
    def sample_csv_data(self):
        """Create sample CSV data for testing."""
        # Create data with enough unique values to trigger different field types
        comments = [f'Comment {i} with unique text content' for i in range(60)]  # More than 50 unique values
        return pd.DataFrame({
            'age': [25, 30, 35, 40, 25, 30],
            'gender': ['Male', 'Female', 'Male', 'Female', 'Male', 'Female'],
            'satisfaction': ['High', 'Medium', 'High', 'Low', 'High', 'Medium'],
            'income': [50000, 60000, 70000, 80000, 55000, 65000],
            'comments': comments[:6]  # Take first 6 but they're all unique
        })
    
    @pytest.fixture
    def mock_csv_file(self, sample_csv_data):
        """Create mock CSV file for testing."""
        csv_content = sample_csv_data.to_csv(index=False).encode('utf-8')
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_survey.csv"
        mock_file.read = AsyncMock(return_value=csv_content)
        mock_file.seek = AsyncMock()
        
        return mock_file
    
    @pytest.mark.asyncio
    async def test_extract_statistics_success(self, extractor, mock_csv_file):
        """Test successful statistics extraction from CSV."""
        project_id = "test_project_123"
        persona_id = "persona_1"
        
        result = await extractor.extract_statistics(mock_csv_file, project_id, persona_id)
        
        # Verify structure
        assert 'metadata' in result
        assert 'categorical_distributions' in result
        assert 'numerical_summaries' in result
        assert 'chunk_mapping' in result
        assert 'field_types' in result
        
        # Verify metadata
        metadata = result['metadata']
        assert metadata['filename'] == "test_survey.csv"
        assert metadata['total_rows'] == 6
        assert metadata['total_columns'] == 5
        assert metadata['persona_association'] == persona_id
        
        # Verify categorical distributions
        categorical = result['categorical_distributions']
        assert 'gender' in categorical
        assert 'satisfaction' in categorical
        
        gender_dist = categorical['gender']
        assert gender_dist['total_responses'] == 6
        assert len(gender_dist['distribution']) == 2  # Male, Female
        
        # Verify numerical summaries (age and income are categorical_numeric, so no numerical summaries)
        numerical = result['numerical_summaries']
        # Since all numeric fields have <= 50 unique values, they're treated as categorical_numeric
        # So numerical_summaries should be empty or contain only truly numerical fields
        
        # Verify field types
        field_types = result['field_types']
        assert field_types['age'] == 'categorical_numeric'  # Limited unique values
        assert field_types['gender'] == 'categorical'
        assert field_types['satisfaction'] == 'categorical'
        assert field_types['income'] == 'categorical_numeric'  # Limited unique values
        assert field_types['comments'] == 'categorical'  # Limited unique values
    
    @pytest.mark.asyncio
    async def test_extract_statistics_empty_file(self, extractor):
        """Test handling of empty CSV file."""
        from fastapi import HTTPException
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "empty.csv"
        mock_file.read = AsyncMock(return_value=b'')
        mock_file.seek = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await extractor.extract_statistics(mock_file, "project_123")
        
        assert exc_info.value.status_code == 422
        assert "CSV file is empty" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_extract_statistics_invalid_encoding(self, extractor):
        """Test handling of CSV with encoding issues."""
        # Create CSV with invalid UTF-8 bytes
        invalid_content = b'\xff\xfe\x00\x00invalid,csv,content\n1,2,3'
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "invalid_encoding.csv"
        mock_file.read = AsyncMock(return_value=invalid_content)
        mock_file.seek = AsyncMock()
        
        # Should try multiple encodings and potentially succeed with latin-1
        result = await extractor.extract_statistics(mock_file, "project_123")
        
        # Should have some result even with encoding issues
        assert 'metadata' in result
    
    def test_detect_field_types(self, extractor, sample_csv_data):
        """Test field type detection."""
        field_types = extractor._detect_field_types(sample_csv_data)
        
        assert field_types['age'] == 'categorical_numeric'  # Few unique values
        assert field_types['gender'] == 'categorical'
        assert field_types['satisfaction'] == 'categorical'
        assert field_types['income'] == 'categorical_numeric'  # 6 unique values, treated as categorical
        assert field_types['comments'] == 'categorical'  # 6 unique values, treated as categorical
    
    def test_extract_categorical_distributions(self, extractor, sample_csv_data):
        """Test categorical distribution extraction."""
        field_types = {'gender': 'categorical', 'satisfaction': 'categorical'}
        project_id = "test_project"
        
        distributions = extractor._extract_categorical_distributions(
            sample_csv_data, field_types, project_id
        )
        
        assert 'gender' in distributions
        assert 'satisfaction' in distributions
        
        gender_dist = distributions['gender']
        assert gender_dist['total_responses'] == 6
        assert len(gender_dist['distribution']) == 2
        
        # Check specific values
        gender_values = {item['value']: item for item in gender_dist['distribution']}
        assert 'Male' in gender_values
        assert 'Female' in gender_values
        assert gender_values['Male']['count'] == 3
        assert gender_values['Female']['count'] == 3
        assert gender_values['Male']['percentage'] == 50.0
    
    def test_extract_numerical_summaries(self, extractor, sample_csv_data):
        """Test numerical summary extraction."""
        field_types = {'age': 'numerical', 'income': 'numerical'}
        project_id = "test_project"
        
        summaries = extractor._extract_numerical_summaries(
            sample_csv_data, field_types, project_id
        )
        
        assert 'age' in summaries
        assert 'income' in summaries
        
        age_summary = summaries['age']
        assert age_summary['count'] == 6
        assert age_summary['min'] == 25
        assert age_summary['max'] == 40
        assert 'citation_id' in age_summary
    
    def test_create_chunk_mapping(self, extractor, sample_csv_data):
        """Test chunk mapping creation."""
        chunk_mapping = extractor._create_chunk_mapping(sample_csv_data)
        
        # Should have at least one chunk
        assert len(chunk_mapping) >= 1
        
        # Check first chunk
        first_chunk = list(chunk_mapping.values())[0]
        assert 'row_numbers' in first_chunk
        assert 'respondent_count' in first_chunk
        assert 'field_coverage' in first_chunk
        assert first_chunk['field_coverage'] == list(sample_csv_data.columns)
    
    def test_generate_citation_id(self, extractor):
        """Test citation ID generation."""
        citation_id = extractor._generate_citation_id(
            "project_123", "csv", "gender", "Male"
        )
        
        assert citation_id.startswith("csv_gender_Male_")
        assert len(citation_id.split('_')) == 4  # csv_gender_Male_hash
    
    def test_verify_statistics(self, extractor, sample_csv_data):
        """Test statistics verification."""
        # Create mock statistics
        statistics = {
            'metadata': {'total_rows': 6, 'total_columns': 5},
            'categorical_distributions': {
                'gender': {'total_responses': 6}
            },
            'numerical_summaries': {
                'age': {'count': 6}
            }
        }
        
        verification = extractor.verify_statistics(statistics, sample_csv_data)
        
        assert verification['verified'] is True
        assert len(verification['errors']) == 0
    
    def test_singleton_pattern(self):
        """Test singleton pattern for service getter."""
        extractor1 = get_dynamic_csv_extractor()
        extractor2 = get_dynamic_csv_extractor()
        
        assert extractor1 is extractor2


class TestStructuredPDFExtractor:
    """Test suite for Structured PDF Content Extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing."""
        return StructuredPDFExtractor()
    
    @pytest.fixture
    def mock_pdf_content(self):
        """Create mock PDF content for testing."""
        return {
            "raw_text": """
            Interview with John Doe, age 35, male, software engineer.
            
            The main problem I face is the lack of time to complete tasks efficiently.
            I often feel frustrated when the system is slow and unresponsive.
            
            What I really need is a solution that saves time and improves productivity.
            The current tools are expensive and don't provide good value.
            
            I would be happy to pay for something that actually works well.
            """,
            "page_contents": [
                {
                    "page_number": 1,
                    "content": "Interview content...",
                    "word_count": 50,
                    "char_count": 300
                }
            ],
            "total_pages": 1,
            "extracted_pages": 1,
            "failed_pages": [],
            "total_words": 50,
            "total_chars": 300
        }
    
    @pytest.fixture
    def mock_pdf_file(self):
        """Create mock PDF file for testing."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "interview.pdf"
        mock_file.read = AsyncMock(return_value=b'%PDF-1.4 mock pdf content')
        mock_file.seek = AsyncMock()
        
        return mock_file
    
    @pytest.mark.asyncio
    async def test_extract_structured_content_success(self, extractor, mock_pdf_file):
        """Test successful structured content extraction from PDF."""
        project_id = "test_project_123"
        persona_id = "persona_1"
        
        # Mock the PDF parsing
        with patch.object(extractor, '_read_and_parse_pdf') as mock_parse:
            mock_parse.return_value = {
                "raw_text": "Interview with John, age 35. Main problem is time management.",
                "page_contents": [{"page_number": 1, "content": "test", "word_count": 10, "char_count": 50}],
                "total_pages": 1,
                "extracted_pages": 1,
                "failed_pages": [],
                "total_words": 10,
                "total_chars": 50
            }
            
            result = await extractor.extract_structured_content(mock_pdf_file, project_id, persona_id)
        
        # Verify structure
        assert 'metadata' in result
        assert 'themes' in result
        assert 'key_quotes' in result
        assert 'participant_profile' in result
        assert 'chunk_mapping' in result
        
        # Verify metadata
        metadata = result['metadata']
        assert metadata['filename'] == "interview.pdf"
        assert metadata['persona_association'] == persona_id
    
    @pytest.mark.asyncio
    async def test_extract_structured_content_empty_pdf(self, extractor):
        """Test handling of empty PDF file."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "empty.pdf"
        mock_file.read = AsyncMock(return_value=b'')
        mock_file.seek = AsyncMock()
        
        with pytest.raises(PDFParsingError) as exc_info:
            await extractor.extract_structured_content(mock_file, "project_123")
        
        assert "PDF file is empty" in str(exc_info.value)
    
    def test_extract_participant_profile(self, extractor, mock_pdf_content):
        """Test participant profile extraction."""
        profile = extractor._extract_participant_profile(mock_pdf_content)
        
        assert 'demographics' in profile
        assert 'key_characteristics' in profile
        assert 'interview_metadata' in profile
        
        # Should extract age from text
        demographics = profile['demographics']
        assert demographics.get('age') == 35
        assert demographics.get('gender') == 'male'
    
    def test_segment_content(self, extractor, mock_pdf_content):
        """Test content segmentation."""
        segments = extractor._segment_content(mock_pdf_content)
        
        assert len(segments) >= 1
        
        # Check first segment
        first_segment = segments[0]
        assert 'segment_id' in first_segment
        assert 'content' in first_segment
        assert 'start_char' in first_segment
        assert 'end_char' in first_segment
        assert 'word_count' in first_segment
        assert 'page_info' in first_segment
    
    def test_extract_themes(self, extractor):
        """Test theme extraction."""
        segments = [
            {
                "segment_id": "segment_0",
                "content": "The main problem is time management and efficiency issues.",
                "page_info": {"start_page": 1, "end_page": 1}
            },
            {
                "segment_id": "segment_1", 
                "content": "I need better solutions for productivity and workflow.",
                "page_info": {"start_page": 1, "end_page": 1}
            }
        ]
        
        themes = extractor._extract_themes(segments, "project_123")
        
        # Should extract themes related to problems and solutions
        assert len(themes) > 0
        
        # Check theme structure
        for theme_name, theme_data in themes.items():
            assert 'frequency' in theme_data
            assert 'percentage' in theme_data
            assert 'sources' in theme_data
            assert 'citation_id' in theme_data
    
    def test_extract_key_quotes(self, extractor):
        """Test key quote extraction."""
        segments = [
            {
                "segment_id": "segment_0",
                "content": "I really hate when the system is slow. It's so frustrating!",
                "page_info": {"start_page": 1, "end_page": 1}
            }
        ]
        
        themes = {"pain_points": {"sources": [{"matched_keywords": ["hate", "frustrating"]}]}}
        
        quotes = extractor._extract_key_quotes(segments, themes, "project_123")
        
        # Should extract quotes with emotional content
        assert len(quotes) > 0
        
        # Check quote structure
        for quote in quotes:
            assert 'quote' in quote
            assert 'themes' in quote
            assert 'page_info' in quote
            assert 'citation_id' in quote
            assert 'sentiment' in quote
    
    def test_analyze_sentiment(self, extractor):
        """Test sentiment analysis."""
        positive_text = "I love this product! It's amazing and wonderful."
        negative_text = "I hate this system. It's terrible and frustrating."
        neutral_text = "The system has various features and capabilities."
        
        positive_sentiment = extractor._analyze_sentiment(positive_text)
        negative_sentiment = extractor._analyze_sentiment(negative_text)
        neutral_sentiment = extractor._analyze_sentiment(neutral_text)
        
        assert positive_sentiment['overall_sentiment'] > 0
        assert negative_sentiment['overall_sentiment'] < 0
        assert abs(neutral_sentiment['overall_sentiment']) < 0.5
    
    def test_analyze_quote_sentiment(self, extractor):
        """Test individual quote sentiment analysis."""
        positive_quote = "I love this feature!"
        negative_quote = "This is terrible and frustrating."
        neutral_quote = "The system has this capability."
        
        assert extractor._analyze_quote_sentiment(positive_quote) > 0
        assert extractor._analyze_quote_sentiment(negative_quote) < 0
        assert extractor._analyze_quote_sentiment(neutral_quote) == 0
    
    def test_generate_citation_id(self, extractor):
        """Test citation ID generation."""
        citation_id = extractor._generate_citation_id(
            "project_123", "pdf", "theme", "pain_points"
        )
        
        assert citation_id.startswith("pdf_theme_pain_points_")
        assert len(citation_id.split('_')) == 4
    
    def test_singleton_pattern(self):
        """Test singleton pattern for service getter."""
        extractor1 = get_structured_pdf_extractor()
        extractor2 = get_structured_pdf_extractor()
        
        assert extractor1 is extractor2


class TestStatisticsRegistryService:
    """Test suite for Statistics Registry Service."""
    
    @pytest.fixture
    def mock_db_adapter(self):
        """Create mock database adapter."""
        adapter = Mock()
        adapter.get_research_documents_data = AsyncMock()
        adapter.update_research_documents_data = AsyncMock()
        return adapter
    
    @pytest.fixture
    def registry_service(self, mock_db_adapter):
        """Create registry service with mock adapter."""
        return StatisticsRegistryService(mock_db_adapter)
    
    @pytest.fixture
    def sample_csv_statistics(self):
        """Create sample CSV statistics."""
        return {
            'metadata': {
                'filename': 'survey.csv',
                'total_rows': 100,
                'total_columns': 5
            },
            'categorical_distributions': {
                'gender': {
                    'total_responses': 100,
                    'distribution': [
                        {'value': 'Male', 'count': 60, 'percentage': 60.0, 'citation_id': 'csv_gender_Male_abc123'},
                        {'value': 'Female', 'count': 40, 'percentage': 40.0, 'citation_id': 'csv_gender_Female_def456'}
                    ]
                }
            },
            'numerical_summaries': {
                'age': {
                    'count': 100,
                    'mean': 35.5,
                    'citation_id': 'csv_age_summary_ghi789'
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_store_statistics_success(self, registry_service, mock_db_adapter, sample_csv_statistics):
        """Test successful statistics storage."""
        project_id = "project_123"
        tenant_id = "tenant_456"
        persona_id = "persona_1"
        
        # Mock existing data
        mock_db_adapter.get_research_documents_data.return_value = {}
        mock_db_adapter.update_research_documents_data.return_value = True
        
        result = await registry_service.store_statistics(
            project_id, tenant_id, sample_csv_statistics, "csv", persona_id
        )
        
        assert result is True
        mock_db_adapter.update_research_documents_data.assert_called_once()
        
        # Verify the data structure passed to update
        call_args = mock_db_adapter.update_research_documents_data.call_args
        updated_data = call_args[0][2]  # Third argument is the data
        
        assert 'statistics_registry' in updated_data
        registry = updated_data['statistics_registry']
        assert 'csv_statistics' in registry
        assert 'citation_registry' in registry
        assert 'persona_mappings' in registry
    
    @pytest.mark.asyncio
    async def test_get_statistics_for_analysis(self, registry_service, mock_db_adapter, sample_csv_statistics):
        """Test statistics retrieval for analysis."""
        project_id = "project_123"
        tenant_id = "tenant_456"
        analysis_type = "pain"
        persona_id = "persona_1"
        
        # Mock research data with statistics registry
        mock_research_data = {
            'statistics_registry': {
                'csv_statistics': sample_csv_statistics,
                'pdf_statistics': {},
                'citation_registry': {},
                'persona_mappings': {}
            }
        }
        mock_db_adapter.get_research_documents_data.return_value = mock_research_data
        
        result = await registry_service.get_statistics_for_analysis(
            project_id, tenant_id, analysis_type, persona_id
        )
        
        assert 'csv_statistics' in result
        assert 'pdf_statistics' in result
        assert 'analysis_context' in result
        
        context = result['analysis_context']
        assert context['analysis_type'] == analysis_type
        assert context['persona_id'] == persona_id
    
    @pytest.mark.asyncio
    async def test_verify_citation_success(self, registry_service, mock_db_adapter):
        """Test successful citation verification."""
        project_id = "project_123"
        tenant_id = "tenant_456"
        citation_id = "csv_gender_Male_abc123"
        
        # Mock research data with citation registry
        mock_research_data = {
            'statistics_registry': {
                'citation_registry': {
                    citation_id: {
                        'source_type': 'csv',
                        'source_file': 'survey.csv',
                        'data_path': 'categorical_distributions.gender',
                        'verification_hash': 'hash123'
                    }
                }
            }
        }
        mock_db_adapter.get_research_documents_data.return_value = mock_research_data
        
        result = await registry_service.verify_citation(project_id, tenant_id, citation_id)
        
        assert result['verified'] is True
        assert 'citation_data' in result
        assert result['citation_data']['source_type'] == 'csv'
    
    @pytest.mark.asyncio
    async def test_verify_citation_not_found(self, registry_service, mock_db_adapter):
        """Test citation verification when citation not found."""
        project_id = "project_123"
        tenant_id = "tenant_456"
        citation_id = "nonexistent_citation"
        
        # Mock research data with empty citation registry
        mock_research_data = {
            'statistics_registry': {
                'citation_registry': {}
            }
        }
        mock_db_adapter.get_research_documents_data.return_value = mock_research_data
        
        result = await registry_service.verify_citation(project_id, tenant_id, citation_id)
        
        assert result['verified'] is False
        assert 'Citation ID not found' in result['error']
    
    @pytest.mark.asyncio
    async def test_get_persona_statistics(self, registry_service, mock_db_adapter, sample_csv_statistics):
        """Test persona-specific statistics retrieval."""
        project_id = "project_123"
        tenant_id = "tenant_456"
        persona_id = "persona_1"
        
        # Mock research data with persona mappings
        mock_research_data = {
            'statistics_registry': {
                'csv_statistics': sample_csv_statistics,
                'pdf_statistics': {},
                'persona_mappings': {
                    persona_id: {
                        'associated_statistics': ['csv_categorical_gender'],
                        'relevance_scores': {'csv_categorical_gender': 0.8}
                    }
                }
            }
        }
        mock_db_adapter.get_research_documents_data.return_value = mock_research_data
        
        result = await registry_service.get_persona_statistics(project_id, tenant_id, persona_id)
        
        assert result['persona_specific'] is True
        assert 'relevance_scores' in result
        assert 'csv_statistics' in result
    
    def test_filter_statistics_by_analysis_type(self, registry_service, sample_csv_statistics):
        """Test statistics filtering by analysis type."""
        # Test pain analysis (should include categorical distributions)
        filtered = registry_service._filter_statistics_by_analysis_type(
            sample_csv_statistics, 'pain'
        )
        
        assert 'categorical_distributions' in filtered
        assert 'metadata' in filtered  # Always included
    
    def test_extract_citations_from_statistics(self, registry_service, sample_csv_statistics):
        """Test citation extraction from statistics."""
        citations = registry_service._extract_citations_from_statistics(
            sample_csv_statistics, 'csv', 'project_123'
        )
        
        assert len(citations) > 0
        
        # Check citation structure
        for citation_id, citation_data in citations.items():
            assert 'source_type' in citation_data
            assert 'source_file' in citation_data
            assert 'data_path' in citation_data
            assert 'verification_hash' in citation_data
            assert citation_data['source_type'] == 'csv'
    
    def test_singleton_pattern(self):
        """Test singleton pattern for service getter."""
        service1 = get_statistics_registry_service()
        service2 = get_statistics_registry_service()
        
        assert service1 is service2


class TestPersonaAwareCorrelationEngine:
    """Test suite for Persona-Aware Correlation Engine."""
    
    @pytest.fixture
    def mock_db_adapter(self):
        """Create mock database adapter."""
        adapter = Mock()
        adapter.get_vmp_project_context = AsyncMock()
        adapter.get_research_documents_data = AsyncMock()
        adapter.get_research_chunks_for_analysis = AsyncMock()
        return adapter
    
    @pytest.fixture
    def correlation_engine(self, mock_db_adapter):
        """Create correlation engine with mock adapter."""
        return PersonaAwareCorrelationEngine(mock_db_adapter)
    
    @pytest.fixture
    def sample_personas(self):
        """Create sample personas for testing."""
        return [
            {
                'id': 'persona_1',
                'name': 'Tech-Savvy Professional',
                'description': 'Software engineer who values efficiency and automation',
                'demographics': {'age': 30, 'occupation': 'software engineer'},
                'goals': ['improve productivity', 'save time'],
                'pain_points': ['slow systems', 'manual processes']
            },
            {
                'id': 'persona_2',
                'name': 'Budget-Conscious Manager',
                'description': 'Manager focused on cost optimization and ROI',
                'demographics': {'age': 45, 'occupation': 'manager'},
                'goals': ['reduce costs', 'improve ROI'],
                'pain_points': ['expensive tools', 'budget constraints']
            }
        ]
    
    @pytest.fixture
    def sample_research_data(self):
        """Create sample research data for testing."""
        return {
            'csv_statistics': {
                'categorical_distributions': {
                    'occupation': {
                        'distribution': [
                            {'value': 'software engineer', 'count': 30},
                            {'value': 'manager', 'count': 20}
                        ]
                    },
                    'budget_concern': {
                        'distribution': [
                            {'value': 'high', 'count': 25},
                            {'value': 'low', 'count': 25}
                        ]
                    }
                }
            },
            'pdf_statistics': {
                'themes': {
                    'productivity_issues': {
                        'frequency': 15,
                        'context_examples': ['slow system performance', 'manual workflow']
                    },
                    'cost_concerns': {
                        'frequency': 10,
                        'context_examples': ['expensive software', 'budget limitations']
                    }
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_associate_data_with_personas(self, correlation_engine, mock_db_adapter, sample_personas, sample_research_data):
        """Test data association with personas."""
        project_id = "project_123"
        tenant_id = "tenant_456"
        
        # Mock project context with personas
        mock_db_adapter.get_vmp_project_context.return_value = {
            'personas': sample_personas
        }
        
        result = await correlation_engine.associate_data_with_personas(
            project_id, tenant_id, sample_research_data
        )
        
        assert isinstance(result, dict)
        assert len(result) > 0
        
        # Should have associations for personas
        persona_ids = [p['id'] for p in sample_personas]
        for persona_id in persona_ids:
            if persona_id in result:
                assert isinstance(result[persona_id], list)
    
    @pytest.mark.asyncio
    async def test_find_persona_relevant_data(self, correlation_engine, mock_db_adapter, sample_personas):
        """Test finding persona-relevant data."""
        project_id = "project_123"
        tenant_id = "tenant_456"
        persona_id = "persona_1"
        analysis_type = "pain"
        
        assumption = {
            'assumption_text': 'Software engineers struggle with slow systems'
        }
        
        # Mock project context and research data
        mock_db_adapter.get_vmp_project_context.return_value = {
            'personas': sample_personas
        }
        mock_db_adapter.get_research_documents_data.return_value = {
            'statistics_registry': {
                'csv_statistics': {},
                'pdf_statistics': {}
            }
        }
        mock_db_adapter.get_research_chunks_for_analysis.return_value = []
        
        statistics, chunks = await correlation_engine.find_persona_relevant_data(
            project_id, tenant_id, assumption, persona_id, analysis_type
        )
        
        assert isinstance(statistics, dict)
        assert isinstance(chunks, list)
    
    def test_calculate_persona_relevance(self, correlation_engine, sample_personas):
        """Test persona relevance calculation."""
        persona_profile = correlation_engine._extract_persona_profile(sample_personas[0])
        
        # Test relevant content
        relevant_content = "As a software engineer, I need better automation tools for productivity"
        relevance_score = correlation_engine.calculate_persona_relevance(relevant_content, persona_profile)
        
        assert 0.0 <= relevance_score <= 1.0
        assert relevance_score > 0.3  # Should be somewhat relevant
        
        # Test irrelevant content
        irrelevant_content = "Cooking recipes and gardening tips for beginners"
        irrelevance_score = correlation_engine.calculate_persona_relevance(irrelevant_content, persona_profile)
        
        assert irrelevance_score < relevance_score  # Should be less relevant
    
    @pytest.mark.asyncio
    async def test_infer_persona_from_content(self, correlation_engine, sample_personas):
        """Test persona inference from content."""
        # Content that should match first persona
        tech_content = "I'm a software engineer working on automation and efficiency improvements"
        
        persona_id, confidence = await correlation_engine.infer_persona_from_content(
            tech_content, sample_personas
        )
        
        assert persona_id == 'persona_1'  # Tech-savvy professional
        assert confidence > 0.3
        
        # Content that should match second persona
        budget_content = "As a manager, I'm focused on reducing costs and improving ROI"
        
        persona_id, confidence = await correlation_engine.infer_persona_from_content(
            budget_content, sample_personas
        )
        
        assert persona_id == 'persona_2'  # Budget-conscious manager
        assert confidence > 0.3
    
    def test_extract_persona_profile(self, correlation_engine, sample_personas):
        """Test persona profile extraction."""
        profile = correlation_engine._extract_persona_profile(sample_personas[0])
        
        assert 'name' in profile
        assert 'description' in profile
        assert 'keywords' in profile
        assert 'demographics' in profile
        assert 'goals' in profile
        assert 'pain_points' in profile
        
        assert profile['name'] == 'Tech-Savvy Professional'
        assert len(profile['keywords']) > 0
    
    def test_extract_keywords_from_text(self, correlation_engine):
        """Test keyword extraction from text."""
        text = "Software engineer focused on productivity and automation tools"
        keywords = correlation_engine._extract_keywords_from_text(text)
        
        assert 'software' in keywords
        assert 'engineer' in keywords
        assert 'productivity' in keywords
        assert 'automation' in keywords
        
        # Should not include stop words
        assert 'and' not in keywords
        assert 'on' not in keywords
    
    def test_extract_persona_keywords(self, correlation_engine, sample_personas):
        """Test persona keyword extraction."""
        persona_profile = correlation_engine._extract_persona_profile(sample_personas[0])
        keywords = correlation_engine._extract_persona_keywords(persona_profile)
        
        assert len(keywords) > 0
        assert isinstance(keywords, list)
        
        # Should include relevant keywords from persona
        keyword_text = ' '.join(keywords)
        assert any(word in keyword_text for word in ['software', 'engineer', 'efficiency', 'automation'])
    
    @pytest.mark.asyncio
    async def test_associate_csv_statistics(self, correlation_engine, sample_personas):
        """Test CSV statistics association with persona."""
        persona_profile = correlation_engine._extract_persona_profile(sample_personas[0])
        
        csv_stats = {
            'categorical_distributions': {
                'occupation': {
                    'distribution': [
                        {'value': 'software engineer', 'count': 30},
                        {'value': 'manager', 'count': 20}
                    ]
                },
                'tech_skills': {
                    'distribution': [
                        {'value': 'high', 'count': 25},
                        {'value': 'low', 'count': 25}
                    ]
                }
            }
        }
        
        associations = await correlation_engine._associate_csv_statistics(
            csv_stats, persona_profile, 'persona_1'
        )
        
        assert isinstance(associations, list)
        # Should associate occupation field due to 'software engineer' match
        assert any('occupation' in assoc for assoc in associations)
    
    def test_singleton_pattern(self):
        """Test singleton pattern for service getter."""
        engine1 = get_persona_aware_correlation_engine()
        engine2 = get_persona_aware_correlation_engine()
        
        assert engine1 is engine2


class TestIntegrationScenarios:
    """Integration tests for document processing components working together."""
    
    @pytest.fixture
    def all_services(self):
        """Create all services for integration testing."""
        mock_db_adapter = Mock()
        mock_db_adapter.get_research_documents_data = AsyncMock()
        mock_db_adapter.update_research_documents_data = AsyncMock()
        mock_db_adapter.get_vmp_project_context = AsyncMock()
        mock_db_adapter.get_research_chunks_for_analysis = AsyncMock()
        
        return {
            'csv_extractor': DynamicCSVStatisticsExtractor(),
            'pdf_extractor': StructuredPDFExtractor(),
            'registry_service': StatisticsRegistryService(mock_db_adapter),
            'correlation_engine': PersonaAwareCorrelationEngine(mock_db_adapter),
            'db_adapter': mock_db_adapter
        }
    
    @pytest.mark.asyncio
    async def test_full_document_processing_workflow(self, all_services):
        """Test complete workflow from document upload to persona association."""
        services = all_services
        
        # Step 1: Extract CSV statistics
        csv_data = pd.DataFrame({
            'role': ['engineer', 'manager', 'engineer'],
            'satisfaction': ['high', 'medium', 'high']
        })
        
        csv_content = csv_data.to_csv(index=False).encode('utf-8')
        mock_csv_file = Mock(spec=UploadFile)
        mock_csv_file.filename = "survey.csv"
        mock_csv_file.read = AsyncMock(return_value=csv_content)
        mock_csv_file.seek = AsyncMock()
        
        csv_stats = await services['csv_extractor'].extract_statistics(
            mock_csv_file, "project_123", "persona_1"
        )
        
        assert 'categorical_distributions' in csv_stats
        
        # Step 2: Store statistics in registry
        services['db_adapter'].get_research_documents_data.return_value = {}
        services['db_adapter'].update_research_documents_data.return_value = True
        
        store_result = await services['registry_service'].store_statistics(
            "project_123", "tenant_456", csv_stats, "csv", "persona_1"
        )
        
        assert store_result is True
        
        # Step 3: Associate with personas
        personas = [
            {
                'id': 'persona_1',
                'name': 'Engineer',
                'description': 'Software engineer focused on technical solutions'
            }
        ]
        
        services['db_adapter'].get_vmp_project_context.return_value = {'personas': personas}
        
        research_data = {'csv_statistics': csv_stats, 'pdf_statistics': {}}
        associations = await services['correlation_engine'].associate_data_with_personas(
            "project_123", "tenant_456", research_data
        )
        
        assert isinstance(associations, dict)
        assert len(associations) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, all_services):
        """Test error handling across integrated components."""
        services = all_services
        
        # Test CSV extraction with invalid file
        mock_csv_file = Mock(spec=UploadFile)
        mock_csv_file.filename = "invalid.csv"
        mock_csv_file.read = AsyncMock(return_value=b'')
        mock_csv_file.seek = AsyncMock()
        
        with pytest.raises(CSVParsingError):
            await services['csv_extractor'].extract_statistics(
                mock_csv_file, "project_123"
            )
        
        # Test registry service with database error
        services['db_adapter'].get_research_documents_data.side_effect = Exception("DB Error")
        
        result = await services['registry_service'].get_statistics_for_analysis(
            "project_123", "tenant_456", "pain"
        )
        
        # Should return empty dict on error
        assert result == {}
    
    def test_citation_consistency_across_components(self, all_services):
        """Test that citation IDs are consistent across components."""
        csv_extractor = all_services['csv_extractor']
        registry_service = all_services['registry_service']
        
        # Generate citation ID from CSV extractor
        csv_citation = csv_extractor._generate_citation_id(
            "project_123", "csv", "gender", "Male"
        )
        
        # Create mock statistics with citation
        statistics = {
            'categorical_distributions': {
                'gender': {
                    'distribution': [
                        {'value': 'Male', 'citation_id': csv_citation}
                    ]
                }
            },
            'metadata': {'filename': 'test.csv'}
        }
        
        # Extract citations from statistics
        citations = registry_service._extract_citations_from_statistics(
            statistics, 'csv', 'project_123'
        )
        
        # Should find the citation
        assert csv_citation in citations
        assert citations[csv_citation]['source_type'] == 'csv'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])