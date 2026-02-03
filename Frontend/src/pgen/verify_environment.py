#!/usr/bin/env python3
"""
Environment Verification Script for Problem Generator

This script verifies that all required environment variables and API connections
are properly configured for the Problem Generator feature using existing config systems.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent.parent
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path=dotenv_path, override=True)

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.mint.utils.config import get_config
from src.mint.api.ai.config import (
    is_azure_configured,
    get_azure_config,
    ModelUseCase,
    AZURE_DEPLOYMENTS,
    OPENAI_MODELS
)
from src.mint.providers.factory import get_provider

class EnvironmentVerifier:
    """Verifies Problem Generator environment configuration."""
    
    def __init__(self):
        """Initialize the environment verifier."""
        self.config = get_config()
        self.results = {}
        
    def print_header(self, title: str) -> None:
        """Print a formatted header."""
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print('='*60)
    
    def print_check(self, item: str, status: bool, details: str = "") -> None:
        """Print a check result."""
        icon = "✅" if status else "❌"
        print(f"{icon} {item}")
        if details:
            print(f"   {details}")
    
    def verify_azure_openai(self) -> bool:
        """Verify Azure OpenAI configuration."""
        self.print_header("Azure OpenAI Configuration")
        
        is_configured = is_azure_configured()
        self.print_check("Azure OpenAI Environment Variables", is_configured)
        
        if is_configured:
            azure_config = get_azure_config()
            endpoint = azure_config.get('endpoint', '')
            api_key = azure_config.get('api_key', '')
            
            self.print_check("Azure Endpoint", bool(endpoint), f"Endpoint: {endpoint[:50]}...")
            self.print_check("Azure API Key", bool(api_key), f"Key length: {len(api_key)}")
            
            # Check specific deployments for Problem Generator
            required_deployments = [
                ModelUseCase.REPORT_GENERATION,  # For complex problem generation
                ModelUseCase.CHAT_COMPLETION,    # For interactive generation
                ModelUseCase.EMBEDDING           # For vector similarity
            ]
            
            for use_case in required_deployments:
                deployment_name = AZURE_DEPLOYMENTS.get(use_case)
                fallback_model = OPENAI_MODELS.get(use_case)
                self.print_check(
                    f"{use_case.value} model",
                    bool(deployment_name),
                    f"Azure: {deployment_name}, Fallback: {fallback_model}"
                )
        
        return is_configured
    
    def verify_search_providers(self) -> Dict[str, bool]:
        """Verify search provider configurations."""
        self.print_header("Search Provider Configuration")
        
        results = {}
        
        # Check Tavily API key (DEPRECATED - replaced with Brave)
        tavily_key = os.getenv('TAVILY_API_KEY')
        results['tavily'] = bool(tavily_key)
        self.print_check("Tavily API Key (DEPRECATED)", results['tavily'], 
                        f"Key length: {len(tavily_key) if tavily_key else 0}")
        
        # Check Brave API key (now required - replaces Tavily)
        brave_key = os.getenv('BRAVE_API_KEY')
        results['brave'] = bool(brave_key)
        self.print_check("Brave API Key (Required)", results['brave'], 
                        f"Key length: {len(brave_key) if brave_key else 0}")
        
        # Check provider factory configuration
        try:
            search_provider = get_provider("search", "brave")
            results['provider_factory'] = True
            self.print_check("Search Provider Factory", True, "Successfully initialized Brave provider")
        except Exception as e:
            results['provider_factory'] = False
            self.print_check("Search Provider Factory", False, f"Error: {str(e)}")
        
        return results
    
    def verify_vector_storage(self) -> bool:
        """Verify vector storage configuration."""
        self.print_header("Vector Storage Configuration")
        
        # Check Supabase configuration (already verified in previous tests)
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        
        supabase_configured = bool(supabase_url and supabase_key)
        self.print_check("Supabase Configuration", supabase_configured,
                        f"URL: {supabase_url[:50] if supabase_url else 'Not set'}...")
        
        # Check vector provider factory
        try:
            vector_provider = get_provider("vector", "pgvector")
            self.print_check("Vector Provider Factory", True, "Successfully initialized pgvector provider")
        except Exception as e:
            self.print_check("Vector Provider Factory", False, f"Error: {str(e)}")
            supabase_configured = False
        
        return supabase_configured
    
    def verify_llm_provider(self) -> bool:
        """Verify LLM provider configuration."""
        self.print_header("LLM Provider Configuration")
        
        # Check provider factory
        try:
            llm_provider = get_provider("llm", "openai")
            self.print_check("LLM Provider Factory", True, "Successfully initialized OpenAI provider")
            
            # Test if it can handle Azure configuration
            if is_azure_configured():
                self.print_check("Azure OpenAI Integration", True, "Provider will use Azure OpenAI")
            else:
                openai_key = os.getenv('OPENAI_API_KEY')
                self.print_check("OpenAI Fallback", bool(openai_key), 
                               f"Key length: {len(openai_key) if openai_key else 0}")
            
            return True
        except Exception as e:
            self.print_check("LLM Provider Factory", False, f"Error: {str(e)}")
            return False
    
    def verify_config_system(self) -> bool:
        """Verify the configuration system."""
        self.print_header("Configuration System")
        
        try:
            # Test config loading
            config = get_config()
            self.print_check("Config System", True, "Configuration loaded successfully")
            
            # Check LLM config
            llm_config = config.get_llm_config()
            self.print_check("LLM Config", bool(llm_config), f"Provider: {llm_config.get('provider', 'Not set')}")
            
            # Check search config
            search_config = config.get_search_config()
            self.print_check("Search Config", bool(search_config), f"Provider: {search_config.get('provider', 'Not set')}")
            
            return True
        except Exception as e:
            self.print_check("Config System", False, f"Error: {str(e)}")
            return False
    
    def verify_problem_generator_config(self) -> bool:
        """Verify Problem Generator specific configuration."""
        self.print_header("Problem Generator Configuration")
        
        try:
            # Check if problem generator config exists
            pgen_config = self.config.get("agents.problem_generator", {})
            has_config = bool(pgen_config)
            self.print_check("Problem Generator Config", has_config,
                           "Found in mint_config.yaml" if has_config else "Will use defaults")
            
            # Check required models for problem generation
            required_use_cases = [
                ModelUseCase.REPORT_GENERATION,  # Complex problem analysis
                ModelUseCase.CHAT_COMPLETION,    # Interactive generation
                ModelUseCase.EMBEDDING           # Vector similarity
            ]
            
            all_models_available = True
            for use_case in required_use_cases:
                azure_model = AZURE_DEPLOYMENTS.get(use_case)
                openai_model = OPENAI_MODELS.get(use_case)
                model_available = bool(azure_model or openai_model)
                all_models_available = all_models_available and model_available
                self.print_check(f"Model for {use_case.value}", model_available,
                               f"Azure: {azure_model}, OpenAI: {openai_model}")
            
            return all_models_available
        except Exception as e:
            self.print_check("Problem Generator Config", False, f"Error: {str(e)}")
            return False
    
    async def run_verification(self) -> bool:
        """Run complete environment verification."""
        print("🚀 Problem Generator Environment Verification")
        print("=" * 60)
        
        # Run all verifications
        azure_ok = self.verify_azure_openai()
        search_ok = all(self.verify_search_providers().values())
        vector_ok = self.verify_vector_storage()
        llm_ok = self.verify_llm_provider()
        config_ok = self.verify_config_system()
        pgen_ok = self.verify_problem_generator_config()
        
        # Summary
        self.print_header("Verification Summary")
        
        all_checks = [
            ("Azure OpenAI", azure_ok),
            ("Search Providers", search_ok),
            ("Vector Storage", vector_ok),
            ("LLM Provider", llm_ok),
            ("Config System", config_ok),
            ("Problem Generator", pgen_ok)
        ]
        
        passed = 0
        for check_name, status in all_checks:
            self.print_check(check_name, status)
            if status:
                passed += 1
        
        success_rate = passed / len(all_checks) * 100
        
        print(f"\n📊 Verification Results: {passed}/{len(all_checks)} checks passed ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print("\n🎉 Environment is fully configured for Problem Generator!")
            print("✅ Ready to proceed with Phase 2: Backend Implementation")
        elif success_rate >= 80:
            print("\n⚠️  Environment is mostly configured. Some optional features may not work.")
            print("✅ Can proceed with Phase 2 with limited functionality")
        else:
            print("\n❌ Environment configuration incomplete.")
            print("🔧 Please configure missing components before proceeding.")
        
        return success_rate >= 80

async def main():
    """Main verification function."""
    verifier = EnvironmentVerifier()
    success = await verifier.run_verification()
    
    if not success:
        sys.exit(1)
    
    print("\n🚀 Environment verification completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
