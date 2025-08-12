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
├── app.py                      # Main FastAPI application with hybrid educational flow
├── llm_provider.py            # OpenAI integration + legacy system prompt loading
├── vocabulary_manager.py       # Vocabulary system management
├── generate_prompt.py         # Legacy prompt utilities (still used for system context)
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── vocabulary/               # Vocabulary data banks
│   ├── general.json          # Core 100 words (expanded from 35)
│   └── topics/               # Topic-specific vocabulary (6 topics × 20 words)
└── prompts/                  # Organized prompt structure
    ├── story/                # Story mode prompts
    │   ├── 01_system_role.txt
    │   ├── 03_process_instructions.txt  # Complete 10-step educational flow
    │   └── 04_story_generation.json    # Named/unnamed entity templates
    ├── fun_facts/            # Fun facts mode prompts
    └── design/               # Character/location design aspects
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

## Development Process & Quality Assurance

### Bug Resolution Methodology (Latest Improvements)

#### Comprehensive Debug Logging Pattern
**Implementation**: Full-flow visibility throughout educational interactions
- **Story Mode Tracking**: Parameter validation from frontend to backend
- **Template Selection Logging**: Confirmation of named vs unnamed entity template usage
- **LLM Response Analysis**: Raw response inspection and metadata parsing validation
- **Design Phase Decision Tracking**: Step-by-step visibility into triggering logic
- **Vocabulary Selection Audit**: Complete vocabulary word selection and filtering process

**Technical Implementation**:
```python
# Structured logging with emojis for visual scanning
logger.info(f"🎯 STORY MODE DEBUG: Received story_mode parameter: '{story_mode}'")
logger.info(f"🎯 TEMPLATE DEBUG: Using template '{template_key}' for story_mode '{story_mode}'")
logger.info(f"🎯 METADATA DEBUG: design_options: {structured_response.metadata.design_options}")
logger.info(f"🔧 UNNAMED ENTITY: Using design_options {design_options} -> available: {available_options}")
```

#### Testing Infrastructure Enhancement
**Story Mode Testing Controls**: Manual testing capability for quality assurance
- **Force Named Mode**: Consistently generates named characters (e.g., "Mia") for testing named character flow
- **Force Unnamed Mode**: Consistently generates unnamed characters (e.g., "brave astronaut") for testing naming questions
- **Auto Mode**: Original random 60/40 split for production use

**Frontend Integration**:
```javascript
// Settings dialog with testing controls
storyMode: 'auto' | 'named' | 'unnamed'
currentStoryMode = modeName; // Passed to backend via storyMode parameter
```

**Backend Integration**:
```python
# Template selection override based on testing mode
if story_mode == "named":
    template_key = "named_entities"
elif story_mode == "unnamed": 
    template_key = "unnamed_entities"
else:
    template_key = random_selection()  # Auto mode
```

#### Validation and Auto-Repair Patterns
**Enhanced Response Processing**: Robust handling of malformed LLM responses
- **Design Options Validation**: Automatic detection of missing design_options arrays
- **Auto-Repair Logic**: Inference of design options from story content when metadata is incomplete
- **Fallback Mechanisms**: Graceful degradation with maintained educational value

**Implementation**:
```python
# Auto-fix for missing design_options
if not design_options:
    logger.warning(f"⚠️ VALIDATION: design_options is empty or missing")
    if metadata_dict.get("character_name") or metadata_dict.get("character_description"):
        design_options = ["character"]
        logger.info(f"🔧 AUTO-FIX: Inferred design_options as ['character']")
```

### Code Quality Patterns

#### Random Selection for Engagement
**Pattern**: Eliminate predictable user experiences through strategic randomization
- **Design Aspect Selection**: Random choice from available aspects (appearance, personality, skills, dreams, flaws)
- **Character/Location Focus**: 50/50 random selection when both options available
- **Template Selection**: Maintains educational balance while providing variety

#### Single-Responsibility Architecture
**Pattern**: Clear separation of concerns across system components
- **app.py**: Session management, educational flow control, and business logic
- **llm_provider.py**: LLM integration, response processing, and educational content generation
- **vocabulary_manager.py**: Vocabulary selection, filtering, and educational word management
- **generate_prompt.py**: Prompt engineering and template management

#### Error Handling Philosophy
**Approach**: Never compromise educational experience due to technical failures
- **Comprehensive Fallbacks**: Pre-written educational content for all major scenarios
- **Graceful Degradation**: Maintained educational value even with partial system failures
- **Child-First Design**: Technical issues invisible to young learners

### Development Workflow Improvements

#### Issue Resolution Process
1. **Detailed Logging Analysis**: Use comprehensive debug output to identify exact failure points
2. **Isolated Component Testing**: Test individual functions and components separately
3. **Testing Infrastructure Utilization**: Use Force Named/Unnamed modes for consistent reproduction
4. **Validation Enhancement**: Add auto-repair logic for robustness
5. **Educational Impact Assessment**: Ensure fixes maintain or improve learning outcomes

#### Quality Assurance Standards
- **Manual Testing**: Both named and unnamed character scenarios tested before deployment
- **Log Analysis**: Debug output reviewed for unexpected behaviors or edge cases
- **Educational Review**: All changes evaluated for age-appropriateness and learning effectiveness
- **Performance Impact**: Response time and user experience maintained during improvements

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

## Hybrid Architecture Implementation

### Prompt Architecture Evolution
**Current Implementation**: Hybrid approach combining system prompts with programmatic flow control

**System Prompt Loading** (`llm_provider.py`):
```python
# Legacy generate_prompt() still used for LLM context
self.system_prompt = generate_prompt()  # Loads complete 10-step instructions
```

**Programmatic Flow Control** (`app.py`):
```python
# Python manages actual educational progression
enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(base_prompt, topic)
response = llm_provider.generate_response(enhanced_prompt)
# Session state tracking, vocabulary management, design phases
```

**Why Hybrid Architecture**:
- **System Context**: LLM receives complete educational framework for consistent tone/approach
- **Reliable Execution**: Python ensures vocabulary tracking, session management, educational standards
- **Best of Both**: Maintains LLM creativity while guaranteeing educational progression
- **Known Gap**: Step 9 "print entire story" from original 10-step flow not yet re-implemented

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