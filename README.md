# Providentia - EPFO Bot Backend

A secure, modular, and scalable FastAPI backend that serves as the brain for an EPFO guidance chatbot, integrating a pre-existing, advanced RAG pipeline.

## 🏗️ Architecture Overview

This backend follows the **Separation of Concerns** principle:

- **`main.py`**: FastAPI orchestrator and router
- **Services**: Modular business logic (RAG, LLM, Database)
- **Core**: Configuration management
- **Dependencies**: Authentication and security
- **Models**: Data validation and contracts

## 🚀 Key Features

- **Secure Authentication**: JWT-based authentication with Supabase
- **Rate Limiting**: Configurable request rate limiting
- **RAG Integration**: Advanced retrieval-augmented generation
- **Vector Search**: Pinecone-powered document search
- **AI Models**: Google AI embeddings + Hugging Face LLM
- **Database**: Supabase for user management and chat history
- **Monitoring**: Health checks and comprehensive logging

## 📁 Project Structure

```
epfo-bot-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, endpoints, orchestration
│   ├── api_models.py           # Pydantic models for data validation
│   ├── dependencies.py         # Authentication & other reusable checks
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Environment variable loading
│   └── services/
│       ├── __init__.py
│       ├── rag_service.py      # Pre-built RAG logic using Google AI models
│       ├── llm_service.py      # Logic for querying the final Hugging Face LLM
│       └── supabase_service.py # All database logic (saving interactions)
├── requirements.txt
├── env.example
└── README.md
```

## 🔧 Setup Instructions

### 1. Prerequisites

- Python 3.8+
- Supabase account and project
- Pinecone account and API key
- Google AI API key
- Hugging Face account and API token
- Fine-tuned Mistral model hosted on Hugging Face

### 2. Installation

```bash
# Clone or navigate to the project directory
cd epfo-bot-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy the example environment file
cp env.example .env

# Edit .env with your actual values
nano .env
```

**Required Environment Variables:**

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_JWT_SECRET=your_supabase_jwt_secret

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=epfo-documents

# Google AI Configuration
GOOGLE_API_KEY=your_google_ai_api_key

# Hugging Face Configuration
HUGGINGFACE_API_TOKEN=your_huggingface_api_token
HUGGINGFACE_MODEL_URL=https://api-inference.huggingface.co/models/your_model_name
```

### 4. Database Setup

Create the required table in your Supabase project:

```sql
-- Create chat_history table
CREATE TABLE chat_history (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID REFERENCES auth.users(id),
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    source_context TEXT
);

-- Create index for better performance
CREATE INDEX idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX idx_chat_history_created_at ON chat_history(created_at);
```

### 5. Running the Application

#### Development Mode

```bash
# Run with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Mode

```bash
# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 6. API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔄 Request Lifecycle

1. **Authentication**: JWT validation with Supabase
2. **Rate Limiting**: Request frequency check
3. **RAG Processing**: Context retrieval using Google AI embeddings
4. **LLM Query**: Fine-tuned Mistral model on Hugging Face
5. **Database Storage**: Save interaction to Supabase
6. **Response**: Return structured JSON response

## 📡 API Endpoints

### Health Check
```http
GET /health
```

### Chat Endpoint
```http
POST /chat
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "question": "What is the minimum contribution period for EPF withdrawal?"
}
```

### Chat History
```http
GET /chat/history?limit=50&offset=0
Authorization: Bearer <jwt_token>
```

### Statistics
```http
GET /stats
Authorization: Bearer <jwt_token>
```

## 🔒 Security Features

- **JWT Authentication**: Secure user authentication
- **Rate Limiting**: Prevents abuse and ensures fair usage
- **CORS Protection**: Configurable cross-origin resource sharing
- **Input Validation**: Pydantic models for request validation
- **Error Handling**: Comprehensive error management

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_main.py
```

## 📊 Monitoring

- **Health Checks**: `/health` endpoint for service status
- **Logging**: Structured logging with configurable levels
- **Error Tracking**: Comprehensive error handling and reporting

## 🚀 Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables for Production

Ensure all environment variables are properly set in your production environment:

- Database credentials
- API keys and tokens
- CORS origins
- Rate limiting settings

## 🔧 Configuration

The application uses Pydantic Settings for configuration management. All settings can be overridden via environment variables.

Key configuration options:
- `RATE_LIMIT_PER_MINUTE`: Requests per minute per user
- `CORS_ORIGINS`: Allowed frontend origins
- `DEBUG`: Enable debug mode
- `PINECONE_INDEX_NAME`: Vector database index name

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the logs for error details
2. Verify environment variables are set correctly
3. Test individual service connections
4. Check API documentation at `/docs`

## 🔄 Service Dependencies

- **Supabase**: User authentication and database
- **Pinecone**: Vector search and document retrieval
- **Google AI**: Text embeddings and AI services
- **Hugging Face**: Fine-tuned Mistral model hosting

Ensure all services are properly configured and accessible before running the application.
