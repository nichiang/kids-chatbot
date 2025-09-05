import os
import json
import logging
import time
from functools import wraps
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
import openai
from prompt_manager import prompt_manager
from consolidated_prompts import consolidated_prompt_builder

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global list to track LLM call timing data - accessed by app.py latency logger
llm_call_timings = []

def measure_llm_call(call_type: str):
    """Decorator to measure LLM API call duration (for sync functions)"""
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
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        # Feature flag for consolidated prompts (defaults to False for backward compatibility)
        self.use_consolidated_prompts = os.getenv('USE_CONSOLIDATED_PROMPTS', 'False').lower() == 'true'
        
        # PROMPT MANAGER ARCHITECTURE: Load system prompts via centralized PromptManager
        # Provides LLM with complete educational framework while maintaining clean separation
        # Story mode: Complete 10-step educational process with tutor personality
        # Facts mode: Engaging content creation guidelines for elementary students
        self.system_prompt = prompt_manager.get_story_system_prompt()
        self.fun_facts_system_prompt = prompt_manager.get_facts_system_prompt()
        
        # Initialize OpenAI client
        if self.api_key:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("OpenAI client initialized successfully")
            if self.use_consolidated_prompts:
                logger.info("🚀 Consolidated prompts enabled")
        else:
            logger.warning("OpenAI API key not found. Using fallback responses.")
            self.client = None
        
    # REMOVED: _load_fun_facts_system_prompt() -> now handled by prompt_manager.get_facts_system_prompt()
    
    @measure_llm_call('story_generation')
    def generate_response(self, prompt: str, max_tokens: int = 300, system_prompt: str = None) -> str:
        """
        Generate a response using OpenAI API or fallback to sample responses
        """
        # Use provided system prompt or default to story system prompt
        effective_system_prompt = system_prompt if system_prompt is not None else self.system_prompt
        
        if self.client and self.api_key:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": effective_system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.7
                )

                print(prompt)
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                return self._get_fallback_response(prompt)
        else:
            logger.info("Using fallback response (no OpenAI API key)")
            return self._get_fallback_response(prompt)
    
    def _get_fallback_response(self, prompt: str) -> str:
        """Fallback responses when OpenAI API is not available"""
        prompt_lower = prompt.lower()
        
        # Story responses
        if "story" in prompt_lower:
            if "space" in prompt_lower:
                return """🚀 Space adventures are incredible! Here's how our story begins:

Captain Zoe strapped herself into the **gleaming** spacecraft and checked all the controls. Her mission was to explore a mysterious new planet that scientists had **discovered** last week. As the rocket engines roared to life, she felt both nervous and excited about what **extraordinary** creatures she might encounter among the stars.

What happens next in our space adventure? Tell me what Captain Zoe sees or does when she reaches the mysterious planet!"""
            
            elif "fantasy" in prompt_lower:
                return """🏰 Fantasy quests are magical! Here's how our story begins:

Princess Maya ventured into the **enchanted** forest, carrying her grandmother's ancient map. The trees whispered secrets as she walked deeper into the woods, searching for the **legendary** Crystal of Courage. Strange **glimmers** of light danced between the branches, leading her toward an adventure she'd never forget.

What happens next in our fantasy quest? Tell me what Princess Maya discovers in the enchanted forest!"""
                
            else:
                return """Great choice! Let me start our story:

Our hero stepped into a new **adventure**, ready to face whatever challenges lay ahead. The **journey** would test their courage and **determination** in ways they never imagined.

What happens next in our story? Tell me how our hero begins their adventure!"""
        
        # Fact responses
        elif "fact" in prompt_lower:
            if "space" in prompt_lower:
                return """Jupiter is so **enormous** that more than 1,300 Earths could fit inside it! Scientists still **investigate** Jupiter to learn about its powerful storms, like the Great Red Spot — a giant spinning storm that's been raging for hundreds of years. Space missions help us **discover** new facts about our solar system every day! 🚀🪐✨"""
            
            elif "animal" in prompt_lower or "ocean" in prompt_lower:
                return """The blue whale is so **massive** that its heart alone weighs as much as a car! These **magnificent** creatures can **communicate** with each other across hundreds of miles using low-frequency sounds. Scientists still **study** these gentle giants to learn more about their amazing abilities! 🐋🌊💙"""
                
            else:
                return """Did you know that honey never spoils? Archaeologists have found **ancient** honey in Egyptian tombs that's over 3,000 years old and still perfectly good to eat! The **unique** properties of honey help it **preserve** itself naturally forever! 🍯✨🏺"""
        
        else:
            return "I'm here to help with stories and fun facts! What would you like to explore?"

    @measure_llm_call('vocabulary_question')
    def generate_vocabulary_question(self, word: str, context: str) -> Dict:
        """Generate vocabulary questions following Step 8 format"""
        if self.client and self.api_key:
            try:
                # FIXED: Use the already-selected vocabulary word from app.py (don't re-select)
                # The word parameter was already carefully selected using filtered available_words
                actual_word = word
                sentence_with_word = self._extract_sentence_with_word(actual_word, context)
                
                if not sentence_with_word:
                    sentence_with_word = context  # Fallback to full context
                
                prompt = f"""Following Step 8 of the story process, create a vocabulary question for the word "{actual_word}" from this sentence: "{sentence_with_word}"

Create the question in this exact format:
What does the word **{actual_word}** mean?

Show the sentence where it was used: "{sentence_with_word}"

Then provide 4 multiple choice answers (a, b, c, d) with one correct answer and three distractors.
Make it appropriate for 2nd-3rd grade students.

Example format:
{{
  "question": "What does the word **courage** mean?\\n\\n\\"As Leo went forward, he felt a sense of **courage**.\\""
  "options": ["a) being scared", "b) being brave", "c) being tired", "d) being hungry"],
  "correctIndex": 1
}}

Return ONLY valid JSON with: question, options (array of 4 strings), correctIndex (0-3)"""

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.3
                )
                
                result = json.loads(response.choices[0].message.content.strip())
                return result
                
            except Exception as e:
                logger.error(f"Error generating vocabulary question: {e}")
                return self._get_fallback_vocab_question(word, context)
        else:
            return self._get_fallback_vocab_question(word, context)

    def _get_fallback_vocab_question(self, word: str, context: str) -> Dict:
        """Fallback vocabulary questions with proper sentence extraction"""
        # FIXED: Use the already-selected vocabulary word from app.py (don't re-select)  
        # The word parameter was already carefully selected using filtered available_words
        actual_word = word
        sentence_with_word = self._extract_sentence_with_word(actual_word, context)
        
        if not sentence_with_word:
            sentence_with_word = context  # Fallback to full context
        
        vocab_questions = {
            "enormous": {
                "question": f'What does the word **enormous** mean?\n\n"{sentence_with_word}"',
                "options": ["a) very small", "b) very big", "c) very old", "d) very cold"],
                "correctIndex": 1
            },
            "investigate": {
                "question": f'What does the word **investigate** mean?\n\n"{sentence_with_word}"',
                "options": ["a) to ignore", "b) to find out about", "c) to run away", "d) to eat"],
                "correctIndex": 1
            },
            "discover": {
                "question": f'What does the word **discover** mean?\n\n"{sentence_with_word}"',
                "options": ["a) to lose something", "b) to hide something", "c) to find something new", "d) to break something"],
                "correctIndex": 2
            },
            "magnificent": {
                "question": f'What does the word **magnificent** mean?\n\n"{sentence_with_word}"',
                "options": ["a) very small", "b) very boring", "c) very beautiful", "d) very scary"],
                "correctIndex": 2
            },
            "ancient": {
                "question": f'What does the word **ancient** mean?\n\n"{sentence_with_word}"',
                "options": ["a) very new", "b) very old", "c) very fast", "d) very loud"],
                "correctIndex": 1
            },
            "gleaming": {
                "question": f'What does the word **gleaming** mean?\n\n"{sentence_with_word}"',
                "options": ["a) very dirty", "b) very shiny", "c) very broken", "d) very small"],
                "correctIndex": 1
            },
            "extraordinary": {
                "question": f'What does the word **extraordinary** mean?\n\n"{sentence_with_word}"',
                "options": ["a) very ordinary", "b) very boring", "c) very amazing", "d) very sad"],
                "correctIndex": 2
            },
            "enchanted": {
                "question": f'What does the word **enchanted** mean?\n\n"{sentence_with_word}"',
                "options": ["a) very scary", "b) very magical", "c) very dark", "d) very small"],
                "correctIndex": 1
            },
            "legendary": {
                "question": f'What does the word **legendary** mean?\n\n"{sentence_with_word}"',
                "options": ["a) very new", "b) very small", "c) very famous", "d) very quiet"],
                "correctIndex": 2
            },
            "massive": {
                "question": f'What does the word **massive** mean?\n\n"{sentence_with_word}"',
                "options": ["a) very tiny", "b) very huge", "c) very fast", "d) very quiet"],
                "correctIndex": 1
            },
            "communicate": {
                "question": f'What does the word **communicate** mean?\n\n"{sentence_with_word}"',
                "options": ["a) to be silent", "b) to talk or share", "c) to run away", "d) to eat food"],
                "correctIndex": 1
            },
            "courage": {
                "question": f'What does the word **courage** mean?\n\n"{sentence_with_word}"',
                "options": ["a) being scared", "b) being brave", "c) being tired", "d) being hungry"],
                "correctIndex": 1
            },
            "curious": {
                "question": f'What does the word **curious** mean?\n\n"{sentence_with_word}"',
                "options": ["a) wanting to know more", "b) feeling sleepy", "c) being angry", "d) being quiet"],
                "correctIndex": 0
            },
            "suspicious": {
                "question": f'What does the word **suspicious** mean?\n\n"{sentence_with_word}"',
                "options": ["a) very happy", "b) very loud", "c) seeming strange or wrong", "d) very bright"],
                "correctIndex": 2
            },
            "unique": {
                "question": f'What does the word **unique** mean?\n\n"{sentence_with_word}"',
                "options": ["a) very common", "b) one of a kind", "c) very old", "d) very small"],
                "correctIndex": 1
            },
            "preserve": {
                "question": f'What does the word **preserve** mean?\n\n"{sentence_with_word}"',
                "options": ["a) to throw away", "b) to keep safe", "c) to break", "d) to hide"],
                "correctIndex": 1
            },
            "study": {
                "question": f'What does the word **study** mean?\n\n"{sentence_with_word}"',
                "options": ["a) to ignore", "b) to learn about", "c) to forget", "d) to destroy"],
                "correctIndex": 1
            }
        }
        
        # Generate reasonable definitions for unknown words
        if actual_word.lower() not in vocab_questions:
            return {
                "question": f'What does the word **{actual_word}** mean?\n\n"{sentence_with_word}"',
                "options": [
                    f"a) something related to {actual_word}",
                    f"b) the opposite of {actual_word}",
                    f"c) a type of {actual_word}",
                    f"d) similar to {actual_word}"
                ],
                "correctIndex": 0
            }
        
        return vocab_questions.get(actual_word.lower())

    def _extract_sentence_with_word(self, word: str, context: str) -> Optional[str]:
        """
        Extract sentence containing the vocabulary word with improved matching
        Handles case-insensitive matching and punctuation variations
        """
        import re
        
        # Split on sentence-ending punctuation while preserving it
        sentences = re.split(r'([.!?])', context)
        
        # Reconstruct sentences properly
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                full_sentence = sentences[i] + sentences[i + 1]
                
                # Create a regex pattern that matches the word with case insensitivity and punctuation
                # This looks for **word** or **word,** or **word!** etc and handles case differences
                word_pattern = re.compile(
                    r'\*\*' + re.escape(word) + r'([,;:.!?]*)\*\*',
                    re.IGNORECASE
                )
                
                if word_pattern.search(full_sentence):
                    return full_sentence.strip()
        
        return None

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

    @measure_llm_call('grammar_feedback')
    def provide_grammar_feedback(self, user_text: str) -> Optional[str]:
        """Provide grammar feedback following Step 5 of the story process"""
        if self.client and self.api_key:
            try:
                prompt = f"""As a friendly English tutor for elementary students, analyze this text: "{user_text}"

Following Step 5 of the story process, if there are any grammatical errors or if this is an incomplete sentence, explain what a better written sentence would be. If there is better vocabulary to use, suggest it. 

IMPORTANT: Always include a specific example of a better sentence, especially for incomplete sentences.

If the grammar is correct and complete, return "CORRECT".
If there's a suggestion, provide it in this format: "You could make that sentence even better by saying '[improved version]'. [Brief explanation]."

Examples:
- For "practiced." → "You could make that sentence even better by saying 'They practiced hard for the next game.' This gives us more detail about what happened!"
- For "sara has curly hair" → "Great job, that's a nice start! You could add more details like 'Sara has curly hair and beautiful green eyes.' This makes the description more vivid!"
- For "He go to the store." → "You could make that sentence even better by saying 'He went to the store.' We use 'went' for past actions!"

Always provide encouraging feedback and specific examples to help young learners improve their writing."""

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.3
                )
                
                result = response.choices[0].message.content.strip()
                return None if result == "CORRECT" else result
                
            except Exception as e:
                logger.error(f"Error providing grammar feedback: {e}")
                return self._get_fallback_grammar_feedback(user_text)
        else:
            return self._get_fallback_grammar_feedback(user_text)

    def _get_fallback_grammar_feedback(self, user_text: str) -> Optional[str]:
        """Fallback grammar suggestions"""
        user_lower = user_text.lower().strip()
        
        # Check for incomplete sentences (single words or very short fragments)
        if len(user_text.split()) <= 2 and not user_text.endswith("!") and not user_text.endswith("?"):
            if user_lower == "practiced." or user_lower == "practiced":
                return "You could make that sentence even better by saying 'They practiced hard for the next game.' This gives us more detail about what happened!"
            elif user_lower in ["ran.", "ran", "walked.", "walked", "played.", "played"]:
                return f"You could make that sentence even better by saying 'They {user_lower.replace('.', '')} together.' This tells us more about what happened!"
            elif len(user_text.split()) == 1:
                return f"You could make that sentence even better by adding more details! Try something like 'They {user_text.replace('.', '')} hard to get better.'"
        
        # Check for descriptive writing opportunities
        if "has curly hair" in user_lower:
            return "Great job, that's a nice start! You could add more details like 'Sara has curly hair and beautiful green eyes.' This makes the description more vivid!"
            
        # Check for common grammar errors
        if user_lower.startswith("she find"):
            return "You could make that sentence even better by saying 'She discovers' or 'She finds'. The word 'discovers' sounds more exciting for an adventure story!"
        
        if "there" in user_lower and "alien" in user_lower:
            return "Nice addition! You could make that more descriptive by saying 'There was a strange alien' or 'A mysterious alien appeared'."
        
        if user_lower.startswith("he go"):
            return "You could make that sentence even better by saying 'He goes' or 'He went'. This makes the sentence sound more complete!"
        
        if user_lower.startswith("they go"):
            return "You could make that sentence even better by saying 'They go' or 'They went'. This makes the sentence sound more complete!"
        
        return None

    # NEW CONSOLIDATED METHODS
    
    @measure_llm_call('consolidated_story_generation')
    def generate_consolidated_story_response(self, 
                                           topic: str, 
                                           user_input: str = None,
                                           story_step: str = "opening",
                                           include_feedback: bool = True,
                                           include_vocabulary: bool = True) -> Dict:
        """
        Generate consolidated response with story content, vocabulary questions, and feedback
        in a single API call to reduce latency.
        
        Args:
            topic: Story topic (space, animals, fantasy, etc.)
            user_input: User's story contribution (for continuation/feedback)
            story_step: Story phase (opening, continuation, conclusion)
            include_feedback: Whether to include writing feedback
            include_vocabulary: Whether to include vocabulary question
            
        Returns:
            Dictionary with structured response containing all components
        """
        if not self.use_consolidated_prompts:
            # Fallback to individual method calls for backward compatibility
            logger.info("🔄 Falling back to individual API calls (consolidated prompts disabled)")
            return self._generate_individual_responses(topic, user_input, story_step, include_feedback, include_vocabulary)
        
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
                
                logger.info(f"🚀 Making consolidated API call for {story_step} story")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": consolidated_prompt}
                    ],
                    max_tokens=800,  # Increased for consolidated response
                    temperature=0.7
                )
                
                # Parse consolidated response
                result = json.loads(response.choices[0].message.content.strip())
                
                # Validate response structure
                return self._validate_consolidated_response(result)
                
            except Exception as e:
                logger.error(f"❌ Consolidated API call failed: {e}")
                # Fallback to individual calls
                logger.info("🔄 Falling back to individual API calls")
                return self._generate_individual_responses(topic, user_input, story_step, include_feedback, include_vocabulary)
        else:
            return self._get_consolidated_fallback_response(topic, user_input, story_step)
    
    def _generate_individual_responses(self, topic: str, user_input: str, story_step: str, include_feedback: bool, include_vocabulary: bool) -> Dict:
        """
        Generate responses using individual API calls (backward compatibility mode)
        """
        result = {}
        
        # Generate story content
        if story_step == "opening":
            prompt = f"Create a story opening about {topic} for 2nd-3rd graders."
        elif story_step == "continuation":
            prompt = f"Continue this story: {user_input}"
        else:  # conclusion
            prompt = f"Conclude this story: {user_input}"
        
        result["story_content"] = self.generate_response(prompt)
        
        # Add vocabulary question if requested
        if include_vocabulary and result["story_content"]:
            vocab_words = self.extract_vocabulary_words(result["story_content"])
            if vocab_words:
                result["vocabulary_question"] = self.generate_vocabulary_question(vocab_words[0], result["story_content"])
        
        # Add writing feedback if requested and user input exists
        if include_feedback and user_input:
            feedback = self.provide_grammar_feedback(user_input)
            if feedback:
                result["writing_feedback"] = {
                    "feedback": feedback,
                    "suggestions": [],
                    "praise": "Keep up the great work!"
                }
        
        result["next_step"] = "Continue the story with your next contribution!"
        
        return result
    
    def _validate_consolidated_response(self, response: Dict) -> Dict:
        """
        Validate and ensure consolidated response has expected structure
        """
        validated = {
            "story_content": response.get("story_content", ""),
            "vocabulary_question": response.get("vocabulary_question", {}),
            "writing_feedback": response.get("writing_feedback", {}),
            "next_step": response.get("next_step", "Continue the story!")
        }
        
        # Ensure vocabulary question has proper structure
        if validated["vocabulary_question"] and not all(key in validated["vocabulary_question"] for key in ["question", "options", "correct_answer"]):
            logger.warning("⚠️  Vocabulary question missing required fields")
            validated["vocabulary_question"] = {}
        
        return validated
    
    def _get_consolidated_fallback_response(self, topic: str, user_input: str, story_step: str) -> Dict:
        """
        Consolidated fallback response when API is unavailable
        """
        # Use existing fallback logic
        story_content = self._get_fallback_response(f"story about {topic}")
        
        result = {
            "story_content": story_content,
            "vocabulary_question": {},
            "writing_feedback": {},
            "next_step": "Continue the story with your next contribution!"
        }
        
        # Add vocabulary question from story content
        vocab_words = self.extract_vocabulary_words(story_content)
        if vocab_words:
            result["vocabulary_question"] = self._get_fallback_vocab_question(vocab_words[0], story_content)
        
        return result
    
    @measure_llm_call('consolidated_vocabulary_generation')
    def generate_consolidated_vocabulary_question(self, word: str, context: str) -> Dict:
        """
        Generate vocabulary question using consolidated prompts
        """
        if not self.use_consolidated_prompts:
            return self.generate_vocabulary_question(word, context)
        
        if self.client and self.api_key:
            try:
                consolidated_prompt = consolidated_prompt_builder.build_vocabulary_question_prompt(word, context)
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": consolidated_prompt}
                    ],
                    max_tokens=200,
                    temperature=0.3
                )
                
                result = json.loads(response.choices[0].message.content.strip())
                return result
                
            except Exception as e:
                logger.error(f"❌ Consolidated vocabulary question failed: {e}")
                return self.generate_vocabulary_question(word, context)
        else:
            return self._get_fallback_vocab_question(word, context)
    
    @measure_llm_call('consolidated_writing_feedback')
    def provide_consolidated_writing_feedback(self, user_input: str) -> Optional[Dict]:
        """
        Provide writing feedback using consolidated prompts
        """
        if not self.use_consolidated_prompts:
            # Convert individual feedback to consolidated format
            feedback = self.provide_grammar_feedback(user_input)
            if feedback:
                return {
                    "feedback": feedback,
                    "suggestions": [],
                    "praise": "Keep up the great work!"
                }
            return None
        
        if self.client and self.api_key:
            try:
                consolidated_prompt = consolidated_prompt_builder.build_writing_feedback_prompt(user_input)
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": consolidated_prompt}
                    ],
                    max_tokens=150,
                    temperature=0.3
                )
                
                result = json.loads(response.choices[0].message.content.strip())
                return result if result.get("feedback") else None
                
            except Exception as e:
                logger.error(f"❌ Consolidated writing feedback failed: {e}")
                # Fallback to individual method
                feedback = self.provide_grammar_feedback(user_input)
                if feedback:
                    return {
                        "feedback": feedback,
                        "suggestions": [],
                        "praise": "Keep up the great work!"
                    }
                return None
        else:
            # Fallback to individual method
            feedback = self._get_fallback_grammar_feedback(user_input)
            if feedback:
                return {
                    "feedback": feedback,
                    "suggestions": [],
                    "praise": "Keep up the great work!"
                }
            return None
    
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
    
    def enable_consolidated_prompts(self):
        """Enable consolidated prompts feature flag"""
        self.use_consolidated_prompts = True
        logger.info("🚀 Consolidated prompts enabled")
    
    def disable_consolidated_prompts(self):
        """Disable consolidated prompts feature flag (use individual calls)"""
        self.use_consolidated_prompts = False
        logger.info("🔄 Consolidated prompts disabled - using individual API calls")

# Global instance
llm_provider = LLMProvider()