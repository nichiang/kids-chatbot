"""
PromptManager - Centralized prompt generation for English Learning Chatbot

This module provides a single source of truth for all prompt generation, making the 
complete user experience visible and maintainable without separate documentation.

Architecture: Self-documenting prompt methods with clear naming that shows exactly
what prompts exist for each educational scenario.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import random
import logging

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Single source of truth for all prompt generation in the educational chatbot.
    
    Method names self-document the complete user experience flow.
    """
    
    def __init__(self):
        """Initialize PromptManager with template loading"""
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from ContentManager (centralized content system)"""
        try:
            # Import here to avoid circular imports
            from content_manager import content_manager
            
            # Load consolidated storywriting prompts
            self.storywriting_prompts = content_manager.content.get("storywriting_prompts", {})
            
            # Load character design prompts  
            self.character_design_prompts = content_manager.content.get("character_design_prompts", {})
            
            # Load shared vocabulary prompts
            self.shared_prompts = content_manager.content.get("shared_prompts", {})
            
            # Extract commonly used sections for backwards compatibility
            self.story_templates = self.storywriting_prompts.get("story_generation", {}).get("story_opening", {})
            self.conflict_types = self.storywriting_prompts.get("narrative_enhancement", {}).get("conflict_scenarios", {})
            self.character_aspects = self.character_design_prompts.get("description_prompts", {})
            
            # Legacy loading for backwards compatibility during transition
            # TODO: Remove these after updating all method implementations
            self.story_templates_legacy = content_manager.content.get("story_templates_legacy", {})
            self.conflict_types_legacy = content_manager.content.get("narrative_guidance_legacy", {})
            design_templates_legacy = content_manager.content.get("design_templates_legacy", {})
            self.character_aspects_legacy = design_templates_legacy.get("character", {})
            self.location_aspects = design_templates_legacy.get("location", {})
                
            logger.info("✅ PromptManager templates loaded from ContentManager (consolidated + legacy)")
            
        except Exception as e:
            logger.error(f"❌ Failed to load PromptManager templates: {e}")
            # Initialize with empty templates as fallback
            self.storywriting_prompts = {}
            self.character_design_prompts = {}
            self.shared_prompts = {}
            self.story_templates = {}
            self.character_aspects = {}
            self.location_aspects = {}
            self.conflict_types = {}
    
    def _load_file(self, file_path: str) -> str:
        """Load text content from file"""
        return Path(file_path).read_text().strip()
    
    # ================================
    # STORY MODE PROMPTS
    # ================================
    
    def get_story_system_prompt(self) -> str:
        """
        Complete educational context and framework for story mode LLM.
        
        Uses ContentManager for centralized content management.
        This provides the LLM with the educational framework and tone.
        """
        try:
            # Import here to avoid circular imports
            from content_manager import content_manager
            return content_manager.get_system_prompt("story")
            
        except Exception as e:
            logger.error(f"❌ Failed to load story system prompt: {e}")
            return "You are a friendly English tutor for elementary school students."
    
    def get_story_opening_prompt(self, topic: str, story_mode: str = "auto") -> str:
        """
        Generate first story paragraph with named or unnamed entities.
        
        Args:
            topic: Story topic chosen by child (e.g., "space", "animals")
            story_mode: "auto" (random), "named" (force named), "unnamed" (force unnamed)
            
        Returns:
            Structured prompt requesting JSON response with story and metadata
        """
        try:
            # Import here to avoid circular imports
            from content_manager import content_manager
            
            # Select template based on story mode
            if story_mode == "named":
                template_key = "named_entities"
                logger.info("🎯 Story Opening: FORCED NAMED entity template (testing mode)")
            elif story_mode == "unnamed":
                template_key = "unnamed_entities"
                logger.info("🎯 Story Opening: FORCED UNNAMED entity template (testing mode)")
            else:  # auto mode - use random selection
                # 60% named, 40% unnamed for natural variety
                template_key = "named_entities" if random.random() < 0.6 else "unnamed_entities"
                logger.info(f"🎯 Story Opening: Random selection chose '{template_key}' template")
            
            # Get template from ContentManager (now returns the prompt_template string directly)
            selected_template = content_manager.get_prompt_template("story_templates", template_key)
            
            formatted_prompt = selected_template.format(topic=topic)
            
            logger.info(f"🎯 Story Opening: Generated prompt for topic '{topic}' using '{template_key}' template")
            return formatted_prompt
            
        except Exception as e:
            logger.error(f"❌ Failed to generate story opening prompt: {e}")
            # Fallback prompt
            return f"""Create a story opening for the topic: {topic}
            
Write 1-3 sentences suitable for strong 2nd graders or 3rd graders.
Bold 2-3 vocabulary words using **word** format.
Use engaging, age-appropriate language that sparks imagination."""
    
    def get_story_continuation_prompt(self, context: str = "") -> str:
        """
        Invite child to continue the story.
        
        Args:
            context: Previous story context for continuation
            
        Returns:
            Simple continuation invitation prompt
        """
        return "Now continue the story! What happens next?"
    
    def get_story_ending_prompt(self, topic: str, context: str) -> str:
        """
        Generate final story conclusion.
        
        Args:
            topic: Story topic for context
            context: Previous story context
            
        Returns:
            Prompt to end story with satisfying conclusion
        """
        return f"""End the story about {topic}. Previous context: {context}. 

Write a final paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. End the story with a satisfying conclusion and add 'The end!' at the very end. 

DO NOT ask the child to continue. DO NOT include vocabulary questions - those will be handled separately."""
    
    def get_design_continuation_prompt(self, topic: str, context: str, design_summary: str, user_input: str, subject_name: str) -> str:
        """
        Continue story after design phase with child's creative input.
        
        Args:
            topic: Story topic
            context: Previous story context
            design_summary: Summary of design session
            user_input: Child's design input
            subject_name: Name of designed entity
            
        Returns:
            Prompt to continue story incorporating child's design
        """
        return f"""Continue the story about {topic}. Previous context: {context}

{design_summary} The child just described: "{user_input}"

Write a paragraph that is 2-4 sentences long incorporating the child's creative input about {subject_name}. Use vocabulary suitable for a strong 2nd grader or 3rd grader. Then invite the child to continue the story without giving them any options. Bold 2-3 vocabulary words using **word** format."""
    
    def get_grammar_feedback_prompt(self, user_text: str, subject_name: str, design_phase: str) -> str:
        """
        Provide writing improvement suggestions as English tutor.
        
        Args:
            user_text: Child's writing to provide feedback on
            subject_name: Name of designed entity
            design_phase: Type of design (character/location)
            
        Returns:
            Prompt for constructive writing feedback
        """
        return f"""As a friendly English tutor, provide very brief feedback on this child's descriptive writing about their {design_phase} {subject_name}:

"{user_text}"

If the writing is already good, praise it. If it could be improved, give specific example sentences showing how. Keep feedback positive and encouraging. Be as brief as possible."""
    
    def get_story_completion_prompt(self) -> str:
        """
        Invite child to write another story after vocabulary questions complete.
        
        Returns:
            Engaging new story invitation with topic suggestions
        """
        return """Wonderful job with the vocabulary! You've done great! Would you like to write another story? Here are some fun ideas:

🚀 Space adventures
🏰 Fantasy quests
⚽ Sports excitement
🦄 Magical creatures
🕵️ Mystery solving
🍕 Food adventures
🐾 Animal stories
🌊 Ocean explorations

What sounds interesting to you?"""
    
    def get_topic_selection_story_prompt(self, topic: str) -> str:
        """
        Generate story beginning when child selects new topic.
        
        Args:
            topic: New topic chosen by child
            
        Returns:
            Prompt for story paragraph with vocabulary integration
        """
        return f"""The child has chosen the topic: {topic}. Now write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Then invite the child to continue the story without giving them any options. DO NOT include vocabulary questions - those will be handled separately."""
    
    def get_continue_story_prompt(self, topic: str, context: str) -> str:
        """
        Continue existing story with vocabulary integration.
        
        Args:
            topic: Story topic
            context: Previous story context
            
        Returns:
            Prompt to continue story while managing length
        """
        return f"""Continue the story about {topic}. Previous context: {context}. 

Write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Then invite the child to continue the story without giving them any options. Keep this a short story - try to end it before it goes over 300 words total. DO NOT include vocabulary questions - those will be handled separately."""
    
    # ================================
    # ENHANCED STORY STRUCTURE METHODS
    # ================================
    
    def get_story_arc_assessment_prompt(self, story_parts: List[str], topic: str) -> str:
        """
        Analyze story for narrative structure, conflict, and character development.
        
        Creates prompt for LLM to assess current story phase and readiness for completion.
        Follows PromptManager pattern of self-documenting method names.
        
        Args:
            story_parts: List of story exchanges so far
            topic: Story topic for context
            
        Returns:
            Assessment prompt for LLM to analyze narrative structure
        """
        story_text = "\n".join(story_parts)
        
        return f"""Analyze this collaborative story for 2nd-3rd graders:

STORY TOPIC: {topic}
STORY SO FAR:
{story_text}

Assess the narrative structure and return JSON in this exact format:
{{
    "current_phase": "setup|development|climax|resolution",
    "completeness_score": 0-100,
    "character_growth": 0-100,
    "has_clear_conflict": true|false,
    "conflict_type": "emotional|social|problem_solving|environmental|adventure|none",
    "lesson_learned": true|false,
    "ready_to_resolve": true|false,
    "next_guidance": "Brief guidance for what should happen next"
}}

ASSESSMENT CRITERIA:
- Setup: Character and setting introduced, conflict hinted
- Development: Character faces challenges, tries solutions
- Climax: Most important moment, biggest challenge
- Resolution: Problem solved, character growth shown

- Character Growth: How much has the character learned/changed?
- Completeness: Does story feel ready to end naturally?
- Conflict: Is there a clear challenge being addressed?
- Lesson: Has character learned something valuable?

Focus on age-appropriate narrative elements for elementary students."""
    
    def get_narrative_continuation_prompt(self, assessment: dict, topic: str, story_context: str) -> str:
        """
        Generate phase-aware story continuation prompt based on narrative assessment.
        
        Uses assessment results to create intelligent guidance for next story beat.
        Integrates seamlessly with existing enhance_with_vocabulary() method.
        
        Args:
            assessment: Dictionary from story arc assessment
            topic: Story topic
            story_context: Previous story context
            
        Returns:
            Intelligent prompt for narrative-aware story continuation
        """
        current_phase = assessment.get('current_phase', 'development')
        character_growth = assessment.get('character_growth', 0)
        has_conflict = assessment.get('has_clear_conflict', False)
        
        # Phase-specific guidance
        phase_prompts = {
            'setup': f"Continue setting up the {topic} story. Introduce the main character's problem or adventure. Make the character relatable to children and hint at the challenge ahead.",
            
            'development': f"Develop the {topic} story by having the character face challenges. Escalate the problem or adventure. Show the character trying different solutions and learning from attempts.",
            
            'climax': f"Bring the {topic} story to its most exciting or important moment. This is where the character faces their biggest challenge and must use what they've learned.",
            
            'resolution': f"Resolve the {topic} story in a satisfying way. Show how the character has grown and what they learned. End with 'The end!' Make it feel complete and rewarding."
        }
        
        base_guidance = phase_prompts.get(current_phase, phase_prompts['development'])
        
        # Add specific guidance based on assessment
        additional_guidance = []
        
        if character_growth < 50:
            additional_guidance.append("Focus on how this experience is changing or teaching the character")
            
        if not has_conflict:
            additional_guidance.append("Introduce a clear, age-appropriate problem or challenge for the character to overcome")
            
        if assessment.get('ready_to_resolve', False) and current_phase != 'resolution':
            additional_guidance.append("Begin working toward a satisfying resolution that shows character growth")
        
        if additional_guidance:
            base_guidance += " " + ". ".join(additional_guidance) + "."
        
        return f"""{base_guidance}

Previous story context: {story_context}

Write 2-4 engaging sentences using vocabulary suitable for 2nd-3rd graders. 
Then invite the child to continue the story without giving them any options.
Bold 2-3 vocabulary words using **word** format."""
    
    def get_conflict_integration_prompt(self, topic: str, conflict_type: str = None, scale: str = None) -> str:
        """
        Add age-appropriate conflict to story based on type and scale.
        
        Selects from conflict_types.json and integrates into narrative naturally.
        Provides variety from epic adventures to everyday challenges.
        
        Args:
            topic: Story topic for context
            conflict_type: Type of conflict (emotional, social, etc.) or None for random
            scale: Scale of conflict (epic_scale, daily_scale) or None for random
            
        Returns:
            Prompt for introducing appropriate conflict into story
        """
        try:
            # Select conflict type and scale if not specified
            if conflict_type is None:
                available_types = [k for k in self.conflict_types.keys() if k != 'educational_themes' and k != 'age_appropriate_guidelines' and k != 'narrative_patterns']
                conflict_type = random.choice(available_types)
            
            if scale is None:
                scale = random.choice(['epic_scale', 'daily_scale'])
            
            # Get scenarios for the selected type and scale
            if conflict_type in self.conflict_types and scale in self.conflict_types[conflict_type]:
                scenarios = self.conflict_types[conflict_type][scale].get('scenarios', [])
                if scenarios:
                    selected_scenario = random.choice(scenarios)
                    
                    return f"""Introduce this type of conflict into the {topic} story: {selected_scenario}

Make the conflict age-appropriate for 2nd-3rd graders. The challenge should be:
- Engaging but not frightening
- Something the character can realistically overcome
- Connected to the {topic} theme
- An opportunity for character growth and learning

Write 2-4 sentences that naturally introduce this challenge into the story.
Bold 2-3 vocabulary words using **word** format."""
            
        except Exception as e:
            logger.error(f"❌ Failed to generate conflict integration prompt: {e}")
        
        # Fallback prompt if conflict selection fails
        return f"""Introduce an age-appropriate challenge or problem into the {topic} story.

The challenge should be:
- Suitable for 2nd-3rd graders (engaging but not scary)
- Something the character can overcome through their own efforts
- Connected to the {topic} theme
- An opportunity for learning and growth

Write 2-4 sentences that naturally introduce this challenge.
Bold 2-3 vocabulary words using **word** format."""
    
    def should_end_story_intelligently(self, session_data) -> Tuple[bool, str]:
        """
        Determine if story should end based on narrative completeness rather than rigid rules.
        
        Replaces arbitrary character count and step limits with intelligent assessment.
        Maintains 3-6 exchange range while prioritizing narrative satisfaction.
        
        Args:
            session_data: Current session data with story progress
            
        Returns:
            Tuple of (should_end: bool, reason: str)
        """
        # Import here to avoid circular imports
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from app import SessionData
        
        # Hard limits for attention span and minimum structure
        if session_data.currentStep < 3:
            return False, f"Minimum exchanges not reached: {session_data.currentStep} < 3"
            
        if session_data.currentStep >= 6:
            return True, f"Maximum exchanges reached: {session_data.currentStep} >= 6"
        
        # Check if we have narrative assessment data
        if hasattr(session_data, 'narrativeAssessment') and session_data.narrativeAssessment:
            assessment = session_data.narrativeAssessment
            
            completeness = assessment.get('completeness_score', 0)
            character_growth = assessment.get('character_growth', 0)
            ready_to_resolve = assessment.get('ready_to_resolve', False)
            current_phase = assessment.get('current_phase', 'development')
            
            # Intelligent ending conditions
            if completeness >= 85 and character_growth >= 70:
                return True, f"Story complete: {completeness}% completeness, {character_growth}% character growth"
                
            if ready_to_resolve and current_phase == 'resolution' and session_data.currentStep >= 4:
                return True, f"Natural resolution reached in {current_phase} phase after {session_data.currentStep} exchanges"
                
            if character_growth >= 80 and completeness >= 60 and session_data.currentStep >= 4:
                return True, f"Strong character development: {character_growth}% growth, {completeness}% complete"
            
            return False, f"Story developing: {completeness}% complete, {character_growth}% growth, phase: {current_phase}"
        
        # Fallback to improved quality gates if no assessment available
        story_parts = getattr(session_data, 'storyParts', [])
        if story_parts:
            story_text = ' '.join(story_parts).lower()
            
            # Quality indicators
            has_character = any(word in story_text for word in ['he', 'she', 'they', 'character', 'hero', 'girl', 'boy'])
            has_action = any(word in story_text for word in ['went', 'found', 'discovered', 'saw', 'met', 'tried', 'solved'])
            has_resolution = any(word in story_text for word in ['finally', 'then', 'after', 'solved', 'learned', 'the end'])
            
            word_count = len(story_text.split())
            
            # Quality-based ending decision
            quality_score = 0
            if has_character: quality_score += 25
            if has_action: quality_score += 25
            if has_resolution: quality_score += 35
            if word_count >= 100: quality_score += 15
            
            if quality_score >= 70 and session_data.currentStep >= 3:
                return True, f"Quality threshold met: {quality_score}% quality score with {session_data.currentStep} exchanges"
            
            return False, f"Quality developing: {quality_score}% quality, {word_count} words, {session_data.currentStep} exchanges"
        
        # Final fallback
        return False, f"Insufficient data for assessment at step {session_data.currentStep}"
    
    # ================================
    # FUN FACTS MODE PROMPTS  
    # ================================
    
    def get_facts_system_prompt(self) -> str:
        """
        Educational context for fun facts mode LLM.
        
        Returns:
            System prompt for facts mode personality and requirements
        """
        try:
            # Import here to avoid circular imports
            from content_manager import content_manager
            return content_manager.get_system_prompt("facts")
        except Exception as e:
            logger.error(f"❌ Failed to load facts system prompt: {e}")
            return "You are a friendly and educational content creator for elementary school students."
    
    def get_first_fact_prompt(self, topic: str) -> str:
        """
        Generate initial engaging fact for new topic.
        
        Args:
            topic: Topic for fact generation
            
        Returns:
            Prompt for first fact with engaging guidelines
        """
        return self._get_facts_prompt_template("FIRST_FACT_PROMPT", topic=topic)
    
    def get_continuing_fact_prompt(self, topic: str, fact_number: int, previous_facts: str) -> str:
        """
        Generate additional facts with anti-repetition.
        
        Args:
            topic: Topic for fact generation
            fact_number: Current fact number
            previous_facts: String of previous facts to avoid repeating
            
        Returns:
            Prompt for continuing fact that avoids repetition
        """
        return self._get_facts_prompt_template(
            "CONTINUING_FACT_PROMPT", 
            topic=topic, 
            fact_number=fact_number, 
            previous_facts=previous_facts
        )
    
    def get_new_topic_fact_prompt(self, topic: str) -> str:
        """
        Generate fact for topic change or continuation.
        
        Args:
            topic: New or continuing topic
            
        Returns:
            Prompt for topic change fact
        """
        return self._get_facts_prompt_template("NEW_TOPIC_PROMPT", topic=topic)
    
    def _get_facts_prompt_template(self, template_key: str, **kwargs) -> str:
        """
        Load and format fun facts prompt templates.
        
        Args:
            template_key: Template identifier
            **kwargs: Template formatting variables
            
        Returns:
            Formatted prompt combining instructions and template
        """
        try:
            # Load content instructions
            instructions = self._load_file("prompts/fun_facts/02_content_instructions.txt")
            
            # Load and parse scenario templates
            templates_text = self._load_file("prompts/fun_facts/03_scenario_templates.txt")
            templates = self._parse_template_file(templates_text)
            
            # Get base template and format
            base_template = templates.get(template_key, '')
            formatted_template = base_template.format(**kwargs)
            
            # Combine instructions with template
            return f"{instructions}\n\n{formatted_template}"
            
        except Exception as e:
            logger.error(f"❌ Failed to generate facts template {template_key}: {e}")
            topic = kwargs.get('topic', 'science')
            return f"Generate an engaging fun fact about: {topic}. Write 2-3 sentences using vocabulary suitable for strong 2nd-3rd graders."
    
    def _parse_template_file(self, content: str) -> Dict[str, str]:
        """Parse template file with KEY: format into dictionary"""
        templates = {}
        current_key = None
        current_content = []
        
        for line in content.split('\n'):
            if line.endswith(':') and line.count(':') == 1:
                # Save previous template
                if current_key:
                    templates[current_key] = '\n'.join(current_content).strip()
                # Start new template
                current_key = line[:-1]  # Remove colon
                current_content = []
            elif current_key:
                current_content.append(line)
        
        # Save last template
        if current_key:
            templates[current_key] = '\n'.join(current_content).strip()
            
        return templates
    
    # ================================
    # DESIGN PHASE PROMPTS
    # ================================
    
    def get_design_phase_prompt(self, entity_type: str, aspect: str, subject_name: str, subject_descriptor: str = None) -> Dict:
        """
        Generate character or location design prompts.
        
        Args:
            entity_type: "character" or "location"
            aspect: Design aspect (e.g., "appearance", "personality")
            subject_name: Name of entity being designed
            subject_descriptor: Descriptor for unnamed entities
            
        Returns:
            Dictionary with prompt_text, suggested_words, and placeholder
        """
        try:
            # Select appropriate aspects data
            aspects_data = self.character_aspects if entity_type == "character" else self.location_aspects
            aspect_data = aspects_data.get(aspect, {})
            
            # Generate prompt text based on naming state
            if aspect == "naming":
                prompt_text = aspect_data.get("prompt_template", "").format(descriptor=subject_descriptor or "the character")
                placeholder_text = aspect_data.get("placeholder", "").format(descriptor=subject_descriptor or "the character")
            else:
                prompt_text = aspect_data.get("prompt_template", "").format(name=subject_name)
                placeholder_text = aspect_data.get("placeholder", "Write 1-2 sentences")
            
            return {
                "prompt_text": prompt_text,
                "suggested_words": aspect_data.get("suggestions", []),
                "input_placeholder": placeholder_text
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate design prompt for {entity_type}/{aspect}: {e}")
            return {
                "prompt_text": f"Tell us about this {entity_type}!",
                "suggested_words": [],
                "input_placeholder": "Write 1-2 sentences"
            }
    
    # ================================
    # VOCABULARY ENHANCEMENT
    # ================================
    
    def enhance_with_vocabulary(self, base_prompt: str, topic: str, excluded_words: List[str] = None, word_count: int = 3) -> Tuple[str, List[str]]:
        """
        Add massive vocabulary pool to any prompt for LLM intelligent curation.
        
        SOLUTION 3: Provides 40 example words (20 general tier 2+3 + 20 topic words)
        for LLM to intelligently select 2-4 most natural words.
        
        Args:
            base_prompt: The base prompt to enhance
            topic: Topic for vocabulary selection  
            excluded_words: Previously used words to avoid
            word_count: Target word count (for logging)
            
        Returns:
            Tuple of (enhanced_prompt, expected_vocabulary_range)
        """
        if excluded_words is None:
            excluded_words = []
            
        # Generate massive vocabulary pools
        vocab_pools = self.generate_massive_vocabulary_pool(topic, excluded_words)
        
        if vocab_pools['total_examples'] > 0:
            # Create enhanced prompt with vocabulary instruction
            vocab_instruction = f"""

VOCABULARY INTEGRATION INSTRUCTIONS:
GENERAL WORDS (Tier 2+3): {', '.join(vocab_pools['general_pool'])}
TOPIC-SPECIFIC WORDS: {', '.join(vocab_pools['topic_pool'])}

CRITICAL INSTRUCTIONS:
- Select ONLY 2-4 words total that fit most naturally in your content
- Choose words that enhance meaning rather than feel forced  
- Bold selected words using **word** format
- DO NOT include vocabulary questions or definitions in the content
- Focus on creating compelling educational content

TARGET USAGE: Select 2-4 most natural words only"""

            enhanced_prompt = base_prompt + vocab_instruction
            expected_vocab = ['LLM_SELECTED_2_TO_4_WORDS']
            
            logger.info(f"🎯 Vocabulary Enhancement: Provided {vocab_pools['total_examples']} example words for topic '{topic}'")
            
        else:
            # Fallback if no vocabulary available
            enhanced_prompt = base_prompt + " Bold 2-4 challenging or important words using **word** format. DO NOT include vocabulary questions or definitions in the content."
            expected_vocab = []
            logger.warning(f"⚠️ Vocabulary Enhancement: No vocabulary available for topic '{topic}', using fallback")
        
        return enhanced_prompt, expected_vocab
    
    def generate_massive_vocabulary_pool(self, topic: str, used_words: List[str] = None) -> Dict[str, any]:
        """
        SOLUTION 3: Generate massive vocabulary pools for LLM intelligent selection
        
        Creates 40-word example pools (20 general + 20 topic) with anti-repetition filtering.
        This provides 1,233% more variety than previous 3-word approach.
        
        Args:
            topic: Topic for vocabulary selection
            used_words: Words to exclude from selection
            
        Returns:
            Dictionary with general_pool, topic_pool, and metadata
        """
        if used_words is None:
            used_words = []
            
        try:
            # Import vocabulary manager for actual vocabulary loading
            from vocabulary_manager import vocabulary_manager
            
            # Get vocabulary pools using correct method names
            general_vocab = [word['word'] for word in vocabulary_manager.general_vocabulary]
            topic_vocab = [word['word'] for word in vocabulary_manager.get_vocabulary_for_topic(topic)]
            
            # Filter out used words
            available_general = [word for word in general_vocab if word not in used_words]
            available_topic = [word for word in topic_vocab if word not in used_words]
            
            # Select random pools (20 each, or all available if fewer)
            general_pool = random.sample(available_general, min(20, len(available_general)))
            topic_pool = random.sample(available_topic, min(20, len(available_topic)))
            
            return {
                'general_pool': general_pool,
                'topic_pool': topic_pool,
                'excluded_words': used_words,
                'total_examples': len(general_pool) + len(topic_pool)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate vocabulary pool: {e}")
            return {
                'general_pool': [],
                'topic_pool': [],
                'excluded_words': used_words,
                'total_examples': 0
            }
    
    # ================================
    # SELF-DOCUMENTATION METHODS
    # ================================
    
    def get_complete_story_flow(self, topic: str = "space") -> Dict[str, str]:
        """
        Generate example of complete story mode user experience.
        
        This method provides self-updating documentation of the complete user journey
        by showing actual prompts that would be sent to the LLM.
        
        Args:
            topic: Example topic for demonstration
            
        Returns:
            Dictionary mapping each step to actual prompt text
        """
        return {
            "system_context": self.get_story_system_prompt(),
            "story_opening_named": self.get_story_opening_prompt(topic, "named"),
            "story_opening_unnamed": self.get_story_opening_prompt(topic, "unnamed"), 
            "continuation_invite": self.get_story_continuation_prompt(),
            "grammar_feedback": self.get_grammar_feedback_prompt("sara has curly hair", "Sara", "character"),
            "design_character_naming": self.get_design_phase_prompt("character", "naming", "", "the brave astronaut"),
            "design_character_appearance": self.get_design_phase_prompt("character", "appearance", "Luna", ""),
            "design_continuation": self.get_design_continuation_prompt(topic, "story context", "design summary", "She has long brown hair", "Luna"),
            "story_ending": self.get_story_ending_prompt(topic, "story context"),
            "story_completion": self.get_story_completion_prompt(),
            "vocabulary_enhanced_example": self.enhance_with_vocabulary(
                self.get_topic_selection_story_prompt(topic), 
                topic, 
                ["universe", "galaxy"]
            )[0]
        }
    
    def get_complete_facts_flow(self, topic: str = "animals") -> Dict[str, str]:
        """
        Generate example of complete fun facts mode user experience.
        
        Args:
            topic: Example topic for demonstration
            
        Returns:
            Dictionary mapping each step to actual prompt text
        """
        return {
            "system_context": self.get_facts_system_prompt(),
            "first_fact": self.get_first_fact_prompt(topic),
            "continuing_fact": self.get_continuing_fact_prompt(topic, 2, "Lions are the kings of the jungle"),
            "new_topic_fact": self.get_new_topic_fact_prompt(topic),
            "vocabulary_enhanced_example": self.enhance_with_vocabulary(
                self.get_first_fact_prompt(topic),
                topic,
                ["habitat", "predator"]
            )[0]
        }
    
    def get_all_prompt_types(self) -> Dict[str, List[str]]:
        """
        Catalog all available prompt methods for complete system overview.
        
        Returns:
            Dictionary organizing all prompt methods by category
        """
        return {
            "story_mode": [
                "get_story_system_prompt",
                "get_story_opening_prompt", 
                "get_story_continuation_prompt",
                "get_story_ending_prompt",
                "get_design_continuation_prompt",
                "get_grammar_feedback_prompt",
                "get_story_completion_prompt",
                "get_topic_selection_story_prompt",
                "get_continue_story_prompt"
            ],
            "enhanced_story_structure": [
                "get_story_arc_assessment_prompt",
                "get_narrative_continuation_prompt",
                "get_conflict_integration_prompt",
                "should_end_story_intelligently"
            ],
            "facts_mode": [
                "get_facts_system_prompt",
                "get_first_fact_prompt",
                "get_continuing_fact_prompt", 
                "get_new_topic_fact_prompt"
            ],
            "design_phase": [
                "get_design_phase_prompt"
            ],
            "vocabulary": [
                "enhance_with_vocabulary",
                "generate_massive_vocabulary_pool"
            ],
            "self_documentation": [
                "get_complete_story_flow",
                "get_complete_facts_flow",
                "get_all_prompt_types"
            ]
        }


# Create singleton instance for app usage
prompt_manager = PromptManager()