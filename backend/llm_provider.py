import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
import openai

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
                        {"role": "system", "content": "You are a friendly and playful English tutor for elementary school students (1st-3rd grade). Use simple language, be encouraging, and make learning fun. Bold important vocabulary words with **word** format."},
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
                return """🌌 Space — excellent choice, explorer! Here's an amazing space fact:

Jupiter is so **enormous** that more than 1,300 Earths could fit inside it! Scientists still **investigate** Jupiter to learn about its powerful storms, like the Great Red Spot — a giant spinning storm that's been raging for hundreds of years. Space missions help us **discover** new facts about our solar system every day!"""
            
            elif "animal" in prompt_lower:
                return """🐾 Animals — great choice! Here's a fascinating animal fact:

The blue whale is so **massive** that its heart alone weighs as much as a car! These **magnificent** creatures can **communicate** with each other across hundreds of miles using low-frequency sounds. Scientists still **study** these gentle giants to learn more about their amazing abilities!"""
                
            else:
                return """Awesome topic choice! Here's a cool fact:

Did you know that honey never spoils? Archaeologists have found **ancient** honey in Egyptian tombs that's over 3,000 years old and still perfectly good to eat! The **unique** properties of honey help it **preserve** itself naturally forever!"""
        
        else:
            return "I'm here to help with stories and fun facts! What would you like to explore?"

    def generate_vocabulary_question(self, word: str, context: str) -> Dict:
        """Generate vocabulary questions"""
        if self.client and self.api_key:
            try:
                prompt = f"""Create a multiple choice vocabulary question for the word "{word}" used in this context: "{context}"

Generate a question in this exact format:
- Question: What does the word **{word}** mean?
- Show the sentence where it was used
- 4 multiple choice answers (a, b, c, d) with one correct answer
- Make it appropriate for 2nd-3rd grade students

Return as JSON with: question, options (array of 4 strings), correctIndex (0-3)"""

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are creating vocabulary questions for elementary students. Always respond with valid JSON only."},
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
        """Fallback vocabulary questions"""
        vocab_questions = {
            "enormous": {
                "question": f'What does the word **enormous** mean?\n"{context}"',
                "options": ["a) very small", "b) very big", "c) very old", "d) very cold"],
                "correctIndex": 1
            },
            "investigate": {
                "question": f'What does the word **investigate** mean?\n"{context}"',
                "options": ["a) to ignore", "b) to find out about", "c) to run away", "d) to eat"],
                "correctIndex": 1
            },
            "discover": {
                "question": f'What does the word **discover** mean?\n"{context}"',
                "options": ["a) to lose something", "b) to hide something", "c) to find something new", "d) to break something"],
                "correctIndex": 2
            },
            "magnificent": {
                "question": f'What does the word **magnificent** mean?\n"{context}"',
                "options": ["a) very small", "b) very boring", "c) very beautiful", "d) very scary"],
                "correctIndex": 2
            },
            "ancient": {
                "question": f'What does the word **ancient** mean?\n"{context}"',
                "options": ["a) very new", "b) very old", "c) very fast", "d) very loud"],
                "correctIndex": 1
            },
            "gleaming": {
                "question": f'What does the word **gleaming** mean?\n"{context}"',
                "options": ["a) very dirty", "b) very shiny", "c) very broken", "d) very small"],
                "correctIndex": 1
            },
            "extraordinary": {
                "question": f'What does the word **extraordinary** mean?\n"{context}"',
                "options": ["a) very ordinary", "b) very boring", "c) very amazing", "d) very sad"],
                "correctIndex": 2
            },
            "enchanted": {
                "question": f'What does the word **enchanted** mean?\n"{context}"',
                "options": ["a) very scary", "b) very magical", "c) very dark", "d) very small"],
                "correctIndex": 1
            },
            "legendary": {
                "question": f'What does the word **legendary** mean?\n"{context}"',
                "options": ["a) very new", "b) very small", "c) very famous", "d) very quiet"],
                "correctIndex": 2
            },
            "massive": {
                "question": f'What does the word **massive** mean?\n"{context}"',
                "options": ["a) very tiny", "b) very huge", "c) very fast", "d) very quiet"],
                "correctIndex": 1
            },
            "communicate": {
                "question": f'What does the word **communicate** mean?\n"{context}"',
                "options": ["a) to be silent", "b) to talk or share", "c) to run away", "d) to eat food"],
                "correctIndex": 1
            }
        }
        
        return vocab_questions.get(word.lower(), {
            "question": f'What does the word **{word}** mean?\n"{context}"',
            "options": ["a) option 1", "b) option 2", "c) option 3", "d) option 4"],
            "correctIndex": 0
        })

    def extract_vocabulary_words(self, text: str) -> List[str]:
        """Extract vocabulary words from text (words between ** markers)"""
        import re
        words = re.findall(r'\*\*(.*?)\*\*', text)
        return words

    def provide_grammar_feedback(self, user_text: str) -> Optional[str]:
        """Provide grammar feedback"""
        if self.client and self.api_key:
            try:
                prompt = f"""As a friendly English tutor for elementary students, provide ONE brief grammar suggestion for this sentence if needed: "{user_text}"

If the grammar is correct, return "CORRECT".
If there's a suggestion, provide it in this format: "You could make that sentence even better by saying '[improved version]'. [Brief explanation]."

Keep it encouraging and simple for 2nd-3rd graders."""

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a friendly English tutor. Be encouraging and keep suggestions brief."},
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
        user_lower = user_text.lower()
        
        if user_lower.startswith("she find"):
            return "You could make that sentence even better by saying 'She discovers' or 'She finds'. The word 'discovers' sounds more exciting for an adventure story!"
        
        if "there" in user_lower and "alien" in user_lower:
            return "Nice addition! You could make that more descriptive by saying 'There was a strange alien' or 'A mysterious alien appeared'."
        
        if user_lower.startswith("he go"):
            return "You could make that sentence even better by saying 'He goes' or 'He went'. This makes the sentence sound more complete!"
        
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