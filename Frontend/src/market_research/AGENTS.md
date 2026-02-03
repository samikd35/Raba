# Market Research Architecture

## Purpose
The `src/market_research` module provides a specialized AI agent for analyzing documents, verifying assumptions, and conducting autonomous market analysis.

## Directory Structure
- `api/`: FastAPI endpoints (`analysis_router`).
- `agent/`: The core logic for the analysis agent.
- `tools/`: Specialized tools used by the agent (e.g., PDF parsing, Web Search).

## Key Components
- **Analysis Agent:** An autonomous agent that can process uploaded documents (PDFs, Docx) and answer specific market questions.
- **Tools:**
    - `DocumentLoader`: Extracts text from user uploads.
    - `TavilySearch`: Searches the web for validation data.
    - `AssumptionValidator`: Cross-references user claims with external data.

## Integration
- **Input:** Takes Project ID and optional documents.
- **Output:** Returns a comprehensive analysis report with citations.
