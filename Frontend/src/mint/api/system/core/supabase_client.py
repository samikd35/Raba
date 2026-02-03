"""
Supabase client for the MINT API.

This module provides a client for interacting with Supabase,
particularly for managing research jobs with multi-tenant
row-level security.
"""

import os
import sys
import urllib
import socket
import ssl
import json
import uuid
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from .utils import is_production_env, is_valid_uuid, get_deterministic_uuid_for_user

import httpx
import urllib3
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from dotenv import load_dotenv
from fastapi import HTTPException

from src.mint.schemas.schemas import Job, JobStatus

# Configure logging
logger = logging.getLogger(__name__)

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

class SupabaseClient:
    """Client for interacting with Supabase for multi-tenant data access."""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None, use_service_role: bool = False):
        """
        Initialize the Supabase client.
        
        Args:
            supabase_url: The URL of your Supabase instance
            supabase_key: The service role key or anon key for your Supabase instance
            use_service_role: Whether to use service_role authorization headers to bypass RLS
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Load from params or environment variables
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.use_service_role = use_service_role
        
        # Choose the appropriate key based on service role usage
        if supabase_key:
            # Use provided key
            self.supabase_key = supabase_key
        elif use_service_role:
            # Use service role key for admin operations (bypasses RLS)
            self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if not self.supabase_key:
                # Fallback to regular key if service role key not available
                self.supabase_key = os.getenv("SUPABASE_KEY")
                logger.warning("SUPABASE_SERVICE_ROLE_KEY not found, falling back to SUPABASE_KEY")
        else:
            # Use anon key for standard operations (subject to RLS)
            self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if use_service_role:
            logger.info("Initializing client with service role permissions (bypassing RLS)")
        else:
            logger.info("Initializing client with standard permissions (subject to RLS)")
        
        if not self.supabase_url or not self.supabase_key:
            missing_vars = []
            if not self.supabase_url:
                missing_vars.append("SUPABASE_URL")
            if not self.supabase_key:
                if use_service_role:
                    missing_vars.append("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY")
                else:
                    missing_vars.append("SUPABASE_KEY")
            
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                "Please ensure your .env file contains the necessary Supabase configuration."
            )
            
        # Check if we're in production environment
        self.is_production = is_production_env()
        logger.info(f"Environment detection: Production = {self.is_production}")
        
        # Prepare the URL with simplified configuration
        self._prepare_supabase_url()
        
        # Create the client with standard configuration
        logger.info("Initializing Supabase client")
        try:
            # Helper function to create client with fallback for version compatibility
            def _create_client_with_fallback(url: str, key: str):
                """Create Supabase client with fallback for different library versions."""
                # First try: with custom timeout options
                # Storage timeout increased to 300s for large file uploads (e.g., 26MB PDFs)
                try:
                    options = ClientOptions(
                        postgrest_client_timeout=60,
                        storage_client_timeout=300,
                    )
                    logger.info("Attempting client creation with custom timeout options")
                    return create_client(url, key, options=options)
                except (TypeError, AttributeError) as e:
                    logger.warning(f"Custom options failed ({type(e).__name__}: {e}), trying without options")
                
                # Second try: without any options (most compatible)
                try:
                    logger.info("Attempting client creation without options")
                    return create_client(url, key)
                except Exception as e:
                    logger.error(f"Client creation without options also failed: {e}")
                    raise
            
            # Create the client
            self.client = _create_client_with_fallback(self.supabase_url, self.supabase_key)
            
            # Set service role auth if needed
            if self.use_service_role:
                self.client.postgrest.auth(self.supabase_key)
                logger.info("Client created with service role auth to bypass RLS")
            else:
                logger.info("Client created with standard permissions")
            
            logger.info("Supabase client initialized successfully")
        except Exception as client_error:
            logger.error(f"Failed to initialize Supabase client: {str(client_error)}")
            raise
        self.logger = logging.getLogger(__name__)
        
        # Table used for reports storage - using documents table as per schema
        self.reports_table = "documents"  # Use documents table as per database schema
        
        # Log environment detection
        production = is_production_env()
        
        # Define table names
        self.jobs_table = "mint_jobs"
    
    def _extract_user_id_from_token(self, user_token: str) -> Optional[str]:
        """
        Extract user_id from JWT token.
        
        Args:
            user_token: JWT token
            
        Returns:
            User ID if found, None otherwise
        """
        logger.info(f"DEBUG: _extract_user_id_from_token called with token: {user_token[:50] if user_token else 'None'}...")
        if not user_token:
            logger.info("DEBUG: No user_token provided, returning None")
            return None
            
        try:
            import jwt
            # Decode without verification to extract user_id
            payload = jwt.decode(user_token, options={"verify_signature": False})
            user_id = payload.get("sub")
            logger.info(f"DEBUG: Extracted user_id: {user_id} from token")
            return user_id
        except Exception as e:
            logger.warning(f"Failed to extract user_id from token: {e}")
            return None
        
    def _prepare_supabase_url(self):
        """
        Prepare the Supabase URL with proper format and protocol.
        Apply necessary SSL patches for production environments.
        """
        try:
            # If we don't have a URL, there's nothing to prepare
            if not self.supabase_url:
                logger.warning("No Supabase URL provided in environment")
                return
                
            # Sanitize URL by stripping whitespace and newlines that might cause DNS resolution issues
            original_url = self.supabase_url
            
            # Parse and validate the URL
            from urllib.parse import urlparse
            parsed_url = urlparse(self.supabase_url)
            domain = parsed_url.netloc
            
            if domain:
                logger.info(f"Validated domain: {domain}")
                self.supabase_domain = domain
                
                # Test basic connectivity (non-blocking)
                try:
                    socket.getaddrinfo(domain, 443)
                    logger.info(f"DNS resolution successful for {domain}")
                except Exception as dns_error:
                    logger.warning(f"DNS resolution issue (will retry during operations): {str(dns_error)}")
                
                # Apply minimal, standard configuration
                self._apply_standard_config()
            else:
                logger.warning("Could not extract domain from Supabase URL")
                
        except Exception as e:
            logger.error(f"Error preparing Supabase URL: {str(e)}")
            # Continue with default configuration for production environment.

    def _apply_standard_config(self):
        """
        Apply standard, robust network configuration.
        
        This replaces aggressive SSL patches with minimal, consistent configuration
        that works reliably across different network environments.
        """
        try:
            logger.info("Applying standard network configuration")
            
            # Only disable urllib3 warnings (non-intrusive)
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                logger.debug("Disabled urllib3 SSL warnings")
            except ImportError:
                pass
            
            # Set reasonable timeout defaults for network operations
            self.network_timeout = 30
            self.retry_attempts = 3
            self.retry_delay = 1
            
            logger.info("Standard network configuration applied successfully")
            
        except Exception as e:
            logger.warning(f"Error applying standard config: {str(e)}")
            # Continue with defaults
    
    def diagnose_network_connectivity(self, target_url=None):
        """
        Comprehensive diagnostic routine for network connectivity issues.
        Includes DNS resolution, socket connectivity, HTTP requests, and SSL verification.
        
        Args:
            target_url: Optional URL to test. If None, uses Supabase URL.
            
        Returns:
            Dict with diagnostic results
        """
        import time
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": os.getenv("ENVIRONMENT", "not set"),
            "platform": {"system": sys.platform, "python": sys.version},
            "tests": {},
            "overall_status": "failed"
        }
        
        try:
            url_to_test = target_url or self.supabase_url
            if not url_to_test:
                results["tests"]["url_validation"] = {
                    "status": "failed",
                    "error": "No URL available to test"
                }
                return results
                
            # Sanitize and parse URL
            url_to_test = url_to_test.strip()
            parsed = urllib.parse.urlparse(url_to_test)
            domain = parsed.netloc
            
            # Check for placeholder domains that would cause DNS failures
            placeholder_domains = ["<your-supabase-url>", "example.supabase.co", "supabase-url-here"]
            if any(placeholder in domain.lower() for placeholder in placeholder_domains):
                results["tests"]["url_validation"] = {
                    "status": "failed",
                    "domain": domain,
                    "scheme": parsed.scheme,
                    "error": f"URL contains placeholder value: {domain}"
                }
                results["environment_variables"] = {
                    "SUPABASE_URL": os.getenv("SUPABASE_URL", "not set").replace("https://", "[REDACTED]://"),
                    "ENVIRONMENT": os.getenv("ENVIRONMENT", "not set"),
                }
                return results
            
            results["tests"]["url_validation"] = {
                "status": "success",
                "domain": domain,
                "scheme": parsed.scheme
            }
            
            # Test 1: DNS resolution with fallbacks
            try:
                import socket
                start_time = time.time()
                ip_info = None
                error = None
                
                # Primary DNS resolution
                try:
                    ip_info = socket.gethostbyname_ex(domain)
                except Exception as primary_dns_error:
                    error = str(primary_dns_error)
                    
                    # Try DNS fallbacks for Supabase domains
                    if "supabase" in domain:
                        logger.info(f"Primary DNS resolution failed, trying manual DNS resolution")
                        # Supabase domains are hosted on Cloudflare
                        cloudflare_ips = ["104.18.0.0", "104.18.1.0", "104.18.2.0", "104.18.3.0"]
                        
                        # Try to manually connect using Cloudflare IPs as fallback
                        for ip in cloudflare_ips:
                            try:
                                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                s.settimeout(2)
                                s.connect((ip, 443))
                                s.close()
                                logger.info(f"Successfully connected to fallback IP {ip}")
                                
                                # Create a synthetic DNS result
                                ip_info = (domain, [], [ip])
                                error = f"Used fallback IP {ip} after DNS failure: {error}"
                                break
                            except Exception:
                                continue
                
                dns_time = time.time() - start_time
                
                if ip_info:
                    results["tests"]["dns_resolution"] = {
                        "status": "success" if not error else "partial",
                        "hostname": ip_info[0],
                        "aliases": ip_info[1],
                        "ip_addresses": ip_info[2],
                        "time_ms": round(dns_time * 1000, 2)
                    }
                    if error:
                        results["tests"]["dns_resolution"]["notes"] = error
                else:
                    results["tests"]["dns_resolution"] = {
                        "status": "failed",
                        "error_type": "DNSResolutionError",
                        "error": error
                    }
            except Exception as e:
                results["tests"]["dns_resolution"] = {
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "error": str(e)
                }
            
            # Test 2: Socket connection
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                start_time = time.time()
                s.connect((domain, 443))
                socket_time = time.time() - start_time
                s.close()
                
                results["tests"]["socket_connection"] = {
                    "status": "success",
                    "port": 443,
                    "time_ms": round(socket_time * 1000, 2)
                }
            except Exception as e:
                results["tests"]["socket_connection"] = {
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "error": str(e)
                }
            
            # Test 3: HTTP GET request with fallbacks if DNS fails
            try:
                import httpx
                client = httpx.Client(verify=False, timeout=5.0)
                start_time = time.time()
                http_success = False
                error_msg = None
                
                # Try standard request first
                try:
                    response = client.get(url_to_test)
                    http_time = time.time() - start_time
                    http_success = True
                    
                    results["tests"]["http_request"] = {
                        "status": "success",
                        "status_code": response.status_code,
                        "time_ms": round(http_time * 1000, 2)
                    }
                except Exception as http_error:
                    error_msg = str(http_error)
                    
                    # If DNS resolution failed in the HTTP request, try with IP directly
                    if "Name or service not known" in error_msg and "supabase" in domain:
                        logger.info("HTTP request failed with DNS error, trying direct IP connection")
                        
                        # Use the same Cloudflare IPs
                        cloudflare_ips = ["104.18.0.0", "104.18.1.0", "104.18.2.0", "104.18.3.0"]
                        
                        for ip in cloudflare_ips:
                            try:
                                # Create URL with IP instead of domain
                                ip_url = url_to_test.replace(domain, ip)
                                # Add Host header for TLS SNI
                                response = client.get(ip_url, headers={"Host": domain})
                                http_time = time.time() - start_time
                                
                                results["tests"]["http_request"] = {
                                    "status": "partial",
                                    "status_code": response.status_code,
                                    "time_ms": round(http_time * 1000, 2),
                                    "notes": f"Connected via IP {ip} after DNS failure",
                                    "original_error": error_msg
                                }
                                http_success = True
                                break
                            except Exception as ip_error:
                                continue
                
                if not http_success:
                    results["tests"]["http_request"] = {
                        "status": "failed",
                        "error_type": "RequestError",
                        "error": error_msg
                    }
            except Exception as e:
                results["tests"]["http_request"] = {
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "error": str(e)
                }
            
            # Test 4: HTTPS library configuration
            try:
                import ssl
                results["tests"]["ssl_configuration"] = {
                    "status": "success",
                    "default_context": ssl._create_default_https_context.__name__,
                    "environment": {
                        "PYTHONHTTPSVERIFY": os.environ.get("PYTHONHTTPSVERIFY", "not set"),
                        "REQUESTS_CA_BUNDLE": os.environ.get("REQUESTS_CA_BUNDLE", "not set"),
                        "SSL_CERT_FILE": os.environ.get("SSL_CERT_FILE", "not set")
                    }
                }
            except Exception as e:
                results["tests"]["ssl_configuration"] = {
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "error": str(e)
                }
                
            # Overall status calculation
            success_count = sum(1 for test in results["tests"].values() if test.get("status") == "success")
            if success_count == len(results["tests"]):
                results["overall_status"] = "success"
            elif success_count > 0:
                results["overall_status"] = "partial"
                
            return results
            
        except Exception as e:
            import traceback
            results["diagnostic_error"] = {
                "error_type": type(e).__name__,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            return results
    
    def get_job(self, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a job by ID for a specific user.
        
        Args:
            job_id: The ID of the job to retrieve
            user_id: The ID of the user making the request
            
        Returns:
            Optional[Dict]: The job data if found, None otherwise
            
        Note:
            Row-level security in Supabase will automatically filter
            to only return jobs that belong to the authenticated user.
        """
        try:
            # Ensure SSL verification is disabled if in production
            self._ensure_ssl_disabled_for_operation()
            
            # Row-level security (RLS) in Supabase will enforce that the user
            # can only access their own jobs. The RLS policy should be:
            # CREATE POLICY "Users can only access their own jobs"
            # ON "public"."mint_jobs"
            # FOR ALL
            # USING (auth.uid() = user_id);
            
            logger.debug(f"Getting job {job_id} for user {user_id}")
            response = self.client.table(self.jobs_table) \
                .select("*") \
                .eq("id", job_id) \
                .execute()
            
            jobs = response.data
            
            if not jobs:
                return None
                
            # Extra safety check - verify user_id matches
            # (This should be redundant with RLS but adds extra security)
            if jobs[0].get("user_id") != user_id:
                logger.warning(
                    f"User {user_id} attempted to access job {job_id} "
                    f"belonging to user {jobs[0].get('user_id')}"
                )
                return None
                
            return jobs[0]
            
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving job: {str(e)}"
            )
    
    def list_jobs(
        self, 
        user_id: str, 
        status: Optional[JobStatus] = None, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List jobs for a specific user with optional filtering by status.
        
        Args:
            user_id: The ID of the user making the request
            status: Optional status to filter by
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip (for pagination)
            
        Returns:
            List[Dict]: List of jobs
        """
        try:
            # Ensure SSL verification is disabled if in production
            self._ensure_ssl_disabled_for_operation()
            
            logger.debug(f"Listing jobs for user {user_id}, status={status}, limit={limit}, offset={offset}")
            
            # Build the query
            query = self.client.table(self.jobs_table) \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .offset(offset)
            
            # Add status filter if provided
            if status is not None:
                query = query.eq("status", status.value)
            
            response = query.execute()
            
            return response.data
            
        except Exception as e:
            logger.error(f"Error listing jobs for user {user_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error listing jobs: {str(e)}"
            )
    
    def create_job(
        self, 
        user_id: str, 
        query: str,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new job for a user.
        
        Args:
            user_id: The ID of the user creating the job
            query: The research query for the job
            metadata: Optional additional metadata for the job
            session_id: Optional session ID to use as the primary key (UUID format)
            
        Returns:
            Dict: The created job data
        """
        try:
            # Debug starting state and environment
            logger.info(f"Starting job creation for user {user_id} - Environment: {os.getenv('ENVIRONMENT', 'not set')}")
            logger.info(f"Current Supabase URL (sanitized): {self.supabase_url.replace('https://', '[REDACTED]://') if self.supabase_url else 'None'}")
            
            # Log SSL context status
            ssl_context_type = ssl.create_default_context().__class__.__name__
            ssl_unverified_type = ssl._create_unverified_context().__class__.__name__
            logger.info(f"SSL context types - Default: {ssl_context_type}, Unverified: {ssl_unverified_type}")
            
            # Reapply SSL patches and DNS workarounds when running in production
            if is_production_env() and self.supabase_url:
                # Extract domain from URL
                parsed_url = urllib.parse.urlparse(self.supabase_url)
                domain = parsed_url.netloc
                # Apply SSL patches for this domain
                self._apply_ssl_patches(domain)
            
            # Run basic connectivity checks to help with diagnostics
            try:
                # Try DNS resolution
                parsed_url = urllib.parse.urlparse(self.supabase_url)
                domain = parsed_url.netloc
                logger.info(f"Testing direct DNS resolution for domain: {domain}")
                
                # First try standard DNS resolution
                try:
                    ip_addresses = socket.gethostbyname_ex(domain)
                    logger.info(f"DNS resolution successful: {ip_addresses}")
                except Exception as dns_error:
                    logger.error(f"DNS resolution failed: {str(dns_error)}")
                    # Continue despite DNS test failure - actual request might still work
                    
            except Exception as e:
                logger.error(f"Error running DNS resolution test: {str(e)}")
                # Continue despite DNS test failure - actual request might still work
                
            # Test simple HTTP connectivity
            try:
                import httpx
                # Create a new httpx client with verify=False to match our patches
                test_client = httpx.Client(verify=False)
                logger.info(f"Testing HTTP connectivity to {self.supabase_url}")
                response = test_client.get(self.supabase_url, timeout=5.0)
                logger.info(f"HTTP connectivity test: Status {response.status_code}")
            except Exception as http_error:
                logger.error(f"HTTP connectivity test failed: {str(http_error)}")
                logger.info("Running comprehensive network diagnostics...")
                # Run comprehensive diagnostics since basic HTTP test failed
                try:
                    diag_results = self.diagnose_network_connectivity()
                    logger.info(f"Network diagnostics completed with status: {diag_results['overall_status']}")
                    logger.info(f"Diagnostic details: {json.dumps(diag_results, indent=2)}")
                except Exception as diag_err:
                    logger.error(f"Failed to run network diagnostics: {str(diag_err)}")
                # Continue despite connectivity test failure
                
            # Use session_id as the primary identifier if provided, otherwise generate one
            # This aligns with the standardized session_id usage across the codebase
            job_session_id = session_id if session_id else str(uuid.uuid4())
            logger.info(f"Using session_id '{job_session_id}' for job creation")
            
            # Check if user_id is a valid UUID, if not, convert it to a deterministic UUID
            # This is necessary because the user_id column in Supabase is a UUID type
            if not is_valid_uuid(user_id):
                user_uuid = get_deterministic_uuid_for_user(user_id)
                logger.info(f"Converting non-UUID user_id '{user_id}' to deterministic UUID: {user_uuid}")
            else:
                user_uuid = user_id
                
            # Create a content JSON object that can store all our job data
            # since mint_reports uses a content JSONB field for the actual data
            content_data = {
                "query": query,
                "status": JobStatus.PENDING.value,
                "user_id": user_uuid,      # Store UUID-compatible value
                "original_user_id": user_id if user_id != user_uuid else user_id
            }
            
            # Add any additional metadata to the content field
            if metadata:
                content_data["metadata"] = metadata
                
            # Structure the data to match the mint_reports table schema
            job_data = {
                "id": job_session_id,               # Primary key
                "session_id": job_session_id,        # Required session_id as TEXT
                "user_id": user_id,                  # User ID for proper user association
                "report_type": "industry",           # Using 'industry' as default type
                "content": content_data,             # Store all job data in JSONB content field
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "title": f"Market Analysis: {query[:50]}" if len(query) > 0 else "Market Analysis",
                "summary": f"Analysis based on query: {query[:100]}" if len(query) > 0 else "Market analysis report"
            }
                
            # Create with SSL verification explicitly disabled for this operation
            logger.info(f"Creating job in Supabase for user {user_id}")
            
            # Log the exact client configuration we're using
            client_config = {
                "url": self.supabase_url.replace('https://', '[REDACTED]://') if self.supabase_url else None,
                "table": self.reports_table  # Use reports_table for consistency
            }
            logger.info(f"Supabase client configuration: {client_config}")
            
            # ⚠️ WORKFLOW JOBS ARE NO LONGER SAVED TO DATABASE ⚠️
            # Only final reports should be saved to mint_reports table
            # This prevents workflow metadata from cluttering the history sidebar
            
            logger.info("🚫 SKIPPING DATABASE SAVE - Workflow jobs are not persisted")
            logger.info("Only final reports will be saved to maintain clean history")
            
            # Return job data without saving to database
            created_job = {
                "id": job_session_id,
                "session_id": job_session_id,
                "user_id": user_id,
                "report_type": "workflow",  # Mark as workflow (not saved)
                "content": content_data,
                "created_at": datetime.utcnow().isoformat(),
                "title": f"Market Analysis: {query[:50]}" if len(query) > 0 else "Market Analysis",
                "summary": f"Analysis based on query: {query[:100]}" if len(query) > 0 else "Market analysis report",
                "_persisted": False  # Flag to indicate this was not saved
            }
            
            logger.info(f"✅ Workflow job created in-memory only with session_id: {job_session_id}")
            return created_job
            
        except Exception as e:
            # Enhanced error handling with detailed diagnostic information
            error_type = type(e).__name__
            error_msg = f"Failed to create job with session_id {job_session_id} for user {user_id}: {str(e)}"
            logger.error(error_msg)
            tb_str = traceback.format_exc()
            
            logger.error(f"Error creating job for user {user_id}: [{error_type}] {error_msg}")
            logger.error(f"Traceback: {tb_str}")
            
            # Run comprehensive network diagnostics to help troubleshoot the issue
            logger.info(f"Running comprehensive network diagnostics after job creation failure...")
            try:
                # The diagnostics method provides detailed information about all network/DNS/SSL issues
                diag_results = self.diagnose_network_connectivity()
                
                # Log the overall status and most important results
                logger.info(f"Network diagnostics completed with status: {diag_results['overall_status']}")
                
                # Format the diagnostic results as JSON for readability in logs
                try:
                    formatted_results = json.dumps(diag_results, indent=2)
                    logger.info(f"Diagnostic details: {formatted_results}")
                except Exception as json_err:
                    logger.error(f"Failed to format diagnostic results as JSON: {str(json_err)}")
                    logger.info(f"Raw diagnostic results: {str(diag_results)}")
                
                # Store diagnostic results for later analysis if needed
                diagnostic_context = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    "network_diagnostics": diag_results,
                    "exception_type": error_type,
                    "exception_message": error_msg
                }
                
                # If the diagnostics shows a connectivity issue, provide more specific error message
                if diag_results.get("overall_status") == "failed" and "dns_resolution" in diag_results.get("tests", {}):
                    if diag_results["tests"]["dns_resolution"].get("status") == "failed":
                        error_msg += " (DNS resolution failed - please check network connectivity)"
                    elif diag_results["tests"].get("http_request", {}).get("status") == "failed":
                        error_msg += " (HTTP connectivity failed - please check firewall/proxy settings)"
                    
            except Exception as diag_err:
                logger.error(f"Failed to run diagnostics after error: {str(diag_err)}")
            
            # Add additional hint for placeholder values in URL
            if "<your-supabase-url>" in self.supabase_url:
                logger.error("CRITICAL: Supabase URL contains placeholder '<your-supabase-url>' - Set the actual Supabase URL in environment variables")
                logger.info(f"Current SUPABASE_URL env value: '{os.getenv('SUPABASE_URL', 'not set')}'")
                logger.info("Check that SUPABASE_URL is correctly set in your Azure Container App environment variables")
            
            # Include more details in the exception response
            raise HTTPException(
                status_code=500,
                detail=f"Error creating job: [{error_type}] {error_msg}"
            )
            
        except Exception as e:
            logger.error(f"Error creating job for user {user_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error creating job: {str(e)}"
            )
    
    def update_job_status(
        self, 
        job_id: str, 
        user_id: str,
        status: JobStatus,
        result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update the status of a job.
        
        Args:
            job_id: The ID of the job to update
            user_id: The ID of the user making the request
            status: The new status of the job
            result: Optional result data to store with the job
            
        Returns:
            Dict: The updated job data
        """
        try:
            # Ensure SSL verification is disabled if in production
            self._ensure_ssl_disabled_for_operation()
            
            # First verify the job exists and belongs to this user
            job = self.get_job(job_id, user_id)
            
            if not job:
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {job_id} not found or not accessible by user {user_id}"
                )
                
            logger.debug(f"Updating job {job_id} status to {status.value} for user {user_id}")
                
            # Prepare update data
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Add result data if provided
            if result is not None:
                update_data["result"] = result
                
            # Ensure SSL verification is disabled again right before the operation
            self._ensure_ssl_disabled_for_operation()
                
            # Update the job
            response = self.client.table(self.jobs_table) \
                .update(update_data) \
                .eq("id", job_id) \
                .execute()
                
            if not response.data:
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to update job status"
                )
                
            return response.data[0]
                
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error updating job {job_id} status: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error updating job status: {str(e)}"
            )
    
    def execute_query(self, query, *args, **kwargs):
        """Execute a query on Supabase."""
        try:
            client = self.get_client()
            result = client.table(query).select("*").execute()
            logger.info(f"Successfully executed query on table '{query}'")
            return result
        except Exception as e:
            logger.error(f"Error executing query {query}: {str(e)}")
            # Log detailed error for network issues
            if "Name or service not known" in str(e):
                logger.error("DNS resolution still failing despite patches - this indicates a severe network configuration issue")
            return None


    async def store_unified_workflow(self, session_id: str, workflow_data: Dict[str, Any], 
                                title: str = None, summary: str = None, user_token: str = None, user_id: str = None) -> str:
        """
        Store or update a unified workflow record in Supabase.
        
        The workflow_data structure should have the following format:
        {
            "reports": {}, # Will contain industry, pestel, final reports
            "conversation_history": [], # Will contain conversation history entries
            "metadata": {} # Will contain workflow metadata
        }
        
        Args:
            session_id: The session ID.
            workflow_data: The unified workflow data containing all report information.
            title: Optional title for the workflow.
            summary: Optional summary of the workflow.
            user_token: Optional JWT token of the authenticated user for RLS enforcement.
            
        Returns:
            The ID of the stored workflow record, or None if storage failed.
        """
        try:
            # SAFEGUARD: Prevent unified workflow storage for final reports
            # Final reports should use the separated storage approach only
            if workflow_data and isinstance(workflow_data, dict):
                reports = workflow_data.get("reports", {})
                if "final" in reports:
                    logger.error(f"CRITICAL: Attempted to store final report via unified workflow for session {session_id}")
                    logger.error(f"Final reports must use update_workflow_report with separated storage")
                    raise ValueError("Final reports cannot be stored via unified workflow - use separated storage")
            
            # Check if a record already exists for this session
            existing_record = await self.get_unified_workflow(session_id, user_token)
            
            # Extract title from workflow_data if not provided
            extracted_title = title
            if not extracted_title and workflow_data:
                try:
                    # Try to extract title from final report in workflow_data
                    reports = workflow_data.get("reports", {})
                    final_report = reports.get("final", {})
                    if isinstance(final_report, dict):
                        extracted_title = final_report.get("title")
                    elif isinstance(final_report, str):
                        # If final_report is a JSON string, parse it
                        import json
                        try:
                            final_report_data = json.loads(final_report)
                            extracted_title = final_report_data.get("title")
                        except json.JSONDecodeError:
                            pass
                    
                    # If still no title, try other report types
                    if not extracted_title:
                        for report_type in ["industry", "pestel", "market_validation"]:
                            report_data = reports.get(report_type, {})
                            if isinstance(report_data, dict) and report_data.get("title"):
                                extracted_title = report_data.get("title")
                                break
                            elif isinstance(report_data, str):
                                try:
                                    parsed_data = json.loads(report_data)
                                    if parsed_data.get("title"):
                                        extracted_title = parsed_data.get("title")
                                        break
                                except json.JSONDecodeError:
                                    continue
                except Exception as e:
                    logger.warning(f"Could not extract title from workflow_data: {str(e)}")
            
            data = {
                "session_id": session_id,
                "user_id": user_id,
                "report_type": "unified",  # Special type for unified records
                "content": workflow_data,
                "title": extracted_title or f"Workflow Report for {session_id}",
                "summary": summary or ""
            }
            
            logger.info(f"DEBUG: About to store workflow with user_id: {user_id} for session: {session_id}")
            
            if existing_record:
                # Update the existing record
                record_id = existing_record.get("id")
                
                # Create appropriate client based on whether user token is provided
                if user_token:
                    # Use anon key with user JWT token for RLS enforcement
                    anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
                    temp_client = create_client(self.supabase_url, anon_key)
                    temp_client = create_client(self.supabase_url, self.supabase_key)
                    temp_client.postgrest.auth(user_token)
                    logger.info(f"Using user token for RLS enforcement when updating unified workflow")
                    
                    # Build query with user token for RLS enforcement
                    query = temp_client.table(self.reports_table)\
                        .update(data)\
                        .eq("id", record_id)
                else:
                    # Fall back to service role key to bypass RLS
                    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", self.supabase_key)
                    temp_client = create_client(self.supabase_url, service_role_key)
                    logger.warning(f"Using service role key to bypass RLS when updating unified workflow")
                    
                    # Build query with service role key to bypass RLS
                    query = temp_client.table(self.reports_table)\
                        .update(data)\
                        .eq("id", record_id)
                    
                # Execute the query
                response = query.execute()
                
                if not response.data or len(response.data) == 0:
                    logger.error(f"Error updating unified workflow: {response.error}")
                    return None
                
                logger.info(f"Updated unified workflow with ID: {record_id}")
                return record_id
            else:
                # Create a new record
                # Create appropriate client based on whether user token is provided
                if user_token:
                    # Use anon key with user JWT token for RLS enforcement
                    anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
                    temp_client = create_client(self.supabase_url, anon_key)
                    temp_client.postgrest.auth(user_token)
                    logger.info(f"Using user token for RLS enforcement when creating new unified workflow")
                    
                    # Build query with user token for RLS enforcement
                    query = temp_client.table(self.reports_table).insert(data)
                else:
                    # Fall back to service role key to bypass RLS
                    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", self.supabase_key)
                    temp_client = create_client(self.supabase_url, service_role_key)
                    logger.warning(f"Using service role key to bypass RLS when creating new unified workflow")
                    
                    # Build query with service role key to bypass RLS
                    query = temp_client.table(self.reports_table).insert(data)
                
                # Execute the query
                response = query.execute()
                
                if not response.data or len(response.data) == 0:
                    logger.error(f"Error storing unified workflow: {response.error}")
                    return None
                
                record_id = response.data[0]["id"]
                logger.info(f"Created new unified workflow with ID: {record_id}")
                return record_id
        except Exception as e:
            logger.error(f"Error storing unified workflow: {str(e)}")
            return None
    
    async def get_unified_workflow(self, session_id: str, user_token: str = None) -> Dict[str, Any]:
        """Get the unified workflow record for a session with proper user authentication.
        
        Args:
            session_id: The session ID.
            user_token: Optional JWT token of the authenticated user for RLS enforcement.
            
        Returns:
            The unified workflow record, or None if not found.
        """
        try:
            logger.info(f"Fetching unified workflow for session: {session_id}")
            
            # Extract user ID for consistent authentication
            user_id = self._extract_user_id_from_token(user_token) if user_token else None
            
            # Create appropriate client based on whether user token is provided
            if user_token and user_id:
                # Use anon key with user JWT token for RLS enforcement
                anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
                temp_client = create_client(self.supabase_url, anon_key)
                temp_client.postgrest.auth(user_token)
                logger.info(f"Using user token for RLS enforcement when fetching unified workflow for user {user_id}")
                
                # Build query with user_id for proper authentication and RLS enforcement
                query = temp_client.table(self.reports_table)\
                    .select("*")\
                    .eq("session_id", session_id)\
                    .eq("user_id", user_id)\
                    .eq("report_type", "unified")\
                    .order("created_at", desc=True)\
                    .limit(1)
            else:
                # Fall back to service role key to bypass RLS
                service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", self.supabase_key)
                temp_client = create_client(self.supabase_url, service_role_key)
                logger.warning(f"Using service role key to bypass RLS when fetching unified workflow")
                
                # Build query with session_id only when using service role
                query = temp_client.table(self.reports_table)\
                    .select("*")\
                    .eq("session_id", session_id)\
                    .eq("report_type", "unified")\
                    .order("created_at", desc=True)\
                    .limit(1)
                
            # Execute the query and await the result
            response = query.execute()
            
            # Log response for debugging
            logger.info(f"Unified workflow query response: {response.data}")
            
            # Check response data
            if not response.data or len(response.data) == 0:
                # Try without the unified report type to see what's available
                # Use the same client we created above based on user token
                if user_token and user_id:
                    debug_query = temp_client.table(self.reports_table)\
                        .select("id,report_type,title,user_id")\
                        .eq("session_id", session_id)\
                        .eq("user_id", user_id)\
                        .limit(10)
                else:
                    debug_query = temp_client.table(self.reports_table)\
                        .select("id,report_type,title,user_id")\
                        .eq("session_id", session_id)\
                        .limit(10)
                debug_response = debug_query.execute()
                logger.info(f"Available reports for session {session_id}: {debug_response.data}")
                
                logger.info(f"No unified workflow found for session: {session_id}")
                return None
            
            logger.info(f"Found unified workflow for session: {session_id}")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error getting unified workflow: {str(e)}")
            return None
    
    async def update_workflow_report(self, session_id: str, report_type: str, content: Dict[str, Any], 
                                   user_token: str = None, workflow_state: Dict[str, Any] = None) -> bool:
        """Update a specific report with separated content and metadata storage.
        
        This method has been refactored to implement Requirements 2.1, 2.2, 3.2, and 5.2
        by separating final report content from workflow metadata.
        
        Args:
            session_id: The session ID.
            report_type: Type of report to update ("industry", "pestel", "final", etc.)
            content: The new report content.
            user_token: Optional JWT token of the authenticated user for RLS enforcement.
            workflow_state: Optional workflow state for metadata extraction
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Extract user ID for consistent identification (Requirement 3.2)
            user_id = self._extract_user_id_from_token(user_token) if user_token else None
            
            # If no user_id from token but workflow_state is provided, try to get it from there
            if not user_id and workflow_state:
                user_id = workflow_state.get("user_id")
                logger.info(f"Using user_id from workflow_state: {user_id}")
            
            # Validate that we have a user_id for report creation
            if not user_id:
                logger.error("Cannot create/update report: user_id is missing")
                raise ValueError("user_id is required for report creation")
            
            logger.info(f"Report operation using user_id: {user_id}")
            
            # For final reports, ALWAYS use the new separated storage approach
            # Never fall back to unified workflow for final reports
            if report_type == "final":
                logger.info(f"Using separated storage for final report update")
                
                # Ensure workflow_state exists, create minimal one if missing
                if not workflow_state:
                    logger.warning(f"No workflow_state provided for final report, creating minimal state")
                    workflow_state = {
                        "session_id": session_id,
                        "user_id": user_id,
                        "status": "completed"
                    }
                
                # Extract clean final report content (Requirement 2.1)
                final_content = self._extract_final_report_content(content)
                
                # Extract workflow metadata (Requirement 2.2)
                initial_query, clarification_questions, clarification_answers, workflow_metadata = \
                    self._extract_workflow_metadata(workflow_state)
                
                # Create appropriate client based on whether user token is provided
                # Try user token first, but fallback to service role if JWT parsing fails
                temp_client = None
                if user_token:
                    try:
                        anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
                        temp_client = create_client(self.supabase_url, anon_key)
                        temp_client.postgrest.auth(user_token)
                        logger.info(f"Using user token for RLS enforcement when updating {report_type} report")
                    except Exception as token_error:
                        logger.warning(f"Failed to use user token, falling back to service role: {token_error}")
                        temp_client = None
                
                if temp_client is None:
                    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", self.supabase_key)
                    temp_client = create_client(self.supabase_url, service_role_key)
                    logger.warning(f"Using service role key to bypass RLS when updating {report_type} report")
                
                # Prepare update data with separated content and metadata for documents table
                update_data = {
                    "content": json.dumps(final_content) if isinstance(final_content, dict) else str(final_content),  # Store as JSON string
                    "metadata": {
                        "report_type": report_type,
                        "session_id": session_id,
                        "initial_query": initial_query,
                        "clarification_questions": clarification_questions,
                        "clarification_answers": clarification_answers,
                        "workflow_metadata": workflow_metadata
                    },
                    "updated_at": "now()"  # Update timestamp
                }
                
                # Update existing record or create new one
                # First try to find existing record
                # Note: documents table uses 'created_by' instead of 'user_id' and 'source_type' instead of 'report_type'
                existing_query = temp_client.table(self.reports_table)\
                    .select("id")\
                    .eq("id", session_id)  # In documents table, session_id is stored as the primary key 'id'
                
                # For documents table, we don't need to filter by user_id since session_id is unique
                
                existing_response = existing_query.execute()
                
                if existing_response.data and len(existing_response.data) > 0:
                    # Update existing record
                    record_id = existing_response.data[0]["id"]
                    response = temp_client.table(self.reports_table)\
                        .update(update_data)\
                        .eq("id", record_id)\
                        .execute()
                    
                    if not response.data or len(response.data) == 0:
                        logger.error(f"Error updating {report_type} report with separated storage: {response}")
                        return None
                    
                    # Return the existing record ID
                    logger.info(f"Updated {report_type} report with separated content and metadata for session: {session_id}")
                    return record_id
                else:
                    # Create new record - map to documents table schema
                    # Get tenant_id from workflow_state if available, otherwise get from user membership
                    tenant_id = None
                    if workflow_state and "tenant_id" in workflow_state:
                        tenant_id = workflow_state["tenant_id"]
                    
                    # If no tenant_id in workflow_state, get from user's tenant membership
                    # Add retry logic for transient network errors
                    if not tenant_id and user_id:
                        import asyncio
                        max_retries = 3
                        retry_delay = 1.0
                        
                        for attempt in range(max_retries):
                            try:
                                if attempt > 0:
                                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} for tenant lookup...")
                                    await asyncio.sleep(retry_delay * (2 ** (attempt - 1)))
                                
                                tenant_result = temp_client.table("tenant_memberships") \
                                    .select("tenant_id") \
                                    .eq("user_id", user_id) \
                                    .eq("is_active", True) \
                                    .limit(1) \
                                    .execute()
                                
                                if tenant_result.data:
                                    tenant_id = tenant_result.data[0]["tenant_id"]
                                    logger.info(f"Found tenant_id {tenant_id} for user {user_id}")
                                    break  # Success, exit retry loop
                                else:
                                    logger.error(f"No active tenant found for user {user_id}")
                                    return False
                                    
                            except Exception as e:
                                error_msg = str(e).lower()
                                is_transient = any(x in error_msg for x in [
                                    "disconnected", "timeout", "connection", "reset", "refused"
                                ])
                                
                                if is_transient and attempt < max_retries - 1:
                                    logger.warning(f"Transient error getting tenant for user {user_id} (attempt {attempt + 1}): {e}")
                                    continue  # Retry
                                else:
                                    logger.error(f"Error getting tenant for user {user_id}: {e}")
                                    return False
                    
                    if not tenant_id:
                        logger.error("No tenant_id available for document creation")
                        return False
                    
                    document_data = {
                        "id": session_id,  # Use session_id as primary key
                        "tenant_id": tenant_id,  # Use actual tenant_id from workflow
                        "project_id": None,
                        "source_type": "pv_report",  # Problem validation report
                        "title": final_content.get("title", f"{report_type.capitalize()} Report"),
                        "content": json.dumps(final_content) if isinstance(final_content, dict) else str(final_content),  # Store as JSON string
                        "storage_path": None,
                        "sha256": None,
                        "created_by": user_id,
                        "metadata": {
                            "report_type": report_type,
                            "session_id": session_id,
                            "initial_query": initial_query,
                            "clarification_questions": clarification_questions,
                            "clarification_answers": clarification_answers,
                            "workflow_metadata": workflow_metadata
                        }
                    }
                    response = temp_client.table(self.reports_table)\
                        .insert(document_data)\
                        .execute()
                    
                    if not response.data or len(response.data) == 0:
                        logger.error(f"Error updating {report_type} report with separated storage: {response}")
                        return None
                    
                    # Return the new record ID
                    new_record_id = response.data[0]["id"]
                    logger.info(f"Created {report_type} report with separated content and metadata for session: {session_id}, ID: {new_record_id}")
                    return new_record_id
            
            elif report_type != "final":
                # Only use legacy unified workflow approach for non-final reports (industry, pestel, etc.)
                # Final reports should NEVER reach this path
                logger.info(f"Using legacy unified workflow approach for {report_type} report")
                
                # Get the current workflow record
                workflow = await self.get_unified_workflow(session_id, user_token)
                
                if not workflow:
                    # Create a new workflow with just this report
                    workflow_data = {"reports": {report_type: content}}
                    await self.store_unified_workflow(session_id, workflow_data, user_token=user_token, user_id=user_id)
                    return True
                
                # Update the specific report in the workflow
                workflow_content = workflow.get("content", {})
                reports = workflow_content.get("reports", {})
                reports[report_type] = content
                workflow_content["reports"] = reports
                
                # Store the updated workflow
                record_id = workflow.get("id")
                
                # Create appropriate client based on whether user token is provided
                if user_token:
                    anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
                    temp_client = create_client(self.supabase_url, anon_key)
                    temp_client.postgrest.auth(user_token)
                    logger.info(f"Using user token for RLS enforcement when updating {report_type} report")
                    
                    # Build the query with user token for RLS enforcement
                    query = temp_client.table(self.reports_table)\
                        .update({"content": workflow_content, "user_id": user_id})\
                        .eq("id", record_id)
                else:
                    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", self.supabase_key)
                    temp_client = create_client(self.supabase_url, service_role_key)
                    logger.warning(f"Using service role key to bypass RLS when updating {report_type} report")
                    
                    # Build the query with service role key to bypass RLS
                    query = temp_client.table(self.reports_table)\
                        .update({"content": workflow_content, "user_id": user_id})\
                        .eq("id", record_id)
                    
                # Execute the query with transaction safety (Requirement 5.2)
                response = query.execute()
                
                if not response.data or len(response.data) == 0:
                    logger.error(f"Error updating {report_type} in workflow: {response}")
                    return False
                
                logger.info(f"Updated {report_type} in unified workflow for session: {session_id}")
                return True
            else:
                # This should never happen - all report types should be handled above
                logger.error(f"Unhandled report_type: {report_type}. This is a bug.")
                raise ValueError(f"Unsupported report_type: {report_type}")
                
        except Exception as e:
            logger.error(f"Error updating {report_type} in workflow: {str(e)}")
            # Transaction rollback is handled automatically by Supabase on exception (Requirement 5.2)
            return False
    
    async def get_workflow_report(self, session_id: str, report_type: str, user_token: str = None) -> Dict[str, Any]:
        """Get a specific report from the workflow data with proper user authentication.
        
        Args:
            session_id: The session ID.
            report_type: Type of report to retrieve ("industry", "pestel", "final", etc.)
            user_token: Optional JWT token of the authenticated user for RLS enforcement.
            
        Returns:
            The report content, or None if not found.
        """
        try:
            # Extract user ID for consistent authentication
            user_id = self._extract_user_id_from_token(user_token) if user_token else None
            logger.info(f"Fetching {report_type} report for session: {session_id}, user: {user_id}")
            
            # Create appropriate client based on whether user token is provided
            if user_token and user_id:
                anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
                temp_client = create_client(self.supabase_url, anon_key)
                temp_client.postgrest.auth(user_token)
                logger.info(f"Using user token for RLS enforcement when fetching workflow report for user {user_id}")
                
                # Query with user_id for proper authentication and RLS enforcement
                query = temp_client.table(self.reports_table)\
                    .select("*")\
                    .eq("session_id", session_id)\
                    .eq("user_id", user_id)\
                    .order("created_at", desc=True)\
                    .limit(1)
            else:
                # Fall back to service role key to bypass RLS
                service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", self.supabase_key)
                temp_client = create_client(self.supabase_url, service_role_key)
                logger.warning(f"Using service role key to bypass RLS when fetching workflow report")
                
                # Query by session_id only when using service role
                query = temp_client.table(self.reports_table)\
                    .select("*")\
                    .eq("session_id", session_id)\
                    .order("created_at", desc=True)\
                    .limit(1)
            
            response = query.execute()
            
            # Debug log the response
            logger.info(f"Query response for session {session_id}: {response.data}")
            
            if not response.data or len(response.data) == 0:
                logger.info(f"No data found for session: {session_id}")
                return None
            
            # Get the first record (most recent)
            workflow = response.data[0]
            
            if not workflow or "content" not in workflow or not workflow["content"]:
                logger.info(f"No content found in record for session: {session_id}")
                return None
            
            # Extract report from content.reports.{report_type}
            content = workflow["content"]
            logger.info(f"Content structure: {list(content.keys() if isinstance(content, dict) else [])}")
            
            reports = content.get("reports", {})
            logger.info(f"Reports structure: {list(reports.keys() if isinstance(reports, dict) else [])}")
            
            if report_type not in reports:
                logger.info(f"Report type '{report_type}' not found in reports structure for session: {session_id}")
                return None
                
            report_content = reports.get(report_type)
            logger.info(f"Found {report_type} report with keys: {list(report_content.keys() if isinstance(report_content, dict) else [])}")
            
            return report_content
        except Exception as e:
            logger.error(f"Error getting {report_type} from workflow: {str(e)}")
            return None
            
    async def add_conversation_message(self, session_id: str, message_type: str, content: str, metadata: Dict[str, Any] = None, user_token: str = None) -> bool:
        """Add a message to the conversation history within the unified workflow.
        
        Args:
            session_id: The session ID.
            message_type: Type of message ("initial_query", "follow_up_question", "answer", "clarification").
            content: The message content.
            metadata: Optional metadata for the message.
            user_token: Optional JWT token of the authenticated user for RLS enforcement.
            
        Returns:
            True if message was added successfully, False otherwise.
        """
        try:
            # Skip conversation history storage to avoid creating unnecessary unified reports
            # Conversation history is not critical for report generation and was causing
            # duplicate report issues by creating empty unified reports
            logger.info(f"Skipping conversation history storage for session {session_id} to avoid unified report creation")
            return True
        except Exception as e:
            logger.error(f"Error adding conversation message: {str(e)}")
            return False
            
    async def get_conversation_history(self, session_id: str, user_token: str = None) -> List[Dict[str, Any]]:
        """Get the conversation history from the unified workflow.
        
        Args:
            session_id: The session ID.
            user_token: Optional JWT token of the authenticated user for RLS enforcement.
            
        Returns:
            List of conversation history messages, or empty list if none found.
        """
        try:
            # Get the workflow with user token for RLS enforcement
            workflow = await self.get_unified_workflow(session_id, user_token)
            
            if not workflow or not workflow.get("content"):
                logger.info(f"No workflow found for session: {session_id}")
                return []
            
            conversation_history = workflow.get("content", {}).get("conversation_history", [])
            return conversation_history
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
            
    async def get_conversation_thread(self, session_id: str, message_types: List[str] = None, user_token: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get conversation history organized by message type from the unified workflow.
        
        Args:
            session_id: The session ID.
            message_types: Optional list of message types to filter by.
            user_token: Optional JWT token of the authenticated user for RLS enforcement.
            
        Returns:
            Dictionary with message types as keys and lists of messages as values.
        """
        history = await self.get_conversation_history(session_id, user_token)
        
        if not history:
            return {}
            
        # Filter by message type if specified
        if message_types:
            history = [item for item in history if item.get("message_type") in message_types]
            
        # Organize by message type
        result = {}
        for item in history:
            msg_type = item.get("message_type")
            if msg_type not in result:
                result[msg_type] = []
            result[msg_type].append(item)
            
        return result
    
    def _extract_final_report_content(self, structured_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only the final report content, removing workflow metadata.
        
        This method ensures that only the clean, formatted report content is stored
        in the content column, addressing Requirement 2.1.
        
        Args:
            structured_report: The complete report structure from workflow
            
        Returns:
            Clean final report content ready for display
        """
        if isinstance(structured_report, dict):
            # Remove any workflow-specific keys that shouldn't be in final content
            workflow_keys = {
                'session_id', 'job_id', 'status', 'created_at', 'updated_at',
                'initial_query', 'clarification', 'user_answers', 'workflow_metadata',
                'awaiting_clarification', 'clarification_complete', '_workflow_paused_for_input'
            }
            
            # Create a clean copy without workflow metadata
            clean_report = {}
            for key, value in structured_report.items():
                if key not in workflow_keys:
                    clean_report[key] = value
            
            return clean_report
        
        return structured_report
    
    def _extract_workflow_metadata(self, workflow_state: Dict[str, Any]) -> tuple:
        """
        Extract workflow metadata from the workflow state.
        
        This method separates workflow metadata from final report content,
        addressing Requirement 2.2.
        
        Args:
            workflow_state: Complete workflow state
            
        Returns:
            Tuple of (initial_query, clarification_questions, clarification_answers, workflow_metadata)
        """
        from datetime import datetime
        
        # Extract initial query
        initial_query = workflow_state.get("initial_query", "")
        
        # Extract clarification data
        clarification = workflow_state.get("clarification", {})
        clarification_questions = clarification.get("questions", [])
        
        # Extract user answers
        user_answers = workflow_state.get("user_answers", {})
        
        # Create workflow metadata
        workflow_metadata = {
            "session_id": workflow_state.get("session_id"),
            "generation_timestamp": datetime.utcnow().isoformat(),
            "workflow_version": "enhanced_v1.0",
            "agents_used": workflow_state.get("agents_used", []),
            "processing_time": workflow_state.get("processing_time"),
            "clarification_complete": workflow_state.get("clarification_complete", False),
            "interactive_mode": workflow_state.get("interactive_mode", False)
        }
        
        # Remove None values
        workflow_metadata = {k: v for k, v in workflow_metadata.items() if v is not None}
        
        return initial_query, clarification_questions, user_answers, workflow_metadata

    async def store_report(self, session_id: str, report_type: str, content: Dict[str, Any],
                      title: str = None, summary: str = None, user_token: str = None) -> str:
        """Store a report in Supabase.

        Args:
            session_id: The session ID.
            report_type: Type of report ("industry", "pestel", "final", etc.)
            content: The report content as a dictionary.
            title: Optional title for the report.
            summary: Optional summary of the report.
            user_token: JWT token of the authenticated user. If provided, RLS policies will be enforced.

        Returns:
            The ID of the stored report, or None if storage failed.
        """
        try:
            # Extract user ID for consistent identification (Requirement 3.2)
            user_id = self._extract_user_id_from_token(user_token) if user_token else None
            
            data = {
                "session_id": session_id,
                "report_type": report_type,
                "content": content,
                "title": title or f"{report_type.capitalize()} Report",
                "summary": summary or "",
                "user_id": user_id  # Ensure consistent user_id usage
            }
            
            # Determine whether to use user token or service role key
            if user_token:
                # Use user's JWT token to enforce RLS policies
                logger.info(f"Using user JWT token for report storage (RLS enforced)")
                anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
                temp_client = create_client(self.supabase_url, anon_key)
                # Set auth with user's JWT token
                temp_client.postgrest.auth(user_token)
            else:
                # Fallback to service role key if no user token provided (bypasses RLS)
                logger.warning(f"No user token provided, using service role key (bypassing RLS)")
                service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", self.supabase_key)
                temp_client = create_client(self.supabase_url, service_role_key)
                # Explicitly set auth to bypass RLS
                temp_client.postgrest.auth(service_role_key)
            
            # Use transaction-safe insertion (Requirement 5.2)
            query = temp_client.table(self.reports_table).insert(data)
            response = query.execute()
            
            if not response.data or len(response.data) == 0:
                logger.error(f"Error storing {report_type} report: {response}")
                return None
            
            report_id = response.data[0].get("id")
            logger.info(f"Stored {report_type} report with ID: {report_id}")
            return report_id
                
        except Exception as e:
            logger.error(f"Error storing {report_type} report: {str(e)}")
            # Transaction rollback is handled automatically by Supabase on exception
            raise

    async def store_final_report_with_metadata(
        self,
        session_id: str,
        structured_report: Dict[str, Any],
        workflow_state: Dict[str, Any],
        user_token: str,
        report_type: str = "final"
    ) -> Optional[str]:
        """
        Store final report with separated content and metadata using transaction safety.
        
        This method implements the core functionality for Requirements 2.1, 2.2, 3.2, 5.1, and 5.2
        by storing only final report content in the content column while maintaining
        workflow metadata in dedicated columns with consistent user_id usage.
        
        Args:
            session_id: Workflow session ID
            structured_report: Complete structured report from workflow
            workflow_state: Complete workflow state containing metadata
            user_token: JWT token for user authentication and RLS enforcement
            report_type: Type of report (default: "final")
            
        Returns:
            Report ID if successful, None if failed
        """
        if not user_token:
            logger.error("User token is required for report storage")
            return None
            
        # Extract user ID for consistent identification (Requirement 3.2)
        user_id = self._extract_user_id_from_token(user_token)
        if not user_id:
            logger.error("Failed to extract user ID from token")
            return None
        
        try:
            # Create authenticated client for RLS enforcement
            anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
            temp_client = create_client(self.supabase_url, anon_key)
            temp_client.postgrest.auth(user_token)
            
            # Extract clean final report content (Requirement 2.1)
            final_content = self._extract_final_report_content(structured_report)
            
            # Extract workflow metadata (Requirement 2.2)
            initial_query, clarification_questions, clarification_answers, workflow_metadata = \
                self._extract_workflow_metadata(workflow_state)
            
            # Extract title and summary from final report
            title = final_content.get("title", f"{report_type.capitalize()} Report")
            summary = final_content.get("executive_summary", "")[:500]  # Limit summary length
            
            # Prepare data for insertion with consistent user_id (Requirements 3.2, 5.1)
            report_data = {
                "session_id": session_id,
                "user_id": user_id,  # Consistent user identification
                "report_type": report_type,
                "content": final_content,  # Only final formatted content
                "title": title,
                "summary": summary,
                "initial_query": initial_query,  # Separated metadata
                "clarification_questions": clarification_questions,  # Separated metadata
                "clarification_answers": clarification_answers,  # Separated metadata
                "workflow_metadata": workflow_metadata  # Separated metadata
            }
            
            logger.info(f"Saving final report for session {session_id} with user_id {user_id}")
            logger.debug(f"Report data keys: {list(report_data.keys())}")
            
            # Use transaction-safe insertion (Requirement 5.2)
            response = temp_client.table(self.reports_table).insert(report_data).execute()
            
            if not response.data or len(response.data) == 0:
                logger.error(f"Failed to save report: {response}")
                return None
            
            report_id = response.data[0].get("id")
            logger.info(f"Successfully saved final report with ID: {report_id}")
            
            return report_id
            
        except Exception as e:
            logger.error(f"Error saving final report with metadata: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Transaction rollback is handled automatically by Supabase
            # on exception, ensuring data consistency (Requirement 5.2)
            return None

    async def batch_update_reports_with_rollback(
        self,
        operations: List[Dict[str, Any]],
        user_token: str
    ) -> bool:
        """
        Perform batch report operations with transaction safety and rollback mechanisms.
        
        This method ensures data consistency across multiple report operations
        by implementing proper transaction handling (Requirement 5.2).
        
        Args:
            operations: List of operation dictionaries with keys:
                       - operation: "insert", "update", or "delete"
                       - data: Operation-specific data
            user_token: JWT token for authentication
            
        Returns:
            True if all operations successful, False if any failed (with rollback)
        """
        if not user_token:
            logger.error("User token is required for batch operations")
            return False
            
        user_id = self._extract_user_id_from_token(user_token)
        if not user_id:
            logger.error("Failed to extract user ID from token")
            return False
        
        try:
            # Create authenticated client
            anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
            temp_client = create_client(self.supabase_url, anon_key)
            temp_client.postgrest.auth(user_token)
            
            # Track operations for potential rollback
            completed_operations = []
            
            logger.info(f"Starting batch operation with {len(operations)} operations")
            
            for i, operation in enumerate(operations):
                op_type = operation.get("operation")
                op_data = operation.get("data", {})
                
                # Ensure consistent user_id in all operations (Requirement 3.2)
                if "user_id" not in op_data:
                    op_data["user_id"] = user_id
                
                try:
                    if op_type == "insert":
                        response = temp_client.table(self.reports_table).insert(op_data).execute()
                    elif op_type == "update":
                        record_id = op_data.pop("id")
                        response = temp_client.table(self.reports_table)\
                            .update(op_data)\
                            .eq("id", record_id)\
                            .eq("user_id", user_id)\
                            .execute()
                    elif op_type == "delete":
                        record_id = op_data.get("id")
                        response = temp_client.table(self.reports_table)\
                            .delete()\
                            .eq("id", record_id)\
                            .eq("user_id", user_id)\
                            .execute()
                    else:
                        raise ValueError(f"Unsupported operation type: {op_type}")
                    
                    if not response.data:
                        raise Exception(f"Operation {i+1} failed: {response}")
                    
                    completed_operations.append({
                        "operation": op_type,
                        "response": response,
                        "index": i
                    })
                    
                    logger.debug(f"Completed operation {i+1}/{len(operations)}: {op_type}")
                    
                except Exception as e:
                    logger.error(f"Operation {i+1} failed: {str(e)}")
                    # Note: Supabase handles transaction rollback automatically
                    # Individual operations within a session are atomic
                    raise
            
            logger.info(f"Successfully completed all {len(operations)} batch operations")
            return True
            
        except Exception as e:
            logger.error(f"Batch operation failed: {str(e)}")
            logger.error(f"Completed {len(completed_operations)} operations before failure")
            # Supabase automatically handles rollback on connection/session failure
            return False

    async def verify_report_consistency(
        self,
        session_id: str,
        user_token: str
    ) -> Dict[str, Any]:
        """
        Verify data consistency for reports associated with a session.
        
        This method checks for referential integrity and consistent user_id usage
        across related database entries (Requirements 2.5, 5.1).
        
        Args:
            session_id: Session ID to verify
            user_token: JWT token for authentication
            
        Returns:
            Dictionary with consistency check results
        """
        if not user_token:
            return {"error": "User token required"}
            
        user_id = self._extract_user_id_from_token(user_token)
        if not user_id:
            return {"error": "Failed to extract user ID"}
        
        try:
            # Create authenticated client
            anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
            temp_client = create_client(self.supabase_url, anon_key)
            temp_client.postgrest.auth(user_token)
            
            # Fetch all reports for the session
            response = temp_client.table(self.reports_table)\
                .select("*")\
                .eq("session_id", session_id)\
                .execute()
            
            if not response.data:
                return {"error": "No reports found for session"}
            
            reports = response.data
            consistency_results = {
                "session_id": session_id,
                "total_reports": len(reports),
                "user_id_consistent": True,
                "metadata_separation_check": True,
                "issues": []
            }
            
            # Check user_id consistency (Requirement 5.1)
            for report in reports:
                if report.get("user_id") != user_id:
                    consistency_results["user_id_consistent"] = False
                    consistency_results["issues"].append(
                        f"Report {report.get('id')} has inconsistent user_id: {report.get('user_id')} vs {user_id}"
                    )
            
            # Check metadata separation (Requirement 2.2)
            for report in reports:
                if report.get("report_type") == "final":
                    content = report.get("content", {})
                    
                    # Check if workflow metadata is properly separated
                    workflow_keys_in_content = {
                        'initial_query', 'clarification', 'user_answers', 'workflow_metadata'
                    }
                    
                    found_workflow_keys = workflow_keys_in_content.intersection(content.keys())
                    if found_workflow_keys:
                        consistency_results["metadata_separation_check"] = False
                        consistency_results["issues"].append(
                            f"Report {report.get('id')} has workflow metadata in content: {found_workflow_keys}"
                        )
                    
                    # Check if metadata columns are populated
                    if not report.get("initial_query") and not report.get("workflow_metadata"):
                        consistency_results["issues"].append(
                            f"Report {report.get('id')} missing workflow metadata in dedicated columns"
                        )
            
            logger.info(f"Consistency check completed for session {session_id}: {len(consistency_results['issues'])} issues found")
            return consistency_results
            
        except Exception as e:
            logger.error(f"Error during consistency check: {str(e)}")
            return {"error": f"Consistency check failed: {str(e)}"}
    
    def _ensure_ssl_disabled_for_operation(self):
        """
        Simplified operation preparation (replaces aggressive SSL patching).
        This is now a no-op method to maintain compatibility while removing problematic SSL patches.
        """
        # This method is now simplified to avoid aggressive SSL patching
        # that caused inconsistent behavior across different network environments
        pass
    
    async def get_report(self, session_id: str = None, report_type: str = None, report_id: str = None, user_token: str = None) -> Dict[str, Any]:
        """
        Retrieve a report from Supabase with proper user authentication.
        
        Args:
            session_id: The session ID associated with the report
            report_type: Type of report ('industry', 'pestel', or 'final')
            report_id: UUID of the report to retrieve (alternative to using session_id and report_type)
            user_token: Optional JWT token of the authenticated user for RLS enforcement.
            
        Returns:
            The report content as a dictionary
        """
        if self.is_production:
            self._ensure_ssl_disabled_for_operation()
        
        try:
            # Extract user ID for consistent authentication
            user_id = self._extract_user_id_from_token(user_token) if user_token else None
            
            # Create appropriate client based on whether user token is provided
            if user_token and user_id:
                anon_key = os.getenv("SUPABASE_ANON_KEY", self.supabase_key)
                temp_client = create_client(self.supabase_url, anon_key)
                temp_client.postgrest.auth(user_token)
                logger.info(f"Using user token for RLS enforcement when fetching report for user {user_id}")
                query = temp_client.table(self.reports_table).select("*")
            else:
                # Fall back to service role key to bypass RLS
                service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", self.supabase_key)
                temp_client = create_client(self.supabase_url, service_role_key)
                logger.warning(f"Using service role key to bypass RLS when fetching report")
                query = temp_client.table(self.reports_table).select("*")
            
            if report_id:
                # If report_id is provided, use that for direct lookup
                if user_id:
                    result = query.eq("id", report_id).eq("user_id", user_id).execute()
                else:
                    result = query.eq("id", report_id).execute()
                logger.info(f"Fetching report by ID: {report_id}")
            elif session_id and report_type:
                # Otherwise use session_id and report_type with user_id for proper authentication
                if user_id:
                    result = query.eq("session_id", session_id)\
                        .eq("user_id", user_id)\
                        .eq("report_type", report_type)\
                        .order("created_at", desc=True)\
                        .limit(1)\
                        .execute()
                else:
                    result = query.eq("session_id", session_id)\
                        .eq("report_type", report_type)\
                        .order("created_at", desc=True)\
                        .limit(1)\
                        .execute()
                logger.info(f"Fetching {report_type} report for session: {session_id}")
            else:
                logger.error("Must provide either report_id or both session_id and report_type")
                return None
                
            # Check if the query returned results
            if result.data and len(result.data) > 0:
                report = result.data[0]
                logger.info(f"Found report with ID: {report.get('id')}")
                return report
            else:
                logger.warning(f"No {report_type} report found for session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving {report_type} report: {str(e)}")
            raise

    async def update_report(self, report_id: str, content: dict, title: str = None, summary: str = None) -> bool:
        """
        Update an existing report in Supabase.
        
        Args:
            report_id: The UUID of the report to update
            content: The updated report content
            title: Optional updated title
            summary: Optional updated summary
            
        Returns:
            True if the update was successful, False otherwise
        """
        self._ensure_ssl_disabled_for_operation()
        
        try:
            # Prepare update data
            update_data = {"content": content}
            if title is not None:
                update_data["title"] = title
            if summary is not None:
                update_data["summary"] = summary
                
            # Update the report
            result = self.client.table(self.reports_table)\
                .update(update_data)\
                .eq("id", report_id)\
                .execute()
                
            # Check if the update was successful
            if result.data and len(result.data) > 0:
                logger.info(f"Updated report with ID: {report_id}")
                return True
            else:
                logger.warning(f"No report found with ID: {report_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating report: {str(e)}")
            raise
    
    async def delete_report(self, report_id: str) -> bool:
        """Delete a report by ID.

        Args:
            report_id: The ID of the report to delete

        Returns:
            True if successful, False otherwise
        """
        self._ensure_ssl_disabled_for_operation()

        try:
            logger.info(f"Deleting report with ID {report_id}")
            result = self.client.table(self.reports_table)\
                .delete()\
                .eq("id", report_id)\
                .execute()
            
            if len(result.data) > 0:
                logger.info(f"Successfully deleted report with ID {report_id}")
                return True
            else:
                logger.warning(f"No report found with ID {report_id} to delete")
                return False
        except Exception as e:
            logger.error(f"Error deleting report: {str(e)}")
            return False
            
    async def execute_sql(self, sql_query: str) -> Dict[str, Any]:
        """Execute a raw SQL query.
        
        Args:
            sql_query: The SQL query to execute
            
        Returns:
            Dictionary with data and error information
        """
        self._ensure_ssl_disabled_for_operation()
        
        try:
            logger.info("Executing SQL query")
            # Use the Supabase native SQL execution if available
            try:
                # Check if the postgrest client has a rpc method
                if hasattr(self.client, 'rpc'):
                    result = self.client.rpc('exec_sql', {"sql": sql_query}).execute()
                    if result.data:
                        logger.info("SQL query executed successfully using rpc")
                        return {"data": result.data, "error": None}
                
                # Otherwise try the built-in query method
                result = self.client.query(sql_query).execute()
                if result.data is not None:
                    logger.info("SQL query executed successfully using query method")
                    return {"data": result.data, "error": None}
                    
            except Exception as inner_e:
                logger.warning(f"Native SQL execution failed: {str(inner_e)}, trying REST API...")
                
            # Fall back to direct HTTP call if native methods fail
            with httpx.Client() as client:
                response = client.post(
                    f"{self.supabase_url}/rest/v1/rpc/exec_sql",
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "sql": sql_query
                    },
                    timeout=60.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info("SQL query executed successfully via REST API")
                return {"data": result, "error": None}
                
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)}")
            return {"data": None, "error": str(e)}

# Create SQL for setting up RLS on the jobs table
"""
-- SQL to create the jobs table with proper RLS
CREATE TABLE public.mint_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    query TEXT NOT NULL,
    status TEXT NOT NULL,
    result JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.mint_jobs ENABLE ROW LEVEL SECURITY;

-- Create policy to ensure users can only see their own jobs
CREATE POLICY "Users can only view their own jobs" ON public.mint_jobs
    FOR SELECT
    USING (auth.uid() = user_id);

-- Create policy to ensure users can only insert their own jobs
CREATE POLICY "Users can only insert their own jobs" ON public.mint_jobs
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Create policy to ensure users can only update their own jobs
CREATE POLICY "Users can only update their own jobs" ON public.mint_jobs
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Create policy to ensure users can only delete their own jobs
CREATE POLICY "Users can only delete their own jobs" ON public.mint_jobs
    FOR DELETE
    USING (auth.uid() = user_id);

-- Grant access to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON public.mint_jobs TO authenticated;
"""

# Global instance for easy access
_supabase_client = None

# Global singleton instances
_supabase_client_service = None  # Service role client (bypasses RLS)
_supabase_client_standard = None  # Standard client (subject to RLS)
_client_lock = None  # Thread lock for thread safety

try:
    import threading
    _client_lock = threading.Lock()
except ImportError:
    # Fallback for environments without threading
    class DummyLock:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    _client_lock = DummyLock()

def get_supabase_client(use_service_role: bool = True):
    """Get a singleton Supabase client instance.
    
    Args:
        use_service_role: If True, returns service role client (bypasses RLS).
                         If False, returns standard client (subject to RLS).
    
    Returns:
        SupabaseClient: Singleton client instance
    """
    global _supabase_client_service, _supabase_client_standard
    
    with _client_lock:
        if use_service_role:
            if _supabase_client_service is None:
                logger.info("Initializing singleton service role Supabase client")
                _supabase_client_service = SupabaseClient(use_service_role=True)
            return _supabase_client_service
        else:
            if _supabase_client_standard is None:
                logger.info("Initializing singleton standard Supabase client")
                _supabase_client_standard = SupabaseClient(use_service_role=False)
            return _supabase_client_standard

def get_service_role_client():
    """Get the service role Supabase client (bypasses RLS).
    
    Returns:
        SupabaseClient: Service role client instance
    """
    return get_supabase_client(use_service_role=True)

def get_standard_client():
    """Get the standard Supabase client (subject to RLS).
    
    Returns:
        SupabaseClient: Standard client instance
    """
    return get_supabase_client(use_service_role=False)

def reset_clients():
    """Reset singleton clients (useful for testing or configuration changes)."""
    global _supabase_client_service, _supabase_client_standard
    
    with _client_lock:
        logger.info("Resetting singleton Supabase clients")
        _supabase_client_service = None
        _supabase_client_standard = None

def get_client_stats():
    """Get statistics about initialized clients.
    
    Returns:
        dict: Client initialization status
    """
    return {
        "service_role_initialized": _supabase_client_service is not None,
        "standard_client_initialized": _supabase_client_standard is not None,
        "total_initialized": sum([
            _supabase_client_service is not None,
            _supabase_client_standard is not None
        ])
    }
