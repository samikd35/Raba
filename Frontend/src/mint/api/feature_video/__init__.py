"""
Feature Video Seen Tracking Module

Tracks which feature help videos a user has seen for first-visit autoplay.
"""

from .endpoints import router as feature_video_router

__all__ = ["feature_video_router"]
