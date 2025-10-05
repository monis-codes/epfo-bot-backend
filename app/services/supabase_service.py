"""
Supabase service for EPFO Bot Backend.
Handles all database operations including chat history storage.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from supabase import create_client, Client
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for handling Supabase database operations."""
    
    def __init__(self):
        """Initialize the Supabase service."""
        self.settings = get_settings()
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """
        Initialize the Supabase client.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            self.client = create_client(
                self.settings.supabase_url,
                self.settings.supabase_key
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise Exception(f"Supabase initialization failed: {str(e)}")
    
    def initialize_supabase_client(self, url: str, key: str) -> Client:
        """
        Initialize Supabase client with provided credentials.
        This function is kept for backward compatibility.
        
        Args:
            url: Supabase project URL
            key: Supabase project key
            
        Returns:
            Client: The Supabase client
            
        Note:
            This function is deprecated. Use the constructor instead.
        """
        logger.warning("initialize_supabase_client is deprecated. Use constructor instead.")
        return create_client(url, key)
    
    def save_chat_to_db(
        self, 
        user_id: str, 
        user_query: str, 
        bot_response: str, 
        context: Optional[str] = None
    ) -> None:
        """
        Save chat interaction to the database.
        
        Args:
            user_id: The user's ID from Supabase auth
            user_query: The user's question
            bot_response: The bot's response
            context: Optional source context used for the response
            
        Raises:
            Exception: If the database operation fails
        """
        try:
            if not self.client:
                raise Exception("Supabase client not initialized")
            
            # Prepare the data for insertion
            chat_data = {
                "user_id": user_id,
                "user_message": user_query,
                "bot_response": bot_response,
                "source_context": context,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Insert into chat_history table
            result = self.client.table("chat_history").insert(chat_data).execute()
            
            if result.data:
                logger.info(f"Successfully saved chat interaction for user {user_id}")
            else:
                logger.warning(f"No data returned when saving chat for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to save chat to database: {str(e)}")
            raise Exception(f"Database operation failed: {str(e)}")
    
    def get_user_chat_history(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chat history for a specific user.
        
        Args:
            user_id: The user's ID
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List[Dict[str, Any]]: List of chat history records
            
        Raises:
            Exception: If the database operation fails
        """
        try:
            if not self.client:
                raise Exception("Supabase client not initialized")
            
            result = (
                self.client.table("chat_history")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to retrieve chat history: {str(e)}")
            raise Exception(f"Database operation failed: {str(e)}")
    
    def get_chat_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get chat statistics for analytics.
        
        Args:
            user_id: Optional user ID to get stats for specific user
            
        Returns:
            Dict[str, Any]: Statistics data
            
        Raises:
            Exception: If the database operation fails
        """
        try:
            if not self.client:
                raise Exception("Supabase client not initialized")
            
            query = self.client.table("chat_history").select("*")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.execute()
            chats = result.data or []
            
            # Calculate statistics
            total_chats = len(chats)
            total_users = len(set(chat["user_id"] for chat in chats)) if chats else 0
            
            # Get recent activity (last 24 hours)
            recent_chats = [
                chat for chat in chats 
                if datetime.fromisoformat(chat["created_at"].replace('Z', '+00:00')) > 
                   datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            ]
            
            stats = {
                "total_chats": total_chats,
                "total_users": total_users,
                "recent_chats_24h": len(recent_chats),
                "average_response_length": sum(len(chat.get("bot_response", "")) for chat in chats) / total_chats if total_chats > 0 else 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get chat statistics: {str(e)}")
            raise Exception(f"Database operation failed: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        Test the connection to Supabase.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            if not self.client:
                return False
            
            # Try to query the chat_history table
            result = self.client.table("chat_history").select("id").limit(1).execute()
            return True
            
        except Exception as e:
            logger.error(f"Supabase connection test failed: {str(e)}")
            return False


# Global Supabase service instance
_supabase_service: Optional[SupabaseService] = None


def get_supabase_service() -> SupabaseService:
    """
    Get the global Supabase service instance.
    Creates a new instance if one doesn't exist.
    
    Returns:
        SupabaseService: The Supabase service instance
    """
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service
