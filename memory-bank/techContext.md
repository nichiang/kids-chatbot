# Technology Context - English Learning Chatbot

## Technology Stack

### Backend Technologies
- **Python 3.8+**: Core backend language
- **FastAPI**: Modern async web framework for API development
- **OpenAI GPT-4o-mini**: Large language model for educational content generation
- **Uvicorn**: ASGI server for FastAPI applications
- **Pydantic**: Data validation and serialization
- **Python-dotenv**: Environment variable management

### Frontend Technologies
- **Vanilla HTML5**: Semantic markup for accessibility
- **CSS3**: Modern styling with custom properties and responsive design
- **Vanilla JavaScript (ES6+)**: Interactive functionality without framework overhead
- **Web Speech API**: Speech-to-text input capability
- **CSS Grid & Flexbox**: Layout systems for responsive design

### Development Dependencies
From `backend/requirements.txt`:
```
fastapi==0.104.1
uvicorn==0.24.0
openai==1.3.8
python-dotenv==1.0.0
pydantic==2.5.0
```

## Architecture Decisions

### Why FastAPI + Vanilla JS
- **FastAPI**: Modern async framework, automatic API documentation, excellent type hints
- **Vanilla JS**: Zero build complexity, direct browser compatibility, educational simplicity
- **No Frontend Framework**: Maintains simplicity for educational focus, reduces complexity for contributors

### Why Single Server Architecture
- **Unified Development**: One server handles both API and static files
- **Simplified Deployment**: Single process, single port (8000)
- **Reduced Complexity**: No CORS issues, simplified environment setup

## Development Environment Setup

### Prerequisites
- Python 3.8 or higher
- OpenAI API key (optional - fallback responses available)

### Environment Configuration
Required environment variables in `backend/.env`:
```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Setup Commands
```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
cd backend
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env file and add your OpenAI API key

# 4. Start development server
uvicorn app:app --reload
```

### Development Workflow
1. **Start Server**: `uvicorn app:app --reload` from backend directory
2. **Access Application**: http://localhost:8000
3. **API Documentation**: http://localhost:8000/docs (automatic FastAPI docs)
4. **Health Check**: http://localhost:8000/health

## File Structure & Organization

### Backend Structure
```
backend/
├── app.py                      # Main FastAPI application
├── llm_provider.py            # OpenAI integration
├── vocabulary_manager.py       # Vocabulary system management
├── generate_prompt.py         # Prompt engineering utilities
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── vocabulary/               # Vocabulary data banks
│   ├── general.json          # Core 35 words
│   └── topics/               # Topic-specific vocabulary
└── prompt templates (*.txt)   # Educational prompt files
```

### Frontend Structure
```
frontend/
├── index.html                # Main application HTML
├── style.css                 # Complete styling system
├── app.js                    # Core application logic
├── character-config.js       # Avatar system configuration
└── assets/
    ├── characters/           # Theme-aware character avatars
    └── icons/                # UI icons (microphone, settings)
```

## API Architecture

### RESTful Endpoints
- **POST /chat**: Main educational interaction endpoint
- **GET /health**: System health check

### Request/Response Format
```typescript
// Chat Request
interface ChatRequest {
  message: string;
  mode: "storywriting" | "funfacts";
  sessionData: SessionData;
}

// Chat Response
interface ChatResponse {
  response: string;
  vocabQuestion?: VocabularyQuestion;
  sessionData: SessionData;
  suggestedTheme?: string;
}
```

### Session Data Structure
```python
class SessionData:
    topic: str = ""
    currentStep: int = 1
    storyParts: List[str] = []
    factsShown: int = 0
    askedVocabWords: List[str] = []
    contentVocabulary: List[str] = []
    vocabularyPhase: dict = {}
    # ... additional educational tracking fields
```

## Data Management

### Vocabulary Data Format (ENHANCED)
**JSON Structure** (vocabulary banks):
```json
{
  "vocabulary": [
    {
      "word": "coordination",
      "definition": "the ability to move your body parts together smoothly",
      "difficulty": 3,
      "type": "noun",
      "example": "Gymnasts need excellent coordination for their routines",
      "grade_level": "3-4"
    }
  ]
}
```

**Major Enhancement**: 
- **General Vocabulary**: Expanded from 35 → 100 words (50 tier 2 + 50 tier 3)
- **Selection Method**: Solution 3 provides 40 example words to LLM for intelligent curation
- **Variety Impact**: 1,233% increase in selection options eliminates vocabulary repetition

### Educational Content Files
- **System Prompts**: Plain text files defining AI personality and educational approach
- **Template Prompts**: Structured prompt templates for different educational scenarios
- **Base Instructions**: Guidelines for content generation and vocabulary integration

## Performance & Optimization

### Backend Optimization
- **Async Operations**: FastAPI async handlers for concurrent request processing
- **Memory Efficiency**: Vocabulary banks loaded once at startup
- **Response Caching**: Fallback responses cached for instant delivery
- **Minimal Dependencies**: Lean dependency list for fast startup

### Frontend Optimization
- **No Build Process**: Direct browser execution, zero build time
- **Vanilla JS**: Minimal JavaScript bundle size
- **CSS Custom Properties**: Efficient theme switching
- **Asset Optimization**: Compressed character images and icons

## Security Considerations

### API Security
- **Environment Variables**: Secrets stored in .env files (not committed)
- **Input Validation**: Pydantic models validate all incoming data
- **CORS Configuration**: Configured for local development

### Child Safety
- **Content Filtering**: All educational content reviewed for age-appropriateness
- **No User Data Storage**: Session data not persisted beyond conversation
- **Safe Content Generation**: Comprehensive fallbacks prevent inappropriate content

## Testing & Quality Assurance

### Development Testing
- **Manual Testing**: Interactive testing with target age group
- **Fallback Testing**: Comprehensive offline functionality verification
- **Cross-Browser Testing**: Verified across modern browsers
- **Educational Content Review**: All vocabulary reviewed for grade-level appropriateness

### Quality Metrics
- **Educational Standards**: Flesch-Kincaid 2nd-3rd grade reading level
- **Uptime**: 99.9% content delivery through fallback system
- **Response Time**: Sub-second response times for educational interactions

## Deployment Considerations

### Development Deployment
- **Single Server**: Unified FastAPI server for both API and frontend
- **Port Configuration**: Default port 8000 for all services
- **Environment Management**: .env files for configuration

### Production Readiness
- **Static File Serving**: FastAPI serves frontend files efficiently
- **Environment Variables**: Production secrets management
- **Process Management**: Single uvicorn process handles all requests

## Tool Usage Patterns

### OpenAI Integration
```python
# Configured for educational content
response = client.chat.completions.create(
    model="gpt-4o-mini",        # Optimized for educational content
    max_tokens=300,             # Perfect for story paragraphs/facts
    temperature=0.7             # Creative but controlled
)
```

### Vocabulary Management
```python
# Smart vocabulary selection
vocabulary_manager.select_vocabulary_word(
    topic="sports",
    excluded_words=session_data.askedVocabWords,
    difficulty_range=[2, 3]    # 2nd-3rd grade level
)
```

This technology stack prioritizes educational effectiveness, development simplicity, and reliable learning experiences for young students. The architecture supports rapid iteration while maintaining robust educational functionality.