# Value Proposition Module (VPM) Architecture

## Purpose
The `src/vpm` module helps users articulate the **value** of their solution. It focuses on the Value Proposition Canvas (VPC) and preparing users for field validation.

## Directory Structure
- `api/`: FastAPI endpoints.
- `vpc/`: Logic for generating and refining the Value Proposition Canvas.
- `integration/`: Hooks for connecting VPM data to other modules (like MVP/BMC).
- `models/`: Data models for VPC entities (Customer Segments, Pain Points, Gain Creators).

## Key Components
- **VPC Generator:** AI agent that takes a Problem Statement + Solution Idea and fills out the VPC (Jobs to be Done, Pains, Gains).
- **Field Prep:** Generates interview scripts and validation experiments based on the VPC assumptions.

## Integration
- **Input:** Consumes Problem Statements from `src/pgen`.
- **Output:** Produces a validated VPC, which feeds into the **Business Model Canvas (BMC)** in `src/mvp`.
