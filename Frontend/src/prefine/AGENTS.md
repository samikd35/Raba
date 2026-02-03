# Idea Refinement (Prefine) Architecture

## Purpose
The `src/prefine` module (historically "Module 0" or "Module 1") is responsible for the initial **Idea Refinement** phase. It helps users crystallize vague thoughts into structured inputs before they enter the main Problem Generator (PGEN).

## Directory Structure
- `database_service.py`: CRUD operations for idea history.
- `history_service.py`: Manages user sessions and idea iterations.
- `models.py`: Data structures for raw ideas and refined concepts.
- `service.py`: Business logic for the refinement process.

## Key Components
- **Idea Processor:** Takes raw text input and structures it into core components (Who, What, Why).
- **History Tracking:** Maintains a log of user's thought evolution.

## Integration
- **Input:** User provides a "raw idea" or "observation".
- **Output:** Produces a structured concept that serves as the primary input for `src/pgen` (Problem Generation).
