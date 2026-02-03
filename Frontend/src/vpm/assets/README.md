# VPM Assets

This directory contains assets for document generation.

## Required Files

### yuba_logo.png
- **Purpose**: Logo for PDF and Word documents
- **Recommended size**: 300x100 pixels (3:1 ratio)
- **Format**: PNG with transparent background
- **Location**: Place the Yuba logo file here as `yuba_logo.png`

## Usage

The document generator will automatically use the logo if it exists at:
- `/Backend/src/vpm/assets/yuba_logo.png`

If the logo is not found, documents will still generate without it.
