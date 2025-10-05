"""
Simple test script to verify the EPFO Bot Backend setup.
Run this to test basic functionality without external dependencies.
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_imports():
    """Test that all modules can be imported successfully."""
    try:
        from app.core.config import get_settings
        from app.api_models import ChatRequest, ChatResponse
        from app.dependencies import get_current_user
        from app.services.rag_service import get_rag_service
        from app.services.llm_service import get_llm_service
        from app.services.supabase_service import get_supabase_service
        from app.main import app
        
        print("✅ All imports successful!")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration loading."""
    try:
        from app.core.config import get_settings
        
        # Test with minimal environment variables
        os.environ["SUPABASE_URL"] = "test_url"
        os.environ["SUPABASE_KEY"] = "test_key"
        os.environ["SUPABASE_JWT_SECRET"] = "test_secret"
        os.environ["PINECONE_API_KEY"] = "test_key"
        os.environ["GOOGLE_API_KEY"] = "test_key"
        os.environ["HUGGINGFACE_API_TOKEN"] = "test_token"
        os.environ["HUGGINGFACE_MODEL_URL"] = "test_url"
        
        settings = get_settings()
        print(f"✅ Configuration loaded: {settings.app_name}")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_models():
    """Test Pydantic models."""
    try:
        from app.api_models import ChatRequest, ChatResponse
        
        # Test ChatRequest
        request = ChatRequest(question="Test question?")
        assert request.question == "Test question?"
        
        # Test ChatResponse
        response = ChatResponse(answer="Test answer")
        assert response.answer == "Test answer"
        assert response.success is True
        
        print("✅ Models validation successful!")
        return True
    except Exception as e:
        print(f"❌ Models error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing EPFO Bot Backend Setup...")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_config),
        ("Models Test", test_models),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed!")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The backend is ready to run.")
        print("\n📝 Next steps:")
        print("1. Set up your environment variables in .env")
        print("2. Run: uvicorn app.main:app --reload")
        print("3. Visit: http://localhost:8000/docs")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
