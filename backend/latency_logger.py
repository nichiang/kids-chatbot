"""
Latency Logger Module

Comprehensive request and LLM call timing measurement system for educational interactions.
This module provides timing instrumentation and educational metadata logging capabilities.
"""

import logging
import time
import json
from functools import wraps
from typing import List


class LatencyLogger:
    """Comprehensive request and LLM call timing measurement"""
    
    def __init__(self):
        self.logger = logging.getLogger('latency')
        self.request_start = None
        self.llm_calls = []
        
    def measure_request(self, func):
        """Decorator to measure total request processing time"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.request_start = time.perf_counter()
            
            try:
                result = await func(*args, **kwargs)
                
                total_time = (time.perf_counter() - self.request_start) * 1000
                
                # Log comprehensive timing data
                self.log_request_completion(
                    total_time=total_time,
                    llm_calls=self.llm_calls.copy(),
                    result_type=getattr(result, 'response_type', 'unknown'),
                    educational_data=getattr(result, 'educational_data', None)
                )
                
                return result
            finally:
                self.llm_calls.clear()
                
        return wrapper
    
    def measure_llm_call(self, call_type: str):
        """Decorator to measure individual LLM API calls"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                
                try:
                    result = await func(*args, **kwargs)
                    duration = (time.perf_counter() - start_time) * 1000
                    
                    self.llm_calls.append({
                        'type': call_type,
                        'duration': round(duration, 2),
                        'timestamp': time.time()
                    })
                    
                    return result
                except Exception as e:
                    duration = (time.perf_counter() - start_time) * 1000
                    self.llm_calls.append({
                        'type': call_type,
                        'duration': round(duration, 2),
                        'error': str(e),
                        'timestamp': time.time()
                    })
                    raise
                    
            return wrapper
        return decorator
    
    def log_request_completion(self, total_time: float, llm_calls: list, result_type: str, 
                             educational_data: dict = None):
        """Log comprehensive request timing data with educational metadata"""
        # Import here to avoid circular imports
        from llm_provider import llm_call_timings
        
        # Get LLM call timings from llm_provider and clear the list
        current_llm_calls = llm_call_timings.copy()
        llm_call_timings.clear()
        
        llm_total = sum(call['duration'] for call in current_llm_calls)
        processing_time = total_time - llm_total
        
        log_data = {
            'timestamp': time.time(),
            'total_request_time': round(total_time, 2),
            'llm_total_time': round(llm_total, 2),
            'processing_time': round(processing_time, 2),
            'llm_calls': current_llm_calls,
            'result_type': result_type,
            'llm_call_count': len(current_llm_calls)
        }
        
        # Add educational fields if provided
        if educational_data:
            log_data.update(educational_data)
        
        self.logger.info(json.dumps(log_data))
    
    def log_educational_interaction(self, interaction_type: str, ai_output: str, duration: float, educational_data: dict = None, prompt_data: dict = None):
        """Log individual educational interaction with separated content"""
        llm_call = {
            'type': interaction_type,
            'ai_output': ai_output,
            'duration': round(duration, 2)
        }
        
        # Add prompt data to individual LLM call if provided
        if prompt_data:
            llm_call['prompt'] = prompt_data
        
        log_data = {
            'timestamp': time.time(),
            'llm_calls': [llm_call]
        }
        
        # Add educational metadata if provided
        if educational_data:
            log_data.update(educational_data)
        
        self.logger.info(json.dumps(log_data))
    
    def get_current_llm_call_types(self) -> List[str]:
        """Get list of LLM call types for current request"""
        # Import here to avoid circular imports
        from llm_provider import llm_call_timings
        return [call.get('type', 'unknown') for call in llm_call_timings]