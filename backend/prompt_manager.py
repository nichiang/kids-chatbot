"""
PromptManager - Compatibility stub for consolidated prompts system

This module provides minimal compatibility methods for existing app.py code
while the new consolidated prompts system handles the main functionality.
"""

from typing import Dict, List, Optional, Tuple
import json
import random
import logging

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Compatibility stub for prompt manager functionality.
    Main prompt generation now handled by consolidated_prompts system.
    """
    
    def __init__(self):
        """Initialize with minimal compatibility methods"""
        try:
            # Import here to avoid circular imports
            from content_manager import content_manager
            
            # Get minimal templates needed for compatibility
            self.story_templates = content_manager.content.get("story_templates", {})
            self.conflict_types = content_manager.content.get("narrative_guidance", {})
            
            logger.info("✅ PromptManager compatibility stub loaded")
            
        except Exception as e:
            logger.error(f"❌ Failed to load PromptManager stub: {e}")
            self.story_templates = {}
            self.conflict_types = {}
    
    def enhance_with_vocabulary(self, base_prompt: str, topic: str, used_words: List[str]) -> Tuple[str, List[str]]:
        """Compatibility method - returns prompt as-is since consolidated system handles vocabulary"""
        return base_prompt, []
    
    def should_end_story_intelligently(self, session_data) -> Tuple[bool, str]:
        """Compatibility method - simple story ending logic"""
        # Simple logic: end after 4+ story parts
        story_parts_count = len([part for part in session_data.storyParts if not part.startswith("User:")])
        should_end = story_parts_count >= 4
        reason = "Story has enough content" if should_end else "Story needs more development"
        return should_end, reason
    
    def get_story_arc_assessment_prompt(self, story_parts: List[str], topic: str) -> str:
        """Compatibility method - returns simple assessment prompt"""
        return f"Assess this {topic} story: {' '.join(story_parts[-2:])}"
    
    def get_design_continuation_prompt(self, *args, **kwargs) -> str:
        """Compatibility method"""
        return "Continue with the design elements."
    
    def get_grammar_feedback_prompt(self, user_message: str, *args, **kwargs) -> str:
        """Compatibility method"""
        return f"Provide feedback on: {user_message}"
    
    def generate_massive_vocabulary_pool(self, topic: str, used_words: List[str]) -> Dict:
        """Compatibility method"""
        return {"space": ["asteroid", "galaxy", "planet"], "fantasy": ["magical", "enchanted", "legendary"]}
    
    def get_story_opening_prompt(self, topic: str, mode: str = "auto") -> str:
        """Compatibility method - not used by consolidated system"""
        return f"Create a story opening about {topic} for elementary students."
    
    def get_continue_story_prompt(self, topic: str, context: str) -> str:
        """Compatibility method"""
        return f"Continue this {topic} story: {context}"
    
    def get_narrative_continuation_prompt(self, assessment: Dict, topic: str, context: str) -> str:
        """Compatibility method"""
        return f"Continue this {topic} story with narrative awareness: {context}"
    
    def get_conflict_integration_prompt(self, topic: str, conflict_type: str, conflict_scale: int) -> str:
        """Compatibility method"""
        return f"Add age-appropriate {conflict_type} conflict to {topic} story."
    
    def get_story_ending_prompt(self, topic: str, context: str) -> str:
        """Compatibility method"""
        return f"End this {topic} story: {context}"


# Global instance for compatibility
prompt_manager = PromptManager()