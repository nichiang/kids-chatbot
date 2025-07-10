from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
from llm_provider import llm_provider
from generate_prompt import generate_prompt, load_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Allow frontend to call backend locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class SessionData(BaseModel):
    topic: Optional[str] = None
    storyParts: List[str] = []
    currentStep: int = 0
    isComplete: bool = False
    factsShown: int = 0
    currentFact: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    mode: str = "storywriting"  # "storywriting" or "funfacts"
    sessionData: Optional[SessionData] = None

class VocabQuestion(BaseModel):
    question: str
    options: List[str]
    correctIndex: int

class ChatResponse(BaseModel):
    response: str
    vocabQuestion: Optional[VocabQuestion] = None
    sessionData: Optional[SessionData] = None

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest):
    try:
        user_message = chat_request.message
        mode = chat_request.mode
        session_data = chat_request.sessionData or SessionData()
        
        logger.info(f"Processing {mode} message: {user_message}")
        
        if mode == "storywriting":
            return await handle_storywriting(user_message, session_data)
        elif mode == "funfacts":
            return await handle_funfacts(user_message, session_data)
        else:
            return ChatResponse(response="I'm not sure what mode that is! Try storywriting or fun facts.")
            
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return ChatResponse(response="Sorry, I'm having trouble right now. Please try again!")

async def handle_storywriting(user_message: str, session_data: SessionData) -> ChatResponse:
    """Handle storywriting mode interactions following the 10-step process"""
    
    # If no topic is set, user is choosing a topic (Step 1)
    if not session_data.topic:
        # Extract topic from user message
        topic = extract_topic_from_message(user_message)
        session_data.topic = topic
        session_data.currentStep = 2  # Moving to Step 2 after topic selection
        
        # Generate story beginning following Steps 2-4
        story_prompt = f"The child has chosen the topic: {topic}. Now write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words. Then invite the child to continue the story without giving them any options."
        story_response = llm_provider.generate_response(story_prompt)
        session_data.storyParts.append(story_response)
        
        return ChatResponse(
            response=story_response,
            sessionData=session_data
        )
    
    # Story is in progress (Steps 5-6)
    else:
        # Add user's contribution to story
        session_data.storyParts.append(f"User: {user_message}")
        
        # Provide grammar feedback if needed (Step 5)
        grammar_feedback = llm_provider.provide_grammar_feedback(user_message)
        
        # Generate next part of story (Steps 2-4 repeated)
        story_context = "\n".join(session_data.storyParts[-3:])  # Last 3 parts for context
        
        # Check if story should end (after 4 exchanges)
        if session_data.currentStep >= 4:
            # End the story (Step 7)
            story_prompt = f"End the story about {session_data.topic}. Previous context: {story_context}. Write a final paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words. End the story with a satisfying conclusion - do not ask the child to continue."
            story_response = llm_provider.generate_response(story_prompt)
            
            # Add grammar feedback if available
            if grammar_feedback:
                story_response = grammar_feedback + "\n\n" + story_response
            
            session_data.storyParts.append(story_response)
            session_data.isComplete = True
            
            # Start vocabulary questions (Step 8)
            vocab_words = llm_provider.extract_vocabulary_words(story_response)
            vocab_question = None
            if vocab_words:
                vocab_word = vocab_words[0]  # Use first vocabulary word
                vocab_question = llm_provider.generate_vocabulary_question(vocab_word, story_response)
            
            return ChatResponse(
                response=story_response,
                vocabQuestion=VocabQuestion(**vocab_question) if vocab_question else None,
                sessionData=session_data
            )
        else:
            # Continue story (Steps 2-4 repeated)
            story_prompt = f"Continue the story about {session_data.topic}. Previous context: {story_context}. Write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words. Then invite the child to continue the story without giving them any options. Keep this a short story - try to end it before it goes over 300 words total."
            story_response = llm_provider.generate_response(story_prompt)
            
            # Add grammar feedback if available
            if grammar_feedback:
                story_response = grammar_feedback + "\n\n" + story_response
            
            session_data.storyParts.append(story_response)
            session_data.currentStep += 1
            
            return ChatResponse(
                response=story_response,
                sessionData=session_data
            )

async def handle_funfacts(user_message: str, session_data: SessionData) -> ChatResponse:
    """Handle fun facts mode interactions"""
    
    # If no topic is set, user is choosing a topic
    if not session_data.topic:
        # Extract topic from user message
        topic = extract_topic_from_message(user_message)
        session_data.topic = topic
        session_data.factsShown = 0
        
        # Generate first fact
        fact_prompt = f"Generate a fun fact about: {topic}. Write 2-3 sentences using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words using **word** format. End with relevant emojis that match the topic."
        fact_response = llm_provider.generate_response(fact_prompt)
        session_data.currentFact = fact_response
        session_data.factsShown += 1
        
        # Generate vocabulary question
        vocab_words = llm_provider.extract_vocabulary_words(fact_response)
        vocab_question = None
        if vocab_words:
            vocab_word = vocab_words[0]  # Use first vocabulary word
            vocab_question = llm_provider.generate_vocabulary_question(vocab_word, fact_response)
        
        return ChatResponse(
            response=fact_response,
            vocabQuestion=VocabQuestion(**vocab_question) if vocab_question else None,
            sessionData=session_data
        )
    
    # Topic is set, continue with more facts
    else:
        if session_data.factsShown < 3:  # Show 3 facts per topic
            # Generate another fact
            fact_prompt = f"Generate a different fun fact about: {session_data.topic}. Write 2-3 sentences using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words using **word** format. End with relevant emojis that match the topic."
            fact_response = llm_provider.generate_response(fact_prompt)
            session_data.currentFact = fact_response
            session_data.factsShown += 1
            
            # Generate vocabulary question
            vocab_words = llm_provider.extract_vocabulary_words(fact_response)
            vocab_question = None
            if vocab_words:
                vocab_word = vocab_words[0]
                vocab_question = llm_provider.generate_vocabulary_question(vocab_word, fact_response)
            
            return ChatResponse(
                response=fact_response,
                vocabQuestion=VocabQuestion(**vocab_question) if vocab_question else None,
                sessionData=session_data
            )
        else:
            # Ask if they want to switch topics
            return ChatResponse(
                response=f"We've explored some great {session_data.topic} facts! Would you like to learn about a different topic? Try animals, space, inventions, or something else!",
                sessionData=session_data
            )

def extract_topic_from_message(message: str) -> str:
    """Extract topic from user message"""
    message_lower = message.lower()
    
    # Topic mapping
    topic_keywords = {
        "space": ["space", "planet", "star", "rocket", "astronaut", "jupiter", "mars", "galaxy", "alien"],
        "animals": ["animal", "dog", "cat", "elephant", "lion", "whale", "bird", "creature"],
        "inventions": ["invention", "science", "technology", "robot", "computer"],
        "sports": ["sport", "soccer", "football", "basketball", "tennis", "baseball"],
        "food": ["food", "cooking", "eat", "pizza", "ice cream", "fruit"],
        "ocean": ["ocean", "sea", "fish", "shark", "whale", "coral", "water"],
        "fantasy": ["fantasy", "magic", "magical", "dragon", "unicorn", "wizard", "fairy", "enchanted", "mystical"],
        "mystery": ["mystery", "detective", "clue", "solve", "secret", "hidden"],
        "adventure": ["adventure", "explore", "journey", "quest", "travel"]
    }
    
    for topic, keywords in topic_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            return topic
    
    # Default topic extraction - use first word that looks like a topic
    words = message.split()
    return words[0] if words else "adventure"

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "English Learning Chatbot API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)