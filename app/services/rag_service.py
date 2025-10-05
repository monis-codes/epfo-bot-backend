"""
RAG (Retrieval-Augmented Generation) service for EPFO Bot Backend.
Encapsulates the pre-built RAG pipeline logic using Google AI services.
"""

import os
from typing import Tuple, Optional, Any
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
import logging

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class RAGService:
    """Service for handling RAG operations using Google AI and Pinecone."""
    
    def __init__(self):
        """Initialize the RAG service with required clients."""
        self.settings = get_settings()
        self.pinecone_client: Optional[Pinecone] = None
        self.index: Optional[Any] = None
        self._initialize_clients()
    
    def _initialize_clients(self) -> None:
        """
        Initialize Pinecone and Google AI clients.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            # Initialize Pinecone
            self.pinecone_client = Pinecone(api_key=self.settings.pinecone_api_key)
            
            # Get or create index
            if self.settings.pinecone_index_name not in self.pinecone_client.list_indexes().names():
                logger.info(f"Creating Pinecone index: {self.settings.pinecone_index_name}")
                self.pinecone_client.create_index(
                    name=self.settings.pinecone_index_name,
                    dimension=768,  # Google's text-embedding-004 dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.settings.pinecone_environment
                    )
                )
            
            self.index = self.pinecone_client.Index(self.settings.pinecone_index_name)
            
            # Configure Google AI
            genai.configure(api_key=self.settings.google_api_key)
            
            logger.info("RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {str(e)}")
            raise Exception(f"RAG service initialization failed: {str(e)}")
    
    def get_final_prompt_for_llm(self, user_query: str) -> Tuple[str, str]:
        """
        Retrieve relevant context and build final prompt for the LLM.
        
        Args:
            user_query: The user's question
            
        Returns:
            Tuple[str, str]: Final prompt and source context
            
        Raises:
            Exception: If retrieval or prompt building fails
        """
        try:
            if not self.index:
                raise Exception("Pinecone index not initialized")
            
            # Generate embedding for the user query
            search_embedding = genai.embed_content(
                model="models/text-embedding-004",
                content=user_query,
                task_type="RETRIEVAL_QUERY"
            )["embedding"]
            
            # Search Pinecone for relevant context
            matches = self.index.query(
                vector=search_embedding,
                top_k=8,
                include_metadata=True
            ).get("matches", [])
            
            if not matches:
                logger.warning(f"No relevant context found for query: {user_query}")
                return self._create_fallback_prompt(user_query), ""
            
            # Extract context from matches
            context_parts = []
            source_contexts = []
            
            for match in matches:
                if match.get("metadata", {}).get("text"):
                    context_parts.append(match["metadata"]["text"])
                    source_contexts.append(match["metadata"]["text"])
            
            if not context_parts:
                logger.warning(f"No text content found in matches for query: {user_query}")
                return self._create_fallback_prompt(user_query), ""
            
            # Combine context
            context = "\n\n---\n\n".join(context_parts)
            source_context = "\n\n".join(source_contexts)
            
            # Build final prompt
            final_prompt = self._build_prompt(user_query, context)
            
            logger.info(f"Successfully built prompt for query: {user_query[:50]}...")
            return final_prompt, source_context
            
        except Exception as e:
            logger.error(f"Error in get_final_prompt_for_llm: {str(e)}")
            raise Exception(f"Failed to retrieve context and build prompt: {str(e)}")
    
    def _build_prompt(self, user_query: str, context: str) -> str:
        """
        Build the final prompt for the LLM.
        
        Args:
            user_query: The user's question
            context: Retrieved context from Pinecone
            
        Returns:
            str: The final prompt
        """
        prompt = f"""You are Providentia, an expert EPFO (Employees' Provident Fund Organisation) assistant. Your role is to provide accurate, helpful, and comprehensive answers about EPF-related matters based on the provided context.

Instructions:
1. Answer ONLY based on the provided context
2. Be precise, concise, and professional
3. If the context doesn't contain enough information, clearly state what information is missing
4. Always cite relevant sections or rules when possible
5. Provide step-by-step guidance for complex procedures
6. Use simple language that's easy to understand

Context:
{context}

Question: {user_query}

Answer:"""
        
        return prompt
    
    def _create_fallback_prompt(self, user_query: str) -> str:
        """
        Create a fallback prompt when no context is found.
        
        Args:
            user_query: The user's question
            
        Returns:
            str: Fallback prompt
        """
        return f"""You are Providentia, an expert EPFO (Employees' Provident Fund Organisation) assistant. 

Question: {user_query}

Please provide a helpful response about EPF-related matters. If you need more specific information to give a complete answer, please let the user know what additional details would be helpful.

Answer:"""


# Global RAG service instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    Get the global RAG service instance.
    Creates a new instance if one doesn't exist.
    
    Returns:
        RAGService: The RAG service instance
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def initialize_rag_clients(pinecone_api_key: str, google_api_key: str) -> None:
    """
    Initialize RAG clients with provided API keys.
    This function is kept for backward compatibility.
    
    Args:
        pinecone_api_key: Pinecone API key
        google_api_key: Google API key
        
    Note:
        This function is deprecated. Use get_rag_service() instead.
    """
    logger.warning("initialize_rag_clients is deprecated. Use get_rag_service() instead.")
    # The service will use environment variables for configuration
    get_rag_service()
