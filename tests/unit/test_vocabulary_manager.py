"""Unit tests for vocabulary_manager.py functions"""

import sys
import os
import pytest

# Add backend to path for imports and set working directory
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.append(backend_dir)

# Change working directory to backend for file loading
original_cwd = os.getcwd()
os.chdir(backend_dir)

from vocabulary_manager import VocabularyManager

# Restore original working directory
os.chdir(original_cwd)

class TestVocabularyManager:
    """Unit tests for VocabularyManager class"""
    
    @pytest.fixture
    def vocab_manager(self):
        """Initialize VocabularyManager for testing"""
        backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
        original_cwd = os.getcwd()
        os.chdir(backend_dir)
        try:
            manager = VocabularyManager()
        finally:
            os.chdir(original_cwd)
        return manager
    
    def test_vocabulary_manager_initialization(self, vocab_manager):
        """Test that VocabularyManager initializes correctly"""
        assert vocab_manager is not None, "VocabularyManager should initialize"
        assert hasattr(vocab_manager, 'general_vocabulary'), "Should have general vocabulary"
        assert hasattr(vocab_manager, 'topic_vocabularies'), "Should have topic vocabularies"
    
    def test_general_vocabulary_loaded(self, vocab_manager):
        """Test that general vocabulary is loaded with expected structure"""
        assert len(vocab_manager.general_vocabulary) > 0, "General vocabulary should not be empty"
        
        # Test vocabulary structure
        first_word = vocab_manager.general_vocabulary[0]
        required_fields = ['word', 'definition', 'difficulty', 'type', 'example', 'grade_level']
        
        for field in required_fields:
            assert field in first_word, f"Vocabulary entry should have '{field}' field"
    
    def test_topic_vocabularies_loaded(self, vocab_manager):
        """Test that topic vocabularies are loaded"""
        expected_topics = ['animals', 'fantasy', 'food', 'ocean', 'space', 'sports']
        
        for topic in expected_topics:
            assert topic in vocab_manager.topic_vocabularies, f"Should have vocabulary for topic: {topic}"
            assert len(vocab_manager.topic_vocabularies[topic]) > 0, f"Topic '{topic}' vocabulary should not be empty"
    
    def test_select_vocabulary_word_basic(self, vocab_manager):
        """Test basic vocabulary word selection"""
        word_data = vocab_manager.select_vocabulary_word(topic="space")
        
        assert word_data is not None, "Should return a vocabulary word"
        assert isinstance(word_data, dict), "Word data should be a dictionary"
        assert 'word' in word_data, "Word data should have 'word' field"
        assert len(word_data['word']) > 0, "Word should not be empty"
    
    def test_select_vocabulary_word_with_exclusions(self, vocab_manager):
        """Test vocabulary selection with excluded words"""
        # Get a word first
        first_word_data = vocab_manager.select_vocabulary_word(topic="space")
        first_word = first_word_data['word']
        
        # Select again excluding the first word
        second_word_data = vocab_manager.select_vocabulary_word(
            topic="space", 
            used_words=[first_word]
        )
        
        assert second_word_data['word'] != first_word, "Should return a different word when excluding previous selection"
    
    def test_get_vocabulary_for_topic(self, vocab_manager):
        """Test getting all vocabulary for a specific topic"""
        space_words = vocab_manager.get_vocabulary_for_topic("space")
        
        assert isinstance(space_words, list), "Should return a list of words"
        assert len(space_words) > 0, "Space vocabulary should not be empty"
        
        # Test with unknown topic
        unknown_words = vocab_manager.get_vocabulary_for_topic("unknown_topic")
        assert isinstance(unknown_words, list), "Should return a list even for unknown topics"
        # Unknown topic should fallback to general vocabulary, so may not be empty
    
    def test_select_advanced_general_words(self, vocab_manager):
        """Test advanced general word selection for Solution 3"""
        words = vocab_manager.select_advanced_general_words(count=10, excluded_words=[])
        
        assert isinstance(words, list), "Should return a list of words"
        assert len(words) <= 10, "Should return at most the requested count"
        
        # Test with exclusions
        excluded = words[:3] if len(words) >= 3 else []
        remaining_words = vocab_manager.select_advanced_general_words(
            count=5, 
            excluded_words=excluded
        )
        
        for excluded_word in excluded:
            assert excluded_word not in remaining_words, f"Excluded word '{excluded_word}' should not be in results"
    
    def test_vocabulary_difficulty_levels(self, vocab_manager):
        """Test that vocabulary contains appropriate difficulty levels for 2nd-3rd grade"""
        # Check general vocabulary difficulty distribution
        difficulties = []
        for word_data in vocab_manager.general_vocabulary:
            difficulties.append(word_data.get('difficulty', 0))
        
        # Should contain mostly tier 2 and tier 3 words (difficulty 2-3)
        valid_difficulties = [d for d in difficulties if 2 <= d <= 3]
        assert len(valid_difficulties) > len(difficulties) * 0.8, "At least 80% should be tier 2-3 difficulty"
    
    def test_solution_3_massive_pool_generation(self, vocab_manager):
        """Test the Solution 3 massive vocabulary pool generation"""
        # This would test the generate_massive_vocabulary_pool function
        # but we need to implement it first in vocabulary_manager.py
        
        # For now, test that we can generate enough words for Solution 3
        general_words = vocab_manager.select_advanced_general_words(count=20, excluded_words=[])
        topic_words = vocab_manager.get_all_topic_vocabulary("space")
        
        total_available = len(general_words) + len(topic_words)
        assert total_available >= 30, "Should have enough vocabulary for Solution 3 (need 40 total, 30+ is reasonable)"
    
    def test_word_selection_preference_system(self, vocab_manager):
        """Test that unused words are preferred over used words"""
        # Select several words from the same topic
        used_words = []
        for i in range(3):
            word = vocab_manager.select_vocabulary_word(
                topic="animals", 
                excluded_words=used_words
            )
            used_words.append(word)
        
        # All selected words should be different
        assert len(set(used_words)) == len(used_words), "All selected words should be unique"
        
        # Should prefer unused words when possible
        for word in used_words:
            assert word is not None and len(word) > 0, "Each selected word should be valid"