"""Regression test to prevent proper noun vocabulary selection bug from returning (GitHub Issue #3)"""

import sys
import os
import pytest

# Add backend to path for imports and set working directory
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.append(backend_dir)

# Change working directory to backend for file loading
original_cwd = os.getcwd()
os.chdir(backend_dir)

from app import extract_vocabulary_from_content, select_best_vocabulary_word
from llm_provider import LLMProvider

# Restore original working directory
os.chdir(original_cwd)

class TestProperNounFix:
    """Regression test for proper noun filtering in vocabulary selection (GitHub Issue #3)"""
    
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
    def vincent_van_gogh_context(self):
        """The problematic context from GitHub issue #3 - Vincent van Gogh example"""
        return """Did you know that the famous artist **Vincent van Gogh** created over 2,100 pieces of art in his lifetime? One of his most **magnificent** paintings, "Starry Night," shows a night sky swirling with bright stars and is one of the most beloved paintings in the world! People are often **curious** about how he painted with such emotion and color, making his work truly **fascinating** even today! 🎨✨🌌"""
    
    @pytest.fixture
    def pablo_picasso_context(self):
        """The problematic context from GitHub issue #3 - Pablo Picasso example"""
        return """Did you know that the famous artist **Pablo Picasso** created a painting called "Guernica" that is over 25 feet long? This **stunning** piece is a **treasure** of modern art, and it shows the horrors of war, reminding us that artists have the **responsibility** to tell important stories through their work. Picasso's unique style, with bold shapes and colors, gives everyone the **opportunity** to see the world in a new way! 🖌️🖼️🌍"""
    
    def test_extracts_all_vocabulary_words_including_proper_nouns(self, vincent_van_gogh_context):
        """Test that extraction still works but includes proper nouns for filtering"""
        extracted_words = extract_vocabulary_from_content(
            vincent_van_gogh_context, 
            ['magnificent', 'curious', 'fascinating']
        )
        
        # Should extract all bolded words, including the proper noun
        assert len(extracted_words) == 4, f"Expected 4 words, got {len(extracted_words)}: {extracted_words}"
        assert 'Vincent van Gogh' in extracted_words, "Should extract proper noun for filtering"
        assert 'magnificent' in extracted_words, "Should extract vocabulary word"
        assert 'curious' in extracted_words, "Should extract vocabulary word"
        assert 'fascinating' in extracted_words, "Should extract vocabulary word"
    
    def test_filters_out_multi_word_proper_nouns(self, vincent_van_gogh_context):
        """Test that select_best_vocabulary_word filters out multi-word proper nouns"""
        extracted_words = extract_vocabulary_from_content(
            vincent_van_gogh_context, 
            ['magnificent', 'curious', 'fascinating']
        )
        
        selected_word = select_best_vocabulary_word(extracted_words)
        
        # Should NOT select the multi-word proper noun
        assert selected_word != 'Vincent van Gogh', "Should not select multi-word proper noun"
        assert selected_word in ['magnificent', 'curious', 'fascinating'], f"Should select appropriate vocabulary word, got: {selected_word}"
        
        # Should select first single word (after filtering)
        single_words = [word for word in extracted_words if len(word.split()) == 1]
        assert selected_word == single_words[0], f"Should select first single word: expected {single_words[0]}, got {selected_word}"
    
    def test_pablo_picasso_scenario(self, pablo_picasso_context):
        """Test the Pablo Picasso scenario from the bug report"""
        extracted_words = extract_vocabulary_from_content(
            pablo_picasso_context,
            ['stunning', 'treasure', 'responsibility', 'opportunity']
        )
        
        selected_word = select_best_vocabulary_word(extracted_words)
        
        # Should NOT select the multi-word proper noun
        assert selected_word != 'Pablo Picasso', "Should not select multi-word proper noun 'Pablo Picasso'"
        assert selected_word in ['stunning', 'treasure', 'responsibility', 'opportunity'], f"Should select appropriate vocabulary word, got: {selected_word}"
    
    def test_vocabulary_question_generation_uses_filtered_word(self, llm_provider, vincent_van_gogh_context):
        """Test that vocabulary question generation uses filtered vocabulary word, not proper noun"""
        # This tests the end-to-end flow including the LLM provider fixes
        question_result = llm_provider._get_fallback_vocab_question("vincent van gogh", vincent_van_gogh_context)
        
        assert question_result is not None, "Should generate vocabulary question"
        
        # Should NOT use the proper noun in the question
        question_text = question_result["question"]
        assert "**Vincent van Gogh**" not in question_text, "Should not use proper noun in question"
        
        # Should use one of the appropriate vocabulary words
        appropriate_words = ['magnificent', 'curious', 'fascinating']
        found_appropriate_word = False
        for word in appropriate_words:
            if f"**{word}**" in question_text:
                found_appropriate_word = True
                break
        
        assert found_appropriate_word, f"Should use appropriate vocabulary word in question, got: {question_text}"
    
    def test_single_word_proper_nouns_allowed(self):
        """Test that single word proper nouns (like 'Olympics') are still allowed"""
        # This ensures we don't break legitimate single-word vocabulary like "Olympics"
        test_words = ['Olympics', 'determination', 'Vincent van Gogh']
        selected = select_best_vocabulary_word(test_words)
        
        # Should filter out multi-word but keep single words
        assert selected in ['Olympics', 'determination'], f"Should keep single words, got: {selected}"
        assert selected != 'Vincent van Gogh', "Should filter out multi-word proper noun"
    
    def test_edge_case_all_multi_word_proper_nouns(self):
        """Test edge case where all words are multi-word proper nouns"""
        test_words = ['Vincent van Gogh', 'Pablo Picasso', 'Leonardo da Vinci']
        selected = select_best_vocabulary_word(test_words)
        
        # Should return first word as last resort (this shouldn't happen in practice)
        assert selected == 'Vincent van Gogh', "Should return first word as last resort when all words are filtered out"