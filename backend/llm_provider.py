"""
Clean LLM Provider with Consolidated Prompts Only

This module provides a simplified LLM interface that uses only consolidated prompts
to reduce API call latency. No more complex fallbacks or feature flags - just clean,
efficient single API calls for all educational interactions.
"""

import os
import json
import logging
import time
from functools import wraps
from typing import Dict, List, Optional
from dotenv import load_dotenv
import openai
from consolidated_prompts import consolidated_prompt_builder

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global list to track LLM call timing data - accessed by app.py latency logger
llm_call_timings = []

def measure_llm_call(call_type: str):
    """Decorator to measure LLM API call duration"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start_time) * 1000
                
                llm_call_timings.append({
                    'type': call_type,
                    'duration': round(duration, 2),
                    'timestamp': time.time()
                })
                
                return result
            except Exception as e:
                duration = (time.perf_counter() - start_time) * 1000
                llm_call_timings.append({
                    'type': call_type,
                    'duration': round(duration, 2),
                    'error': str(e),
                    'timestamp': time.time()
                })
                raise
                
        return wrapper
    return decorator


class LLMProvider:
    """
    Clean LLM Provider using consolidated prompts for reduced latency.
    
    All educational interactions (story generation, vocabulary questions, writing feedback)
    are handled through single consolidated API calls instead of multiple sequential calls.
    """
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        # Get basic system context from consolidated prompt builder
        framework = consolidated_prompt_builder._get_component("educational_framework", "persona")
        self.system_context = f"You are a {framework.get('role', 'friendly English tutor')} with a {framework.get('tone', 'encouraging and patient')} approach, working with {framework.get('age_target', '2nd-3rd grade students')}."
        
        # Initialize OpenAI client
        if self.api_key:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("OpenAI client initialized successfully")
            logger.info("Using consolidated prompts for all interactions")
        else:
            logger.warning("OpenAI API key not found. Using fallback responses.")
            self.client = None
    
    @measure_llm_call('consolidated_story_generation')
    def generate_story_response(self, 
                               topic: str, 
                               user_input: str = None,
                               story_step: str = "opening",
                               include_feedback: bool = True,
                               include_vocabulary: bool = True) -> Dict:
        """
        Generate consolidated response with story content, vocabulary questions, and feedback
        in a single API call.
        
        Args:
            topic: Story topic (space, animals, fantasy, etc.)
            user_input: User's story contribution (for continuation/feedback)
            story_step: Story phase (opening, continuation, conclusion)
            include_feedback: Whether to include writing feedback
            include_vocabulary: Whether to include vocabulary question
            
        Returns:
            Dictionary with structured response containing all components
        """
        if self.client and self.api_key:
            try:
                # Build consolidated prompt
                consolidated_prompt = consolidated_prompt_builder.build_consolidated_story_prompt(
                    topic=topic,
                    user_input=user_input,
                    story_step=story_step,
                    include_feedback=include_feedback,
                    include_vocabulary=include_vocabulary
                )
                
                logger.info(f"Making consolidated API call for {story_step} story")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_context},
                        {"role": "user", "content": consolidated_prompt}
                    ],
                    max_tokens=800,  # Increased for consolidated response
                    temperature=0.7
                )
                
                # Parse consolidated response
                result = json.loads(response.choices[0].message.content.strip())
                
                # Validate and clean response structure
                return self._validate_story_response(result)
                
            except Exception as e:
                logger.error(f"Consolidated API call failed: {e}")
                # Return structured fallback instead of individual calls
                return self._get_fallback_story_response(topic, user_input, story_step, include_feedback, include_vocabulary)
        else:
            return self._get_fallback_story_response(topic, user_input, story_step, include_feedback, include_vocabulary)
    
    @measure_llm_call('vocabulary_question_generation')
    def generate_vocabulary_question(self, word: str, context: str) -> Dict:
        """
        Generate vocabulary question using consolidated prompts
        
        Args:
            word: Vocabulary word to create question about
            context: Story context where word appeared
            
        Returns:
            Dictionary with question, options, correct answer, and explanation
        """
        if self.client and self.api_key:
            try:
                consolidated_prompt = consolidated_prompt_builder.build_vocabulary_question_prompt(word, context)
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_context},
                        {"role": "user", "content": consolidated_prompt}
                    ],
                    max_tokens=200,
                    temperature=0.3
                )
                
                result = json.loads(response.choices[0].message.content.strip())
                return self._validate_vocabulary_question(result)
                
            except Exception as e:
                logger.error(f"Vocabulary question generation failed: {e}")
                return self._get_fallback_vocabulary_question(word, context)
        else:
            return self._get_fallback_vocabulary_question(word, context)
    
    @measure_llm_call('writing_feedback_generation')
    def provide_writing_feedback(self, user_input: str) -> Optional[Dict]:
        """
        Provide writing feedback using consolidated prompts
        
        Args:
            user_input: User's text to provide feedback on
            
        Returns:
            Dictionary with feedback, suggestions, and praise, or None if no feedback needed
        """
        if self.client and self.api_key:
            try:
                consolidated_prompt = consolidated_prompt_builder.build_writing_feedback_prompt(user_input)
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_context},
                        {"role": "user", "content": consolidated_prompt}
                    ],
                    max_tokens=150,
                    temperature=0.3
                )
                
                result = json.loads(response.choices[0].message.content.strip())
                return result if result.get("feedback") else None
                
            except Exception as e:
                logger.error(f"Writing feedback generation failed: {e}")
                return self._get_fallback_writing_feedback(user_input)
        else:
            return self._get_fallback_writing_feedback(user_input)
    
    def extract_vocabulary_words(self, text: str) -> List[str]:
        """Extract vocabulary words from text (words between ** markers)"""
        import re
        words = re.findall(r'\*\*(.*?)\*\*', text)
        # Strip punctuation from extracted words for cleaner questions
        cleaned_words = []
        for word in words:
            cleaned_word = re.sub(r'[,;:.!?]+$', '', word.strip())
            if cleaned_word:  # Only add non-empty words
                cleaned_words.append(cleaned_word)
        return cleaned_words
    
    @measure_llm_call('api_status_check')
    def check_api_status(self) -> Dict[str, str]:
        """Check if OpenAI API is available"""
        if not self.api_key:
            return {"status": "missing_key", "message": "OpenAI API key not found"}
        
        if not self.client:
            return {"status": "not_initialized", "message": "OpenAI client not initialized"}
        
        try:
            # Test API connection
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return {"status": "connected", "message": "OpenAI API is working"}
        except Exception as e:
            return {"status": "error", "message": f"API error: {str(e)}"}
    
    # VALIDATION METHODS
    
    def _validate_story_response(self, response: Dict) -> Dict:
        """Validate and ensure story response has expected structure"""
        validated = {
            "story_content": response.get("story_content", response.get("story", "")),
            "vocabulary_question": response.get("vocabulary_question", {}),
            "writing_feedback": response.get("writing_feedback", {}),
            "next_step": response.get("next_step", "Continue the story!"),
            "entities": response.get("entities", {}),
            "vocabulary_words": response.get("vocabulary_words", [])
        }
        
        # Ensure vocabulary question has proper structure
        vocab_q = validated["vocabulary_question"]
        if vocab_q and not all(key in vocab_q for key in ["question", "options"]):
            logger.warning("Vocabulary question missing required fields")
            validated["vocabulary_question"] = {}
        
        # Convert old format if needed
        if "correctIndex" in vocab_q:
            # Convert old format to new format
            options = vocab_q.get("options", [])
            correct_index = vocab_q.get("correctIndex", 0)
            if isinstance(options, list) and 0 <= correct_index < len(options):
                vocab_q["correct_answer"] = chr(97 + correct_index)  # Convert 0->a, 1->b, etc.
            vocab_q.pop("correctIndex", None)
        
        return validated
    
    def _validate_vocabulary_question(self, response: Dict) -> Dict:
        """Validate vocabulary question response"""
        # Handle both old and new formats
        if "correctIndex" in response:
            # Convert old format
            options = response.get("options", [])
            correct_index = response.get("correctIndex", 0)
            if isinstance(options, list) and 0 <= correct_index < len(options):
                response["correct_answer"] = chr(97 + correct_index)
            response.pop("correctIndex", None)
        
        return {
            "question": response.get("question", ""),
            "options": response.get("options", {}),
            "correct_answer": response.get("correct_answer", "a"),
            "explanation": response.get("explanation", "")
        }
    
    # FALLBACK METHODS
    
    def _get_fallback_story_response(self, topic: str, user_input: str, story_step: str, include_feedback: bool, include_vocabulary: bool) -> Dict:
        """Consolidated fallback response when API is unavailable"""
        # Generate story content based on topic and step
        if story_step == "opening":
            if topic.lower() == "space":
                story_content = "Captain Zoe strapped herself into the **gleaming** spacecraft and checked all the controls. Her mission was to explore a mysterious new planet that scientists had **discovered** last week. As the rocket engines roared to life, she felt both nervous and excited about what **extraordinary** creatures she might encounter among the stars."
            elif topic.lower() == "fantasy":
                story_content = "Princess Maya ventured into the **enchanted** forest, carrying her grandmother's ancient map. The trees whispered secrets as she walked deeper into the woods, searching for the **legendary** Crystal of Courage. Strange **glimmers** of light danced between the branches, leading her toward an adventure she'd never forget."
            else:
                story_content = f"Our hero stepped into a new **adventure** about {topic}, ready to face whatever challenges lay ahead. The **journey** would test their courage and **determination** in ways they never imagined."
        else:
            story_content = f"The {topic} adventure continued with new **discoveries** and **challenges** ahead."
        
        result = {
            "story_content": story_content,
            "vocabulary_question": {},
            "writing_feedback": {},
            "next_step": "Tell me what happens next!",
            "entities": {},
            "vocabulary_words": self.extract_vocabulary_words(story_content)
        }
        
        # Add vocabulary question if requested
        if include_vocabulary and result["vocabulary_words"]:
            word = result["vocabulary_words"][0]
            result["vocabulary_question"] = self._get_fallback_vocabulary_question(word, story_content)
        
        # Add writing feedback if requested and user input exists
        if include_feedback and user_input:
            feedback = self._get_fallback_writing_feedback(user_input)
            if feedback:
                result["writing_feedback"] = feedback
        
        return result
    
    def _get_fallback_vocabulary_question(self, word: str, context: str) -> Dict:
        """Fallback vocabulary questions"""
        vocab_questions = {
            "gleaming": {"question": f"What does **gleaming** mean?", "options": {"a": "very dirty", "b": "very shiny", "c": "very broken", "d": "very small"}, "correct_answer": "b"},
            "discovered": {"question": f"What does **discovered** mean?", "options": {"a": "to lose something", "b": "to hide something", "c": "to find something new", "d": "to break something"}, "correct_answer": "c"},
            "extraordinary": {"question": f"What does **extraordinary** mean?", "options": {"a": "very ordinary", "b": "very boring", "c": "very amazing", "d": "very sad"}, "correct_answer": "c"},
            "enchanted": {"question": f"What does **enchanted** mean?", "options": {"a": "very scary", "b": "very magical", "c": "very dark", "d": "very small"}, "correct_answer": "b"},
            "legendary": {"question": f"What does **legendary** mean?", "options": {"a": "very new", "b": "very small", "c": "very famous", "d": "very quiet"}, "correct_answer": "c"},
            "adventure": {"question": f"What does **adventure** mean?", "options": {"a": "staying home", "b": "an exciting journey", "c": "being bored", "d": "sleeping"}, "correct_answer": "b"},
            "determination": {"question": f"What does **determination** mean?", "options": {"a": "giving up easily", "b": "being lazy", "c": "trying very hard", "d": "being scared"}, "correct_answer": "c"}
        }
        
        return vocab_questions.get(word.lower(), {
            "question": f"What does **{word}** mean?",
            "options": {"a": f"something about {word}", "b": f"the opposite of {word}", "c": f"a type of {word}", "d": f"similar to {word}"},
            "correct_answer": "a"
        })
    
    def _get_fallback_writing_feedback(self, user_input: str) -> Optional[Dict]:
        """Fallback writing feedback"""
        user_lower = user_input.lower().strip()
        
        # Check for incomplete sentences
        if len(user_input.split()) <= 2:
            return {
                "feedback": f"You could make that even better by adding more details! Try something like '{user_input} and then something exciting happened.'",
                "suggestions": ["Add more descriptive words", "Tell us what happened next"],
                "praise": "Great start! Keep building the story!"
            }
        
        # Check for common grammar patterns
        if user_lower.startswith("he go") or user_lower.startswith("she go"):
            return {
                "feedback": "You could make that sentence even better by saying 'He went' or 'She went'. We use 'went' for past actions!",
                "suggestions": ["Use 'went' instead of 'go' for past tense"],
                "praise": "Good story idea! Just a small grammar tip to make it perfect."
            }
        
        return None


# Global instance
llm_provider = LLMProvider()