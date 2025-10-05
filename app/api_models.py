"""
Pydantic models for API request and response validation.
Defines the data contracts for the EPFO Bot Backend API.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class ChatRequest(BaseModel):
    """
    Request model for the chat endpoint.
    Validates incoming user queries.
    """
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The user's question about EPFO-related topics",
        example="What is the minimum contribution period for EPF withdrawal?"
    )
    
    @validator('question')
    def validate_question(cls, v):
        """Validate that the question is not just whitespace."""
        if not v.strip():
            raise ValueError('Question cannot be empty or just whitespace')
        return v.strip()


class ChatResponse(BaseModel):
    """
    Response model for the chat endpoint.
    Contains the bot's answer and source context.
    """
    answer: str = Field(
        ...,
        description="The bot's response to the user's question",
        example="The minimum contribution period for EPF withdrawal is 5 years..."
    )
    source_context: Optional[str] = Field(
        None,
        description="The source context used to generate the answer",
        example="According to EPF Act 1952, Section 69..."
    )
    success: bool = Field(
        True,
        description="Indicates if the request was processed successfully"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if the request failed"
    )


class HealthResponse(BaseModel):
    """
    Response model for the health check endpoint.
    """
    status: str = Field(
        "healthy",
        description="The health status of the application"
    )
    version: str = Field(
        ...,
        description="The application version"
    )
    timestamp: str = Field(
        ...,
        description="The timestamp of the health check"
    )


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    """
    success: bool = Field(False, description="Always false for error responses")
    error_message: str = Field(..., description="The error message")
    error_code: Optional[str] = Field(None, description="Optional error code")
    details: Optional[dict] = Field(None, description="Additional error details")


class User(BaseModel):
    """
    User model for authentication.
    Represents the authenticated user from Supabase.
    """
    id: str = Field(..., description="User ID from Supabase")
    email: str = Field(..., description="User's email address")
    created_at: str = Field(..., description="User creation timestamp")
    
    class Config:
        from_attributes = True
