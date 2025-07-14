import json
import os
import random
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class VocabularyManager:
    """Manages curated vocabulary banks for both topic-specific and general educational words"""
    
    def __init__(self):
        self.vocabulary_dir = os.path.join(os.path.dirname(__file__), "vocabulary")
        self.topics_dir = os.path.join(self.vocabulary_dir, "topics")
        self.general_vocabulary = []
        self.topic_vocabularies = {}
        self.load_all_vocabularies()
    
    def load_all_vocabularies(self):
        """Load general and all topic-specific vocabularies at startup"""
        try:
            # Load general vocabulary
            general_path = os.path.join(self.vocabulary_dir, "general.json")
            if os.path.exists(general_path):
                with open(general_path, 'r') as f:
                    data = json.load(f)
                    self.general_vocabulary = data.get('vocabulary', [])
                logger.info(f"Loaded {len(self.general_vocabulary)} general vocabulary words")
            
            # Load topic-specific vocabularies
            if os.path.exists(self.topics_dir):
                for filename in os.listdir(self.topics_dir):
                    if filename.endswith('.json'):
                        topic_name = filename[:-5]  # Remove .json extension
                        topic_path = os.path.join(self.topics_dir, filename)
                        with open(topic_path, 'r') as f:
                            data = json.load(f)
                            self.topic_vocabularies[topic_name] = data.get('vocabulary', [])
                        logger.info(f"Loaded {len(self.topic_vocabularies[topic_name])} words for topic: {topic_name}")
                        
        except Exception as e:
            logger.error(f"Error loading vocabularies: {e}")
            # Fallback to empty lists
            self.general_vocabulary = []
            self.topic_vocabularies = {}
    
    def get_vocabulary_for_topic(self, topic: str) -> List[Dict]:
        """Get combined vocabulary (topic-specific + general) for a given topic"""
        combined_vocabulary = []
        
        # Add topic-specific vocabulary if available
        topic_lower = topic.lower()
        if topic_lower in self.topic_vocabularies:
            combined_vocabulary.extend(self.topic_vocabularies[topic_lower])
            logger.info(f"Using topic vocabulary for: {topic_lower}")
        
        # Always add general vocabulary
        combined_vocabulary.extend(self.general_vocabulary)
        
        logger.info(f"Total vocabulary pool for '{topic}': {len(combined_vocabulary)} words")
        return combined_vocabulary
    
    def select_vocabulary_word(self, topic: str, used_words: List[str] = None, 
                             difficulty_mix: Dict[str, float] = None) -> Optional[Dict]:
        """
        Select a vocabulary word using the 50/50 Level 2-3 mix for advanced learners
        
        Args:
            topic: The topic for vocabulary selection
            used_words: List of recently used words to avoid
            difficulty_mix: Dict with level percentages (defaults to 50% level 2, 50% level 3)
        
        Returns:
            Dictionary with word data or None if no suitable words found
        """
        if used_words is None:
            used_words = []
        
        if difficulty_mix is None:
            # Default 50/50 Level 2-3 mix for advanced learner
            difficulty_mix = {"level2": 0.5, "level3": 0.5}
        
        # Get vocabulary pool for this topic
        vocabulary_pool = self.get_vocabulary_for_topic(topic)
        
        if not vocabulary_pool:
            logger.warning(f"No vocabulary available for topic: {topic}")
            return None
        
        # Filter out recently used words
        available_words = [word for word in vocabulary_pool 
                          if word['word'] not in used_words]
        
        if not available_words:
            # If all words have been used recently, reset and use full pool
            logger.info("All words recently used, resetting to full vocabulary pool")
            available_words = vocabulary_pool
        
        # Separate by difficulty levels (skip Level 1 for advanced learner)
        level_2_words = [w for w in available_words if w['difficulty'] == 2]
        level_3_words = [w for w in available_words if w['difficulty'] == 3]
        
        # Select based on difficulty mix
        selected_words = []
        
        # Add Level 2 words (50% by default)
        level2_count = int(len(level_2_words) * difficulty_mix.get("level2", 0.5))
        if level2_count > 0 and level_2_words:
            selected_words.extend(random.sample(level_2_words, min(level2_count, len(level_2_words))))
        
        # Add Level 3 words (50% by default)  
        level3_count = int(len(level_3_words) * difficulty_mix.get("level3", 0.5))
        if level3_count > 0 and level_3_words:
            selected_words.extend(random.sample(level_3_words, min(level3_count, len(level_3_words))))
        
        # If no words in desired difficulty range, fall back to any available word
        if not selected_words:
            selected_words = available_words
        
        if not selected_words:
            logger.warning(f"No vocabulary words available for topic: {topic}")
            return None
        
        # Select one word randomly from the difficulty-balanced pool
        selected_word = random.choice(selected_words)
        
        logger.info(f"Selected vocabulary word: '{selected_word['word']}' "
                   f"(difficulty {selected_word['difficulty']}) for topic: {topic}")
        
        return selected_word
    
    def get_word_by_name(self, word_name: str, topic: str = None) -> Optional[Dict]:
        """Get a specific word's data by name"""
        vocabulary_pool = []
        
        if topic:
            vocabulary_pool = self.get_vocabulary_for_topic(topic)
        else:
            # Search in all vocabularies
            vocabulary_pool.extend(self.general_vocabulary)
            for topic_vocab in self.topic_vocabularies.values():
                vocabulary_pool.extend(topic_vocab)
        
        for word_data in vocabulary_pool:
            if word_data['word'].lower() == word_name.lower():
                return word_data
        
        return None
    
    def get_available_topics(self) -> List[str]:
        """Get list of all available topic vocabularies"""
        return list(self.topic_vocabularies.keys())
    
    def get_vocabulary_stats(self) -> Dict:
        """Get statistics about loaded vocabularies"""
        stats = {
            "general_words": len(self.general_vocabulary),
            "topics": {}
        }
        
        for topic, vocab in self.topic_vocabularies.items():
            difficulty_counts = {}
            for word in vocab:
                diff = word['difficulty']
                difficulty_counts[f"level_{diff}"] = difficulty_counts.get(f"level_{diff}", 0) + 1
            
            stats["topics"][topic] = {
                "total_words": len(vocab),
                "difficulty_breakdown": difficulty_counts
            }
        
        return stats

# Global vocabulary manager instance
vocabulary_manager = VocabularyManager()