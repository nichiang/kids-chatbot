import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
import openai
from generate_prompt import generate_prompt

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMProvider:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        # Generate the full prompt from spec files
        self.system_prompt = generate_prompt()
        
        # Initialize OpenAI client
        if self.api_key:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("OpenAI client initialized successfully")
        else:
            logger.warning("OpenAI API key not found. Using fallback responses.")
            self.client = None
        
    def generate_response(self, prompt: str, max_tokens: int = 300) -> str:
        """
        Generate a response using OpenAI API or fallback to sample responses
        """
        if self.client and self.api_key:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                
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

    def generate_vocabulary_question(self, word: str, context: str) -> Dict:
        """Generate vocabulary questions following Step 8 format"""
        if self.client and self.api_key:
            try:
                # Extract just the sentence containing the word
                import re
                # Split on sentence-ending punctuation while preserving it
                sentences = re.split(r'([.!?])', context)
                sentence_with_word = None
                
                # Reconstruct sentences properly
                for i in range(0, len(sentences) - 1, 2):
                    if i + 1 < len(sentences):
                        full_sentence = sentences[i] + sentences[i + 1]
                        if f"**{word}**" in full_sentence:
                            sentence_with_word = full_sentence.strip()
                            break
                
                if not sentence_with_word:
                    sentence_with_word = context  # Fallback to full context
                
                prompt = f"""Following Step 8 of the story process, create a vocabulary question for the word "{word}" from this sentence: "{sentence_with_word}"

Create the question in this exact format:
What does the word **{word}** mean?

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
        # Extract just the sentence containing the word
        import re
        # Split on sentence-ending punctuation while preserving it
        sentences = re.split(r'([.!?])', context)
        sentence_with_word = None
        
        # Reconstruct sentences properly
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                full_sentence = sentences[i] + sentences[i + 1]
                if f"**{word}**" in full_sentence:
                    sentence_with_word = full_sentence.strip()
                    break
        
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
        if word.lower() not in vocab_questions:
            return {
                "question": f'What does the word **{word}** mean?\n\n"{sentence_with_word}"',
                "options": [
                    f"a) something related to {word}",
                    f"b) the opposite of {word}",
                    f"c) a type of {word}",
                    f"d) similar to {word}"
                ],
                "correctIndex": 0
            }
        
        return vocab_questions.get(word.lower())

    def extract_vocabulary_words(self, text: str) -> List[str]:
        """Extract vocabulary words from text (words between ** markers)"""
        import re
        words = re.findall(r'\*\*(.*?)\*\*', text)
        return words

    def provide_grammar_feedback(self, user_text: str) -> Optional[str]:
        """Provide grammar feedback following Step 5 of the story process"""
        if self.client and self.api_key:
            try:
                prompt = f"""As a friendly English tutor for elementary students, analyze this text: "{user_text}"

Following Step 5 of the story process, if there are any grammatical errors or if this is an incomplete sentence, explain what a better written sentence would be. If there is better vocabulary to use, suggest it. Be as brief as possible.

If the grammar is correct and complete, return "CORRECT".
If there's a suggestion, provide it in this format: "You could make that sentence even better by saying '[improved version]'. [Brief explanation]."

Examples:
- For "practiced." → "You could make that sentence even better by saying 'They practiced hard for the next game.' This gives us more detail about what happened!"
- For "He go to the store." → "You could make that sentence even better by saying 'He went to the store.' We use 'went' for past actions!"

Keep it encouraging and simple for 2nd-3rd graders."""

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

# Global instance
llm_provider = LLMProvider()