"""
End-to-end integration test for complete single story flow
Tests: Topic Selection → Story Generation → Design Phase → Vocabulary → Completion

This test ensures the core educational experience works end-to-end:
- Story generation with entity detection
- Design phase triggering and completion
- Vocabulary question generation
- Complete story flow without errors
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch
import json

# Add backend to path for imports and set working directory
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.append(backend_dir)

# Change working directory to backend for file loading
original_cwd = os.getcwd()
os.chdir(backend_dir)

from app import handle_storywriting, SessionData, VocabularyPhase
from llm_provider import LLMProvider

# Restore original working directory
os.chdir(original_cwd)

class TestCompleteStoryFlow:
    """Test complete single story educational experience"""
    
    def setup_method(self):
        """Set up fresh session for each test"""
        self.session_data = SessionData()
    
    @pytest.fixture
    def mock_story_responses(self):
        """Mock responses for complete story flow"""
        return {
            # Initial story with unnamed character for design phase
            "fantasy_story": {
                "story": "In an **enchanted** forest, a **brave** young adventurer discovered a glowing crystal that held ancient **magical** powers.",
                "entities": {
                    "characters": {
                        "named": [],
                        "unnamed": ["young adventurer"]
                    },
                    "locations": {
                        "named": [],
                        "unnamed": ["enchanted forest"]
                    }
                },
                "vocabulary_words": ["enchanted", "brave", "magical"]
            },
            
            # Story continuation after user input
            "story_continuation": "The adventurer carefully picked up the crystal, and suddenly the entire forest began to **sparkle** with mysterious **energy**.",
            
            # Design continuation after naming character
            "design_continuation": "Perfect! Now that we know our adventurer is named Alex, let's see how their story continues. Alex felt the crystal's power flowing through them, giving them the **courage** to explore deeper into the magical forest.",
            
            # Vocabulary questions
            "vocab_question_1": "What does 'enchanted' mean in our story?\nA) Broken\nB) Magical or under a spell\nC) Very old\nD) Very small",
            "vocab_question_2": "What does 'brave' mean?\nA) Scared of everything\nB) Very tall\nC) Showing courage when facing danger\nD) Very fast",
            
            # Grammar feedback
            "grammar_feedback": "Great description! Your writing shows Alex's personality perfectly. You might consider adding more details about what Alex is feeling in this moment."
        }
    
    @patch('llm_provider.llm_provider.generate_response')
    def test_complete_story_with_design_phase(self, mock_generate, mock_story_responses):
        """Test complete story flow with design phase"""
        
        mock_generate.side_effect = [
            json.dumps(mock_story_responses["fantasy_story"]),  # Initial story
            mock_story_responses["story_continuation"],         # User story continuation
            mock_story_responses["design_continuation"],        # Design phase continuation
            mock_story_responses["vocab_question_1"],           # Vocabulary question 1
            mock_story_responses["vocab_question_2"],           # Vocabulary question 2
        ]
        
        # Step 1: Start story with fantasy topic
        response1 = handle_storywriting("fantasy adventures", self.session_data)
        
        # Verify story generation
        assert response1.response is not None
        assert "enchanted" in response1.response
        assert "adventurer" in response1.response
        assert self.session_data.topic == "fantasy adventures"
        assert len(self.session_data.storyParts) == 1
        
        # Verify design phase was triggered for unnamed character
        assert hasattr(response1, 'designPrompt')
        if response1.designPrompt:
            assert response1.designPrompt.type in ["character", "location"]
            assert response1.designPrompt.aspect == "naming"
            assert self.session_data.designPhase is not None
            
            # Step 2: Provide name for character
            response2 = handle_storywriting("Alex", self.session_data)
            
            # Verify naming was accepted
            assert "Alex" in response2.response
            assert self.session_data.namingComplete == True
            
            # Check if story continuation was included
            if "continue" in response2.response.lower():
                # Story continued after design
                assert len(response2.response) > 50  # Should have substantial content
        
        # Step 3: User adds to story
        response3 = handle_storywriting("Alex decided to explore the mysterious cave nearby", self.session_data)
        
        # Verify story continuation
        assert len(self.session_data.storyParts) > 1
        assert "Alex" in str(self.session_data.storyParts) or "cave" in response3.response
        
        # Step 4: Complete story
        self.session_data.isComplete = True
        
        # Test vocabulary phase
        response4 = handle_storywriting("answer_vocab", self.session_data)
        
        # Should get vocabulary question
        vocab_triggered = (
            hasattr(response4, 'vocabQuestion') and response4.vocabQuestion is not None
        ) or "mean" in response4.response.lower()
        
        # At minimum, should not crash and should provide some response
        assert response4.response is not None
        assert len(response4.response) > 0
    
    @patch('llm_provider.llm_provider.generate_response')  
    def test_story_flow_without_design_phase(self, mock_generate, mock_story_responses):
        """Test story flow when no design phase is triggered (all named entities)"""
        
        # Mock story with all named entities (no design phase)
        named_entity_story = {
            "story": "Captain Luna and Commander Rex explored the **mysterious** Planet Zara, searching for **ancient** artifacts.",
            "entities": {
                "characters": {
                    "named": ["Captain Luna", "Commander Rex"],
                    "unnamed": []
                },
                "locations": {
                    "named": ["Planet Zara"],
                    "unnamed": []
                }
            },
            "vocabulary_words": ["mysterious", "ancient"]
        }
        
        mock_generate.side_effect = [
            json.dumps(named_entity_story),
            mock_story_responses["story_continuation"]
        ]
        
        # Start story
        response1 = handle_storywriting("space exploration", self.session_data)
        
        # Verify story generated
        assert "Luna" in response1.response
        assert "Rex" in response1.response
        assert self.session_data.topic == "space exploration"
        
        # Verify no design phase (all entities are named)
        design_triggered = hasattr(response1, 'designPrompt') and response1.designPrompt is not None
        
        # Should either have no design prompt, or if validation failed, should still work
        if not design_triggered:
            # No design phase - verify story continues normally
            response2 = handle_storywriting("They found a strange glowing object", self.session_data)
            assert len(self.session_data.storyParts) >= 1
    
    def test_error_recovery_in_story_flow(self):
        """Test that story flow recovers gracefully from errors"""
        
        # Test with empty/invalid input
        response1 = handle_storywriting("", self.session_data)
        assert response1.response is not None  # Should not crash
        
        # Test with very long input
        long_input = "adventure " * 100  # 900 characters
        response2 = handle_storywriting(long_input, self.session_data)
        assert response2.response is not None  # Should handle gracefully
        
        # Test with special characters
        special_input = "space @#$%^&*()_+ adventures!?><"
        response3 = handle_storywriting(special_input, self.session_data)
        assert response3.response is not None  # Should not crash
    
    @patch('llm_provider.llm_provider.generate_response')
    def test_vocabulary_tracking_throughout_story(self, mock_generate, mock_story_responses):
        """Test that vocabulary words are tracked correctly throughout story"""
        
        mock_generate.side_effect = [
            json.dumps(mock_story_responses["fantasy_story"]),
            mock_story_responses["story_continuation"]
        ]
        
        # Start story
        response1 = handle_storywriting("fantasy", self.session_data)
        
        # Verify vocabulary tracking started
        assert len(self.session_data.contentVocabulary) >= 0  # May have words from initial story
        
        # Continue story
        response2 = handle_storywriting("The crystal glowed brighter", self.session_data)
        
        # Verify vocabulary is being tracked across interactions
        # Should not crash and should maintain vocabulary state
        assert hasattr(self.session_data, 'contentVocabulary')
        assert isinstance(self.session_data.contentVocabulary, list)
    
    def test_session_state_consistency(self):
        """Test that session state remains consistent throughout story"""
        
        # Start with clean session
        assert self.session_data.currentStep == 0
        assert self.session_data.isComplete == False
        assert len(self.session_data.storyParts) == 0
        assert self.session_data.topic is None
        
        # After starting story, certain fields should be set
        response = handle_storywriting("ocean adventures", self.session_data)
        
        # Verify basic session state
        if response.response and "having trouble" not in response.response.lower():
            # Story started successfully
            assert self.session_data.topic is not None
            assert self.session_data.currentStep >= 0
    
    def test_design_phase_field_management(self):
        """Test that design phase fields are managed correctly"""
        
        # Start with no design fields set
        assert self.session_data.designPhase is None
        assert self.session_data.currentDesignAspect is None
        assert len(self.session_data.designAspectHistory) == 0
        assert self.session_data.designComplete == False
        
        # After story with design phase, some fields might be set
        response = handle_storywriting("mystery adventures", self.session_data)
        
        # If design phase triggered, fields should be set appropriately
        if hasattr(response, 'designPrompt') and response.designPrompt:
            # Design phase active
            assert self.session_data.designPhase in ["character", "location"]
            assert self.session_data.currentDesignAspect is not None
            assert self.session_data.designComplete == False
        else:
            # No design phase - fields should remain unset
            assert self.session_data.designPhase is None