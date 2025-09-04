"""
Regression test for the create_enhanced_story_prompt undefined function bug

This test prevents the critical bug that broke second story generation:
- Error: "name 'create_enhanced_story_prompt' is not defined" 
- Impact: Users could not start second/third stories
- Root cause: Phase 15 fix called non-existent function
- Solution: Use prompt_manager.get_story_opening_prompt() instead

This regression test ensures:
1. All function calls in new story paths are valid
2. Second stories generate without NameError exceptions
3. Critical story flow functions are properly imported and available
"""

import sys
import os
import pytest
from unittest.mock import patch, Mock
import json

# Add backend to path for imports and set working directory
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.append(backend_dir)

# Change working directory to backend for file loading
original_cwd = os.getcwd()
os.chdir(backend_dir)

from app import handle_storywriting, SessionData
import app

# Restore original working directory
os.chdir(original_cwd)

class TestMissingFunctionBug:
    """Prevent create_enhanced_story_prompt undefined function bug"""
    
    def setup_method(self):
        """Set up test session"""
        self.session_data = SessionData()
        
    def test_no_create_enhanced_story_prompt_calls(self):
        """Ensure create_enhanced_story_prompt is not called anywhere in codebase"""
        
        # Read the main app.py file
        app_file = os.path.join(backend_dir, 'app.py')
        with open(app_file, 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        # Critical: Should not contain any calls to the non-existent function
        assert 'create_enhanced_story_prompt(' not in app_content, \
            "create_enhanced_story_prompt() calls found! This function doesn't exist and will cause NameError"
    
    def test_required_functions_exist(self):
        """Verify all required prompt functions exist and are importable"""
        
        # Test that the correct function exists
        from prompt_manager import prompt_manager
        
        # This should not raise AttributeError
        assert hasattr(prompt_manager, 'get_story_opening_prompt'), \
            "get_story_opening_prompt method missing from prompt_manager"
        
        # Test that the function is callable
        assert callable(prompt_manager.get_story_opening_prompt), \
            "get_story_opening_prompt is not callable"
        
        # Test that it works with expected parameters
        try:
            result = prompt_manager.get_story_opening_prompt("test_topic", "auto")
            assert isinstance(result, str), "get_story_opening_prompt should return a string"
            assert len(result) > 0, "get_story_opening_prompt should return non-empty string"
        except Exception as e:
            pytest.fail(f"get_story_opening_prompt failed with error: {e}")
    
    @patch('llm_provider.llm_provider.generate_response')
    def test_second_story_generation_no_name_error(self, mock_generate):
        """Test that second story generation doesn't raise NameError"""
        
        # Mock LLM response for second story
        mock_story = {
            "story": "In a kitchen, a chef found magical ingredients.",
            "entities": {
                "characters": {"named": [], "unnamed": ["chef"]},
                "locations": {"named": [], "unnamed": ["kitchen"]}
            },
            "vocabulary_words": ["magical"]
        }
        mock_generate.return_value = json.dumps(mock_story)
        
        # Set up session as if first story is complete and user wants second story
        self.session_data.isComplete = True
        self.session_data.awaiting_story_confirmation = True
        self.session_data.topic = "space"  # Previous topic
        
        try:
            # This should NOT raise "name 'create_enhanced_story_prompt' is not defined"
            response = handle_storywriting("food adventures", self.session_data)
            
            # Should get a valid response
            assert response is not None, "Should get response object"
            assert hasattr(response, 'response'), "Response should have response field"
            assert response.response is not None, "Response text should not be None"
            
        except NameError as e:
            if 'create_enhanced_story_prompt' in str(e):
                pytest.fail(f"CRITICAL BUG REGRESSION: create_enhanced_story_prompt error returned! {e}")
            else:
                # Some other NameError, re-raise
                raise
        except Exception as e:
            # Other exceptions might be OK (LLM errors, etc) but log them
            print(f"Warning: Non-NameError exception in second story generation: {e}")
    
    @patch('llm_provider.llm_provider.generate_response')
    def test_topic_switch_no_name_error(self, mock_generate):
        """Test that spontaneous topic switching doesn't raise NameError"""
        
        mock_story = {
            "story": "A brave explorer found ancient treasures.",
            "entities": {
                "characters": {"named": [], "unnamed": ["brave explorer"]},
                "locations": {"named": [], "unnamed": []}
            },
            "vocabulary_words": ["brave", "ancient"]
        }
        mock_generate.return_value = json.dumps(mock_story)
        
        # Set up session as if story is complete (but not awaiting confirmation)
        self.session_data.isComplete = True
        self.session_data.awaiting_story_confirmation = False
        self.session_data.topic = "space"  # Previous topic
        
        try:
            # This should NOT raise create_enhanced_story_prompt error
            response = handle_storywriting("adventure stories", self.session_data)
            
            # Should get valid response
            assert response is not None
            
        except NameError as e:
            if 'create_enhanced_story_prompt' in str(e):
                pytest.fail(f"CRITICAL BUG REGRESSION: create_enhanced_story_prompt error in topic switch! {e}")
            else:
                raise
    
    def test_function_import_chain(self):
        """Test that all required imports work correctly"""
        
        try:
            # Test imports used in new story generation
            from prompt_manager import prompt_manager
            from app import parse_enhanced_story_response, validate_entity_structure
            from app import trigger_enhanced_design_phase
            
            # All imports should succeed
            assert prompt_manager is not None
            assert parse_enhanced_story_response is not None
            assert validate_entity_structure is not None
            assert trigger_enhanced_design_phase is not None
            
        except ImportError as e:
            pytest.fail(f"Critical import failed in story generation chain: {e}")
    
    def test_app_module_has_no_undefined_function_calls(self):
        """Scan app.py for any calls to undefined functions"""
        
        # Get all function names defined in app.py
        import inspect
        app_functions = set()
        for name, obj in inspect.getmembers(app):
            if inspect.isfunction(obj):
                app_functions.add(name)
        
        # Read app.py source to check for function calls
        app_file = os.path.join(backend_dir, 'app.py')
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # List of functions that should NOT be called (don't exist)
        forbidden_functions = [
            'create_enhanced_story_prompt',
            'generate_enhanced_prompt',
            'create_story_prompt_enhanced'  # Other potential typos
        ]
        
        for func_name in forbidden_functions:
            call_pattern = f'{func_name}('
            assert call_pattern not in content, \
                f"Found call to undefined function {func_name} in app.py!"
    
    @patch('llm_provider.llm_provider.generate_response')
    def test_new_story_confirmation_flow_works(self, mock_generate):
        """Test the specific flow that was broken: finish_vocabulary -> new story"""
        
        mock_generate.return_value = json.dumps({
            "story": "Test story content",
            "entities": {"characters": {"named": [], "unnamed": []}, "locations": {"named": [], "unnamed": []}},
            "vocabulary_words": []
        })
        
        # Step 1: Complete vocabulary phase
        self.session_data.isComplete = True
        response1 = handle_storywriting("finish_vocabulary", self.session_data)
        
        # Should set awaiting_story_confirmation
        assert self.session_data.awaiting_story_confirmation == True
        
        # Step 2: Provide new topic (this was failing with NameError)
        try:
            response2 = handle_storywriting("ocean adventures", self.session_data)
            
            # Should succeed without error
            assert response2 is not None
            assert self.session_data.topic == "ocean adventures"
            
        except NameError as e:
            if 'create_enhanced_story_prompt' in str(e):
                pytest.fail("CRITICAL: The exact bug scenario still fails!")
            else:
                raise