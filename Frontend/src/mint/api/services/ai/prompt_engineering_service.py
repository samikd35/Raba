"""
Prompt Engineering Service for Report Chat Feature

This module provides functionality for creating and managing prompts for the report chat feature.
It handles system prompt design, dynamic prompt assembly with retrieved context, and citation instructions.
"""

from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

class PromptEngineeringService:
    """Service for creating and managing prompts for the report chat feature."""
    
    def __init__(self):
        """Initialize the prompt engineering service."""
        self.system_prompt_template = self._get_system_prompt_template()
    
    def _get_system_prompt_template(self) -> str:
        """
        Get the system prompt template for report question answering.
        
        Returns:
            str: The system prompt template.
        """
        return """
You are an AI assistant helping users understand their market validation report. 
Your task is to answer questions about the report content accurately and helpfully.

Follow these guidelines:
1. Base your answers ONLY on the provided report chunks.
2. If the information is not in the provided chunks, say you don't have that information.
3. ALWAYS cite your sources using [1], [2], etc. format, where the number corresponds to the chunk index.
4. When citing multiple chunks for a single statement, use [1,2,3] format.
5. Be concise and direct in your answers.
6. Do not make up information or use external knowledge not present in the chunks.
7. If the user asks about something unrelated to the report, politely redirect them to ask about the report content.
8. Format your response in a clear, readable way using markdown when appropriate.

Remember: Accuracy and proper citation are the most important aspects of your responses.
"""
    
    def create_prompt(self, 
                     user_query: str, 
                     context_chunks: List[Dict[str, Any]], 
                     chat_history: Optional[List[Dict[str, Any]]] = None,
                     web_search_enabled: bool = False) -> Dict[str, Any]:
        """
        Create a complete prompt for the LLM including system prompt, context, and user query.
        
        Args:
            user_query: The user's question about the report
            context_chunks: List of retrieved context chunks with their indices
            chat_history: Optional list of previous chat messages
            web_search_enabled: Whether web search is enabled for this query
            
        Returns:
            Dict containing the formatted prompt for the LLM
        """
        # Format context chunks for the prompt
        formatted_chunks = self._format_context_chunks(context_chunks)
        
        # Create the complete prompt
        prompt = {
            "system": self.system_prompt_template,
            "messages": []
        }
        
        # Add chat history if provided
        if chat_history and len(chat_history) > 0:
            for message in chat_history:
                prompt["messages"].append({
                    "role": message["role"],
                    "content": message["content"]
                })
        
        # Add context and user query
        context_message = f"""
Here are the relevant sections from the report:

{formatted_chunks}

Remember to cite these chunks using [chunk_index] format when referring to them in your answer.
"""
        
        # Add web search instruction if enabled
        if web_search_enabled:
            context_message += "\nYou may also use web search to supplement your answer if the report doesn't contain the information, but clearly indicate when information comes from web search rather than the report."
        
        # Add context as a system message
        prompt["messages"].append({
            "role": "system",
            "content": context_message
        })
        
        # Add user query
        prompt["messages"].append({
            "role": "user",
            "content": user_query
        })
        
        return prompt
    
    def _format_context_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format context chunks for inclusion in the prompt.
        
        Args:
            chunks: List of context chunks with their indices
            
        Returns:
            str: Formatted context chunks
        """
        formatted_chunks = ""
        
        for chunk in chunks:
            chunk_index = chunk.get("chunk_index", 0)
            content = chunk.get("content", "")
            formatted_chunks += f"[{chunk_index}] {content}\n\n"
        
        return formatted_chunks
    
    def get_citation_instructions(self) -> str:
        """
        Get specific citation instructions for the LLM.
        
        Returns:
            str: Citation instructions
        """
        return """
When citing information from the report chunks, use the following format:
- For a single chunk citation: [1]
- For multiple chunk citations: [1,2,3]
- Place citations immediately after the relevant statement
- Ensure all factual statements from the report have citations
- Do not cite for general knowledge or your own reasoning
"""
    
    def customize_prompt_for_query_type(self, prompt: Dict[str, Any], query_type: str) -> Dict[str, Any]:
        """
        Customize the prompt based on the detected query type.
        
        Args:
            prompt: The base prompt
            query_type: The detected type of query (e.g., "summary", "comparison", "explanation")
            
        Returns:
            Dict: The customized prompt
        """
        # Add specific instructions based on query type
        if query_type == "summary":
            prompt["messages"].insert(0, {
                "role": "system",
                "content": "The user is asking for a summary. Provide a concise summary with key points, ensuring all information is cited properly."
            })
        elif query_type == "comparison":
            prompt["messages"].insert(0, {
                "role": "system",
                "content": "The user is asking for a comparison. Structure your response with clear comparison points, citing evidence for each point."
            })
        elif query_type == "explanation":
            prompt["messages"].insert(0, {
                "role": "system",
                "content": "The user is asking for an explanation. Provide a clear, step-by-step explanation with proper citations."
            })
            
        return prompt