"""
ContentManager - Centralized content management for English Learning Chatbot

This module provides a single source of truth for all user-facing content,
bot responses, prompts, and educational messaging. Content is separated from
business logic for easier maintenance and future internationalization.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ContentManager:
    """
    Centralized manager for all application content including bot responses,
    prompts, UI messages, and educational feedback.
    
    Features:
    - Load content from JSON files at startup
    - Template interpolation for dynamic content
    - Hierarchical content organization
    - Easy content reloading without restart
    """
    
    def __init__(self, content_dir: str = None):
        """Initialize ContentManager with content directory"""
        if content_dir is None:
            content_dir = os.path.join(os.path.dirname(__file__), "content")
        
        self.content_dir = Path(content_dir)
        self.content = {}
        self._load_all_content()
    
    def _load_all_content(self):
        """Load all content from JSON files"""
        try:
            # Load string content
            self._load_strings()
            
            # Load prompt templates
            self._load_prompts()
            
            # Load configuration
            self._load_config()
            
            # Create design templates mapping for app.py compatibility
            self._create_design_templates_mapping()
            
            logger.info("✅ ContentManager: All content loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ ContentManager: Failed to load content: {e}")
            # Initialize with empty content as fallback
            self._initialize_fallback_content()
    
    def _load_strings(self):
        """Load string content from strings directory"""
        strings_dir = self.content_dir / "strings"
        
        if not strings_dir.exists():
            logger.warning(f"Strings directory not found: {strings_dir}")
            return
        
        # Load bot responses
        self._load_json_file(strings_dir / "bot_responses.json", "bot_responses")
        
        # Load UI messages
        self._load_json_file(strings_dir / "ui_messages.json", "ui_messages")
        
        # Load educational feedback
        self._load_json_file(strings_dir / "educational_feedback.json", "educational_feedback")
        
        # Load system messages
        self._load_json_file(strings_dir / "system_messages.json", "system_messages")
    
    def _load_prompts(self):
        """Load prompt templates from prompts directory"""
        prompts_dir = self.content_dir / "prompts"
        
        if not prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {prompts_dir}")
            return
        
        # Load consolidated JSON files (Phase 1 of storywriting consolidation)
        # Storywriting prompts: system, story generation, assessment, narrative enhancement, grammar
        self._load_json_file(prompts_dir / "storywriting-prompts.json", "storywriting_prompts")
        
        # Character design prompts: naming, descriptions, flow patterns
        self._load_json_file(prompts_dir / "character-design-prompts.json", "character_design_prompts")
        
        # Shared vocabulary prompts: used by both story and facts modes  
        self._load_json_file(prompts_dir / "shared-prompts.json", "shared_prompts")
        
        # Legacy prompt loading (for backwards compatibility during transition)
        # TODO: Remove after testing consolidation is complete
        story_dir = prompts_dir / "story_mode"
        if story_dir.exists():
            self._load_text_file(story_dir / "system_context.txt", "story_system_prompt_legacy")
            self._load_json_file(story_dir / "story_templates.json", "story_templates_legacy")
            self._load_json_file(story_dir / "narrative_guidance.json", "narrative_guidance_legacy")
        
        # Load facts mode prompts (not yet consolidated)
        facts_dir = prompts_dir / "facts_mode"
        if facts_dir.exists():
            self._load_text_file(facts_dir / "system_context.txt", "facts_system_prompt")
            self._load_json_file(facts_dir / "fact_templates.json", "fact_templates")
        
        # Load legacy shared prompts (for backwards compatibility)
        shared_dir = prompts_dir / "shared"
        if shared_dir.exists():
            self._load_json_file(shared_dir / "vocabulary_templates.json", "vocabulary_templates_legacy")
            self._load_json_file(shared_dir / "design_templates.json", "design_templates_legacy")
    
    def _load_config(self):
        """Load configuration from config directory"""
        config_dir = self.content_dir / "config"
        
        if not config_dir.exists():
            logger.warning(f"Config directory not found: {config_dir}")
            return
        
        # Load topics configuration
        self._load_json_file(config_dir / "topics.json", "topics")
        
        # Load educational parameters
        self._load_json_file(config_dir / "educational_parameters.json", "educational_parameters")
    
    def _load_json_file(self, file_path: Path, content_key: str):
        """Load JSON content from file"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.content[content_key] = json.load(f)
                logger.info(f"✅ Loaded {content_key} from {file_path}")
            else:
                logger.warning(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load {content_key} from {file_path}: {e}")
    
    def _load_text_file(self, file_path: Path, content_key: str):
        """Load text content from file"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.content[content_key] = f.read().strip()
                logger.info(f"✅ Loaded {content_key} from {file_path}")
            else:
                logger.warning(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load {content_key} from {file_path}: {e}")
    
    def _initialize_fallback_content(self):
        """Initialize minimal fallback content if loading fails"""
        self.content = {
            "bot_responses": {
                "mode_error": "I'm not sure what mode that is! Try storywriting or fun facts.",
                "processing_error": "Sorry, I'm having trouble right now. Please try again!",
                "vocabulary_intro": "Great story! Now let's test your vocabulary:",
                "session_goodbye": "Thanks for sharing this wonderful story adventure with me!"
            },
            "ui_messages": {
                "speech_not_supported": "Speech recognition not supported in this browser.",
                "https_required": "Speech recognition requires HTTPS or localhost."
            }
        }
        logger.info("📄 ContentManager: Initialized with fallback content")
    
    # Public API methods
    
    def get_bot_response(self, key: str, **kwargs) -> str:
        """
        Get bot response message with optional template interpolation
        
        Args:
            key: Response key (e.g., 'vocabulary_intro', 'errors.mode_error')
                 Supports dot notation for nested keys
            **kwargs: Template variables for interpolation
            
        Returns:
            Formatted bot response string
        """
        bot_responses = self.content.get("bot_responses", {})
        
        # Handle dot notation for nested keys
        if '.' in key:
            keys = key.split('.')
            response = bot_responses
            for k in keys:
                if isinstance(response, dict) and k in response:
                    response = response[k]
                else:
                    response = f"[Missing bot response: {key}]"
                    break
        else:
            response = bot_responses.get(key, f"[Missing bot response: {key}]")
        
        if kwargs and isinstance(response, str):
            try:
                response = response.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Template interpolation failed for {key}: missing variable {e}")
        
        return response
    
    def get_ui_message(self, key: str, **kwargs) -> str:
        """
        Get UI message with optional template interpolation
        
        Args:
            key: UI message key
            **kwargs: Template variables for interpolation
            
        Returns:
            Formatted UI message string
        """
        ui_messages = self.content.get("ui_messages", {})
        message = ui_messages.get(key, f"[Missing UI message: {key}]")
        
        if kwargs:
            try:
                message = message.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Template interpolation failed for {key}: missing variable {e}")
        
        return message
    
    def get_educational_feedback(self, category: str, key: str, **kwargs) -> str:
        """
        Get educational feedback message
        
        Args:
            category: Feedback category (e.g., 'grammar', 'encouragement')
            key: Specific feedback key
            **kwargs: Template variables for interpolation
            
        Returns:
            Formatted educational feedback string
        """
        feedback = self.content.get("educational_feedback", {})
        category_feedback = feedback.get(category, {})
        message = category_feedback.get(key, f"[Missing feedback: {category}.{key}]")
        
        if kwargs:
            try:
                message = message.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Template interpolation failed for {category}.{key}: missing variable {e}")
        
        return message
    
    def get_prompt_template(self, category: str, key: str) -> str:
        """
        Get prompt template
        
        Args:
            category: Template category (e.g., 'story_templates', 'vocabulary_templates')
            key: Specific template key
            
        Returns:
            Prompt template string
        """
        # Handle consolidated storywriting prompt templates
        if category == "story_templates":
            storywriting_prompts = self.content.get("storywriting_prompts", {})
            story_generation = storywriting_prompts.get("story_generation", {})
            story_opening = story_generation.get("story_opening", {})
            
            if key in story_opening:
                template_data = story_opening.get(key, {})
                # Return the prompt template string, not the entire template object
                return template_data.get("prompt_template", template_data)
            else:
                # Fall back to legacy for backwards compatibility
                templates = self.content.get("story_templates_legacy", {})
                return templates.get(key, f"[Missing prompt template: {category}.{key}]")
        
        # Handle vocabulary templates from shared prompts
        elif category == "vocabulary_templates":
            shared_prompts = self.content.get("shared_prompts", {})
            vocab_system = shared_prompts.get("vocabulary_system", {})
            
            if key == "question_generation":
                return vocab_system.get("question_generation", {})
            else:
                # Fall back to legacy for backwards compatibility
                templates = self.content.get("vocabulary_templates_legacy", {})
                return templates.get(key, f"[Missing prompt template: {category}.{key}]")
        
        # Handle design templates from character design prompts
        elif category == "design_templates":
            character_design = self.content.get("character_design_prompts", {})
            
            if key == "character":
                return character_design.get("naming_prompts", {}).get("character", {})
            else:
                # Fall back to legacy for backwards compatibility
                templates = self.content.get("design_templates_legacy", {})
                return templates.get(key, f"[Missing prompt template: {category}.{key}]")
        
        # Default legacy handling for other categories
        else:
            templates = self.content.get(category, {})
            return templates.get(key, f"[Missing prompt template: {category}.{key}]")
    
    def get_design_template(self, template_path: str) -> str:
        """
        Get design template using dot notation path
        
        Args:
            template_path: Path like 'character.naming' or 'location.appearance'
            
        Returns:
            Design template string or fallback content
        """
        # Parse the path (e.g., "character.naming")
        parts = template_path.split('.')
        if len(parts) != 2:
            logger.warning(f"Invalid design template path: {template_path}")
            return f"[Invalid template path: {template_path}]"
            
        entity_type, aspect = parts
        
        # Get design templates from content
        design_templates = self.content.get("design_templates", {})
        entity_templates = design_templates.get(entity_type, {})
        aspect_templates = entity_templates.get(aspect, {})
        
        # Return the template or a reasonable fallback
        if isinstance(aspect_templates, dict) and "template" in aspect_templates:
            return aspect_templates["template"]
        elif isinstance(aspect_templates, str):
            return aspect_templates
        else:
            # Fallback for missing templates
            logger.warning(f"Design template not found: {template_path}")
            if aspect == "naming":
                return f"Can you name {entity_type}?"
            else:
                return f"Tell me about the {aspect} of this {entity_type}."

    def get_system_prompt(self, mode: str) -> str:
        """
        Get system prompt for specific mode
        
        Args:
            mode: Mode type ('story' or 'facts')
            
        Returns:
            System prompt string
        """
        if mode == "story":
            # Use consolidated storywriting prompts
            storywriting_prompts = self.content.get("storywriting_prompts", {})
            system_prompts = storywriting_prompts.get("system_prompts", {})
            tutor_persona = system_prompts.get("tutor_persona", {})
            return tutor_persona.get("prompt", f"[Missing story system prompt in consolidated format]")
        elif mode == "facts":
            # Use legacy facts system prompt (not yet consolidated)
            prompt_key = f"{mode}_system_prompt"
            return self.content.get(prompt_key, f"[Missing system prompt for mode: {mode}]")
        else:
            return f"[Unknown mode: {mode}]"
    
    def reload_content(self):
        """Reload all content from files (useful for development)"""
        logger.info("🔄 ContentManager: Reloading all content...")
        self.content = {}
        self._load_all_content()
    
    def get_all_bot_responses(self) -> Dict[str, str]:
        """Get all bot responses (useful for debugging/testing)"""
        return self.content.get("bot_responses", {})
    
    def get_content_summary(self) -> Dict[str, Any]:
        """Get summary of loaded content for debugging"""
        summary = {}
        for key, value in self.content.items():
            if isinstance(value, dict):
                summary[key] = f"{len(value)} items"
            elif isinstance(value, str):
                summary[key] = f"{len(value)} characters"
            else:
                summary[key] = str(type(value))
        return summary

    def _create_design_templates_mapping(self):
        """
        Create design_templates mapping for app.py compatibility.
        Maps character_design_prompts structure to expected design_templates structure.
        """
        try:
            character_design = self.content.get("character_design_prompts", {})
            description_prompts = character_design.get("description_prompts", {})
            
            # Create the mapping that app.py expects: design_templates.character
            design_templates = {
                "character": {}
            }
            
            # Map each description prompt aspect to the expected structure
            for aspect_name, aspect_data in description_prompts.items():
                design_templates["character"][aspect_name] = aspect_data
            
            # Store the mapping in content so app.py can access it
            self.content["design_templates"] = design_templates
            
            aspect_count = len(description_prompts)
            logger.info(f"✅ Created design_templates mapping: character with {aspect_count} aspects")
            
        except Exception as e:
            logger.error(f"❌ Failed to create design_templates mapping: {e}")
            # Fallback: create empty structure
            self.content["design_templates"] = {"character": {}}


# Create singleton instance for app usage
content_manager = ContentManager()