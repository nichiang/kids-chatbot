"""Regression test to prevent Olympics case/punctuation vocabulary bug from returning"""

import sys
import os
import pytest

# Add backend to path for imports and set working directory
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.append(backend_dir)

# Change working directory to backend for file loading
original_cwd = os.getcwd()
os.chdir(backend_dir)

from llm_provider import LLMProvider

# Restore original working directory
os.chdir(original_cwd)

class TestOlympicsFix:
    """Regression test for Olympics case-insensitive and punctuation bug (GitHub Issue #1)"""
    
    @pytest.fixture
    def llm_provider(self):
        """Initialize LLM provider for testing"""
        # Need to be in backend directory when creating LLMProvider
        backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
        original_cwd = os.getcwd()
        os.chdir(backend_dir)
        try:
            provider = LLMProvider()
        finally:
            os.chdir(original_cwd)
        return provider
    
    @pytest.fixture
    def olympics_context(self):
        """The problematic context with case and punctuation mismatch"""
        return """Did you know that the **Olympics,** held every four years, brings together athletes from around the world? The first modern Olympics took place in 1896 in Athens, Greece! Today, both Summer and Winter Olympics showcase incredible talent and **determination** from thousands of competitors. 🏅🌍⭐"""
    
    def test_actual_words_extracted_with_punctuation_cleaned(self, llm_provider, olympics_context):
        """Test that punctuation is stripped from extracted words"""
        actual_words = llm_provider.extract_vocabulary_words(olympics_context)
        
        assert 'Olympics' in actual_words, "Should extract 'Olympics' (capitalized, punctuation stripped)"
        assert 'determination' in actual_words, "Should also extract 'determination'"
        assert 'Olympics,' not in actual_words, "Should strip trailing comma from 'Olympics,'"
    
    def test_case_insensitive_sentence_extraction(self, llm_provider, olympics_context):
        """Test that sentence extraction works despite case differences"""
        intended_word = "olympics"  # lowercase intended
        
        # The current implementation should work due to case-insensitive regex
        sentence = llm_provider._extract_sentence_with_word(intended_word, olympics_context)
        
        assert sentence is not None, "Should extract sentence despite case difference"
        assert "**Olympics,**" in sentence, "Should find the capitalized, punctuated version"
        assert sentence == "Did you know that the **Olympics,** held every four years, brings together athletes from around the world?", "Should extract first sentence only"
    
    def test_actual_word_approach_handles_case_and_punctuation(self, llm_provider, olympics_context):
        """Test that using actual extracted word works perfectly"""
        actual_words = llm_provider.extract_vocabulary_words(olympics_context)
        actual_word = actual_words[0]  # Should be 'Olympics' (cleaned)
        
        sentence = llm_provider._extract_sentence_with_word(actual_word, olympics_context)
        
        assert sentence is not None, "Should extract sentence when using actual cleaned word"
        assert "**Olympics,**" in sentence, "Should match despite the comma in original text"
    
    def test_vocabulary_question_uses_cleaned_word(self, llm_provider, olympics_context):
        """Test that vocabulary questions use cleaned actual word"""
        intended_word = "olympics"
        
        question_result = llm_provider._get_fallback_vocab_question(intended_word, olympics_context)
        
        assert question_result is not None, "Should generate vocabulary question"
        assert "**Olympics**" in question_result["question"], "Question should use cleaned 'Olympics' (no comma)"
        
        # The question should use cleaned word but the reference sentence shows original context
        question_text = question_result["question"]
        assert "What does the word **Olympics** mean?" in question_text, "Question should use cleaned word"
        assert "**Olympics,**" in question_text, "Reference sentence should show original context with punctuation"
        
        # Should extract just the first sentence, not full context
        assert "Athens, Greece" not in question_text, "Should not include second sentence"
        assert "determination" not in question_text, "Should not include other vocabulary words"
    
    def test_multiple_vocabulary_words_handled_correctly(self, llm_provider, olympics_context):
        """Test that context with multiple vocabulary words extracts the first one for questions"""
        actual_words = llm_provider.extract_vocabulary_words(olympics_context)
        
        assert len(actual_words) == 2, "Should extract exactly 2 vocabulary words"
        assert actual_words == ['Olympics', 'determination'], "Should extract both words with punctuation cleaned"
        
        # Test that question generation uses the first word
        question_result = llm_provider._get_fallback_vocab_question("olympics", olympics_context)
        assert "**Olympics**" in question_result["question"], "Should use first word for question"
    
    def test_case_punctuation_integration(self, llm_provider, olympics_context):
        """Integration test: full workflow with case and punctuation variations"""
        intended_word = "olympics"  # lowercase intended
        
        question_result = llm_provider._get_fallback_vocab_question(intended_word, olympics_context)
        
        # Verify question quality  
        assert question_result["question"] is not None
        assert len(question_result["options"]) == 4
        assert question_result["correctIndex"] in [0, 1, 2, 3]
        
        # Key regression test: should use proper sentence extraction
        question_text = question_result["question"]
        sentence_count = question_text.count('!')
        assert sentence_count <= 1, "Should not include multiple exclamatory sentences from full context"