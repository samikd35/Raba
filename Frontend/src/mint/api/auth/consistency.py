"""
API Endpoint Authentication Consistency Audit

This script audits all API endpoints for consistent authentication patterns,
identifies inconsistencies, and provides recommendations for improvements.

Implements requirement 5.1 from the auth-connection-fixes specification.
"""

import os
import ast
import logging
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from .models import AuthPatternType, EndpointInfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# AuthPatternType and EndpointInfo are now imported from models


class AuthConsistencyAuditor:
    """
    Auditor for API endpoint authentication consistency.
    
    This class analyzes all API endpoint files to identify:
    - Authentication patterns used
    - Error handling consistency
    - Logging patterns
    - Inconsistencies and issues
    - Recommendations for improvements
    """
    
    def __init__(self, api_dir: str = "Backend/src/mint/api"):
        """
        Initialize the authentication consistency auditor.
        
        Args:
            api_dir: Directory containing API endpoint files
        """
        self.api_dir = Path(api_dir)
        self.endpoints: List[EndpointInfo] = []
        self.auth_patterns: Dict[AuthPatternType, int] = {}
        self.issues_summary: Dict[str, int] = {}
        
        logger.info(f"AuthConsistencyAuditor initialized for directory: {api_dir}")
    
    def audit_all_endpoints(self) -> Dict[str, Any]:
        """
        Audit all API endpoints for authentication consistency.
        
        Returns:
            Dict: Comprehensive audit report
        """
        logger.info("Starting comprehensive authentication consistency audit")
        
        # Find all Python files in the API directory
        api_files = list(self.api_dir.glob("*.py"))
        endpoint_files = [f for f in api_files if self._is_endpoint_file(f)]
        
        logger.info(f"Found {len(endpoint_files)} endpoint files to audit")
        
        # Audit each endpoint file
        for file_path in endpoint_files:
            try:
                self._audit_file(file_path)
            except Exception as e:
                logger.error(f"Error auditing file {file_path}: {e}")
        
        # Generate summary statistics
        self._generate_statistics()
        
        # Create comprehensive report
        report = self._create_audit_report()
        
        logger.info(f"Audit completed. Found {len(self.endpoints)} endpoints with {len(self.issues_summary)} types of issues")
        
        return report
    
    def _is_endpoint_file(self, file_path: Path) -> bool:
        """
        Determine if a file contains API endpoints.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            bool: True if file contains endpoints
        """
        # Skip certain files that don't contain endpoints
        skip_files = {
            "__init__.py", "auth.py", "supabase_client.py", "utils.py",
            "unified_auth_handler.py", "enhanced_auth_dependencies.py",
            "auth_consistency_audit.py"
        }
        
        if file_path.name in skip_files:
            return False
        
        # Check if file contains FastAPI router or endpoint decorators
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return any(pattern in content for pattern in [
                    "@router.", "@app.", "APIRouter", "FastAPI"
                ])
        except Exception:
            return False
    
    def _audit_file(self, file_path: Path) -> None:
        """
        Audit a single endpoint file for authentication patterns.
        
        Args:
            file_path: Path to the endpoint file
        """
        logger.debug(f"Auditing file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST to find endpoint functions
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    endpoint_info = self._analyze_endpoint_function(
                        node, content, str(file_path)
                    )
                    if endpoint_info:
                        self.endpoints.append(endpoint_info)
                        
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
    
    def _analyze_endpoint_function(
        self, 
        func_node: ast.FunctionDef, 
        file_content: str, 
        file_path: str
    ) -> Optional[EndpointInfo]:
        """
        Analyze a function to determine if it's an API endpoint and its auth pattern.
        
        Args:
            func_node: AST node for the function
            file_content: Full file content
            file_path: Path to the file
            
        Returns:
            EndpointInfo: Information about the endpoint, or None if not an endpoint
        """
        # Check if function has route decorators
        route_info = self._extract_route_info(func_node, file_content)
        if not route_info:
            return None
        
        # Analyze authentication dependencies
        auth_deps = self._extract_auth_dependencies(func_node)
        auth_pattern = self._determine_auth_pattern(auth_deps)
        
        # Analyze error handling patterns
        error_handling = self._extract_error_handling(func_node, file_content)
        
        # Analyze logging patterns
        logging_patterns = self._extract_logging_patterns(func_node, file_content)
        
        # Identify issues and recommendations
        issues, recommendations = self._identify_issues_and_recommendations(
            auth_pattern, auth_deps, error_handling, logging_patterns
        )
        
        return EndpointInfo(
            file_path=file_path,
            function_name=func_node.name,
            route_path=route_info.get("path", "unknown"),
            http_method=route_info.get("method", "unknown"),
            auth_pattern=auth_pattern,
            auth_dependencies=auth_deps,
            error_handling=error_handling,
            logging_patterns=logging_patterns,
            issues=issues,
            recommendations=recommendations
        )
    
    def _extract_route_info(self, func_node: ast.FunctionDef, file_content: str) -> Optional[Dict[str, str]]:
        """
        Extract route information from function decorators.
        
        Args:
            func_node: AST node for the function
            file_content: Full file content
            
        Returns:
            Dict: Route information or None if not a route
        """
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                # Handle @router.get, @router.post, etc.
                if hasattr(decorator, 'attr') and decorator.attr in ['get', 'post', 'put', 'delete', 'patch']:
                    return {
                        "method": decorator.attr.upper(),
                        "path": "extracted_from_decorator"
                    }
            elif isinstance(decorator, ast.Call):
                # Handle @router.get("/path"), etc.
                if (isinstance(decorator.func, ast.Attribute) and 
                    hasattr(decorator.func, 'attr') and 
                    decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']):
                    path = "unknown"
                    if decorator.args:
                        if isinstance(decorator.args[0], ast.Str):
                            path = decorator.args[0].s
                        elif isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                            path = decorator.args[0].value
                    return {
                        "method": decorator.func.attr.upper(),
                        "path": path
                    }
        
        # Also check for async def functions that might be endpoints based on naming
        if func_node.name.startswith(('get_', 'post_', 'put_', 'delete_', 'patch_')):
            return {
                "method": func_node.name.split('_')[0].upper(),
                "path": f"inferred_from_function_name_{func_node.name}"
            }
        
        return None
    
    def _extract_auth_dependencies(self, func_node: ast.FunctionDef) -> List[str]:
        """
        Extract authentication dependencies from function parameters.
        
        Args:
            func_node: AST node for the function
            
        Returns:
            List: Authentication dependency names
        """
        auth_deps = []
        
        for arg in func_node.args.args:
            # Check parameter names for auth-related patterns
            if any(pattern in arg.arg.lower() for pattern in [
                'current_user', 'user_id', 'admin', 'api_key', 'credentials', 'auth'
            ]):
                auth_deps.append(f"param_{arg.arg}")
            
            # Check annotations for Depends() calls
            if hasattr(arg, 'annotation') and arg.annotation:
                if isinstance(arg.annotation, ast.Call):
                    if (isinstance(arg.annotation.func, ast.Name) and 
                        arg.annotation.func.id == 'Depends'):
                        if arg.annotation.args:
                            dep_arg = arg.annotation.args[0]
                            if isinstance(dep_arg, ast.Name):
                                auth_deps.append(dep_arg.id)
                            elif isinstance(dep_arg, ast.Attribute):
                                if hasattr(dep_arg.value, 'id'):
                                    auth_deps.append(f"{dep_arg.value.id}.{dep_arg.attr}")
                                else:
                                    auth_deps.append(f"unknown.{dep_arg.attr}")
        
        return auth_deps
    
    def _determine_auth_pattern(self, auth_deps: List[str]) -> AuthPatternType:
        """
        Determine the authentication pattern based on dependencies.
        
        Args:
            auth_deps: List of authentication dependencies
            
        Returns:
            AuthPatternType: Determined authentication pattern
        """
        if not auth_deps:
            return AuthPatternType.NO_AUTH
        
        # Categorize dependencies
        api_key_deps = [dep for dep in auth_deps if 'api_key' in dep.lower()]
        user_deps = [dep for dep in auth_deps if any(pattern in dep.lower() for pattern in [
            'current_user', 'get_user', 'user_context'
        ])]
        admin_deps = [dep for dep in auth_deps if 'admin' in dep.lower()]
        
        # Determine pattern
        if api_key_deps and not user_deps and not admin_deps:
            return AuthPatternType.API_KEY
        elif admin_deps:
            return AuthPatternType.ADMIN_TOKEN
        elif user_deps:
            return AuthPatternType.USER_TOKEN
        elif len(set([dep.split('.')[0] for dep in auth_deps])) > 1:
            return AuthPatternType.MIXED
        else:
            return AuthPatternType.UNKNOWN
    
    def _extract_error_handling(self, func_node: ast.FunctionDef, file_content: str) -> List[str]:
        """
        Extract error handling patterns from function body.
        
        Args:
            func_node: AST node for the function
            file_content: Full file content
            
        Returns:
            List: Error handling patterns found
        """
        error_patterns = []
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Raise):
                if isinstance(node.exc, ast.Call):
                    if isinstance(node.exc.func, ast.Name):
                        if node.exc.func.id == 'HTTPException':
                            error_patterns.append("HTTPException")
            elif isinstance(node, ast.Try):
                error_patterns.append("try_except_block")
        
        return error_patterns
    
    def _extract_logging_patterns(self, func_node: ast.FunctionDef, file_content: str) -> List[str]:
        """
        Extract logging patterns from function body.
        
        Args:
            func_node: AST node for the function
            file_content: Full file content
            
        Returns:
            List: Logging patterns found
        """
        logging_patterns = []
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if (isinstance(node.func.value, ast.Name) and 
                        node.func.value.id == 'logger'):
                        logging_patterns.append(f"logger.{node.func.attr}")
        
        return logging_patterns
    
    def _identify_issues_and_recommendations(
        self,
        auth_pattern: AuthPatternType,
        auth_deps: List[str],
        error_handling: List[str],
        logging_patterns: List[str]
    ) -> tuple[List[str], List[str]]:
        """
        Identify issues and provide recommendations for an endpoint.
        
        Args:
            auth_pattern: Authentication pattern used
            auth_deps: Authentication dependencies
            error_handling: Error handling patterns
            logging_patterns: Logging patterns
            
        Returns:
            Tuple: (issues, recommendations)
        """
        issues = []
        recommendations = []
        
        # Check for authentication issues
        if auth_pattern == AuthPatternType.NO_AUTH:
            issues.append("no_authentication")
            recommendations.append("Add appropriate authentication dependency")
        elif auth_pattern == AuthPatternType.MIXED:
            issues.append("mixed_auth_patterns")
            recommendations.append("Use consistent authentication pattern")
        elif auth_pattern == AuthPatternType.UNKNOWN:
            issues.append("unknown_auth_pattern")
            recommendations.append("Use standard authentication dependencies")
        
        # Check for error handling issues
        if not error_handling:
            issues.append("no_error_handling")
            recommendations.append("Add proper error handling with HTTPException")
        elif "HTTPException" not in error_handling:
            issues.append("non_standard_error_handling")
            recommendations.append("Use HTTPException for consistent error responses")
        
        # Check for logging issues
        if not logging_patterns:
            issues.append("no_logging")
            recommendations.append("Add authentication event logging")
        elif not any("info" in pattern or "warning" in pattern or "error" in pattern 
                    for pattern in logging_patterns):
            issues.append("insufficient_logging")
            recommendations.append("Add comprehensive authentication logging")
        
        # Check for deprecated dependencies
        deprecated_deps = [dep for dep in auth_deps if any(old in dep for old in [
            "get_api_key", "simple_auth"
        ])]
        if deprecated_deps:
            issues.append("deprecated_auth_dependencies")
            recommendations.append("Update to use enhanced authentication dependencies")
        
        return issues, recommendations
    
    def _generate_statistics(self) -> None:
        """Generate summary statistics from the audit."""
        # Count authentication patterns
        for endpoint in self.endpoints:
            pattern = endpoint.auth_pattern
            self.auth_patterns[pattern] = self.auth_patterns.get(pattern, 0) + 1
            
            # Count issues
            for issue in endpoint.issues:
                self.issues_summary[issue] = self.issues_summary.get(issue, 0) + 1
    
    def _create_audit_report(self) -> Dict[str, Any]:
        """
        Create a comprehensive audit report.
        
        Returns:
            Dict: Comprehensive audit report
        """
        return {
            "summary": {
                "total_endpoints": len(self.endpoints),
                "auth_patterns": {pattern.value: count for pattern, count in self.auth_patterns.items()},
                "total_issues": sum(self.issues_summary.values()),
                "issues_by_type": self.issues_summary,
                "endpoints_with_issues": len([e for e in self.endpoints if e.issues]),
                "endpoints_without_issues": len([e for e in self.endpoints if not e.issues])
            },
            "detailed_findings": [
                {
                    "file_path": endpoint.file_path,
                    "function_name": endpoint.function_name,
                    "route_path": endpoint.route_path,
                    "http_method": endpoint.http_method,
                    "auth_pattern": endpoint.auth_pattern.value,
                    "auth_dependencies": endpoint.auth_dependencies,
                    "error_handling": endpoint.error_handling,
                    "logging_patterns": endpoint.logging_patterns,
                    "issues": endpoint.issues,
                    "recommendations": endpoint.recommendations
                }
                for endpoint in self.endpoints
            ],
            "recommendations": self._generate_global_recommendations(),
            "audit_metadata": {
                "audit_timestamp": "2025-01-26T00:00:00Z",
                "auditor_version": "1.0.0",
                "api_directory": str(self.api_dir)
            }
        }
    
    def _generate_global_recommendations(self) -> List[str]:
        """
        Generate global recommendations based on audit findings.
        
        Returns:
            List: Global recommendations
        """
        recommendations = []
        
        # Authentication pattern recommendations
        if self.auth_patterns.get(AuthPatternType.NO_AUTH, 0) > 0:
            recommendations.append(
                "Implement authentication for all endpoints that handle user data"
            )
        
        if self.auth_patterns.get(AuthPatternType.MIXED, 0) > 0:
            recommendations.append(
                "Standardize authentication patterns across all endpoints"
            )
        
        # Error handling recommendations
        if self.issues_summary.get("no_error_handling", 0) > 0:
            recommendations.append(
                "Implement consistent error handling using unified auth handler"
            )
        
        # Logging recommendations
        if self.issues_summary.get("no_logging", 0) > 0:
            recommendations.append(
                "Add comprehensive authentication event logging to all endpoints"
            )
        
        # Dependency recommendations
        if self.issues_summary.get("deprecated_auth_dependencies", 0) > 0:
            recommendations.append(
                "Update all endpoints to use enhanced authentication dependencies"
            )
        
        # Overall consistency recommendation
        recommendations.append(
            "Migrate all endpoints to use the unified authentication handler for consistency"
        )
        
        return recommendations
    
    def save_report(self, report: Dict[str, Any], output_file: str = "auth_audit_report.json") -> None:
        """
        Save the audit report to a file.
        
        Args:
            report: Audit report to save
            output_file: Output file path
        """
        import json
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Audit report saved to: {output_file}")
        except Exception as e:
            logger.error(f"Error saving audit report: {e}")


def main():
    """Run the authentication consistency audit."""
    auditor = AuthConsistencyAuditor()
    report = auditor.audit_all_endpoints()
    
    # Print summary
    print("\n" + "="*80)
    print("API ENDPOINT AUTHENTICATION CONSISTENCY AUDIT REPORT")
    print("="*80)
    
    summary = report["summary"]
    print(f"\nTotal Endpoints Audited: {summary['total_endpoints']}")
    print(f"Endpoints with Issues: {summary['endpoints_with_issues']}")
    print(f"Endpoints without Issues: {summary['endpoints_without_issues']}")
    print(f"Total Issues Found: {summary['total_issues']}")
    
    print("\nAuthentication Patterns:")
    for pattern, count in summary["auth_patterns"].items():
        print(f"  {pattern}: {count}")
    
    print("\nIssues by Type:")
    for issue, count in summary["issues_by_type"].items():
        print(f"  {issue}: {count}")
    
    print("\nGlobal Recommendations:")
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"  {i}. {rec}")
    
    # Save detailed report
    auditor.save_report(report)
    
    print(f"\nDetailed report saved to: auth_audit_report.json")
    print("="*80)


if __name__ == "__main__":
    main()