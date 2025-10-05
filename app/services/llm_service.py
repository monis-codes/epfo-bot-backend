# /app/services/llm_service.py

"""
LLM service for the Providentia Backend.
Handles all communication with the fine-tuned model hosted on Hugging Face.
Uses direct HTTP requests to bypass InferenceClient issues.
"""

import logging
import threading
import requests
from typing import Optional
from app.core.config import get_settings

# Set up a logger for this module
logger = logging.getLogger(__name__)

class LLMService:
    """
    A thread-safe singleton service for handling all LLM operations with Hugging Face.
    Uses direct HTTP requests for maximum reliability.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super(LLMService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Prevent re-initialization
        if not hasattr(self, '_initialized') or not self._initialized:
            self._initialize_client()
            self._initialized = True

    def _initialize_client(self):
        """
        Initializes the service using settings from the environment.
        This method is called only once.
        """
        try:
            settings = get_settings()
            
            # Extract just the model repo ID from the URL if it's a full URL
            model_repo_id = settings.huggingface_model_url
            
            # Clean up the model repo ID if it's a full URL
            if model_repo_id.startswith('https://api-inference.huggingface.co/models/'):
                model_repo_id = model_repo_id.replace('https://api-inference.huggingface.co/models/', '')
            elif model_repo_id.startswith('https://huggingface.co/'):
                model_repo_id = model_repo_id.replace('https://huggingface.co/', '')
            
            # Validate model repo ID
            if not model_repo_id or model_repo_id == 'your_model_name_here':
                raise ValueError(
                    "HUGGINGFACE_MODEL_URL must be set to your actual model repo ID "
                    "(e.g., 'monis-codes/epfo-chatbot-mistral-7b-4bit')"
                )
            
            api_token = settings.huggingface_api_token
            if not api_token:
                logger.warning("HUGGINGFACE_API_TOKEN not set. Using public inference (may have limitations).")

            # Store configuration
            self.model_repo_id = model_repo_id
            self.api_token = api_token
            self.settings = settings
            self.api_url = f"https://api-inference.huggingface.co/models/{model_repo_id}"
            
            # Set up session for connection pooling
            self.session = requests.Session()
            if api_token:
                self.session.headers.update({
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                })
            
            logger.info(f"LLMService initialized successfully for model: {model_repo_id}")
        
        except Exception as e:
            logger.critical(f"FATAL: Failed to initialize LLMService: {e}")
            raise RuntimeError(f"LLMService initialization failed: {e}")

    def get_response(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95
    ) -> str:
        """
        Queries the fine-tuned model on Hugging Face using direct HTTP request.
        
        Args:
            prompt: The complete prompt to send to the model
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature for creativity
            top_p: Nucleus sampling parameter
            
        Returns:
            A clean, generated response string
            
        Raises:
            Exception: If the API call fails after handling specific errors
        """
        if not hasattr(self, 'api_url') or not self.api_url:
            raise Exception("LLMService is not properly initialized.")

        # Construct the payload
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "return_full_text": False,
                "stop": ["</s>", "[/INST]", "Human:", "Assistant:", "<|endoftext|>"]
            }
        }

        try:
            logger.info("Sending direct HTTP request to Hugging Face model")
            
            # Make the direct HTTP POST request
            response = self.session.post(
                self.api_url, 
                json=payload, 
                timeout=30
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            response_json = response.json()
            logger.debug(f"Raw response: {response_json}")

            # Parse the response based on format
            generated_text = ""
            
            if isinstance(response_json, list) and response_json:
                # Standard successful response format
                generated_text = response_json[0].get("generated_text", "")
            elif isinstance(response_json, dict):
                if 'error' in response_json:
                    # Error response format
                    error_message = response_json['error']
                    logger.error(f"Hugging Face API returned an error: {error_message}")
                    if "is currently loading" in error_message.lower():
                        raise Exception("The model is currently loading. Please try again in a few moments.")
                    elif "rate limited" in error_message.lower():
                        raise Exception("Rate limit exceeded. Please try again later.")
                    else:
                        raise Exception(f"Hugging Face API error: {error_message}")
                elif 'generated_text' in response_json:
                    # Alternative response format
                    generated_text = response_json['generated_text']
                else:
                    logger.warning(f"Unexpected response format: {response_json}")
                    generated_text = ""

            if not generated_text:
                logger.warning("Received empty response from Hugging Face model")
                return "I apologize, but I couldn't generate a response at this time."

            logger.info("Successfully received and processing response")
            return self._clean_response(generated_text)

        except requests.exceptions.Timeout:
            logger.error("Timeout while querying Hugging Face model")
            raise Exception("The request timed out as the model is taking too long to respond.")
        
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            logger.error(f"HTTP error from Hugging Face (Status {status_code}): {e}")
            
            if status_code == 401:
                raise Exception("Authentication failed. Please check your HUGGINGFACE_API_TOKEN.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please try again later.")
            elif status_code == 503:
                raise Exception("The model is currently loading. Please try again in a few moments.")
            elif status_code == 404:
                raise Exception(f"Model '{self.model_repo_id}' not found. Please check the model name.")
            else:
                raise Exception(f"Hugging Face API error (HTTP {status_code}): {e}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while querying Hugging Face model: {e}")
            raise Exception(f"Network error occurred: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error while querying the LLM: {e}", exc_info=True)
            raise Exception("An unexpected error occurred while processing your request.")

    def query_huggingface_model(
        self, 
        prompt: str, 
        hf_api_token: Optional[str] = None,
        model_url: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95
    ) -> str:
        """
        Main method for querying the Hugging Face model.
        Supports overriding token and model per request.
        
        Args:
            prompt: The complete prompt to send to the model
            hf_api_token: Optional API token override
            model_url: Optional model repo ID override
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            
        Returns:
            str: The model's response
        """
        # If overrides are provided, make a direct request with custom settings
        if hf_api_token or model_url:
            try:
                # Clean up model URL if provided
                temp_model = model_url or self.settings.huggingface_model_url
                if temp_model.startswith('https://api-inference.huggingface.co/models/'):
                    temp_model = temp_model.replace('https://api-inference.huggingface.co/models/', '')
                elif temp_model.startswith('https://huggingface.co/'):
                    temp_model = temp_model.replace('https://huggingface.co/', '')
                
                temp_token = hf_api_token or self.settings.huggingface_api_token
                temp_url = f"https://api-inference.huggingface.co/models/{temp_model}"
                
                # Create temporary headers
                temp_headers = {"Content-Type": "application/json"}
                if temp_token:
                    temp_headers["Authorization"] = f"Bearer {temp_token}"
                
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_new_tokens,
                        "temperature": temperature,
                        "top_p": top_p,
                        "return_full_text": False,
                        "stop": ["</s>", "[/INST]", "Human:", "Assistant:", "<|endoftext|>"]
                    }
                }
                
                response = requests.post(temp_url, headers=temp_headers, json=payload, timeout=30)
                response.raise_for_status()
                response_json = response.json()
                
                if isinstance(response_json, list) and response_json:
                    generated_text = response_json[0].get("generated_text", "")
                elif isinstance(response_json, dict) and 'generated_text' in response_json:
                    generated_text = response_json['generated_text']
                else:
                    generated_text = ""
                
                return self._clean_response(generated_text) if generated_text else "I apologize, but I couldn't generate a response at this time."
                
            except Exception as e:
                logger.error(f"Error with custom parameters: {e}")
                raise Exception(f"Error querying the model: {str(e)}")
        else:
            # Use the main service method
            return self.get_response(prompt, max_new_tokens, temperature, top_p)

    def _clean_response(self, response: str) -> str:
        """
        Clean and format the model response.
        
        Args:
            response: Raw response from the model
            
        Returns:
            str: Cleaned response
        """
        cleaned = response.strip()
        
        # Remove any remaining prompt fragments
        if "Answer:" in cleaned:
            cleaned = cleaned.split("Answer:")[-1].strip()
        
        # Remove any trailing incomplete sentences
        if cleaned and not cleaned.endswith(('.', '!', '?')):
            sentences = cleaned.split('. ')
            if len(sentences) > 1:
                cleaned = '. '.join(sentences[:-1]) + '.'
        
        return cleaned

    def test_connection(self) -> bool:
        """
        Test the connection to the Hugging Face model.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            test_prompt = "Hello, this is a test message."
            response = self.get_response(test_prompt)
            return bool(response and len(response.strip()) > 0)
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

# --- Dependency for FastAPI ---

def get_llm_service() -> LLMService:
    """
    FastAPI dependency to get the singleton LLM service instance.
    """
    return LLMService()