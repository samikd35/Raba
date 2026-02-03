# Enhanced Market Research Agent - API Documentation

## Overview

This document describes the enhanced API endpoints and parameters for the Market Research Agent system. The enhanced system maintains full backward compatibility while adding powerful new capabilities for accurate statistical reporting, persona-aware analysis, and comprehensive fact validation.

## Base URL
```
https://api.yuba.com/v1/market-research
```

## Authentication
All API requests require authentication using Bearer tokens:
```http
Authorization: Bearer <your_api_token>
```

## Enhanced Endpoints

### 1. Upload Research Documents

Upload CSV survey data or PDF interview transcripts with enhanced processing capabilities.

#### Endpoint
```http
POST /projects/{project_id}/research-documents
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Unique project identifier |
| `file` | file | Yes | Research document (CSV or PDF, max 50MB) |
| `persona_id` | string | No | Associate document with specific persona |
| `enable_enhanced_processing` | boolean | No | Use enhanced processing pipeline (default: true) |
| `extract_statistics` | boolean | No | Pre-compute statistics registry (default: true) |
| `enable_fact_validation` | boolean | No | Enable fact validation for this document (default: true) |

#### Request Example
```http
POST /projects/proj_123/research-documents
Content-Type: multipart/form-data
Authorization: Bearer your_token_here

--boundary
Content-Disposition: form-data; name="file"; filename="survey_responses.csv"
Content-Type: text/csv

[CSV file content]
--boundary
Content-Disposition: form-data; name="persona_id"

startup_founder
--boundary
Content-Disposition: form-data; name="enable_enhanced_processing"

true
--boundary--
```

#### Response
```json
{
  "document_id": "doc_456",
  "filename": "survey_responses.csv",
  "file_type": "csv",
  "processing_status": "completed",
  "enhanced_processing": {
    "statistics_extracted": true,
    "persona_associated": true,
    "fact_validation_enabled": true
  },
  "statistics_summary": {
    "total_rows": 1000,
    "categorical_fields": 8,
    "numerical_fields": 3,
    "unique_statistics": 45
  },
  "persona_associations": [
    {
      "persona_id": "startup_founder",
      "relevance_score": 0.92,
      "association_type": "explicit"
    }
  ],
  "citation_registry": {
    "total_citations": 45,
    "citation_prefix": "csv_456"
  },
  "upload_timestamp": "2024-01-15T10:30:00Z"
}
```

### 2. Analyze Assumptions (Enhanced)

Run enhanced analysis with persona-aware routing, fact validation, and automatic visualizations.

#### Endpoint
```http
POST /projects/{project_id}/analyze-assumptions
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Unique project identifier |
| `assumptions` | array | Yes | List of assumptions to analyze |
| `enable_fact_validation` | boolean | No | Validate AI claims against data (default: true) |
| `persona_aware_routing` | boolean | No | Use persona-specific analysis (default: true) |
| `include_visualizations` | boolean | No | Generate charts and tables (default: true) |
| `citation_level` | string | No | Citation detail level: "basic", "detailed", "comprehensive" |
| `confidence_threshold` | number | No | Minimum confidence score (0.0-1.0, default: 0.7) |

#### Request Example
```json
{
  "assumptions": [
    {
      "id": "assumption_1",
      "text": "Startup founders struggle with cost management and need affordable solutions",
      "persona_id": "startup_founder",
      "analysis_types": ["pain", "size", "solutions", "gains"]
    }
  ],
  "enable_fact_validation": true,
  "persona_aware_routing": true,
  "include_visualizations": true,
  "citation_level": "detailed",
  "confidence_threshold": 0.8
}
```

#### Response
```json
{
  "analysis_session_id": "session_789",
  "project_id": "proj_123",
  "analysis_results": [
    {
      "assumption_id": "assumption_1",
      "assumption_text": "Startup founders struggle with cost management...",
      "persona_name": "Startup Founder",
      "validation_status": "validated",
      "analyses": {
        "pain_points": {
          "claim": "Based on survey data, 72% of startup founders cite cost management as their primary challenge",
          "accuracy_level": "high",
          "confidence_score": 0.92,
          "fact_validation_score": 1.0,
          "persona_relevance_score": 0.95,
          "supporting_evidence": [
            "Survey responses show cost concerns across 720 of 1000 startup respondents",
            "Interview quotes: 'Budget constraints are our biggest obstacle' - Participant #045"
          ],
          "citation_ids": [
            "csv_456_cost_management_stat",
            "pdf_789_budget_quote_p12"
          ],
          "statistical_data": {
            "source_statistics": {
              "total_respondents": 1000,
              "startup_subset": 350,
              "cost_concern_percentage": 72.0
            },
            "fact_validation": {
              "valid_claims": ["72% of startup founders cite cost management"],
              "fact_check_score": 1.0,
              "validation_details": "Claim verified against statistics registry"
            }
          }
        }
      },
      "visualizations": [
        {
          "id": "viz_001",
          "type": "bar_chart",
          "title": "Primary Challenges - Startup Founders",
          "data_source": "csv_456",
          "citation_ids": ["csv_456_cost_management_stat"]
        }
      ],
      "analyzed_at": "2024-01-15T11:00:00Z"
    }
  ],
  "session_metadata": {
    "total_assumptions": 1,
    "processing_time": 45.2,
    "fact_validation_enabled": true,
    "persona_routing_used": true
  }
}
```

### 3. Get Statistics Registry

Retrieve pre-computed statistics from the enhanced processing pipeline.

#### Endpoint
```http
GET /projects/{project_id}/statistics-registry
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `persona_id` | string | No | Filter statistics by persona |
| `source_type` | string | No | Filter by source: "csv", "pdf", or "all" |
| `statistic_type` | string | No | Filter by type: "categorical", "numerical", "themes" |
| `include_citations` | boolean | No | Include citation metadata (default: true) |

#### Response
```json
{
  "project_id": "proj_123",
  "statistics_registry": {
    "csv_statistics": {
      "doc_456": {
        "filename": "survey_responses.csv",
        "metadata": {
          "total_rows": 1000,
          "processing_timestamp": "2024-01-15T10:30:00Z"
        },
        "categorical_distributions": {
          "primary_challenge": {
            "total_responses": 1000,
            "distribution": [
              {
                "value": "Cost management",
                "count": 350,
                "percentage": 35.0,
                "citation_id": "csv_456_cost_management_stat"
              },
              {
                "value": "Time constraints",
                "count": 250,
                "percentage": 25.0,
                "citation_id": "csv_456_time_constraints_stat"
              }
            ]
          }
        }
      }
    },
    "pdf_statistics": {
      "doc_789": {
        "filename": "startup_interviews.pdf",
        "themes": {
          "budget_concerns": {
            "frequency": 15,
            "percentage": 75.0,
            "citation_id": "pdf_789_budget_theme"
          }
        }
      }
    }
  },
  "persona_associations": {
    "startup_founder": {
      "associated_statistics": [
        "csv_456_cost_management_stat",
        "pdf_789_budget_theme"
      ],
      "relevance_scores": {
        "csv_456_cost_management_stat": 0.95,
        "pdf_789_budget_theme": 0.88
      }
    }
  }
}
```

### 4. Verify Citations

Verify and trace citations back to original source data.

#### Endpoint
```http
GET /projects/{project_id}/citations/{citation_id}
```

#### Response
```json
{
  "citation_id": "csv_456_cost_management_stat",
  "verification_status": "valid",
  "source_information": {
    "document_id": "doc_456",
    "filename": "survey_responses.csv",
    "source_type": "csv",
    "data_location": {
      "column": "primary_challenge",
      "value": "Cost management",
      "row_range": [1, 1000]
    }
  },
  "statistic_details": {
    "value": 35.0,
    "unit": "percentage",
    "sample_size": 1000,
    "calculation_method": "count_percentage"
  },
  "verification_hash": "sha256:abc123...",
  "created_at": "2024-01-15T10:30:00Z",
  "last_verified": "2024-01-15T11:00:00Z"
}
```

### 5. Generate Visualizations

Generate or retrieve visualizations for analysis results.

#### Endpoint
```http
POST /projects/{project_id}/visualizations
```

#### Request
```json
{
  "data_source": "statistics_registry",
  "visualization_types": ["bar_chart", "pie_chart", "table"],
  "filters": {
    "persona_id": "startup_founder",
    "statistic_types": ["categorical_distributions"]
  },
  "format": "interactive",
  "include_citations": true
}
```

#### Response
```json
{
  "visualizations": [
    {
      "id": "viz_001",
      "type": "bar_chart",
      "title": "Primary Challenges Distribution",
      "data": {
        "plotly_json": "{...}",
        "static_image_url": "https://api.yuba.com/viz/viz_001.png",
        "markdown_table": "| Challenge | Count | Percentage |\n|-----------|-------|------------|\n| Cost | 350 | 35% |"
      },
      "metadata": {
        "citation_ids": ["csv_456_cost_management_stat"],
        "data_source": "doc_456",
        "sample_size": 1000
      },
      "accessibility": {
        "alt_text": "Bar chart showing cost management as top challenge at 35%",
        "screen_reader_description": "Chart displays primary challenges with cost management leading at 35% of 1000 respondents"
      }
    }
  ]
}
```

### 6. Get Analysis History

Retrieve historical analysis results with enhanced metadata.

#### Endpoint
```http
GET /projects/{project_id}/analysis-history
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Number of results (default: 50, max: 200) |
| `offset` | integer | No | Pagination offset (default: 0) |
| `persona_id` | string | No | Filter by persona |
| `include_fact_validation` | boolean | No | Include validation metrics (default: true) |
| `min_confidence` | number | No | Minimum confidence score filter |

#### Response
```json
{
  "total_analyses": 150,
  "analyses": [
    {
      "session_id": "session_789",
      "analyzed_at": "2024-01-15T11:00:00Z",
      "assumptions_count": 1,
      "average_confidence": 0.92,
      "fact_validation_summary": {
        "average_fact_score": 0.95,
        "total_claims_validated": 8,
        "flagged_claims": 0
      },
      "persona_distribution": {
        "startup_founder": 1
      }
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

## Enhanced Response Models

### EnhancedAnalysisOutput
```json
{
  "claim": "string",
  "accuracy_level": "high|medium|low",
  "supporting_evidence": ["string"],
  "debunking_evidence": ["string"],
  "statistical_data": {
    "source_statistics": {},
    "fact_validation": {
      "valid_claims": ["string"],
      "unsupported_claims": ["string"],
      "fact_check_score": "number"
    }
  },
  "confidence_score": "number",
  "citation_ids": ["string"],
  "persona_relevance_score": "number",
  "fact_validation_score": "number",
  "visualization_ids": ["string"]
}
```

### StatisticsRegistryEntry
```json
{
  "statistic_id": "string",
  "source_type": "csv|pdf",
  "source_file": "string",
  "data_path": "string",
  "value": "number|string",
  "context": "string",
  "citation_id": "string",
  "persona_associations": ["string"],
  "verification_hash": "string",
  "created_at": "datetime"
}
```

### FactValidationResult
```json
{
  "fact_check_score": "number",
  "valid_claims": ["string"],
  "unsupported_claims": ["string"],
  "questionable_claims": ["string"],
  "validation_details": {
    "total_claims_checked": "number",
    "claims_verified": "number",
    "verification_method": "statistics_registry"
  }
}
```

## Error Handling

### Enhanced Error Responses

#### Validation Errors
```json
{
  "error": "validation_failed",
  "message": "Fact validation detected inconsistencies",
  "details": {
    "fact_check_score": 0.3,
    "unsupported_claims": [
      "85% of users prefer solution A"
    ],
    "suggested_action": "Review source data or adjust analysis parameters"
  },
  "error_code": "FACT_VALIDATION_FAILED"
}
```

#### Processing Errors
```json
{
  "error": "processing_failed",
  "message": "Statistics extraction failed for uploaded document",
  "details": {
    "document_id": "doc_456",
    "processing_stage": "csv_statistics_extraction",
    "fallback_available": true,
    "suggested_action": "Retry with legacy processing or check file format"
  },
  "error_code": "STATISTICS_EXTRACTION_FAILED"
}
```

## Rate Limits

| Endpoint | Rate Limit | Burst Limit |
|----------|------------|-------------|
| Upload Documents | 10 per minute | 20 per hour |
| Analyze Assumptions | 5 per minute | 15 per hour |
| Get Statistics | 100 per minute | 500 per hour |
| Verify Citations | 200 per minute | 1000 per hour |

## Webhooks (Enhanced)

### Fact Validation Alerts
```json
{
  "event": "fact_validation_alert",
  "project_id": "proj_123",
  "session_id": "session_789",
  "alert_details": {
    "fact_check_score": 0.4,
    "unsupported_claims_count": 3,
    "confidence_impact": -0.3
  },
  "timestamp": "2024-01-15T11:00:00Z"
}
```

### Processing Completion
```json
{
  "event": "enhanced_processing_complete",
  "project_id": "proj_123",
  "document_id": "doc_456",
  "processing_results": {
    "statistics_extracted": true,
    "persona_associated": true,
    "citations_generated": 45
  },
  "timestamp": "2024-01-15T10:35:00Z"
}
```

## Migration Guide

### Backward Compatibility
All existing API endpoints continue to work without changes. Enhanced features are opt-in through new parameters.

### Gradual Migration
1. **Phase 1**: Add `enable_enhanced_processing=true` to document uploads
2. **Phase 2**: Enable `enable_fact_validation=true` in analysis requests
3. **Phase 3**: Implement citation verification and persona-aware routing

### Breaking Changes
None. All enhancements are additive and backward compatible.

## SDK Examples

### Python SDK
```python
from yuba_api import YubaClient

client = YubaClient(api_token="your_token")

# Upload with enhanced processing
result = client.upload_document(
    project_id="proj_123",
    file_path="survey.csv",
    persona_id="startup_founder",
    enable_enhanced_processing=True
)

# Analyze with fact validation
analysis = client.analyze_assumptions(
    project_id="proj_123",
    assumptions=[{
        "text": "Users need cost-effective solutions",
        "persona_id": "startup_founder"
    }],
    enable_fact_validation=True,
    include_visualizations=True
)

# Verify citations
citation = client.verify_citation(
    project_id="proj_123",
    citation_id="csv_456_cost_stat"
)
```

### JavaScript SDK
```javascript
const { YubaClient } = require('@yuba/api-client');

const client = new YubaClient({ apiToken: 'your_token' });

// Upload with enhanced processing
const uploadResult = await client.uploadDocument({
  projectId: 'proj_123',
  file: fileBuffer,
  personaId: 'startup_founder',
  enableEnhancedProcessing: true
});

// Analyze with enhanced features
const analysis = await client.analyzeAssumptions({
  projectId: 'proj_123',
  assumptions: [{
    text: 'Users need cost-effective solutions',
    personaId: 'startup_founder'
  }],
  enableFactValidation: true,
  includeVisualizations: true
});
```

## Support

For API support, documentation updates, or feature requests:
- **Email**: api-support@yuba.com
- **Documentation**: https://docs.yuba.com/api/market-research
- **Status Page**: https://status.yuba.com
- **Community**: https://community.yuba.com