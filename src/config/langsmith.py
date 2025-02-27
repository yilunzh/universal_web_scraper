"""Configuration for LangSmith integration."""
import os

def disable_logging():
    """Disable LangSmith logging by setting appropriate environment variables."""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGCHAIN_API_KEY"] = ""
    print("LangSmith logging disabled")

def enable_logging():
    """Enable LangSmith logging by setting appropriate environment variables."""
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    # Note: In a real implementation, you might load the API key from a .env file
    # or other secure storage mechanism rather than hardcoding it.
    # os.environ["LANGCHAIN_API_KEY"] = "your-api-key-here"
    print("LangSmith logging enabled") 