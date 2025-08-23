#!/usr/bin/env python3
"""
Simple latency analysis without unicode for Windows compatibility
"""

import json
import statistics
import os

def analyze_logs():
    print("LATENCY ANALYSIS")
    print("=" * 50)
    
    # Load request data
    request_data = []
    log_file = "../backend/logs/latency.jsonl"
    
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        request_data.append(json.loads(line))
                    except:
                        continue
    
    if not request_data:
        print("No latency data found")
        return
    
    print(f"Total Requests: {len(request_data)}")
    
    # Analyze timing data
    total_times = [req['total_request_time'] for req in request_data]
    llm_times = [req['llm_total_time'] for req in request_data]
    processing_times = [req['processing_time'] for req in request_data]
    
    print(f"\nRequest Performance:")
    print(f"  Average Total Time: {statistics.mean(total_times):.1f}ms")
    print(f"  Median Total Time: {statistics.median(total_times):.1f}ms")
    print(f"  Fastest Request: {min(total_times):.1f}ms")
    print(f"  Slowest Request: {max(total_times):.1f}ms")
    
    print(f"\nLLM Performance:")
    print(f"  Average LLM Time: {statistics.mean(llm_times):.1f}ms")
    print(f"  LLM vs Total: {statistics.mean(llm_times)/statistics.mean(total_times)*100:.1f}%")
    
    print(f"\nProcessing Performance:")
    print(f"  Average Processing: {statistics.mean(processing_times):.1f}ms")
    print(f"  Processing vs Total: {statistics.mean(processing_times)/statistics.mean(total_times)*100:.1f}%")
    
    # Solution 1 impact assessment
    avg_total = statistics.mean(total_times)
    print(f"\nSolution 1 Impact Assessment:")
    print(f"  Current avg response: {avg_total:.1f}ms")
    print(f"  With intent classification: {avg_total + 350:.1f}ms (+350ms estimated)")
    
    if avg_total + 350 > 2000:
        print("  WARNING: Would exceed child-friendly threshold (2000ms)")
    else:
        print("  OK: Should remain within acceptable range")
    
    # Analyze by LLM call count
    by_calls = {}
    for req in request_data:
        count = req['llm_call_count']
        if count not in by_calls:
            by_calls[count] = []
        by_calls[count].append(req['total_request_time'])
    
    print(f"\nPerformance by LLM Calls:")
    for count in sorted(by_calls.keys()):
        times = by_calls[count]
        print(f"  {count} calls: {statistics.mean(times):.1f}ms avg ({len(times)} requests)")

if __name__ == "__main__":
    analyze_logs()