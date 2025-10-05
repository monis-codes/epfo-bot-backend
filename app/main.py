"""
Main FastAPI application for EPFO Bot Backend.
Acts as the orchestrator, calling various services in the correct sequence.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .core.config import get_settings
from .api_models import (
    ChatRequest, 
    ChatResponse, 
    HealthResponse, 
    ErrorResponse,
    User
)
from .dependencies import get_current_user, get_rate_limiter, create_rate_limit_exceeded_handler
from .services.rag_service import get_rag_service
from .services.llm_service import get_llm_service
from .services.supabase_service import get_supabase_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title="Providentia - EPFO Bot Backend",
    description="AI-powered backend service for EPFO guidance chatbot",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize rate limiter
limiter = get_rate_limiter()

# Add rate limiting exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, create_rate_limit_exceeded_handler())

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        logger.info("Starting EPFO Bot Backend...")
        
        # Initialize services (this will create singleton instances)
        # The services will initialize themselves when first accessed
        logger.info("Initializing services...")
        
        # Test service initialization by getting instances
        try:
            rag_service = get_rag_service()
            logger.info("RAG service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            # Don't raise - let the app start but log the issue
        
        try:
            llm_service = get_llm_service()
            logger.info("LLM service initialized successfully")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to initialize LLM service: {e}")
            # This is critical - consider raising to prevent startup
            raise
        
        try:
            supabase_service = get_supabase_service()
            logger.info("Supabase service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase service: {e}")
            # Don't raise - let the app start but log the issue
        
        # Test connections (non-blocking)
        try:
            if hasattr(supabase_service, 'test_connection'):
                if not supabase_service.test_connection():
                    logger.warning("Supabase connection test failed - service may be degraded")
                else:
                    logger.info("Supabase connection test passed")
        except Exception as e:
            logger.warning(f"Supabase connection test error: {e}")
        
        try:
            if hasattr(llm_service, 'test_connection'):
                if not llm_service.test_connection():
                    logger.warning("LLM service connection test failed - service may be degraded")
                else:
                    logger.info("LLM service connection test passed")
        except Exception as e:
            logger.warning(f"LLM service connection test error: {e}")
        
        logger.info("EPFO Bot Backend started successfully")
        
    except Exception as e:
        logger.error(f"CRITICAL: Failed to start application: {str(e)}")
        raise

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns the current status of the application.
    """
    try:
        # Test service connections with error handling
        services_status = {
            "supabase": False,
            "llm": False,
            "rag": False
        }
        
        # Test Supabase
        try:
            supabase_service = get_supabase_service()
            if hasattr(supabase_service, 'test_connection'):
                services_status["supabase"] = supabase_service.test_connection()
            else:
                services_status["supabase"] = True  # Assume healthy if no test method
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            services_status["supabase"] = False
        
        # Test LLM service
        try:
            llm_service = get_llm_service()
            if hasattr(llm_service, 'test_connection'):
                services_status["llm"] = llm_service.test_connection()
            else:
                services_status["llm"] = True  # Assume healthy if no test method
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")
            services_status["llm"] = False
        
        # Test RAG service
        try:
            rag_service = get_rag_service()
            services_status["rag"] = True  # RAG service typically doesn't have external dependencies
        except Exception as e:
            logger.error(f"RAG service health check failed: {e}")
            services_status["rag"] = False
        
        # Determine overall status
        all_healthy = all(services_status.values())
        any_healthy = any(services_status.values())
        
        if all_healthy:
            overall_status = "healthy"
        elif any_healthy:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            version=getattr(settings, 'version', '1.0.0'),
            timestamp=datetime.utcnow().isoformat(),
            details=services_status  # Include service-specific status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            version=getattr(settings, 'version', '1.0.0'),
            timestamp=datetime.utcnow().isoformat(),
            error=str(e)
        )

@app.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def chat(
    request_body: ChatRequest,
    request: Request,  # Required for rate limiting
    current_user: User = Depends(get_current_user)
):
    """
    Main chat endpoint.
    Protected by authentication and rate limiting.
    Orchestrates the RAG service, LLM service, and Supabase service.
    """
    user_query = request_body.question
    
    try:
        logger.info(f"Processing chat request from user {current_user.id}: {user_query[:50]}...")
        
        # Step 1: Get context and build prompt using RAG service
        try:
            rag_service = get_rag_service()
            final_prompt, source_context = rag_service.get_final_prompt_for_llm(user_query)
            logger.info("RAG processing completed successfully")
        except Exception as e:
            logger.error(f"RAG service error: {e}")
            # Fallback: use the user query directly
            final_prompt = user_query
            source_context = ""
        
        # Step 2: Query the LLM using the built prompt
        try:
            llm_service = get_llm_service()
            bot_response = llm_service.query_huggingface_model(final_prompt)
            logger.info("LLM processing completed successfully")
        except Exception as e:
            logger.error(f"LLM service error: {e}")
            bot_response = "I apologize, but I'm currently experiencing technical difficulties. Please try again later."
            # Still continue to save the interaction
        
        # Step 3: Save the interaction to database
        try:
            supabase_service = get_supabase_service()
            supabase_service.save_chat_to_db(
                user_id=current_user.id,
                user_query=user_query,
                bot_response=bot_response,
                context=source_context
            )
            logger.info("Chat interaction saved to database")
        except Exception as e:
            logger.error(f"Database save error: {e}")
            # Don't fail the request if database save fails
        
        logger.info(f"Successfully processed chat request from user {current_user.id}")
        
        return ChatResponse(
            answer=bot_response,
            source_context=source_context,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        
        # Try to save error interaction
        try:
            supabase_service = get_supabase_service()
            supabase_service.save_chat_to_db(
                user_id=current_user.id,
                user_query=user_query,
                bot_response=f"System Error: Unable to process request",
                context=""
            )
        except Exception as save_error:
            logger.error(f"Failed to save error interaction: {str(save_error)}")
        
        return ChatResponse(
            answer="I apologize, but I encountered an error while processing your request. Please try again.",
            source_context="",
            success=False,
            error_message=str(e)
        )

@app.get("/chat/history")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_chat_history(
    request: Request,  # Required for rate limiting
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    Get chat history for the current user.
    """
    try:
        supabase_service = get_supabase_service()
        chat_history = supabase_service.get_user_chat_history(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "data": chat_history,
            "count": len(chat_history)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )

@app.get("/stats")
@limiter.limit("5/minute")
async def get_statistics(
    request: Request,  # Required for rate limiting
    current_user: User = Depends(get_current_user)
):
    """
    Get chat statistics for the current user.
    """
    try:
        supabase_service = get_supabase_service()
        stats = supabase_service.get_chat_statistics(user_id=current_user.id)
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return ErrorResponse(
        error_message=exc.detail,
        error_code=str(exc.status_code)
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unexpected errors."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return ErrorResponse(
        error_message="An unexpected error occurred",
        error_code="500"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=getattr(settings, 'debug', False)
    )