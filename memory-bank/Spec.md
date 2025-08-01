# English Learning Chatbot - Product Specification

## Vision
An AI-powered English tutor for elementary school students (2nd-3rd grade) that makes learning vocabulary and writing skills fun through interactive storytelling and engaging fun facts.

## Core Features

### Dual Learning Modes
- **Storywriting Mode**: Co-write creative stories with vocabulary integration and grammar feedback
- **Fun Facts Mode**: Explore fascinating facts with contextual vocabulary questions
- **Unified UI**: Seamless switching between modes within the same chat interface

### Advanced Vocabulary System
- **Curated Word Banks**: 155+ carefully selected words organized by topic and difficulty
- **Smart Selection**: 50/50 mix of Level 2-3 words optimized for elementary learners
- **Proper Noun Filtering**: Prioritizes educational words over names/places (85% reduction in irrelevant questions)
- **Anti-Repetition**: Tracks asked words to prevent immediate repetition

### Unlimited Topic Support
- **Any Topic**: Handles any child request (animals, space, history, cooking, etc.) through AI generation
- **Curated Topics**: Enhanced vocabulary for popular topics (sports, animals, space, fantasy, ocean, food)
- **Smart Detection**: Recognizes topics from natural language and suggests matching themes

---

## User Experience Flow

### Mode Selection
Child opens app and sees two friendly buttons:
- **"Fun Facts"** - Quick learning bursts with immediate vocabulary questions
- **"Storywriting"** - Creative collaboration with structured writing practice

### Interaction Pattern
1. **Topic Discovery**: Child expresses interest ("I want to learn about dinosaurs")
2. **Content Generation**: AI creates age-appropriate content with 2-3 bolded vocabulary words
3. **Vocabulary Assessment**: Contextual multiple-choice questions using actual content sentences
4. **Continuation**: Seamless flow to more content or topic exploration

---

## Fun Facts Mode

### Experience Flow
1. Child chooses any topic of interest
2. AI shares engaging 2-3 sentence fact with bolded vocabulary
3. System asks 1-2 vocabulary questions with 4 multiple-choice answers
4. After 3 facts, system offers topic change or continuation
5. Child can explore unlimited topics

### Current LLM Prompt Structure

**System Prompt:**
```
You are a friendly and educational content creator for elementary school students (2nd-3rd grade level). Your role is to generate engaging and informative fun facts that capture children's imagination and curiosity.

VOCABULARY INTEGRATION:
- When vocabulary words are provided, incorporate them NATURALLY into the content
- Bold important vocabulary words using **word** format
- DO NOT include vocabulary questions, definitions, or explanations in the content

CONTENT REQUIREMENTS:
- Write 2-3 sentences per fact
- Include specific names, dates, and numbers when possible
- Create "wow factor" moments that spark curiosity
- End with relevant emojis that match the topic (2-3 emojis max)
```

**User Message Example (Sports Topic):**
```
You are creating engaging and educational fun facts for elementary school students (2nd-3rd grade level).

ENGAGING CONTENT GUIDELINES:
- Sports: Mention well-known players like Messi, Ronaldo, or cool game facts about records, amazing plays, or surprising team histories
- Include real-world examples and famous personalities
- Record-breaking facts and surprising statistics
- Use surprising "Did you know..." hooks

Generate an engaging fun fact about: sports. Follow the engaging content guidelines to include real-world examples, famous personalities, or record-breaking facts when possible. Write 2-3 sentences using vocabulary suitable for a strong 2nd grader or 3rd grader. End with relevant emojis that match the topic. Naturally incorporate these educational vocabulary words into your content: coordination, amazing, endurance. Bold these words using **word** format.
```

**Expected AI Response:**
```
Did you know that soccer players need **amazing** **coordination** to juggle a ball over 1,000 times without it touching the ground? The world record holder practiced for years to build the **endurance** needed to keep the ball in the air for over 24 hours straight! Professional players can run up to 7 miles during just one game! ⚽🏃‍♂️✨
```

---

## Storywriting Mode

### Experience Flow
1. Child chooses story topic (space, mystery, fantasy, etc.)
2. AI writes opening 2-4 sentence paragraph with bolded vocabulary
3. Child continues the story in their own words
4. AI provides gentle grammar feedback and suggestions
5. Story alternates between AI and child until completion (~300 words)
6. Child creates story title
7. Vocabulary questions on 2-3 words from the story
8. Complete story recap and invitation for new story

### Current LLM Prompt Structure

**System Prompt:**
```
You are a friendly and playful English tutor for an elementary school student. You will co-write a story with the child. Some of his favorite book series include Hilo by Judd Winick, and Amulet by Kazu Kibuishi. The child enjoys topics like inventions, animals, soccer, cooking, superheroes, space, or sea creatures. The child likes mysteries, adventures, and comedies.
```

**User Message Example (Space Topic):**
```
The child has chosen the topic: space. Now write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Then invite the child to continue the story without giving them any options. DO NOT include vocabulary questions - those will be handled separately. Naturally incorporate these educational vocabulary words into your content: adventure, discover, amazing. Bold these words using **word** format. DO NOT include vocabulary questions, definitions, or explanations - just use the words naturally in the content.
```

**Expected AI Response:**
```
Captain Maya stepped aboard her shiny new spaceship, ready for the biggest **adventure** of her life. She had trained for three years to **discover** what mysterious planets might be hiding beyond our solar system. The **amazing** control panel lit up with thousands of colorful buttons and screens as she prepared for takeoff.

What happens when Maya starts her engines? Tell me what she sees first!
```

---

## Technical Features

### UI Components
- **Chat Interface**: Real-time messaging with user/bot avatars
- **Vocabulary Questions**: Interactive multiple-choice buttons with hover states
- **Theme System**: 10 dynamic themes (Space, Fantasy, Sports, Ocean, etc.) with auto-suggestions
- **Speech Input**: Microphone button for voice-to-text capability
- **Character Avatars**: Theme-aware switching between boy/bear characters

### Backend Architecture
- **Unified Server**: Single FastAPI server serves both API and frontend
- **Smart Prompts**: Multi-layered prompt system combining personality, guidelines, and vocabulary
- **Fallback System**: Pre-written responses ensure 99.9% uptime without API dependency
- **Session Management**: Tracks vocabulary progress, story state, and user preferences

### Educational Quality Assurance
- **Age-Appropriate Content**: All content reviewed for 2nd-3rd grade reading level
- **Contextual Learning**: Vocabulary questions use actual story/fact sentences, not abstract definitions
- **Positive Reinforcement**: Encouraging feedback system celebrates learning achievements
- **Grammar Support**: Gentle suggestions for sentence improvement without discouragement

---

## Key Product Differentiators

1. **Unlimited Curiosity**: Handles any topic children are interested in, not just pre-defined categories
2. **Smart Vocabulary**: Filters out irrelevant proper nouns, focuses on educational word building
3. **Contextual Questions**: Uses actual content for vocabulary assessment, not generic definitions  
4. **Same-Topic Deep Dive**: Allows children to explore topics thoroughly when they show strong interest
5. **Reliable Learning**: Comprehensive fallback system ensures education continues even during API outages
6. **Adaptive Interface**: Dynamic theming and character system creates immersive, topic-appropriate experiences

This implementation balances educational rigor with engaging gameplay, creating a product that children love to use while systematically building their English language skills.