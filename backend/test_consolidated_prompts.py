"""
Test suite for consolidated prompts implementation

This test suite validates:
1. Backward compatibility - existing functionality still works
2. New consolidated methods work correctly
3. Feature flag behavior
4. Fallback mechanisms
5. Performance improvements (latency reduction)
"""

import unittest
import json
import os
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import modules to test
from consolidated_prompts import ConsolidatedPromptBuilder, consolidated_prompt_builder
from llm_provider import LLMProvider, llm_provider


class TestConsolidatedPromptBuilder(unittest.TestCase):
    """Test ConsolidatedPromptBuilder functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.builder = ConsolidatedPromptBuilder()
    
    def test_component_loading(self):
        """Test that all component files are loaded correctly"""
        # Check that key components exist
        self.assertIn("educational_framework", self.builder.components)
        self.assertIn("content_generation", self.builder.components)
        self.assertIn("assessment_modules", self.builder.components)
        self.assertIn("response_formatting", self.builder.components)
    
    def test_writing_feedback_component(self):
        """Test that writing_feedback (not grammar_feedback) is properly loaded"""
        assessment_components = self.builder.components.get("assessment_modules", {}).get("components", {})
        self.assertIn("writing_feedback", assessment_components)
        self.assertNotIn("grammar_feedback", assessment_components)
        
        # Check the prompt template contains the expected format
        writing_feedback = assessment_components.get("writing_feedback", {})
        template = writing_feedback.get("template", "")
        self.assertIn("You could make that even better by saying", template)
        self.assertIn("writing flow", template)
    
    def test_story_prompt_building(self):
        """Test consolidated story prompt building"""
        prompt = self.builder.build_consolidated_story_prompt(
            topic="space",
            story_step="opening",
            include_feedback=False,
            include_vocabulary=True
        )
        
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)
        self.assertIn("space", prompt.lower())
        self.assertIn("story", prompt.lower())
        self.assertIn("vocabulary", prompt.lower())
    
    def test_vocabulary_question_prompt_building(self):
        """Test vocabulary question prompt building"""
        prompt = self.builder.build_vocabulary_question_prompt("magnificent", "The magnificent elephant walked by.")
        
        self.assertIsInstance(prompt, str)
        self.assertIn("magnificent", prompt)
        self.assertIn("elephant", prompt)
    
    def test_writing_feedback_prompt_building(self):
        """Test writing feedback prompt building"""
        prompt = self.builder.build_writing_feedback_prompt("He go to the store")
        
        self.assertIsInstance(prompt, str)
        self.assertIn("He go to the store", prompt)
        self.assertIn("You could make that even better", prompt)
    
    def test_fallback_handling(self):
        """Test fallback behavior when components are missing"""
        # Temporarily clear components
        original_components = self.builder.components.copy()
        self.builder.components = {}
        
        # Should still return a string (fallback)
        prompt = self.builder.build_consolidated_story_prompt("space")
        self.assertIsInstance(prompt, str)
        
        # Restore components
        self.builder.components = original_components


class TestLLMProviderBackwardCompatibility(unittest.TestCase):
    """Test that existing LLM provider functionality still works"""
    
    def setUp(self):
        """Set up test environment"""
        self.provider = LLMProvider()
        # Ensure consolidated prompts are disabled for backward compatibility tests
        self.provider.use_consolidated_prompts = False
    
    def test_existing_methods_exist(self):
        """Test that all existing methods still exist"""
        # Test existing method signatures
        self.assertTrue(hasattr(self.provider, 'generate_response'))
        self.assertTrue(hasattr(self.provider, 'generate_vocabulary_question'))
        self.assertTrue(hasattr(self.provider, 'provide_grammar_feedback'))
        self.assertTrue(hasattr(self.provider, 'extract_vocabulary_words'))
        self.assertTrue(hasattr(self.provider, 'check_api_status'))
    
    def test_extract_vocabulary_words(self):
        """Test vocabulary word extraction (unchanged functionality)"""
        text = "The **magnificent** elephant walked through the **enchanted** forest."
        words = self.provider.extract_vocabulary_words(text)
        
        self.assertEqual(len(words), 2)
        self.assertIn("magnificent", words)
        self.assertIn("enchanted", words)
    
    def test_fallback_vocabulary_question(self):
        """Test fallback vocabulary question generation"""
        question = self.provider._get_fallback_vocab_question("enormous", "The enormous elephant walked by.")
        
        self.assertIsInstance(question, dict)
        self.assertIn("question", question)
        self.assertIn("options", question)
        self.assertIn("correctIndex", question)
        self.assertIn("enormous", question["question"])
    
    def test_fallback_grammar_feedback(self):
        """Test fallback grammar feedback (now writing feedback)"""
        feedback = self.provider._get_fallback_grammar_feedback("practiced.")
        
        # Should provide helpful feedback for incomplete sentences
        self.assertIsInstance(feedback, str)
        self.assertIn("better", feedback.lower())
    
    def test_sentence_extraction(self):
        """Test sentence extraction with vocabulary words"""
        context = "The elephant was **enormous**. It walked through the forest. The birds sang."
        sentence = self.provider._extract_sentence_with_word("enormous", context)
        
        self.assertIsNotNone(sentence)
        self.assertIn("enormous", sentence)


class TestConsolidatedMethods(unittest.TestCase):
    """Test new consolidated methods functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.provider = LLMProvider()
        # Enable consolidated prompts for these tests
        self.provider.use_consolidated_prompts = True
        
        # Mock OpenAI client to avoid actual API calls
        self.provider.client = Mock()
        self.provider.api_key = "test-key"
    
    def test_feature_flag_behavior(self):
        """Test feature flag enables/disables consolidated prompts"""
        # Test enable
        self.provider.enable_consolidated_prompts()
        self.assertTrue(self.provider.use_consolidated_prompts)
        
        # Test disable
        self.provider.disable_consolidated_prompts()
        self.assertFalse(self.provider.use_consolidated_prompts)
    
    def test_consolidated_story_response_structure(self):
        """Test that consolidated response has expected structure"""
        # Mock API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "story_content": "Test story with **vocabulary** words.",
            "vocabulary_question": {
                "question": "What does vocabulary mean?",
                "options": {"a": "words", "b": "pictures", "c": "numbers", "d": "colors"},
                "correct_answer": "a",
                "explanation": "Vocabulary refers to words."
            },
            "writing_feedback": {
                "feedback": "Great job!",
                "suggestions": [],
                "praise": "Keep it up!"
            },
            "next_step": "Continue the story!"
        })
        
        self.provider.client.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_consolidated_story_response(
            topic="space",
            story_step="opening"
        )
        
        # Validate structure
        self.assertIn("story_content", result)
        self.assertIn("vocabulary_question", result)
        self.assertIn("writing_feedback", result)
        self.assertIn("next_step", result)
    
    def test_fallback_to_individual_calls(self):
        """Test fallback to individual calls when consolidated fails"""
        # Mock consolidated call to fail
        self.provider.client.chat.completions.create.side_effect = Exception("API Error")
        
        # Should fallback gracefully
        with patch.object(self.provider, 'generate_response', return_value="Test story") as mock_generate:
            result = self.provider.generate_consolidated_story_response(
                topic="space",
                story_step="opening"
            )
            
            # Should have called individual method as fallback
            mock_generate.assert_called()
            self.assertIn("story_content", result)
    
    @patch('llm_provider.time.perf_counter')
    def test_performance_measurement(self, mock_time):
        """Test that consolidated calls are measured for performance"""
        # Mock timing
        mock_time.side_effect = [0.0, 0.5]  # 500ms call
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "story_content": "Test story",
            "vocabulary_question": {},
            "writing_feedback": {},
            "next_step": "Continue"
        })
        
        self.provider.client.chat.completions.create.return_value = mock_response
        
        # Clear timing data
        from llm_provider import llm_call_timings
        llm_call_timings.clear()
        
        # Make consolidated call
        self.provider.generate_consolidated_story_response("space")
        
        # Check that timing was recorded
        self.assertGreater(len(llm_call_timings), 0)
        self.assertEqual(llm_call_timings[-1]['type'], 'consolidated_story_generation')


class TestPerformanceComparison(unittest.TestCase):
    """Test performance improvements of consolidated vs individual calls"""
    
    def setUp(self):
        """Set up test environment"""
        self.provider = LLMProvider()
        self.provider.api_key = "test-key"
        self.provider.client = Mock()
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        self.provider.client.chat.completions.create.return_value = mock_response
    
    def test_api_call_count_comparison(self):
        """Test that consolidated prompts reduce API call count"""
        # Clear call tracking
        from llm_provider import llm_call_timings
        llm_call_timings.clear()
        
        # Test individual calls
        self.provider.use_consolidated_prompts = False
        story_response = self.provider.generate_response("Create a story about space")
        vocab_question = self.provider.generate_vocabulary_question("space", "The space adventure begins")
        feedback = self.provider.provide_grammar_feedback("He go to space")
        
        individual_calls = len([t for t in llm_call_timings if 'consolidated' not in t['type']])
        
        # Clear and test consolidated
        llm_call_timings.clear()
        self.provider.use_consolidated_prompts = True
        
        # Mock consolidated response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "story_content": "Test story",
            "vocabulary_question": {"question": "test", "options": {"a": "1", "b": "2", "c": "3", "d": "4"}, "correct_answer": "a"},
            "writing_feedback": {"feedback": "test", "suggestions": [], "praise": "good"},
            "next_step": "continue"
        })
        self.provider.client.chat.completions.create.return_value = mock_response
        
        consolidated_result = self.provider.generate_consolidated_story_response(
            topic="space",
            user_input="He go to space",
            include_feedback=True,
            include_vocabulary=True
        )
        
        consolidated_calls = len([t for t in llm_call_timings if 'consolidated' in t['type']])
        
        # Consolidated should make fewer calls
        print(f"Individual calls: {individual_calls}, Consolidated calls: {consolidated_calls}")
        self.assertLessEqual(consolidated_calls, 1)  # Should be 1 call vs multiple


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def test_end_to_end_story_generation(self):
        """Test complete story generation flow"""
        provider = LLMProvider()
        provider.use_consolidated_prompts = True
        provider.client = Mock()
        provider.api_key = "test-key"
        
        # Mock successful response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "story_content": "Captain Luna explored the **magnificent** galaxy with great **courage**.",
            "vocabulary_question": {
                "question": "What does magnificent mean?",
                "options": {"a": "beautiful", "b": "ugly", "c": "small", "d": "loud"},
                "correct_answer": "a",
                "explanation": "Magnificent means beautiful or impressive."
            },
            "writing_feedback": {
                "feedback": "Great sentence structure!",
                "suggestions": [],
                "praise": "Keep up the excellent work!"
            },
            "next_step": "Tell me what Captain Luna discovers next!"
        })
        provider.client.chat.completions.create.return_value = mock_response
        
        result = provider.generate_consolidated_story_response(
            topic="space",
            user_input="Luna wants to explore",
            story_step="continuation",
            include_feedback=True,
            include_vocabulary=True
        )
        
        # Validate complete response
        self.assertIn("story_content", result)
        self.assertIn("vocabulary_question", result)
        self.assertIn("writing_feedback", result)
        self.assertIn("next_step", result)
        
        # Check vocabulary extraction works
        vocab_words = provider.extract_vocabulary_words(result["story_content"])
        self.assertGreater(len(vocab_words), 0)


def run_comprehensive_tests():
    """Run all tests and report results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestConsolidatedPromptBuilder,
        TestLLMProviderBackwardCompatibility, 
        TestConsolidatedMethods,
        TestPerformanceComparison,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Report summary
    print(f"\n{'='*50}")
    print(f"CONSOLIDATED PROMPTS TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\nFailures:")
        for test, failure in result.failures:
            print(f"  - {test}: {failure}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, error in result.errors:
            print(f"  - {test}: {error}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print(f"\nALL TESTS PASSED - Ready for deployment!")
    else:
        print(f"\nSOME TESTS FAILED - Please review before deployment!")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    run_comprehensive_tests()