# MVP Suite (AMRG, BMC, Critique) Architecture

## Purpose
The `src/mvp` module provides tools for **Idea-to-Validation** progression. It includes:
1.  **AMRG (Automated MVP Requirements Generator):** Generates PRDs.
2.  **BMC (Business Model Canvas):** Generates business models.
3.  **Solution Critique:** Validates solutions against market data.

## Directory Structure
- `api/`: FastAPI routers for all sub-modules.
- `mvp_req/`: AMRG Logic (PRD generation).
- `bmc/`: Business Model Canvas logic.
- `soln_critique/`: Solution Validation logic.
- `bootstrap/`: Entry point for "Module 3" (skipping earlier steps).

## Key Components
- **AMRG Router:** Handles multi-step Q&A flow to generate a Product Requirement Document (PRD).
- **Critique Agent:** Uses `RAG` and `Web Search` to challenge user assumptions.
- **BMC v2:** Generates a canvas based on the refined solution and critique feedback.

## Data Flow
1.  User submits a Solution/Idea.
2.  **Critique Module** validates it (Web Search).
3.  **VPS v2 (Value Prop)** refines it based on critique.
4.  **BMC v2** builds the business model.
5.  **AMRG** generates the technical PRD.
