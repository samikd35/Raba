#!/usr/bin/env python3
"""
Apply Data Analysis Agent Schema Migration

This script applies the database schema changes required for the Data Analysis Agent.
It adds the necessary columns to the projects table for storing research documents
and analysis results.
"""

import os
import sys
from pathlib import Path

# Add the Backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.mint.api.system.core.supabase_client import get_service_role_client


def apply_migration():
    """Apply the data analysis agent schema migration"""
    try:
        # Get service role client for admin operations
        supabase = get_service_role_client()
        
        # Read the migration SQL file
        migration_file = backend_dir / "supabase" / "yuba_migrations" / "011_data_analysis_agent_schema.sql"
        
        if not migration_file.exists():
            raise FileNotFoundError(f"Migration file not found: {migration_file}")
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("🔄 Applying Data Analysis Agent schema migration...")
        
        # Execute the migration
        result = supabase.client.rpc('exec_sql', {'sql': migration_sql}).execute()
        
        if result.data:
            print("✅ Migration applied successfully!")
            print(f"📊 Result: {result.data}")
        else:
            print("✅ Migration completed (no data returned)")
            
        # Verify the columns were added
        print("\n🔍 Verifying schema changes...")
        
        # Check if columns exist
        verify_sql = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'vmp_projects' 
        AND column_name IN ('research_documents_data', 'analysis_data', 'analysis_status')
        ORDER BY column_name;
        """
        
        verify_result = supabase.client.rpc('exec_sql', {'sql': verify_sql}).execute()
        
        if verify_result.data:
            print("📋 New columns added:")
            for row in verify_result.data:
                print(f"  - {row['column_name']}: {row['data_type']} (nullable: {row['is_nullable']}, default: {row['column_default']})")
        
        print("\n🎉 Data Analysis Agent schema migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    apply_migration()