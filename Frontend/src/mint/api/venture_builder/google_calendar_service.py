"""
Google Calendar integration service for Venture Builder feature.

Handles OAuth flow, token management, availability computation, and event creation.
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import TimeSlot, GoogleCalendarItem
from ...utils.token_encryption import get_token_encryption, TokenEncryptionError
from ..system.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# OAuth 2.0 scopes for Google Calendar
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",  # Full calendar access
]


class GoogleCalendarError(Exception):
    """Base exception for Google Calendar operations."""
    pass


class GoogleCalendarAuthError(GoogleCalendarError):
    """Raised when authentication fails or needs re-authentication."""
    pass


class GoogleCalendarService:
    """
    Handles Google Calendar API operations for VB scheduling.

    Provides:
    - OAuth flow for VBs to connect their calendar
    - Token management with automatic refresh
    - Free/Busy queries for availability
    - Event creation/deletion for bookings
    - Availability slot computation
    """

    def __init__(self):
        """
        Initialize Google Calendar service.

        Uses its own supabase client with service role.
        """
        self.supabase = get_supabase_client(use_service_role=True).client
        self.token_encryption = get_token_encryption()

        # OAuth client configuration from environment
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv(
            "GOOGLE_CALENDAR_REDIRECT_URI",
            "http://localhost:8000/venture-builder/calendar/callback"
        )

        self.enabled = bool(self.client_id and self.client_secret)

        if not self.enabled:
            logger.warning(
                "Google Calendar integration disabled - missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET"
            )

    def _get_client_config(self) -> Dict[str, Any]:
        """Get OAuth client configuration."""
        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }

    # =========================================================================
    # OAuth Flow
    # =========================================================================

    def create_auth_url(self, vb_id: str) -> Tuple[str, str]:
        """
        Generate OAuth authorization URL for VB to connect calendar.

        Args:
            vb_id: Venture builder ID (used in state token).

        Returns:
            Tuple of (authorization_url, state_token).

        Raises:
            GoogleCalendarError: If OAuth is not configured.
        """
        if not self.enabled:
            raise GoogleCalendarError(
                "Google Calendar integration is not configured"
            )

        # Generate state token with VB ID for validation
        state = f"{vb_id}:{secrets.token_urlsafe(32)}"

        flow = Flow.from_client_config(
            self._get_client_config(),
            scopes=CALENDAR_SCOPES,
            state=state,
        )
        flow.redirect_uri = self.redirect_uri

        authorization_url, _ = flow.authorization_url(
            access_type="offline",  # Get refresh token
            include_granted_scopes="true",
            prompt="consent",  # Force consent to always get refresh token
        )

        return authorization_url, state

    def handle_oauth_callback(
        self, code: str, state: str
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback and store tokens.

        Uses UPSERT to update existing connections (for re-authentication).

        Args:
            code: Authorization code from Google.
            state: State token to validate (contains VB ID).

        Returns:
            Dict with vb_id, calendar_id, and status.

        Raises:
            GoogleCalendarError: If callback processing fails.
        """
        if not self.enabled:
            raise GoogleCalendarError(
                "Google Calendar integration is not configured"
            )

        # Extract VB ID from state
        try:
            vb_id = state.split(":")[0]
        except (IndexError, ValueError):
            raise GoogleCalendarError("Invalid state token")

        try:
            # Exchange code for tokens
            flow = Flow.from_client_config(
                self._get_client_config(),
                scopes=CALENDAR_SCOPES,
                state=state,
            )
            flow.redirect_uri = self.redirect_uri
            flow.fetch_token(code=code)
            credentials = flow.credentials

            if not credentials.refresh_token:
                logger.warning(
                    f"No refresh token received for VB {vb_id}. "
                    "User may need to revoke access and re-authenticate."
                )

            # Get user's calendar list to find primary calendar
            service = build("calendar", "v3", credentials=credentials)
            calendar_list = service.calendarList().list().execute()

            # Find primary calendar
            primary_calendar = None
            for cal in calendar_list.get("items", []):
                if cal.get("primary"):
                    primary_calendar = cal
                    break

            # Fallback to first calendar if no primary
            if not primary_calendar and calendar_list.get("items"):
                primary_calendar = calendar_list["items"][0]

            if not primary_calendar:
                raise GoogleCalendarError("No calendars found in Google account")

            # Encrypt tokens
            encrypted_access = self.token_encryption.encrypt(credentials.token)
            encrypted_refresh = self.token_encryption.encrypt(
                credentials.refresh_token or ""
            )

            # Calculate token expiry
            if credentials.expiry:
                token_expiry = credentials.expiry
            else:
                token_expiry = datetime.now(ZoneInfo("UTC")) + timedelta(hours=1)

            # Ensure expiry is timezone-aware
            if token_expiry.tzinfo is None:
                token_expiry = token_expiry.replace(tzinfo=ZoneInfo("UTC"))

            # UPSERT connection (update if exists, insert if not)
            connection_data = {
                "vb_id": vb_id,
                "google_user_id": primary_calendar.get("id", "unknown"),
                "calendar_id": primary_calendar.get("id"),
                "encrypted_access_token": encrypted_access,
                "encrypted_refresh_token": encrypted_refresh,
                "token_expiry": token_expiry.isoformat(),
                "time_zone": primary_calendar.get("timeZone", "UTC"),
                "is_valid": True,
            }

            self.supabase.table("venture_builder_google_connections").upsert(
                connection_data, on_conflict="vb_id"
            ).execute()

            logger.info(f"Google Calendar connected for VB {vb_id}")

            return {
                "vb_id": vb_id,
                "calendar_id": primary_calendar.get("id"),
                "calendar_name": primary_calendar.get("summary", "Primary"),
                "time_zone": primary_calendar.get("timeZone", "UTC"),
                "status": "connected",
            }

        except Exception as e:
            logger.error(f"OAuth callback failed for VB {vb_id}: {str(e)}")
            raise GoogleCalendarError(f"Failed to connect calendar: {str(e)}")

    # =========================================================================
    # Token Management
    # =========================================================================

    def get_credentials(self, vb_id: str) -> Optional[Credentials]:
        """
        Get valid credentials for a VB, refreshing if necessary.

        Args:
            vb_id: Venture builder ID.

        Returns:
            Google Credentials object or None if not connected.

        Raises:
            GoogleCalendarAuthError: If token refresh fails (needs re-auth).
        """
        # Fetch connection from DB
        result = self.supabase.table("venture_builder_google_connections").select(
            "*"
        ).eq("vb_id", str(vb_id)).eq("is_valid", True).limit(1).execute()

        if not result.data:
            return None

        conn = result.data[0]

        # Decrypt tokens
        try:
            access_token = self.token_encryption.decrypt(
                conn["encrypted_access_token"]
            )
            refresh_token = self.token_encryption.decrypt(
                conn["encrypted_refresh_token"]
            )
        except TokenEncryptionError as e:
            logger.error(f"Failed to decrypt tokens for VB {vb_id}: {str(e)}")
            self._mark_connection_invalid(vb_id)
            raise GoogleCalendarAuthError(
                "Your Google Calendar connection has expired. "
                "Please re-authenticate at /calendar/auth-url"
            )

        # Create credentials
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=CALENDAR_SCOPES,
        )

        # Parse token expiry
        token_expiry_str = conn.get("token_expiry")
        if token_expiry_str:
            token_expiry = datetime.fromisoformat(
                token_expiry_str.replace("Z", "+00:00")
            )
        else:
            token_expiry = datetime.now(ZoneInfo("UTC"))

        # Check if refresh needed (within 5 minutes of expiry)
        now = datetime.now(ZoneInfo("UTC"))
        if token_expiry <= now + timedelta(minutes=5):
            credentials = self._refresh_token(vb_id, credentials)

        return credentials

    def _refresh_token(self, vb_id: str, credentials: Credentials) -> Credentials:
        """
        Refresh access token and update database.

        Args:
            vb_id: Venture builder ID.
            credentials: Current credentials with refresh token.

        Returns:
            Refreshed credentials.

        Raises:
            GoogleCalendarAuthError: If refresh fails.
        """
        try:
            credentials.refresh(Request())

            # Encrypt new access token
            new_encrypted_access = self.token_encryption.encrypt(credentials.token)

            # Calculate new expiry
            if credentials.expiry:
                new_expiry = credentials.expiry
            else:
                new_expiry = datetime.now(ZoneInfo("UTC")) + timedelta(hours=1)

            if new_expiry.tzinfo is None:
                new_expiry = new_expiry.replace(tzinfo=ZoneInfo("UTC"))

            # Update tokens in database
            self.supabase.table("venture_builder_google_connections").update(
                {
                    "encrypted_access_token": new_encrypted_access,
                    "token_expiry": new_expiry.isoformat(),
                }
            ).eq("vb_id", str(vb_id)).execute()

            logger.info(f"Refreshed access token for VB {vb_id}")
            return credentials

        except Exception as e:
            logger.error(f"Failed to refresh token for VB {vb_id}: {str(e)}")
            self._mark_connection_invalid(vb_id)
            raise GoogleCalendarAuthError(
                "Your Google Calendar connection has expired. "
                "Please re-authenticate at /calendar/auth-url"
            )

    def _mark_connection_invalid(self, vb_id: str) -> None:
        """Mark a connection as invalid (needs re-authentication)."""
        try:
            self.supabase.table("venture_builder_google_connections").update(
                {"is_valid": False}
            ).eq("vb_id", str(vb_id)).execute()
            logger.info(f"Marked Google connection as invalid for VB {vb_id}")
        except Exception as e:
            logger.error(f"Failed to mark connection invalid for VB {vb_id}: {str(e)}")

    # =========================================================================
    # Calendar Operations
    # =========================================================================

    def get_connection_status(self, vb_id: str) -> Dict[str, Any]:
        """
        Get Google Calendar connection status for a VB.

        Args:
            vb_id: Venture builder ID.

        Returns:
            Dict with connection status.
        """
        result = self.supabase.table("venture_builder_google_connections").select(
            "calendar_id, time_zone, is_valid"
        ).eq("vb_id", str(vb_id)).limit(1).execute()

        if not result.data:
            return {"connected": False}

        conn = result.data[0]
        return {
            "connected": True,
            "calendar_id": conn.get("calendar_id"),
            "time_zone": conn.get("time_zone"),
            "is_valid": conn.get("is_valid", False),
        }

    def list_calendars(self, vb_id: str) -> List[GoogleCalendarItem]:
        """
        List all calendars for a VB.

        Args:
            vb_id: Venture builder ID.

        Returns:
            List of GoogleCalendarItem objects.

        Raises:
            GoogleCalendarAuthError: If credentials are invalid.
        """
        credentials = self.get_credentials(vb_id)
        if not credentials:
            raise GoogleCalendarError("No valid calendar connection found")

        service = build("calendar", "v3", credentials=credentials)
        calendar_list = service.calendarList().list().execute()

        return [
            GoogleCalendarItem(
                id=cal["id"],
                summary=cal.get("summary", "Unnamed Calendar"),
                primary=cal.get("primary", False),
            )
            for cal in calendar_list.get("items", [])
        ]

    def select_calendar(
        self, vb_id: str, calendar_id: str, time_zone: str
    ) -> None:
        """
        Update selected calendar and timezone for VB.

        Args:
            vb_id: Venture builder ID.
            calendar_id: Google Calendar ID to use.
            time_zone: Timezone string (e.g., "America/New_York").
        """
        self.supabase.table("venture_builder_google_connections").update(
            {"calendar_id": calendar_id, "time_zone": time_zone}
        ).eq("vb_id", str(vb_id)).execute()

        logger.info(f"VB {vb_id} selected calendar {calendar_id}")

    def disconnect(self, vb_id: str) -> None:
        """
        Remove Google Calendar connection for VB.

        Args:
            vb_id: Venture builder ID.
        """
        self.supabase.table("venture_builder_google_connections").delete().eq(
            "vb_id", str(vb_id)
        ).execute()

        logger.info(f"Disconnected Google Calendar for VB {vb_id}")

    # =========================================================================
    # Free/Busy Queries
    # =========================================================================

    def get_busy_times(
        self, vb_id: str, start: datetime, end: datetime
    ) -> List[Tuple[datetime, datetime]]:
        """
        Query Google Calendar Free/Busy API for busy periods.

        Args:
            vb_id: Venture builder ID.
            start: Start of time range.
            end: End of time range.

        Returns:
            List of (start, end) tuples for busy periods.
        """
        try:
            credentials = self.get_credentials(vb_id)
            if not credentials:
                logger.info(f"VB {vb_id} has no calendar connection, skipping busy times")
                return []

            # Get calendar ID
            conn = self.supabase.table("venture_builder_google_connections").select(
                "calendar_id"
            ).eq("vb_id", str(vb_id)).single().execute()

            calendar_id = conn.data["calendar_id"]

            service = build("calendar", "v3", credentials=credentials)

            # Ensure datetimes are timezone-aware
            if start.tzinfo is None:
                start = start.replace(tzinfo=ZoneInfo("UTC"))
            if end.tzinfo is None:
                end = end.replace(tzinfo=ZoneInfo("UTC"))

            body = {
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
                "items": [{"id": calendar_id}],
            }

            result = service.freebusy().query(body=body).execute()
            busy_periods = (
                result.get("calendars", {}).get(calendar_id, {}).get("busy", [])
            )

            return [
                (
                    datetime.fromisoformat(
                        period["start"].replace("Z", "+00:00")
                    ),
                    datetime.fromisoformat(period["end"].replace("Z", "+00:00")),
                )
                for period in busy_periods
            ]

        except GoogleCalendarAuthError:
            # Re-raise auth errors
            raise
        except Exception as e:
            logger.error(f"Failed to get busy times for VB {vb_id}: {str(e)}")
            # Return empty list on error to allow booking to continue
            return []

    # =========================================================================
    # Event Management
    # =========================================================================

    def create_event(
        self,
        vb_id: str,
        summary: str,
        start: datetime,
        end: datetime,
        attendee_email: str,
        description: Optional[str] = None,
        agenda: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a Google Calendar event.

        Args:
            vb_id: Venture builder ID.
            summary: Event title.
            start: Event start time.
            end: Event end time.
            attendee_email: User's email to invite.
            description: Event description.
            agenda: Meeting agenda (included in description).

        Returns:
            Google Calendar event ID, or None if creation failed.
        """
        try:
            credentials = self.get_credentials(vb_id)
            if not credentials:
                logger.warning(f"Cannot create event - VB {vb_id} has no calendar")
                return None

            conn = self.supabase.table("venture_builder_google_connections").select(
                "calendar_id, time_zone"
            ).eq("vb_id", str(vb_id)).single().execute()

            calendar_id = conn.data["calendar_id"]
            time_zone = conn.data.get("time_zone", "UTC")

            service = build("calendar", "v3", credentials=credentials)

            # Build full description
            full_description = "Yuba Coaching Session\n\n"
            if description:
                full_description += f"{description}\n\n"
            if agenda:
                full_description += f"Agenda:\n{agenda}\n\n"
            full_description += "Booked through Yuba platform."

            # Ensure datetimes are timezone-aware
            if start.tzinfo is None:
                start = start.replace(tzinfo=ZoneInfo("UTC"))
            if end.tzinfo is None:
                end = end.replace(tzinfo=ZoneInfo("UTC"))

            event_body = {
                "summary": summary,
                "description": full_description,
                "start": {"dateTime": start.isoformat(), "timeZone": time_zone},
                "end": {"dateTime": end.isoformat(), "timeZone": time_zone},
                "attendees": [{"email": attendee_email}],
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 24 * 60},  # 1 day before
                        {"method": "popup", "minutes": 30},  # 30 min before
                    ],
                },
            }

            # Try to create with Google Meet
            try:
                event_body["conferenceData"] = {
                    "createRequest": {
                        "requestId": f"yuba-{vb_id}-{int(start.timestamp())}",
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                }
                event = service.events().insert(
                    calendarId=calendar_id,
                    body=event_body,
                    conferenceDataVersion=1,
                    sendUpdates="all",
                ).execute()
            except HttpError:
                # Fall back without conference data if Meet is not available
                del event_body["conferenceData"]
                event = service.events().insert(
                    calendarId=calendar_id,
                    body=event_body,
                    sendUpdates="all",
                ).execute()

            event_id = event.get("id")
            logger.info(f"Created Google Calendar event {event_id} for VB {vb_id}")
            return event_id

        except GoogleCalendarAuthError:
            # Re-raise auth errors
            raise
        except Exception as e:
            logger.error(f"Failed to create calendar event for VB {vb_id}: {str(e)}")
            return None

    def delete_event(self, vb_id: str, event_id: str) -> bool:
        """
        Delete a Google Calendar event.

        Args:
            vb_id: Venture builder ID.
            event_id: Google Calendar event ID.

        Returns:
            True if deleted successfully, False otherwise.
        """
        try:
            credentials = self.get_credentials(vb_id)
            if not credentials:
                logger.warning(f"Cannot delete event - VB {vb_id} has no calendar")
                return False

            conn = self.supabase.table("venture_builder_google_connections").select(
                "calendar_id"
            ).eq("vb_id", str(vb_id)).single().execute()

            calendar_id = conn.data["calendar_id"]

            service = build("calendar", "v3", credentials=credentials)

            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates="all",
            ).execute()

            logger.info(f"Deleted Google Calendar event {event_id} for VB {vb_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.info(f"Event {event_id} already deleted or not found")
                return True  # Consider it deleted
            logger.error(f"Failed to delete event {event_id}: {str(e)}")
            return False
        except GoogleCalendarAuthError:
            logger.error(f"Auth error deleting event {event_id} for VB {vb_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {str(e)}")
            return False

    # =========================================================================
    # Availability Computation
    # =========================================================================

    def compute_available_slots(
        self,
        vb_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[TimeSlot]:
        """
        Compute available booking slots for a VB.

        Algorithm:
        1. Get VB's availability slots (specific session start/end times per day)
        2. Get Yuba booked sessions from vb_sessions table
        3. Get Google Calendar busy times via Free/Busy API
        4. For each day in range, check which slots are available

        Args:
            vb_id: Venture builder ID.
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            List of available TimeSlot objects.
        """
        # Ensure dates are timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=ZoneInfo("UTC"))
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=ZoneInfo("UTC"))

        # 1. Get availability slots
        slots_result = self.supabase.table(
            "venture_builder_availability_profiles"
        ).select("*").eq("vb_id", str(vb_id)).execute()

        if not slots_result.data:
            logger.info(f"VB {vb_id} has no availability slots configured")
            return []

        # Group slots by day of week (multiple slots per day allowed)
        slots_by_day = {}
        for slot in slots_result.data:
            day = slot["day_of_week"]
            if day not in slots_by_day:
                slots_by_day[day] = []
            slots_by_day[day].append(slot)

        # 2. Get Yuba booked sessions
        sessions_result = self.supabase.table("vb_sessions").select(
            "session_datetime, session_duration_minutes"
        ).eq("venture_builder_id", str(vb_id)).gte(
            "session_datetime", start_date.isoformat()
        ).lte(
            "session_datetime", end_date.isoformat()
        ).eq(
            "status", "confirmed"
        ).execute()

        yuba_booked = []
        for s in sessions_result.data:
            session_start = datetime.fromisoformat(
                s["session_datetime"].replace("Z", "+00:00")
            )
            duration = s.get("session_duration_minutes", 60)
            session_end = session_start + timedelta(minutes=duration)
            yuba_booked.append((session_start, session_end))

        # 3. Get Google Calendar busy times
        try:
            google_busy = self.get_busy_times(vb_id, start_date, end_date)
        except GoogleCalendarAuthError:
            google_busy = []

        # Combine all busy periods
        all_busy = yuba_booked + google_busy

        # Get VB's timezone
        conn_result = self.supabase.table(
            "venture_builder_google_connections"
        ).select("time_zone").eq("vb_id", str(vb_id)).limit(1).execute()

        vb_timezone = ZoneInfo(
            conn_result.data[0]["time_zone"] if conn_result.data else "UTC"
        )

        # 4. Generate available slots for each day in range
        available_slots = []
        current_date = start_date.date()
        end = end_date.date()
        now = datetime.now(ZoneInfo("UTC"))

        while current_date <= end:
            # Convert Python weekday (0=Mon) to our schema (0=Sun)
            python_weekday = current_date.weekday()
            our_day_of_week = (python_weekday + 1) % 7

            if our_day_of_week not in slots_by_day:
                current_date += timedelta(days=1)
                continue

            # Check each slot for this day
            for slot_config in slots_by_day[our_day_of_week]:
                session_start_time = datetime.strptime(
                    slot_config["session_start"], "%H:%M:%S"
                ).time()
                session_end_time = datetime.strptime(
                    slot_config["session_end"], "%H:%M:%S"
                ).time()

                # Create datetime objects in VB's timezone
                slot_start = datetime.combine(current_date, session_start_time).replace(
                    tzinfo=vb_timezone
                )
                slot_end = datetime.combine(current_date, session_end_time).replace(
                    tzinfo=vb_timezone
                )

                # Convert to UTC for comparison
                slot_start_utc = slot_start.astimezone(ZoneInfo("UTC"))
                slot_end_utc = slot_end.astimezone(ZoneInfo("UTC"))

                # Skip past slots
                if slot_start_utc <= now:
                    continue

                # Check if slot conflicts with any busy period
                is_available = True
                for busy_start, busy_end in all_busy:
                    if not (slot_end_utc <= busy_start or slot_start_utc >= busy_end):
                        is_available = False
                        break

                if is_available:
                    available_slots.append(
                        TimeSlot(start=slot_start_utc, end=slot_end_utc, available=True)
                    )

            current_date += timedelta(days=1)

        return available_slots

    def get_vb_timezone(self, vb_id: str) -> str:
        """
        Get the timezone for a VB from their calendar connection.

        Args:
            vb_id: Venture builder ID.

        Returns:
            Timezone string (defaults to "UTC").
        """
        result = self.supabase.table(
            "venture_builder_google_connections"
        ).select("time_zone").eq("vb_id", str(vb_id)).limit(1).execute()

        return result.data[0]["time_zone"] if result.data else "UTC"


# Singleton instance
_google_calendar_service: Optional[GoogleCalendarService] = None


def get_google_calendar_service() -> GoogleCalendarService:
    """
    Get or create singleton GoogleCalendarService instance.

    Returns:
        GoogleCalendarService instance.
    """
    global _google_calendar_service
    if _google_calendar_service is None:
        _google_calendar_service = GoogleCalendarService()
    return _google_calendar_service
