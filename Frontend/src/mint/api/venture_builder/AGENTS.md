# Venture Builder Architecture

## Purpose
The `src/mint/api/venture_builder` module facilitates the human-expert side of the platform. It manages the interactions between "Builders" (Startups) and "Venture Builders" (Coaches/Experts).

## Directory Structure
- `endpoints.py`: (Deprecated) Legacy single-file router.
- `invitations/`, `expertise/`, `profiles/`, `sessions/`: Domain-specific routers.
- `models/`: Pydantic models for coaching sessions, notes, and disputes.
- `services/`: Business logic for session booking, earnings calculation, and calendar sync.

## Key Components
- **Session Management:** Booking, rescheduling, and completing coaching sessions.
- **Calendar Sync:** Integration with external calendars (Google/Outlook) for availability.
- **Earnings & Payouts:** Tracks expert earnings and handles dispute resolution.
- **Portal:** Dedicated dashboard endpoints for Venture Builders.

## Data Flow
- **Users (Builders)** book **Sessions** with **Venture Builders**.
- **Venture Builders** set **Availability** and provide **Expertise**.
- **Sessions** generate **Notes** and **Earnings**.
