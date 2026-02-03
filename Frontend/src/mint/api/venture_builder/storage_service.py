"""
Supabase Storage utility for VB profile file uploads.
"""

import os
import uuid
import logging
from typing import Optional, Union

from ..system.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class VBStorageService:
    """Service for uploading and managing VB profile files in Supabase Storage."""

    def __init__(self, bucket_name: str = "venture-builder-profiles"):
        """
        Initialize Supabase Storage client for VB profiles.

        Args:
            bucket_name: Name of the storage bucket (default: "venture-builder-profiles")
        """
        self.supabase = get_supabase_client(use_service_role=True).client
        self.bucket_name = bucket_name

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists, create it if it doesn't."""
        try:
            # List all buckets to check if ours exists
            buckets = self.supabase.storage.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]

            if self.bucket_name not in bucket_names:
                # Create bucket with public access for profile pictures
                self.supabase.storage.create_bucket(
                    self.bucket_name,
                    options={"public": True}  # Make bucket public for easy image access
                )
                logger.info(f"Created storage bucket: {self.bucket_name}")
        except Exception as e:
            # If bucket already exists, this is fine
            logger.warning(f"Bucket check/creation: {str(e)}")

    def upload_profile_picture(
        self, file: Union[bytes, bytearray], filename: str, user_id: str
    ) -> str:
        """
        Upload a VB profile picture to Supabase Storage.

        Args:
            file: The file bytes to upload
            filename: Original filename
            user_id: User ID for organizing files

        Returns:
            The public URL of the uploaded file

        Raises:
            RuntimeError: If upload fails
        """
        # Generate a unique file path
        file_extension = os.path.splitext(filename)[1].lower()
        file_path = f"vb-profiles/{user_id}/{uuid.uuid4()}{file_extension}"

        try:
            # Get content type based on file extension
            content_type = self._get_content_type(file_extension)

            # Upload to Supabase Storage
            self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file,
                file_options={
                    "content-type": content_type,
                    "upsert": "true"  # Overwrite if exists
                }
            )

            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)

            logger.info(f"Uploaded VB profile picture to: {file_path}")
            return public_url

        except Exception as e:
            logger.error(f"Failed to upload VB profile picture to Supabase Storage: {str(e)}")
            raise RuntimeError(f"Failed to upload file to Supabase Storage: {str(e)}")

    def delete_file(self, file_url: str) -> bool:
        """
        Delete a file from Supabase Storage.

        Args:
            file_url: The URL of the file to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Extract file path from URL
            file_path = self._extract_file_path_from_url(file_url)
            if not file_path:
                logger.warning(f"Could not extract file path from URL: {file_url}")
                return False

            # Delete from Supabase Storage
            self.supabase.storage.from_(self.bucket_name).remove([file_path])
            logger.info(f"Deleted VB profile file: {file_path}")
            return True

        except Exception as e:
            # Log the error but don't raise - deletion failures shouldn't block operations
            logger.warning(f"Failed to delete VB profile file: {str(e)}")
            return False

    def _extract_file_path_from_url(self, file_url: str) -> Optional[str]:
        """
        Extract file path from Supabase Storage URL.

        URL format: https://{project}.supabase.co/storage/v1/object/public/{bucket}/{path}
        """
        try:
            # Split by bucket name to get the path
            if f"/object/public/{self.bucket_name}/" in file_url:
                parts = file_url.split(f"/object/public/{self.bucket_name}/")
                if len(parts) == 2:
                    return parts[1]
            return None
        except Exception as e:
            logger.error(f"Error extracting file path from URL: {str(e)}")
            return None

    def _get_content_type(self, file_extension: str) -> str:
        """Get MIME type based on file extension."""
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return content_types.get(file_extension, "application/octet-stream")

    def get_file_url(self, file_path: str) -> str:
        """
        Get the public URL for a file.

        Args:
            file_path: The path of the file in the bucket

        Returns:
            The public URL of the file
        """
        return self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)


# Singleton instance
_vb_storage_service: Optional[VBStorageService] = None


def get_vb_storage_service() -> VBStorageService:
    """Get or create the singleton VBStorageService instance."""
    global _vb_storage_service
    if _vb_storage_service is None:
        _vb_storage_service = VBStorageService()
    return _vb_storage_service
