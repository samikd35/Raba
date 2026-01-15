"""RABA Google Custom Search Service.

Search and download reference images for video generation.

Reference: 
- RABA_Architecture.md Section 2.4 ResearchImageSearcher
- PHASE2_3_DEEP_RESEARCH_PLAN.md Step 4
"""

import asyncio
import hashlib
import uuid
from typing import Optional

import httpx
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import get_settings
from app.models.research import ResearchImage
from app.services.supabase import get_supabase_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

ALLOWED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


class GoogleSearchError(Exception):
    """Base exception for Google Search errors."""
    pass


class ImageDownloadError(GoogleSearchError):
    """Error downloading image."""
    pass


class ImageStorageError(GoogleSearchError):
    """Error storing image."""
    pass


class GoogleSearchService:
    """
    Service for searching and downloading reference images.
    
    Uses Google Custom Search API for image search.
    Reference: RABA_Architecture.md Section 2.4
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cx: Optional[str] = None,
    ):
        settings = get_settings()
        self._api_key = api_key or settings.google_custom_search_api_key
        self._cx = cx or settings.google_custom_search_cx
        self._service = None
        self._supabase = get_supabase_service()
        self._validated = False
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate the Custom Search configuration."""
        # Check if CX looks like an API key (starts with AIza)
        if self._cx and self._cx.startswith("AIza"):
            logger.warning(
                "GOOGLE_CUSTOM_SEARCH_CX appears to be an API key, not a CSE ID. "
                "Please set a valid Custom Search Engine ID (format: xxx:yyy). "
                "Image search will be disabled."
            )
            self._cx = None
        
        # Check if API key is missing
        if not self._api_key:
            logger.warning("GOOGLE_CUSTOM_SEARCH_API_KEY not configured. Image search disabled.")
        
        # Check if CX is missing
        if not self._cx:
            logger.warning("GOOGLE_CUSTOM_SEARCH_CX not configured. Image search disabled.")
        
        self._validated = bool(self._api_key and self._cx)
    
    def _get_service(self):
        """Get or create Custom Search service."""
        if self._service is None:
            if not self._api_key:
                raise GoogleSearchError("Google Custom Search API key not configured")
            if not self._cx:
                raise GoogleSearchError("Google Custom Search CX not configured")
            self._service = build("customsearch", "v1", developerKey=self._api_key)
            logger.info("Created Google Custom Search service")
        return self._service
    
    async def search_images(
        self,
        query: str,
        num_images: int = 5,
    ) -> list[dict]:
        """
        Search for images related to the query.
        
        Args:
            query: Search query
            num_images: Number of images to return (max 10)
            
        Returns:
            List of image metadata dicts with url, title, source
        """
        if not self._validated:
            logger.debug("Google Custom Search not properly configured, skipping image search")
            return []
        
        service = self._get_service()
        num_images = min(num_images, 10)
        
        logger.info(f"Searching images for: {query[:50]}... (num={num_images})")
        
        try:
            result = await asyncio.to_thread(
                service.cse().list(
                    q=query,
                    cx=self._cx,
                    searchType="image",
                    num=num_images,
                    imgSize="LARGE",
                    safe="active",
                ).execute
            )
            
            items = result.get("items", [])
            images = []
            
            for item in items:
                image_url = item.get("link", "")
                if not image_url:
                    continue
                    
                if not any(image_url.lower().endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS):
                    if "image" not in item.get("mime", "").lower():
                        continue
                
                images.append({
                    "url": image_url,
                    "title": item.get("title", ""),
                    "source": item.get("displayLink", ""),
                    "context_url": item.get("image", {}).get("contextLink", ""),
                    "width": item.get("image", {}).get("width", 0),
                    "height": item.get("image", {}).get("height", 0),
                })
            
            logger.info(f"Found {len(images)} images for query")
            return images
            
        except HttpError as e:
            logger.error(f"Google Custom Search API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return []
    
    async def download_image(
        self,
        image_url: str,
        timeout: float = 30.0,
    ) -> Optional[bytes]:
        """
        Download an image from URL.
        
        Args:
            image_url: URL to download
            timeout: Request timeout in seconds
            
        Returns:
            Image bytes if successful, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    image_url,
                    follow_redirects=True,
                    headers={
                        "User-Agent": "RABA/1.0 (Video Generation Research)"
                    },
                )
                
                if response.status_code != 200:
                    logger.warning(f"Failed to download image: HTTP {response.status_code}")
                    return None
                
                content_length = len(response.content)
                if content_length > MAX_IMAGE_SIZE_BYTES:
                    logger.warning(f"Image too large: {content_length} bytes")
                    return None
                
                content_type = response.headers.get("content-type", "")
                if "image" not in content_type.lower():
                    logger.warning(f"Invalid content type: {content_type}")
                    return None
                
                return response.content
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout downloading image: {image_url}")
            return None
        except Exception as e:
            logger.warning(f"Failed to download image: {e}")
            return None
    
    async def store_image(
        self,
        image_bytes: bytes,
        workflow_id: str,
        original_url: str,
    ) -> Optional[str]:
        """
        Upload image to Supabase Storage.
        
        Args:
            image_bytes: Image data
            workflow_id: Workflow ID for path organization
            original_url: Original URL (used for filename hash)
            
        Returns:
            Public URL if successful, None otherwise
        """
        try:
            url_hash = hashlib.sha256(original_url.encode()).hexdigest()[:12]
            file_id = str(uuid.uuid4())[:8]
            filename = f"{url_hash}_{file_id}.jpg"
            # Path is relative to bucket - don't include bucket name in path
            storage_path = f"{workflow_id}/{filename}"
            
            public_url = await self._supabase.upload_file(
                bucket="media",  # Use existing 'media' bucket
                path=f"research_images/{storage_path}",
                file_data=image_bytes,
                content_type="image/jpeg",
            )
            
            if public_url:
                logger.info(f"Stored image: {storage_path}")
                return public_url
            else:
                logger.warning(f"Failed to get public URL for: {storage_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to store image: {e}")
            return None
    
    async def search_and_store_images(
        self,
        query: str,
        workflow_id: str,
        num_images: int = 2,
    ) -> list[ResearchImage]:
        """
        Search for images, download, and store them.
        
        This is the main entry point for image research.
        
        Args:
            query: Search query
            workflow_id: Workflow ID for storage organization
            num_images: Number of images to retrieve
            
        Returns:
            List of ResearchImage objects with storage URLs
        """
        search_results = await self.search_images(query, num_images=num_images + 2)
        
        if not search_results:
            logger.info("No images found in search")
            return []
        
        research_images = []
        
        for result in search_results:
            if len(research_images) >= num_images:
                break
            
            image_url = result.get("url", "")
            if not image_url:
                continue
            
            image_bytes = await self.download_image(image_url)
            if not image_bytes:
                continue
            
            storage_url = await self.store_image(
                image_bytes=image_bytes,
                workflow_id=workflow_id,
                original_url=image_url,
            )
            
            if storage_url:
                research_images.append(
                    ResearchImage(
                        url=image_url,
                        storage_path=f"research_images/{workflow_id}/",
                        storage_url=storage_url,
                        title=result.get("title", ""),
                        source_url=result.get("context_url", result.get("source", "")),
                    )
                )
        
        logger.info(f"Successfully stored {len(research_images)} images")
        return research_images


_google_search_service: Optional[GoogleSearchService] = None


def get_google_search_service() -> GoogleSearchService:
    """Get singleton Google Search service instance."""
    global _google_search_service
    if _google_search_service is None:
        _google_search_service = GoogleSearchService()
    return _google_search_service
