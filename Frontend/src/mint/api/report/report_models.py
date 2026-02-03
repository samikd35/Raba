#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Report Models for MINT.

This module provides shared data models for report chunking and storage services.
"""

from typing import List, Dict, Any
from pydantic import BaseModel


class ReportChunk(BaseModel):
    """Schema for a chunk of a report."""
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = {}


class ReportChunkWithEmbedding(ReportChunk):
    """Schema for a chunk of a report with embedding."""
    embedding: List[float]
