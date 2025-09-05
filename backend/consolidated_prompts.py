"""
ConsolidatedPromptBuilder - Unified prompt generation for educational chatbot

This module implements consolidated prompt architecture to reduce API call latency
by combining multiple prompt components into single, comprehensive prompts.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

class ConsolidatedPromptBuilder:
    """
    Builds consolidated prompts by combining discrete components from JSON files.
    
    Features:
    - Load prompt components from JSON files
    - Build comprehensive prompts for single API calls
    - Template variable substitution
    - Fallback handling for missing components
    - Human-readable component management
    """
    
    def __init__(self, components_dir: str = None):
        """Initialize with components directory"""
        if components_dir is None:
            components_dir = os.path.join(os.path.dirname(__file__), "prompt_components")
        
        self.components_dir = Path(components_dir)
        self.components = {}
        self._load_all_components()
    
    def _load_all_components(self):
        """Load all component JSON files"""
        try:
            # Load educational framework
            self._load_component_file("educational_framework.json", "educational_framework")
            
            # Load content generation templates
            self._load_component_file("content_generation.json", "content_generation")
            
            # Load assessment modules
            self._load_component_file("assessment_modules.json", "assessment_modules")
            
            # Load response formatting
            self._load_component_file("response_formatting.json", "response_formatting")
            
            logger.info("✅ ConsolidatedPromptBuilder: All components loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ ConsolidatedPromptBuilder: Failed to load components: {e}")
            self._initialize_fallback_components()
    
    def _load_component_file(self, filename: str, component_key: str):
        """Load individual component file"""
        try:
            file_path = self.components_dir / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.components[component_key] = json.load(f)
                logger.info(f"✅ Loaded {component_key} from {filename}")
            else:
                logger.warning(f"Component file not found: {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to load {component_key} from {filename}: {e}")
    
    def _initialize_fallback_components(self):
        """Initialize minimal fallback components if loading fails"""
        self.components = {
            "educational_framework": {
                "components": {
                    "persona": {
                        "role": "friendly English tutor",
                        "tone": "encouraging and patient"
                    }
                }
            },
            "assessment_modules": {
                "components": {
                    "writing_feedback": {
                        "template": "Provide gentle feedback on '{user_input}' with encouragement."
                    }
                }
            }
        }
        logger.info("📄 ConsolidatedPromptBuilder: Initialized with fallback components")
    
    def build_consolidated_story_prompt(self, 
                                      topic: str, 
                                      user_input: str = None,
                                      story_step: str = "opening",
                                      include_feedback: bool = True,
                                      include_vocabulary: bool = True,
                                      content_type: str = "story") -> str:
        """
        Build consolidated prompt for story generation with optional feedback and vocabulary
        
        Args:
            topic: Story topic (space, animals, fantasy, etc.)
            user_input: User's story contribution (for continuation/feedback)
            story_step: Story phase (opening, continuation, conclusion)
            include_feedback: Whether to include writing feedback
            include_vocabulary: Whether to include vocabulary question generation
            
        Returns:
            Consolidated prompt string for single API call
        """
        try:
            prompt_parts = []
            
            # 1. Educational Framework
            framework = self._get_component("educational_framework", "persona")
            prompt_parts.append(f"""You are a {framework.get('role', 'friendly English tutor')} with a {framework.get('tone', 'encouraging and patient')} approach. You are working with {framework.get('age_target', '2nd-3rd grade students')} using {framework.get('communication_style', 'simple, clear language')}.
""")
            
            # 2. Content Generation Component (Story or Fact)
            if content_type == "fact":
                # Use fact templates
                if story_step == "opening":
                    content_template = self._get_component("content_generation", "fact_opening", "template")
                    story_content = content_template.format(topic=topic)
                else:  # continuation
                    content_template = self._get_component("content_generation", "fact_continuation", "template") 
                    story_content = content_template.format(topic=topic)
            else:
                # Use story templates
                if story_step == "opening":
                    story_template = self._get_component("content_generation", "story_opening", "template")
                    story_content = story_template.format(topic=topic)
                elif story_step == "continuation":
                    story_template = self._get_component("content_generation", "story_continuation", "template")
                    story_content = story_template.format(user_input=user_input or "")
                else:  # conclusion
                    story_template = self._get_component("content_generation", "story_conclusion", "template")
                    story_content = story_template.format(user_input=user_input or "")
            
            content_label = "FACT GENERATION" if content_type == "fact" else "STORY GENERATION"
            prompt_parts.append(f"{content_label}:\n{story_content}\n")
            
            # 3. Writing Feedback Component (if requested and user_input exists)
            if include_feedback and user_input:
                feedback_template = self._get_component("assessment_modules", "writing_feedback", "template")
                feedback_content = feedback_template.format(user_input=user_input)
                prompt_parts.append(f"WRITING FEEDBACK:\n{feedback_content}\n")
            
            # 4. Vocabulary Question Generation (if requested)
            if include_vocabulary:
                vocab_template = self._get_component("content_generation", "vocabulary_question_generation", "template")
                prompt_parts.append(f"VOCABULARY QUESTION:\nAfter generating the story, identify the most interesting vocabulary word and create a question using this template:\n{vocab_template}\n")
            
            # 5. Response Format
            if include_feedback and include_vocabulary:
                format_structure = self._get_component("response_formatting", "consolidated_response_format", "structure")
            else:
                format_structure = self._get_component("response_formatting", "story_response_format", "structure")
            
            json_format_template = self._get_component("response_formatting", "json_response_format", "template")
            format_instruction = json_format_template.format(format_structure=format_structure)
            prompt_parts.append(f"\n{format_instruction}")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"❌ Failed to build consolidated story prompt: {e}")
            return self._get_fallback_story_prompt(topic, user_input, story_step)
    
    def build_vocabulary_question_prompt(self, word: str, context: str) -> str:
        """
        Build prompt for standalone vocabulary question generation
        
        Args:
            word: Vocabulary word to create question about
            context: Story context where word appeared
            
        Returns:
            Prompt for vocabulary question generation
        """
        try:
            prompt_parts = []
            
            # Educational framework
            framework = self._get_component("educational_framework", "persona")
            prompt_parts.append(f"You are a {framework.get('role', 'friendly English tutor')}.\n")
            
            # Vocabulary question template
            vocab_template = self._get_component("content_generation", "vocabulary_question_generation", "template")
            vocab_content = vocab_template.format(word=word, context=context)
            prompt_parts.append(vocab_content)
            
            # Response format
            format_structure = self._get_component("response_formatting", "vocabulary_question_format", "structure")
            json_format_template = self._get_component("response_formatting", "json_response_format", "template")
            format_instruction = json_format_template.format(format_structure=format_structure)
            prompt_parts.append(f"\n{format_instruction}")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"❌ Failed to build vocabulary question prompt: {e}")
            return f"Create a vocabulary question about '{word}' from context: {context}"
    
    def build_writing_feedback_prompt(self, user_input: str) -> str:
        """
        Build prompt for standalone writing feedback
        
        Args:
            user_input: User's text to provide feedback on
            
        Returns:
            Prompt for writing feedback generation
        """
        try:
            prompt_parts = []
            
            # Educational framework
            framework = self._get_component("educational_framework", "persona")
            prompt_parts.append(f"You are a {framework.get('role', 'friendly English tutor')} with a {framework.get('tone', 'encouraging and patient')} approach.\n")
            
            # Writing feedback template
            feedback_template = self._get_component("assessment_modules", "writing_feedback", "template")
            feedback_content = feedback_template.format(user_input=user_input)
            prompt_parts.append(feedback_content)
            
            # Response format
            format_structure = self._get_component("response_formatting", "feedback_format", "structure")
            json_format_template = self._get_component("response_formatting", "json_response_format", "template")
            format_instruction = json_format_template.format(format_structure=format_structure)
            prompt_parts.append(f"\n{format_instruction}")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"❌ Failed to build writing feedback prompt: {e}")
            return f"Provide gentle, encouraging feedback on: '{user_input}'"
    
    def _get_component(self, category: str, *path_parts) -> Union[str, Dict[str, Any]]:
        """
        Get component value using dot notation path
        
        Args:
            category: Main component category
            *path_parts: Path parts to navigate the component structure
            
        Returns:
            Component value or fallback
        """
        try:
            component = self.components.get(category, {})
            
            # Navigate to components section
            if "components" in component:
                component = component["components"]
            
            # Navigate through path parts
            for part in path_parts:
                if isinstance(component, dict) and part in component:
                    component = component[part]
                else:
                    logger.warning(f"Component path not found: {category}.{'.'.join(path_parts)}")
                    return f"[Missing component: {category}.{'.'.join(path_parts)}]"
            
            return component
            
        except Exception as e:
            logger.error(f"❌ Error accessing component {category}.{'.'.join(path_parts)}: {e}")
            return f"[Component error: {category}.{'.'.join(path_parts)}]"
    
    def _get_fallback_story_prompt(self, topic: str, user_input: str = None, story_step: str = "opening") -> str:
        """Fallback prompt if component loading fails"""
        if story_step == "opening":
            return f"Create a 2-3 sentence story opening about {topic} for 2nd-3rd graders. Bold 2-3 vocabulary words."
        elif user_input:
            return f"Continue this story: {user_input}. Add 1-2 sentences and bold vocabulary words."
        else:
            return f"Create an age-appropriate story about {topic} with vocabulary words bolded."
    
    def reload_components(self):
        """Reload all components (useful for development)"""
        logger.info("🔄 ConsolidatedPromptBuilder: Reloading all components...")
        self.components = {}
        self._load_all_components()
    
    def get_component_summary(self) -> Dict[str, Any]:
        """Get summary of loaded components for debugging"""
        summary = {}
        for category, component in self.components.items():
            if isinstance(component, dict) and "components" in component:
                component_items = component["components"]
                summary[category] = list(component_items.keys()) if isinstance(component_items, dict) else "loaded"
            else:
                summary[category] = "loaded"
        return summary


# Create singleton instance for app usage
consolidated_prompt_builder = ConsolidatedPromptBuilder()