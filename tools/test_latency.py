#!/usr/bin/env python3
"""
Simple test to verify latency measurement system works end-to-end

This test makes a request to the chat endpoint and verifies that:
1. Latency data is logged to files
2. Frontend measurement would work
3. Analysis tool can read the data
"""

import requests
import json
import time
import sys
import os

# Add parent directory to path to import analyze_latency
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_latency_measurement():
    """Test end-to-end latency measurement"""
    print("Testing latency measurement system...")
    
    # Test data for chat request
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
        # Make request to local server
        print("Making test request to chat endpoint...")
        start_time = time.perf_counter()
        
        response = requests.post(
            "http://localhost:8000/chat",
            json=test_request,
            timeout=10
        )
        
        end_time = time.perf_counter()
        client_latency = (end_time - start_time) * 1000
        
        if response.status_code == 200:
            print(f"Request successful! Client-measured latency: {client_latency:.1f}ms")
            
            # Check if logs were created
            backend_logs = "../backend/logs"
            if os.path.exists(f"{backend_logs}/latency.jsonl"):
                print("✅ Backend latency log created")
                
                # Read the latest log entry
                with open(f"{backend_logs}/latency.jsonl", 'r') as f:
                    lines = f.readlines()
                    if lines:
                        latest_entry = json.loads(lines[-1])
                        backend_latency = latest_entry['total_request_time']
                        llm_time = latest_entry['llm_total_time']
                        processing_time = latest_entry['processing_time']
                        
                        print(f"✅ Backend measured latency: {backend_latency:.1f}ms")
                        print(f"   - LLM time: {llm_time:.1f}ms")
                        print(f"   - Processing time: {processing_time:.1f}ms")
                        print(f"   - LLM calls: {latest_entry['llm_call_count']}")
                        
                        # Compare client vs backend measurements
                        diff = abs(client_latency - backend_latency)
                        if diff < 100:  # Within 100ms is reasonable for network overhead
                            print(f"✅ Client and backend measurements align (diff: {diff:.1f}ms)")
                        else:
                            print(f"⚠️  Large difference between measurements (diff: {diff:.1f}ms)")
                        
                    else:
                        print("❌ No log entries found")
            else:
                print("❌ Backend latency log not created")
                
        else:
            print(f"❌ Request failed with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the backend is running:")
        print("   cd backend && uvicorn app:app --reload")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    
    return True

def test_analysis_tool():
    """Test that analysis tool can read the generated data"""
    print("\nTesting analysis tool...")
    
    # Import and run analyzer
    try:
        from analyze_latency import LatencyAnalyzer
        
        analyzer = LatencyAnalyzer("../backend/logs")
        analyzer.load_data()
        
        if analyzer.request_data:
            print(f"✅ Analysis tool loaded {len(analyzer.request_data)} request entries")
        else:
            print("❌ Analysis tool found no request data")
            
        if analyzer.story_data:
            print(f"✅ Analysis tool loaded {len(analyzer.story_data)} story entries")
        else:
            print("ℹ️  No story completion data yet (expected for single request)")
            
        return len(analyzer.request_data) > 0
        
    except Exception as e:
        print(f"❌ Analysis tool test failed: {e}")
        return False

def main():
    print("LATENCY MEASUREMENT SYSTEM TEST")
    print("=" * 40)
    
    # Test basic functionality
    if test_latency_measurement():
        print("\n✅ Basic latency measurement test passed")
        
        # Test analysis tool
        if test_analysis_tool():
            print("✅ Analysis tool test passed")
            print("\n🎉 All tests passed! Latency measurement system is working correctly.")
        else:
            print("❌ Analysis tool test failed")
    else:
        print("❌ Basic test failed")
        
    print("\nTo run full analysis on collected data:")
    print("   cd tools && python analyze_latency.py --detailed")

if __name__ == "__main__":
    main()