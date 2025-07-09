# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Start development server
uvicorn app:app --reload
```

### Frontend
The frontend is static HTML/CSS/JS that runs directly in the browser. Open `frontend/index.html` in a web browser.

### Testing the Full Application
1. Start backend server: `uvicorn app:app --reload` (from backend directory)
2. Open `frontend/index.html` in browser
3. Backend runs on http://localhost:8000

## Project Architecture

### Backend Structure
- **FastAPI Application**: `backend/app.py` - Main FastAPI server with CORS middleware and `/chat` endpoint
- **Prompt Generation**: `backend/generate_prompt.py` - Builds complete prompts by combining:
  - `intro_prompt.txt` - System role defining friendly English tutor persona
  - `vocab.csv` - Vocabulary words for 2nd/3rd graders
  - `story_steps_prompt.txt` - 10-step story co-writing and vocabulary quiz process
- **LLM Integration**: `backend/llm_provider.py` - Currently empty, intended for LLM API integration
- **Current State**: `/chat` endpoint returns echo responses; LLM integration not yet implemented

### Frontend Structure
- **Static Web App**: Pure HTML/CSS/JS with no build process
- **Hardcoded Story Flow**: `frontend/app.js` contains predefined story segments and vocabulary questions
- **Space Theme UI**: `frontend/style.css` implements space-themed design with progress bar
- **Chat Interface**: Real-time chat UI with user/bot avatars and message bubbles
- **Vocabulary Quiz**: Interactive multiple choice questions with immediate feedback

### Key Educational Flow
1. Story co-writing with vocabulary integration
2. Grammar correction and vocabulary suggestions
3. Vocabulary comprehension questions with multiple choice answers
4. Complete story recap and invitation to write another story

### Data Files
- `intro_prompt.txt` - Character definition for friendly English tutor
- `story_steps_prompt.txt` - Detailed 10-step instruction process
- `vocab.csv` - Single row of comma-separated vocabulary words for elementary students

## Development Notes

### Current Implementation Status
- Backend has basic FastAPI structure but no LLM integration
- Frontend has hardcoded story flow instead of dynamic LLM responses
- No test framework or linting configuration present
- No package.json or build tools - frontend is vanilla HTML/CSS/JS

### Integration Points
- `/chat` endpoint expects `ChatRequest` with `message` field
- Returns `ChatResponse` with `response` field
- Frontend makes POST requests to backend `/chat` endpoint
- CORS configured for local development

### Prompt Engineering
The `generate_prompt()` function in `backend/generate_prompt.py` combines three components:
1. System role from `intro_prompt.txt`
2. Vocabulary list from `vocab.csv`
3. Step-by-step instructions from `story_steps_prompt.txt`

This creates a comprehensive prompt for LLM integration targeting 2nd/3rd grade English learning through interactive storytelling.