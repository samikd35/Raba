# Go-To-Market (MAV) Architecture

## Purpose
The `src/mav` module (Module 4) handles **Project Strategy & Execution**. It helps users bridge the gap between validation and market entry.

## Directory Structure
- `chat/`: **Project Chat** system. An intelligent agent that discusses the project context with the user.
- `Pitch/`: **Pitch Deck Generator**. Creates structured slide content.
- `Pitch/GTM/`: **GTM Strategy Generator**. Creates go-to-market plans.
- `chunking/`: Utilities for handling large project context (chunking & retrieval).

## Key Components
- **Project Chat:** Uses RAG to answer questions about the specific project. Maintains thread history.
- **Pitch Deck Gen:** Transforms BMC and PRD data into a 10-slide investor deck structure.
- **GTM Strategy:** Generates marketing channels, sales strategy, and launch timeline.

## Data Flow
- **Input:** Takes Project ID (which links to PRD, BMC, VPC).
- **Processing:** Retrieves project context → LLM Synthesis.
- **Output:** Stored in `project_chats`, `pitch_decks`, and `gtm_strategies` tables.
