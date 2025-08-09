"""Regression test to prevent constellation vocabulary bug from returning"""

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

class TestConstellationFix:
    """Regression test for constellation word form mismatch bug (GitHub Issue #1)"""
    
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
    def constellation_context(self):
        """The problematic context that caused the original bug"""
        return """Did you know that there are 88 different **constellations** in the night sky? One of the most famous is Orion, which looks like a hunter with a belt made of three bright stars! People have been looking up at these star patterns for thousands of years, and they still inspire us to explore the universe and feel the wonder of space. So next time you're outside at night, try to spot Orion and imagine all the stories people have told about the stars! 🌟🌌🔭"""
    
    def test_actual_words_extracted_correctly(self, llm_provider, constellation_context):
        """Test that actual bolded words are extracted from context"""
        actual_words = llm_provider.extract_vocabulary_words(constellation_context)
        
        assert actual_words == ['constellations'], f"Expected ['constellations'], got {actual_words}"
        assert 'constellations' in actual_words, "Should extract 'constellations' from context"
    
    def test_sentence_extraction_works_with_actual_word(self, llm_provider, constellation_context):
        """Test that sentence extraction works with the actual word form"""
        actual_words = llm_provider.extract_vocabulary_words(constellation_context)
        actual_word = actual_words[0]  # 'constellations'
        
        sentence = llm_provider._extract_sentence_with_word(actual_word, constellation_context)
        
        assert sentence is not None, "Should extract sentence when using actual word"
        assert "**constellations**" in sentence, "Extracted sentence should contain the bolded word"
        assert sentence == "Did you know that there are 88 different **constellations** in the night sky?", "Should extract the first sentence only"
    
    def test_sentence_extraction_fails_with_intended_word(self, llm_provider, constellation_context):
        """Test that old approach fails with intended word (demonstrates the bug was fixed)"""
        intended_word = "constellation"  # singular
        
        sentence = llm_provider._extract_sentence_with_word(intended_word, constellation_context)
        
        assert sentence is None, "Should fail to extract sentence when word forms don't match"
    
    def test_vocabulary_question_generation_uses_actual_word(self, llm_provider, constellation_context):
        """Test that vocabulary questions use the actual bolded word, not intended word"""
        intended_word = "constellation"  # What vocabulary system intended
        
        question_result = llm_provider._get_fallback_vocab_question(intended_word, constellation_context)
        
        assert question_result is not None, "Should generate vocabulary question"
        assert "**constellations**" in question_result["question"], "Question should use actual word 'constellations'"
        assert "constellations" in question_result["question"], "Question text should contain 'constellations'"
        
        # Verify the sentence reference is correct (single sentence, not full context)
        question_text = question_result["question"]
        sentence_count = question_text.count('?')
        assert sentence_count == 2, f"Should contain exactly 2 question marks (question + reference sentence), got {sentence_count}"
    
    def test_bug_prevention_integration(self, llm_provider, constellation_context):
        """Integration test: entire workflow should work with word form mismatch"""
        intended_word = "constellation"
        
        # This should work end-to-end despite the word form mismatch
        question_result = llm_provider._get_fallback_vocab_question(intended_word, constellation_context)
        
        # Verify question quality
        assert question_result["question"] is not None
        assert len(question_result["options"]) == 4
        assert question_result["correctIndex"] in [0, 1, 2, 3]
        
        # Most importantly: should not fall back to full context
        question_text = question_result["question"]
        assert "Orion" not in question_text, "Should not include full context with multiple sentences"
        assert "imagine all the stories" not in question_text, "Should not include full context"