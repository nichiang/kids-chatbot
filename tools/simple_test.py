#!/usr/bin/env python3
"""
Simple test without unicode for Windows compatibility
"""

import requests
import json
import time

def test_latency():
    print("Testing latency measurement...")
    
    test_request = {
        "message": "Tell me about space",
        "mode": "funfacts",
        "sessionData": {
            "topic": None,
            "factsShown": 0,
            "askedVocabWords": []
        }
    }
    
    try:
        start_time = time.perf_counter()
        response = requests.post("http://localhost:8000/chat", json=test_request, timeout=10)
        end_time = time.perf_counter()
        
        client_latency = (end_time - start_time) * 1000
        
        if response.status_code == 200:
            print(f"SUCCESS: Request completed in {client_latency:.1f}ms")
            
            # Check if logs were created
            import os
            if os.path.exists("../backend/logs/latency.jsonl"):
                print("SUCCESS: Backend latency log created")
                
                with open("../backend/logs/latency.jsonl", 'r') as f:
                    lines = f.readlines()
                    if lines:
                        latest = json.loads(lines[-1])
                        backend_time = latest['total_request_time']
                        llm_time = latest['llm_total_time']
                        print(f"Backend measured: {backend_time:.1f}ms (LLM: {llm_time:.1f}ms)")
                        print("SUCCESS: Latency measurement system working!")
                        return True
            else:
                print("ERROR: No latency log found")
        else:
            print(f"ERROR: Request failed with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server")
        print("Make sure server is running: cd backend && uvicorn app:app --reload")
    except Exception as e:
        print(f"ERROR: {e}")
    
    return False

if __name__ == "__main__":
    test_latency()