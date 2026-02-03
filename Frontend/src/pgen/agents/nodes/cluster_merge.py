"""
Cluster Merge Node

Node 6 in the Problem Generator agent graph.
Clusters embedded passages using K-means and creates 6-8 thematic clusters.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Tuple
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config

from ..graph_state import ProblemGraphState

logger = logging.getLogger(__name__)


@traceable(name="cluster_merge_node")
def cluster_merge_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 6: Cluster Merge
    
    Clusters embedded passages using K-means and creates 6-8 thematic clusters.
    
    Args:
        state: Current workflow state with embedded passages
        
    Returns:
        Updated workflow state with clustered passages
    """
    logger.info("Starting passage clustering")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "cluster_merge"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        clustering_config = agent_config.get("clustering", {})
        
        # Get embedded passages
        embedded_passages = state.get("embedded_passages", [])
        if not embedded_passages:
            logger.warning("No embedded passages found for clustering")
            state["clusters"] = []
            return state
        
        logger.info(f"Clustering {len(embedded_passages)} embedded passages")
        
        # =============================================
        # PREPARE EMBEDDINGS FOR CLUSTERING
        # =============================================
        
        # Extract embeddings and validate
        embeddings = []
        valid_passages = []
        
        for passage in embedded_passages:
            embedding = passage.get("embedding")
            if embedding and isinstance(embedding, list) and len(embedding) > 0:
                embeddings.append(embedding)
                valid_passages.append(passage)
            else:
                logger.warning(f"Invalid embedding found in passage: {passage.get('text', '')[:50]}...")
        
        if len(embeddings) < 2:
            logger.warning(f"Insufficient valid embeddings ({len(embeddings)}) for clustering")
            # Return single cluster with all passages
            single_cluster = {
                "id": 0,
                "theme": "General Problems",
                "passages": valid_passages,
                "size": len(valid_passages),
                "centroid": None,
                "avg_relevance": calculate_avg_relevance(valid_passages)
            }
            state["clusters"] = [single_cluster]
            return state
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings)
        logger.info(f"Prepared {len(embeddings)} embeddings for clustering (dimension: {embeddings_array.shape[1]})")
        
        # =============================================
        # DETERMINE OPTIMAL NUMBER OF CLUSTERS
        # =============================================
        
        # Configure cluster range
        min_clusters = clustering_config.get("min_clusters", 3)
        max_clusters = clustering_config.get("max_clusters", 8)
        target_clusters = clustering_config.get("target_clusters", 6)
        
        # Adjust range based on data size
        max_possible_clusters = min(len(embeddings) // 2, max_clusters)
        if max_possible_clusters < min_clusters:
            max_possible_clusters = min_clusters
        
        # Find optimal number of clusters
        optimal_k = find_optimal_clusters(
            embeddings_array, 
            min_k=min_clusters,
            max_k=max_possible_clusters,
            target_k=target_clusters
        )
        
        logger.info(f"Selected {optimal_k} clusters for {len(embeddings)} passages")
        
        # =============================================
        # PERFORM CLUSTERING
        # =============================================
        
        # Initialize and fit K-means
        kmeans = KMeans(
            n_clusters=optimal_k,
            random_state=42,
            n_init=10,
            max_iter=300
        )
        
        cluster_labels = kmeans.fit_predict(embeddings_array)
        centroids = kmeans.cluster_centers_
        
        # Calculate clustering quality metrics
        if len(set(cluster_labels)) > 1:
            silhouette_avg = silhouette_score(embeddings_array, cluster_labels)
        else:
            silhouette_avg = 0.0
        
        # =============================================
        # CREATE CLUSTER OBJECTS
        # =============================================
        
        clusters = []
        
        for cluster_id in range(optimal_k):
            # Get passages in this cluster
            cluster_passages = [
                valid_passages[i] for i, label in enumerate(cluster_labels) 
                if label == cluster_id
            ]
            
            if not cluster_passages:
                continue
            
            # Generate cluster theme with user context for specificity
            user_params = state.get("params", {})
            user_industry = user_params.get("industry", [""])
            user_industry_str = user_industry[0] if user_industry else ""
            user_geography = user_params.get("geography", [""])
            user_geography_str = user_geography[0] if user_geography else ""
            
            theme = generate_cluster_theme(
                cluster_passages, 
                cluster_id,
                user_industry=user_industry_str,
                user_geography=user_geography_str
            )
            
            # Calculate cluster statistics
            avg_relevance = calculate_avg_relevance(cluster_passages)
            
            # Create cluster object
            cluster = {
                "id": cluster_id,
                "theme": theme,
                "passages": cluster_passages,
                "size": len(cluster_passages),
                "centroid": centroids[cluster_id].tolist(),
                "avg_relevance": avg_relevance,
                "created_at": datetime.now().isoformat()
            }
            
            clusters.append(cluster)
        
        # Sort clusters by size (largest first)
        clusters.sort(key=lambda x: x["size"], reverse=True)
        
        # =============================================
        # STORE RESULTS
        # =============================================
        
        state["clusters"] = clusters
        
        # Add clustering statistics
        clustering_stats = {
            "total_passages": len(embedded_passages),
            "clustered_passages": len(valid_passages),
            "num_clusters": len(clusters),
            "silhouette_score": silhouette_avg,
            "cluster_sizes": [cluster["size"] for cluster in clusters],
            "avg_cluster_size": len(valid_passages) / max(len(clusters), 1)
        }
        
        state["clustering_stats"] = clustering_stats
        
        # Add processing metrics
        total_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        clustering_metrics = {
            "passages_clustered": len(valid_passages),
            "clusters_created": len(clusters),
            "optimal_k": optimal_k,
            "silhouette_score": silhouette_avg,
            "processing_time_ms": total_time
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["cluster_merge"] = clustering_metrics
        
        logger.info(f"Passage clustering completed successfully")
        logger.info(f"Created {len(clusters)} clusters from {len(valid_passages)} passages")
        logger.info(f"Silhouette score: {silhouette_avg:.3f}")
        
        # Log cluster summary
        for cluster in clusters:
            logger.info(f"Cluster {cluster['id']}: {cluster['theme']} ({cluster['size']} passages)")
        
        return state
        
    except Exception as e:
        error_msg = f"Passage clustering failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state


def find_optimal_clusters(embeddings: np.ndarray, min_k: int, max_k: int, target_k: int) -> int:
    """
    Find optimal number of clusters using elbow method and silhouette analysis.
    
    Args:
        embeddings: Embedding vectors
        min_k: Minimum number of clusters
        max_k: Maximum number of clusters
        target_k: Target number of clusters
        
    Returns:
        Optimal number of clusters
    """
    try:
        # If we have very few data points, use minimal clustering
        if len(embeddings) < 6:
            return min(len(embeddings) // 2, max_k)
        
        # If target is within range and reasonable, use it
        if min_k <= target_k <= max_k and target_k <= len(embeddings) // 2:
            return target_k
        
        # Test different k values
        k_range = range(min_k, min(max_k + 1, len(embeddings) // 2 + 1))
        
        if len(k_range) == 0:
            return min_k
        
        if len(k_range) == 1:
            return k_range[0]
        
        # Calculate silhouette scores for different k values
        silhouette_scores = []
        
        for k in k_range:
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=5)
                labels = kmeans.fit_predict(embeddings)
                
                if len(set(labels)) > 1:
                    score = silhouette_score(embeddings, labels)
                    silhouette_scores.append(score)
                else:
                    silhouette_scores.append(0.0)
                    
            except Exception:
                silhouette_scores.append(0.0)
        
        # Find k with highest silhouette score
        if silhouette_scores:
            best_k_idx = np.argmax(silhouette_scores)
            optimal_k = list(k_range)[best_k_idx]
            
            logger.debug(f"Silhouette scores: {dict(zip(k_range, silhouette_scores))}")
            logger.debug(f"Selected k={optimal_k} with silhouette score {silhouette_scores[best_k_idx]:.3f}")
            
            return optimal_k
        
        # Fallback to target
        return target_k
        
    except Exception as e:
        logger.warning(f"Error in optimal cluster selection: {str(e)}")
        return target_k


def generate_cluster_theme(
    passages: List[Dict[str, Any]], 
    cluster_id: int,
    user_industry: str = "",
    user_geography: str = ""
) -> str:
    """
    Generate a descriptive theme for a cluster based on its passages and user context.
    
    Generates specific themes like "Ethiopian Healthcare Access Barriers" instead of
    generic themes like "Healthcare Problems" by incorporating user's industry and geography.
    
    Args:
        passages: List of passages in the cluster
        cluster_id: Cluster identifier
        user_industry: User's specified industry for context
        user_geography: User's specified geography for context
        
    Returns:
        Cluster theme string with geography and industry context
    """
    try:
        # Extract keywords and context from passages
        all_text = ""
        industries = []
        locations = []
        problem_types = []  # Collect specific problem types
        
        for passage in passages:
            text = passage.get("text", "")
            context = passage.get("context", "")
            all_text += f" {text} {context}"
            
            if passage.get("industry"):
                industries.append(passage["industry"])
            if passage.get("location"):
                locations.append(passage["location"])
        
        all_text_lower = all_text.lower()
        
        # Problem type keywords - more specific than sector themes
        problem_type_keywords = {
            "Access Barriers": ["access", "unable to access", "lack of access", "limited access", "inaccessible"],
            "Funding Gaps": ["funding", "financing", "capital", "investment", "credit", "loan"],
            "Infrastructure Deficits": ["infrastructure", "facility", "equipment", "building", "roads"],
            "Supply Chain Issues": ["supply chain", "distribution", "logistics", "transport", "delivery"],
            "Skill Shortages": ["skill", "training", "education", "capacity", "expertise", "qualified"],
            "Market Inefficiencies": ["market", "pricing", "middlemen", "transparency", "information"],
            "Quality Challenges": ["quality", "standard", "reliability", "consistency", "substandard"],
            "Technology Gaps": ["technology", "digital", "mobile", "internet", "connectivity", "app"],
            "Regulatory Barriers": ["regulation", "policy", "license", "permit", "bureaucracy", "compliance"],
            "Resource Scarcity": ["shortage", "scarcity", "insufficient", "limited", "lack of"]
        }
        
        # Sector-specific theme keywords
        sector_keywords = {
            "Healthcare": ["health", "medical", "hospital", "doctor", "disease", "treatment", "clinic", "patient"],
            "Education": ["education", "school", "student", "learning", "teacher", "university", "training"],
            "Agriculture": ["agriculture", "farming", "crop", "farmer", "food", "harvest", "livestock", "agri"],
            "Finance": ["finance", "banking", "money", "credit", "loan", "payment", "fintech", "savings"],
            "Energy": ["energy", "power", "electricity", "solar", "fuel", "battery", "renewable"],
            "Water": ["water", "sanitation", "clean water", "drinking", "well", "pump", "wash"],
            "Transportation": ["transport", "road", "vehicle", "traffic", "mobility", "logistics", "delivery"],
            "Technology": ["technology", "digital", "internet", "mobile", "app", "software", "ict"],
            "Sports": ["sports", "athletics", "fitness", "recreation", "gym", "exercise", "training facilities"],
            "Retail": ["retail", "commerce", "shopping", "store", "merchant", "e-commerce"]
        }
        
        # Find best matching problem type
        problem_scores = {}
        for problem_type, keywords in problem_type_keywords.items():
            score = sum(1 for keyword in keywords if keyword in all_text_lower)
            if score > 0:
                problem_scores[problem_type] = score
        
        best_problem = "Challenges"  # Default
        if problem_scores:
            best_problem = max(problem_scores.items(), key=lambda x: x[1])[0]
        
        # Find best matching sector (prefer user's industry if it matches)
        sector_scores = {}
        for sector, keywords in sector_keywords.items():
            score = sum(1 for keyword in keywords if keyword in all_text_lower)
            # Boost score if it matches user's specified industry
            if user_industry and user_industry.lower() in sector.lower():
                score += 5
            if score > 0:
                sector_scores[sector] = score
        
        best_sector = user_industry if user_industry else "General"  # Default to user's industry
        if sector_scores:
            best_sector = max(sector_scores.items(), key=lambda x: x[1])[0]
        
        # Determine geography - prioritize user's geography, then passage locations
        best_geography = user_geography if user_geography else ""
        if not best_geography and locations:
            best_geography = max(set(locations), key=locations.count)
        
        # Build theme with format: "[Geography] [Sector] [Problem Type]"
        # Examples: "Ethiopian Healthcare Access Barriers", "Nigerian Fintech Funding Gaps"
        theme_parts = []
        
        if best_geography:
            # Add adjective form of geography if possible
            geo_adjectives = {
                "Ethiopia": "Ethiopian",
                "Kenya": "Kenyan",
                "Nigeria": "Nigerian",
                "Ghana": "Ghanaian",
                "South Africa": "South African",
                "Tanzania": "Tanzanian",
                "Uganda": "Ugandan",
                "Rwanda": "Rwandan",
                "Senegal": "Senegalese",
                "Egypt": "Egyptian",
                "Morocco": "Moroccan"
            }
            geo_adj = geo_adjectives.get(best_geography, best_geography)
            theme_parts.append(geo_adj)
        
        theme_parts.append(best_sector)
        theme_parts.append(best_problem)
        
        return " ".join(theme_parts)
        
    except Exception as e:
        logger.warning(f"Error generating cluster theme: {str(e)}")
        # Fallback with user context
        if user_geography and user_industry:
            return f"{user_geography} {user_industry} Challenges"
        return f"Problem Cluster {cluster_id + 1}"


def calculate_avg_relevance(passages: List[Dict[str, Any]]) -> float:
    """
    Calculate average relevance score for passages in a cluster.
    
    Args:
        passages: List of passages
        
    Returns:
        Average relevance score
    """
    try:
        scores = [passage.get("relevance_score", 0) for passage in passages]
        valid_scores = [score for score in scores if isinstance(score, (int, float)) and score > 0]
        
        if not valid_scores:
            return 0.0
        
        return sum(valid_scores) / len(valid_scores)
        
    except Exception:
        return 0.0
