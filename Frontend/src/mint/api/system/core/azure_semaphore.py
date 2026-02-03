#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Shared Azure OpenAI semaphore for concurrency control.

This module provides a single semaphore to control all Azure OpenAI operations
across the entire application to prevent rate limiting issues.
"""

import asyncio

# Global semaphore to control ALL Azure OpenAI operations
# Set to 5 to allow reasonable parallelism while avoiding rate limits
# NOTE: Setting to 1 causes system-wide hangs if any request stalls
azure_openai_semaphore = asyncio.Semaphore(5)
