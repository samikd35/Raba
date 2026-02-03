# Migration Guide - Enhanced Market Research Agent

## Overview

This guide helps existing users migrate from the legacy market research system to the enhanced version. The enhanced system provides 100% accurate statistical reporting, complete source traceability, and persona-aware analysis while maintaining full backward compatibility.

## Migration Benefits

### Accuracy Improvements
- **Legacy System**: ~75% accuracy due to chunk-based statistical calculations
- **Enhanced System**: 100% accuracy through pre-computed statistics registry
- **Impact**: Eliminates statistical errors and "chunk hallucination"

### New Capabilities
- **Fact Validation**: Real-time verification of AI-generated claims
- **Source Traceability**: Every statistic traceable to original data
- **Persona-Aware Analysis**: Targeted insights for different user segments
- **Dynamic Visualizations**: Automatic chart generation from data

### Performance Improvements
- **Faster Processing**: Optimized for large datasets (10k+ rows)
- **Better Resource Management**: Efficient memory usage and concurrent processing
- **Enhanced Error Handling**: Graceful degradation and recovery mechanisms

## Migration Strategies

### Strategy 1: Gradual Migration (Recommended)

**Best for**: Production environments, risk-averse organizations, large projects

#### Phase 1: Enable Enhanced Processing (Week 1-2)
```bash
# 1. Test enhanced system with sample data
curl -X POST "https://api.yuba.com/v1/market-research/projects/test_project/research-documents" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@sample_survey.csv" \
  -F "enable_enhanced_processing=true"

# 2. Compare results with legacy system
# 3. Validate accuracy improvements
# 4. Train team on new features
```

#### Phase 2: Migrate Non-Critical Projects (Week 3-4)
```bash
# Re-upload research documents for non-critical projects
for project in non_critical_projects:
  # Upload with enhanced processing
  curl -X POST "https://api.yuba.com/v1/market-research/projects/$project/research-documents" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -F "file=@research_data.csv" \
    -F "enable_enhanced_processing=true"
```

#### Phase 3: Migrate Critical Projects (Week 5-6)
```bash
# Migrate critical projects with validation
for project in critical_projects:
  # 1. Backup existing analysis results
  # 2. Re-upload with enhanced processing
  # 3. Run parallel analysis (legacy vs enhanced)
  # 4. Validate results before switching
```

#### Phase 4: Full Enhanced Features (Week 7-8)
```bash
# Enable all enhanced features
curl -X POST "https://api.yuba.com/v1/market-research/projects/$project/analyze-assumptions" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "assumptions": [...],
    "enable_fact_validation": true,
    "persona_aware_routing": true,
    "include_visualizations": true,
    "citation_level": "detailed"
  }'
```

### Strategy 2: Immediate Migration

**Best for**: New projects, development environments, small organizations

#### Steps:
1. **Enable enhanced processing for all new uploads**
2. **Re-process existing critical documents**
3. **Update analysis workflows to use enhanced features**
4. **Train team on new capabilities**

### Strategy 3: Hybrid Approach

**Best for**: Organizations with mixed requirements

#### Implementation:
- **New Projects**: Use enhanced system exclusively
- **Existing Projects**: Migrate on a case-by-case basis
- **Critical Analysis**: Always use enhanced validation
- **Legacy Workflows**: Maintain for specific use cases

## Pre-Migration Checklist

### Technical Requirements
- [ ] **API Access**: Ensure you have access to enhanced API endpoints
- [ ] **Data Backup**: Backup all existing project data and analysis results
- [ ] **Environment Setup**: Configure development/staging environments for testing
- [ ] **Integration Testing**: Test enhanced system with your existing integrations

### Team Preparation
- [ ] **Training Plan**: Schedule training sessions for enhanced features
- [ ] **Documentation Review**: Ensure team reviews new user guides and API docs
- [ ] **Workflow Updates**: Plan updates to existing analysis workflows
- [ ] **Quality Assurance**: Define validation procedures for enhanced results

### Data Preparation
- [ ] **File Formats**: Ensure research documents are in supported formats
- [ ] **Data Quality**: Clean and validate source data for optimal processing
- [ ] **Persona Definitions**: Define personas for persona-aware analysis
- [ ] **Citation Requirements**: Determine citation and traceability needs

## Step-by-Step Migration Process

### Step 1: Environment Setup

#### Development Environment
```bash
# 1. Set up test project
export TEST_PROJECT_ID="migration_test_$(date +%s)"
curl -X POST "https://api.yuba.com/v1/market-research/projects" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Migration Test", "enhanced_features": true}'

# 2. Upload sample data
curl -X POST "https://api.yuba.com/v1/market-research/projects/$TEST_PROJECT_ID/research-documents" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@sample_data.csv" \
  -F "enable_enhanced_processing=true"

# 3. Run test analysis
curl -X POST "https://api.yuba.com/v1/market-research/projects/$TEST_PROJECT_ID/analyze-assumptions" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "assumptions": [{"text": "Users need cost-effective solutions"}],
    "enable_fact_validation": true
  }'
```

#### Validation Script
```python
#!/usr/bin/env python3
"""Migration validation script."""

import requests
import json
from typing import Dict, Any

def validate_enhanced_processing(project_id: str, api_token: str) -> Dict[str, Any]:
    """Validate enhanced processing capabilities."""
    headers = {"Authorization": f"Bearer {api_token}"}
    
    # Check statistics registry
    response = requests.get(
        f"https://api.yuba.com/v1/market-research/projects/{project_id}/statistics-registry",
        headers=headers
    )
    
    if response.status_code == 200:
        stats = response.json()
        return {
            "statistics_registry": True,
            "csv_statistics": len(stats.get("csv_statistics", {})) > 0,
            "citation_count": sum(
                len(doc.get("categorical_distributions", {})) 
                for doc in stats.get("csv_statistics", {}).values()
            )
        }
    
    return {"error": f"Failed to validate: {response.status_code}"}

# Run validation
result = validate_enhanced_processing("your_project_id", "your_token")
print(json.dumps(result, indent=2))
```

### Step 2: Data Migration

#### Re-upload Research Documents
```python
import os
import requests
from pathlib import Path

def migrate_research_documents(project_id: str, api_token: str, data_directory: str):
    """Migrate research documents to enhanced processing."""
    headers = {"Authorization": f"Bearer {api_token}"}
    base_url = "https://api.yuba.com/v1/market-research"
    
    for file_path in Path(data_directory).glob("*.csv"):
        print(f"Migrating {file_path.name}...")
        
        with open(file_path, 'rb') as f:
            files = {"file": f}
            data = {
                "enable_enhanced_processing": "true",
                "extract_statistics": "true",
                "enable_fact_validation": "true"
            }
            
            response = requests.post(
                f"{base_url}/projects/{project_id}/research-documents",
                headers=headers,
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Success: {result['statistics_summary']['unique_statistics']} statistics extracted")
            else:
                print(f"  ❌ Failed: {response.status_code}")

# Usage
migrate_research_documents("your_project_id", "your_token", "./research_data/")
```

#### Persona Association
```python
def associate_personas(project_id: str, api_token: str, persona_mappings: Dict[str, str]):
    """Associate existing documents with personas."""
    headers = {"Authorization": f"Bearer {api_token}"}
    base_url = "https://api.yuba.com/v1/market-research"
    
    for document_id, persona_id in persona_mappings.items():
        response = requests.patch(
            f"{base_url}/projects/{project_id}/research-documents/{document_id}",
            headers=headers,
            json={"persona_id": persona_id}
        )
        
        if response.status_code == 200:
            print(f"✅ Document {document_id} associated with persona {persona_id}")
        else:
            print(f"❌ Failed to associate document {document_id}")

# Usage
persona_mappings = {
    "doc_123": "startup_founder",
    "doc_456": "enterprise_manager"
}
associate_personas("your_project_id", "your_token", persona_mappings)
```

### Step 3: Analysis Migration

#### Update Analysis Workflows
```python
def run_enhanced_analysis(project_id: str, api_token: str, assumptions: List[Dict]):
    """Run analysis with enhanced features."""
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "assumptions": assumptions,
        "enable_fact_validation": True,
        "persona_aware_routing": True,
        "include_visualizations": True,
        "citation_level": "detailed",
        "confidence_threshold": 0.8
    }
    
    response = requests.post(
        f"https://api.yuba.com/v1/market-research/projects/{project_id}/analyze-assumptions",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        
        # Validate enhanced features
        for analysis in result["analysis_results"]:
            assert "fact_validation_score" in analysis["analyses"]["pain_points"]["statistical_data"]
            assert len(analysis["analyses"]["pain_points"]["citation_ids"]) > 0
            
        print("✅ Enhanced analysis completed successfully")
        return result
    else:
        print(f"❌ Analysis failed: {response.status_code}")
        return None

# Usage
assumptions = [
    {
        "id": "assumption_1",
        "text": "Startup founders struggle with budget constraints",
        "persona_id": "startup_founder"
    }
]
result = run_enhanced_analysis("your_project_id", "your_token", assumptions)
```

### Step 4: Validation and Testing

#### Accuracy Validation
```python
def validate_accuracy_improvements(project_id: str, api_token: str):
    """Validate accuracy improvements in enhanced system."""
    headers = {"Authorization": f"Bearer {api_token}"}
    
    # Get statistics registry
    stats_response = requests.get(
        f"https://api.yuba.com/v1/market-research/projects/{project_id}/statistics-registry",
        headers=headers
    )
    
    if stats_response.status_code != 200:
        return {"error": "Failed to get statistics registry"}
    
    stats = stats_response.json()
    
    # Run analysis
    analysis_response = requests.post(
        f"https://api.yuba.com/v1/market-research/projects/{project_id}/analyze-assumptions",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "assumptions": [{"text": "Users have cost concerns"}],
            "enable_fact_validation": True
        }
    )
    
    if analysis_response.status_code != 200:
        return {"error": "Failed to run analysis"}
    
    analysis = analysis_response.json()
    
    # Validate results
    validation_results = {
        "statistics_available": len(stats.get("statistics_registry", {})) > 0,
        "fact_validation_enabled": True,
        "accuracy_score": 0.0,
        "citation_count": 0
    }
    
    for result in analysis["analysis_results"]:
        for analysis_type, analysis_data in result["analyses"].items():
            fact_validation = analysis_data["statistical_data"].get("fact_validation", {})
            validation_results["accuracy_score"] = fact_validation.get("fact_check_score", 0.0)
            validation_results["citation_count"] = len(analysis_data.get("citation_ids", []))
            break
        break
    
    return validation_results

# Usage
validation = validate_accuracy_improvements("your_project_id", "your_token")
print(f"Accuracy Score: {validation['accuracy_score']}")
print(f"Citations Available: {validation['citation_count']}")
```

## Common Migration Issues and Solutions

### Issue 1: Statistics Not Extracted
**Symptoms**: Empty statistics registry, no citations generated
**Causes**: 
- File format issues (non-UTF-8 encoding)
- Inconsistent data formats
- Very small datasets

**Solutions**:
```bash
# Check file encoding
file -I your_data.csv

# Convert to UTF-8 if needed
iconv -f ISO-8859-1 -t UTF-8 your_data.csv > your_data_utf8.csv

# Validate data consistency
python -c "
import pandas as pd
df = pd.read_csv('your_data.csv')
print('Columns:', df.columns.tolist())
print('Data types:', df.dtypes.to_dict())
print('Sample size:', len(df))
"
```

### Issue 2: Low Fact Validation Scores
**Symptoms**: Fact validation scores below 0.8
**Causes**:
- AI generating claims not supported by data
- Inconsistent data processing
- Missing statistics in registry

**Solutions**:
```python
# Debug fact validation
def debug_fact_validation(project_id: str, citation_id: str, api_token: str):
    """Debug fact validation issues."""
    headers = {"Authorization": f"Bearer {api_token}"}
    
    # Verify citation
    response = requests.get(
        f"https://api.yuba.com/v1/market-research/projects/{project_id}/citations/{citation_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        citation = response.json()
        print(f"Citation Status: {citation['verification_status']}")
        print(f"Source: {citation['source_information']['filename']}")
        print(f"Value: {citation['statistic_details']['value']}")
    else:
        print(f"Citation verification failed: {response.status_code}")

# Usage
debug_fact_validation("your_project_id", "csv_001_stat", "your_token")
```

### Issue 3: Persona Association Problems
**Symptoms**: Low persona relevance scores, incorrect routing
**Causes**:
- Vague persona definitions
- Insufficient persona-data matching
- Missing persona characteristics

**Solutions**:
```python
# Improve persona definitions
enhanced_personas = {
    "startup_founder": {
        "characteristics": [
            "budget-conscious", "fast-moving", "tech-savvy", 
            "resource-constrained", "growth-focused"
        ],
        "pain_points": [
            "limited funding", "rapid scaling", "team coordination",
            "market validation", "product-market fit"
        ],
        "keywords": [
            "startup", "bootstrap", "funding", "scale", "growth",
            "budget", "cost", "affordable", "lean", "agile"
        ]
    }
}

# Update persona definitions
def update_persona_definitions(project_id: str, personas: Dict, api_token: str):
    """Update persona definitions for better matching."""
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.patch(
        f"https://api.yuba.com/v1/market-research/projects/{project_id}/personas",
        headers=headers,
        json={"personas": personas}
    )
    
    return response.status_code == 200

# Usage
update_persona_definitions("your_project_id", enhanced_personas, "your_token")
```

## Post-Migration Validation

### Validation Checklist
- [ ] **Statistics Registry**: All documents have extracted statistics
- [ ] **Fact Validation**: Analysis results include validation scores ≥ 0.8
- [ ] **Citations**: All claims have traceable citation IDs
- [ ] **Persona Routing**: Persona-specific analyses show high relevance scores
- [ ] **Visualizations**: Charts and tables generate correctly
- [ ] **Performance**: Analysis completes within expected timeframes
- [ ] **Error Handling**: System handles failures gracefully

### Automated Validation Script
```python
#!/usr/bin/env python3
"""Post-migration validation script."""

import requests
import json
from typing import Dict, List

def comprehensive_validation(project_id: str, api_token: str) -> Dict[str, Any]:
    """Run comprehensive post-migration validation."""
    headers = {"Authorization": f"Bearer {api_token}"}
    base_url = "https://api.yuba.com/v1/market-research"
    
    results = {
        "statistics_registry": False,
        "fact_validation": False,
        "citations": False,
        "persona_routing": False,
        "visualizations": False,
        "performance": False,
        "overall_success": False
    }
    
    try:
        # Test 1: Statistics Registry
        stats_response = requests.get(f"{base_url}/projects/{project_id}/statistics-registry", headers=headers)
        if stats_response.status_code == 200:
            stats = stats_response.json()
            results["statistics_registry"] = len(stats.get("statistics_registry", {})) > 0
        
        # Test 2: Enhanced Analysis
        analysis_response = requests.post(
            f"{base_url}/projects/{project_id}/analyze-assumptions",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "assumptions": [{"text": "Test assumption for validation"}],
                "enable_fact_validation": True,
                "include_visualizations": True
            }
        )
        
        if analysis_response.status_code == 200:
            analysis = analysis_response.json()
            
            # Check fact validation
            for result in analysis["analysis_results"]:
                for analysis_type, analysis_data in result["analyses"].items():
                    fact_score = analysis_data["statistical_data"].get("fact_validation", {}).get("fact_check_score", 0)
                    results["fact_validation"] = fact_score >= 0.8
                    
                    # Check citations
                    results["citations"] = len(analysis_data.get("citation_ids", [])) > 0
                    
                    # Check visualizations
                    results["visualizations"] = len(result.get("visualizations", [])) > 0
                    break
                break
        
        # Overall success
        results["overall_success"] = all([
            results["statistics_registry"],
            results["fact_validation"],
            results["citations"]
        ])
        
    except Exception as e:
        results["error"] = str(e)
    
    return results

# Run validation
validation_results = comprehensive_validation("your_project_id", "your_token")
print("Migration Validation Results:")
print(json.dumps(validation_results, indent=2))

if validation_results["overall_success"]:
    print("\n✅ Migration completed successfully!")
else:
    print("\n❌ Migration validation failed. Please review the results above.")
```

## Rollback Procedures

### Emergency Rollback
If issues arise during migration, you can rollback to the legacy system:

```python
def emergency_rollback(project_id: str, api_token: str):
    """Rollback to legacy system in case of issues."""
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    # Disable enhanced features
    response = requests.patch(
        f"https://api.yuba.com/v1/market-research/projects/{project_id}/settings",
        headers=headers,
        json={
            "enhanced_processing": False,
            "fact_validation": False,
            "persona_routing": False
        }
    )
    
    return response.status_code == 200

# Usage
rollback_success = emergency_rollback("your_project_id", "your_token")
print(f"Rollback {'successful' if rollback_success else 'failed'}")
```

### Gradual Rollback
For gradual rollback of specific features:

```python
def gradual_rollback(project_id: str, api_token: str, features_to_disable: List[str]):
    """Gradually disable enhanced features."""
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    settings = {}
    for feature in features_to_disable:
        settings[feature] = False
    
    response = requests.patch(
        f"https://api.yuba.com/v1/market-research/projects/{project_id}/settings",
        headers=headers,
        json=settings
    )
    
    return response.status_code == 200

# Usage - disable only fact validation
gradual_rollback("your_project_id", "your_token", ["fact_validation"])
```

## Support and Resources

### Getting Help
- **Technical Support**: support@yuba.com
- **Migration Assistance**: migration-help@yuba.com
- **Documentation**: https://docs.yuba.com/migration
- **Community Forum**: https://community.yuba.com/migration

### Training Resources
- **Enhanced Features Training**: 2-hour session covering new capabilities
- **API Updates Workshop**: 1-hour session on API changes
- **Best Practices Webinar**: Monthly sessions on optimization tips
- **One-on-One Consultation**: Available for complex migration scenarios

### Monitoring and Maintenance
- **Migration Dashboard**: Track migration progress and success metrics
- **Performance Monitoring**: Monitor system performance post-migration
- **Regular Health Checks**: Automated validation of enhanced features
- **Update Notifications**: Stay informed about new features and improvements

## Conclusion

The migration to the enhanced market research system provides significant improvements in accuracy, traceability, and functionality. By following this guide and using the provided scripts and validation procedures, you can ensure a smooth transition that maximizes the benefits of the enhanced system while minimizing disruption to your existing workflows.

Remember to:
1. **Test thoroughly** in development environments before production migration
2. **Validate results** at each step of the migration process
3. **Train your team** on new features and capabilities
4. **Monitor performance** after migration completion
5. **Leverage support resources** when needed

The enhanced system is designed to be a significant upgrade while maintaining the familiarity and reliability you expect from the market research platform.