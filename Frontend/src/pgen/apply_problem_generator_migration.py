#!/usr/bin/env python3
"""
Problem Generator Database Migration Script

This script applies the problem generator database migration to Supabase.
It creates the necessary tables, indexes, and functions for the problem generator feature.

Usage:
    python apply_problem_generator_migration.py [--dry-run]

Requirements:
    - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables
    - psycopg2 or supabase-py library
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent.parent.parent.parent
dotenv_path = project_root / '.env'
print(f"Loading .env from: {dotenv_path}")
print(f".env file exists: {dotenv_path.exists()}")
load_result = load_dotenv(dotenv_path=dotenv_path, override=True)
print(f"load_dotenv result: {load_result}")

# Add the parent directory to the path to import from src.mint
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.mint.api.supabase_client import get_service_role_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProblemGeneratorMigration:
    """Handles the problem generator database migration."""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the migration handler.
        
        Args:
            dry_run: If True, only validate the migration without applying it
        """
        self.dry_run = dry_run
        self.client = None
        self.migration_file = Path(__file__).parent.parent.parent / "supabase" / "migrations" / "20250804_create_problem_generator_tables.sql"
        
    def connect(self) -> bool:
        """
        Connect to Supabase using service role client.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = get_service_role_client()
            logger.info("Successfully connected to Supabase")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {str(e)}")
            return False
    
    def load_migration_sql(self) -> Optional[str]:
        """
        Load the migration SQL from file.
        
        Returns:
            Migration SQL content or None if failed
        """
        try:
            if not self.migration_file.exists():
                logger.error(f"Migration file not found: {self.migration_file}")
                return None
                
            with open(self.migration_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                
            logger.info(f"Loaded migration SQL from {self.migration_file}")
            logger.info(f"Migration SQL size: {len(sql_content)} characters")
            return sql_content
            
        except Exception as e:
            logger.error(f"Failed to load migration SQL: {str(e)}")
            return None
    
    def validate_migration(self, sql_content: str) -> bool:
        """
        Validate the migration SQL content.
        
        Args:
            sql_content: The SQL content to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        required_elements = [
            "CREATE TABLE IF NOT EXISTS public.problem_statements",
            "CREATE TABLE IF NOT EXISTS public.problem_generation_analytics",
            "CREATE TABLE IF NOT EXISTS public.problem_bookmarks",
            "CREATE TABLE IF NOT EXISTS public.problem_likes",
            "CREATE EXTENSION IF NOT EXISTS vector",
            "ENABLE ROW LEVEL SECURITY",
            "match_problem_statements"
        ]
        
        for element in required_elements:
            if element not in sql_content:
                logger.error(f"Migration validation failed: Missing required element '{element}'")
                return False
                
        logger.info("Migration SQL validation passed")
        return True
    
    def check_existing_tables(self) -> dict:
        """
        Check which problem generator tables already exist.
        
        Returns:
            Dictionary with table existence status
        """
        tables_to_check = [
            'problem_statements',
            'problem_generation_analytics', 
            'problem_bookmarks',
            'problem_likes'
        ]
        
        existing_tables = {}
        
        try:
            for table in tables_to_check:
                query = f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                );
                """
                
                result = self.client.client.rpc('exec_sql', {'sql': query}).execute()
                exists = result.data[0]['exists'] if result.data else False
                existing_tables[table] = exists
                
                if exists:
                    logger.info(f"Table '{table}' already exists")
                else:
                    logger.info(f"Table '{table}' does not exist")
                    
        except Exception as e:
            logger.error(f"Failed to check existing tables: {str(e)}")
            
        return existing_tables
    
    def apply_migration(self, sql_content: str) -> bool:
        """
        Apply the migration to the database.
        
        Args:
            sql_content: The SQL content to execute
            
        Returns:
            True if migration successful, False otherwise
        """
        if self.dry_run:
            logger.info("DRY RUN: Migration would be applied but --dry-run flag is set")
            return True
            
        try:
            logger.info("Starting migration application...")
            
            # Split the SQL into individual statements
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            logger.info(f"Executing {len(statements)} SQL statements...")
            
            for i, statement in enumerate(statements, 1):
                if not statement:
                    continue
                    
                try:
                    # Execute each statement individually for better error reporting
                    self.client.client.rpc('exec_sql', {'sql': statement}).execute()
                    logger.debug(f"Executed statement {i}/{len(statements)}")
                    
                except Exception as e:
                    # Some statements might fail if objects already exist, which is okay
                    if "already exists" in str(e).lower():
                        logger.debug(f"Statement {i} skipped (object already exists): {str(e)}")
                    else:
                        logger.warning(f"Statement {i} failed: {str(e)}")
                        # Continue with other statements
                        
            logger.info("Migration application completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration: {str(e)}")
            return False
    
    def verify_migration(self) -> bool:
        """
        Verify that the migration was applied successfully.
        
        Returns:
            True if verification passes, False otherwise
        """
        try:
            # Check that all tables were created
            existing_tables = self.check_existing_tables()
            
            required_tables = ['problem_statements', 'problem_generation_analytics', 'problem_bookmarks', 'problem_likes']
            
            for table in required_tables:
                if not existing_tables.get(table, False):
                    logger.error(f"Verification failed: Table '{table}' was not created")
                    return False
                    
            # Check that the vector search function exists
            function_check_query = """
            SELECT EXISTS (
                SELECT FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE n.nspname = 'public' 
                AND p.proname = 'match_problem_statements'
            );
            """
            
            result = self.client.client.rpc('exec_sql', {'sql': function_check_query}).execute()
            function_exists = result.data[0]['exists'] if result.data else False
            
            if not function_exists:
                logger.error("Verification failed: Function 'match_problem_statements' was not created")
                return False
                
            logger.info("Migration verification passed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration verification failed: {str(e)}")
            return False
    
    def run(self) -> bool:
        """
        Run the complete migration process.
        
        Returns:
            True if migration successful, False otherwise
        """
        logger.info(f"Starting Problem Generator migration {'(DRY RUN)' if self.dry_run else ''}")
        
        # Step 1: Connect to database
        if not self.connect():
            return False
            
        # Step 2: Load migration SQL
        sql_content = self.load_migration_sql()
        if not sql_content:
            return False
            
        # Step 3: Validate migration
        if not self.validate_migration(sql_content):
            return False
            
        # Step 4: Check existing tables
        existing_tables = self.check_existing_tables()
        
        # Step 5: Apply migration
        if not self.apply_migration(sql_content):
            return False
            
        # Step 6: Verify migration (skip for dry run)
        if not self.dry_run:
            if not self.verify_migration():
                return False
                
        logger.info(f"Problem Generator migration completed successfully {'(DRY RUN)' if self.dry_run else ''}")
        return True

def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Apply Problem Generator database migration to Supabase"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate migration without applying it'
    )
    
    args = parser.parse_args()
    
    # Check required environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    print(f"Debug - SUPABASE_URL: {'[SET]' if supabase_url else '[NOT SET]'}")
    print(f"Debug - SUPABASE_SERVICE_ROLE_KEY: {'[SET]' if supabase_service_role_key else '[NOT SET]'}")
    print(f"Debug - SUPABASE_KEY: {'[SET]' if supabase_key else '[NOT SET]'}")
    
    missing_vars = []
    if not supabase_url:
        missing_vars.append('SUPABASE_URL')
    if not supabase_service_role_key and not supabase_key:
        missing_vars.append('SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY')
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Run migration
    migration = ProblemGeneratorMigration(dry_run=args.dry_run)
    success = migration.run()
    
    if success:
        logger.info("Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
