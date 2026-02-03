"""
Type definitions for optional dependencies.

This module provides type aliases for optional dependencies like ReportLab
to prevent NameError issues when these packages are not available.
"""

from typing import Any, Union

# ReportLab types - use Any when ReportLab is not available
try:
    from reportlab.platypus import Table, Image, Paragraph, Spacer
    from reportlab.graphics.shapes import Drawing
    ReportLabTable = Table
    ReportLabImage = Image
    ReportLabParagraph = Paragraph
    ReportLabSpacer = Spacer
    ReportLabDrawing = Drawing
    REPORTLAB_AVAILABLE = True
except ImportError:
    # Fallback types when ReportLab is not available
    ReportLabTable = Any
    ReportLabImage = Any
    ReportLabParagraph = Any
    ReportLabSpacer = Any
    ReportLabDrawing = Any
    REPORTLAB_AVAILABLE = False

# Matplotlib types - use Any when matplotlib is not available
try:
    import matplotlib.figure
    MatplotlibFigure = matplotlib.figure.Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MatplotlibFigure = Any
    MATPLOTLIB_AVAILABLE = False

# Export commonly used type aliases
__all__ = [
    'ReportLabTable',
    'ReportLabImage', 
    'ReportLabParagraph',
    'ReportLabSpacer',
    'ReportLabDrawing',
    'MatplotlibFigure',
    'REPORTLAB_AVAILABLE',
    'MATPLOTLIB_AVAILABLE'
]
