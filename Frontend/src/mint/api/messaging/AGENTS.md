# Messaging Architecture

## Purpose
The `src/mint/api/messaging` module powers **real-time user-to-user communication**. It supports both HTTP-based REST endpoints (history, status) and WebSockets (live updates).

## Directory Structure
- `endpoints.py`: REST API for creating channels, sending messages (HTTP fallback), and marking as read.
- `websocket.py`: Logic for connection management, heartbeats, and message broadcasting.
- `websocket_endpoints.py`: The actual WebSocket route handlers.
- `service.py`: Business logic for message persistence and retrieval.

## Key Components
- **Connection Manager:** Tracks active WebSocket connections per user.
- **Persistence:** Messages are stored in Supabase (`messages` table).
- **Encryption:** (If implemented) Messages may be encrypted using AES-GCM (referenced in `requirements.txt`).

## Integration
- **Client:** Connects via `ws://{host}/api/messaging/ws/{user_id}`.
- **Events:** Supports standard events like `message`, `typing_started`, `read_receipt`.
