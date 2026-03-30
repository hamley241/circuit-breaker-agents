#!/usr/bin/env python3
"""
Quick test of real API integration - just one call to verify it works.
"""
import sys
import os
from pathlib import Path

# Add current directory to path
HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))

def test_single_api_call():
    """Test a single API call to verify integration."""
    print("Testing single API call...")
    
    try:
        from api_clients import APIClientFactory, APIConfig
        
        # Check which APIs are available
        available = APIClientFactory.get_available_clients()
        print(f"Available APIs: {available}")
        
        if not available:
            print("❌ No API keys available")
            return False
        
        # Create a client for testing
        config = APIConfig(temperature=0.7, max_tokens=100)
        
        if 'gpt' in available:
            print("Testing GPT-4o...")
            client = APIClientFactory.create_gpt_client(config)
            result = client.call_agent_a("Test document analysis task")
            print(f"✅ GPT-4o Response: {result.content[:100]}...")
            print(f"   Confidence: {result.confidence}")
            print(f"   Token Usage: {result.token_usage}")
            return True
            
        elif 'claude' in available:
            print("Testing Claude...")
            client = APIClientFactory.create_claude_client(config)
            result = client.call_agent_a("Test document analysis task")
            print(f"✅ Claude Response: {result.content[:100]}...")
            print(f"   Confidence: {result.confidence}")
            print(f"   Token Usage: {result.token_usage}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    test_single_api_call()