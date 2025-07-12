document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatLog = document.getElementById("chat-log");
    const storywritingBtn = document.getElementById("storywriting-btn");
    const funFactsBtn = document.getElementById("fun-facts-btn");

    // App state
    let currentMode = 'funfacts'; // 'storywriting' or 'funfacts'
    let sessionData = {
        storywriting: {
            topic: null,
            storyParts: [],
            currentStep: 0,
            isComplete: false
        },
        funfacts: {
            topic: null,
            factsShown: 0,
            currentFact: null,
            isComplete: false
        }
    };

    // Mode switching
    function switchMode(mode) {
        currentMode = mode;
        
        // Update button states
        storywritingBtn.classList.toggle('active', mode === 'storywriting');
        funFactsBtn.classList.toggle('active', mode === 'funfacts');
        
        // Clear chat log
        chatLog.innerHTML = '';
        
        // No automatic theme switching when changing modes
        // Theme is now manually controlled by user
        
        // Initialize the selected mode
        if (mode === 'storywriting') {
            initializeStorywriting();
        } else {
            initializeFunFacts();
        }
    }

    // Initialize Storywriting mode
    function initializeStorywriting() {
        if (!sessionData.storywriting.topic) {
            appendMessage("bot", "Hi there! I'm excited to co-write a story with you! 📚✨\n\nWhat kind of story would you like to write today? Here are some fun options:\n\n🚀 Space adventures\n🏰 Fantasy quests\n⚽ Sports excitement\n🦄 Magical creatures\n🕵️ Mystery solving\n\nWhat sounds interesting to you?");
        } else {
            // Continue existing story
            appendMessage("bot", "Let's continue our story! What happens next?");
        }
    }

    // Initialize Fun Facts mode
    function initializeFunFacts() {
        if (!sessionData.funfacts.topic) {
            appendMessage("bot", "Hey explorer! I have so many amazing facts to share! 🤓✨\n\nWhat topic would you like to learn about today?\n\n🐾 Animals\n🌌 Space\n🔬 Science inventions\n🏈 Sports\n🍕 Food\n🌊 Ocean creatures\n\nPick something that sounds cool to you!");
        } else {
            // Continue with more facts
            appendMessage("bot", "Ready for another awesome fact? Let me know when you are!");
        }
    }

    // Smart auto-scroll function - only scrolls when content goes below viewport
    function scrollToBottom() {
        requestAnimationFrame(() => {
            // Check if content actually extends beyond the viewport
            const windowHeight = window.innerHeight;
            const documentHeight = document.body.scrollHeight;
            const currentScrollPosition = window.scrollY;
            
            // Only scroll if:
            // 1. Document is taller than viewport AND
            // 2. User is not already at the bottom (within 100px tolerance)
            const isContentBelowFold = documentHeight > windowHeight;
            const isNearBottom = (currentScrollPosition + windowHeight) >= (documentHeight - 100);
            
            if (isContentBelowFold && !isNearBottom) {
                // Content extends beyond viewport and user is not at bottom - scroll smoothly
                window.scrollTo({
                    top: documentHeight,
                    behavior: 'smooth'
                });
                
                // Fallback for older browsers
                setTimeout(() => {
                    window.scrollTo(0, document.body.scrollHeight);
                }, 150);
            }
            // If content fits in viewport or user is already at bottom, don't scroll
        });
    }

    // Split long messages into multiple bubbles
    function splitLongMessage(text) {
        // Split at double line breaks first (natural paragraph breaks)
        const paragraphs = text.split('\n\n');
        const maxLength = 200; // Maximum characters per bubble
        const result = [];
        
        paragraphs.forEach(paragraph => {
            if (paragraph.length <= maxLength) {
                result.push(paragraph);
            } else {
                // Split long paragraphs at sentence boundaries
                const sentences = paragraph.split(/(?<=[.!?])\s+/);
                let currentChunk = '';
                
                sentences.forEach(sentence => {
                    if (currentChunk.length + sentence.length <= maxLength) {
                        currentChunk += (currentChunk ? ' ' : '') + sentence;
                    } else {
                        if (currentChunk) result.push(currentChunk);
                        currentChunk = sentence;
                    }
                });
                
                if (currentChunk) result.push(currentChunk);
            }
        });
        
        return result.filter(chunk => chunk.trim().length > 0);
    }

    // Message handling with smart splitting for long messages
    function appendMessage(sender, text) {
        if (sender === "bot" && text.length > 200) {
            // Split long bot messages into multiple bubbles
            const messageParts = splitLongMessage(text);
            messageParts.forEach((part, index) => {
                setTimeout(() => {
                    appendSingleMessage(sender, part);
                }, index * 800); // 800ms delay between message parts
            });
        } else {
            // Send short messages normally
            appendSingleMessage(sender, text);
        }
    }

    // Single message handling
    function appendSingleMessage(sender, text) {
        const msgWrapper = document.createElement("div");
        msgWrapper.className = sender === "user" ? "chat-message user" : "chat-message bot";

        const avatar = document.createElement("div");
        avatar.className = "chat-avatar";
        if (sender === "user") {
            setupCharacterAvatar(avatar, "boy", currentTheme);
        } else {
            setupCharacterAvatar(avatar, "bear", currentTheme);
        }

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        
        // Replace **word** with colored spans for vocabulary highlighting
        const processedText = text.replace(/\*\*(.*?)\*\*/g, '<span class="vocab-word">$1</span>');
        bubble.innerHTML = processedText;

        msgWrapper.appendChild(avatar);
        msgWrapper.appendChild(bubble);

        chatLog.appendChild(msgWrapper);
        
        // Scroll to bottom after avatar is set up
        scrollToBottom();
    }

    // Create vocabulary question UI
    function appendVocabQuestion(question, options, correctIndex) {
        const vocabContainer = document.createElement("div");
        vocabContainer.className = "vocab-question-container";

        // Question bubble
        const questionWrapper = document.createElement("div");
        questionWrapper.className = "chat-message bot";

        const avatar = document.createElement("div");
        avatar.className = "chat-avatar";
        setupCharacterAvatar(avatar, "bear", currentTheme);

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        
        // Replace **word** with colored spans for vocabulary highlighting
        const processedQuestion = question.replace(/\*\*(.*?)\*\*/g, '<span class="vocab-word">$1</span>');
        bubble.innerHTML = processedQuestion;

        questionWrapper.appendChild(avatar);
        questionWrapper.appendChild(bubble);

        // Answer buttons
        const answersWrapper = document.createElement("div");
        answersWrapper.className = "vocab-answers-wrapper";

        const kidAvatar = document.createElement("div");
        kidAvatar.className = "kid-avatar";
        setupCharacterAvatar(kidAvatar, "boy", currentTheme);

        const buttonsContainer = document.createElement("div");
        buttonsContainer.className = "answer-buttons-container";

        options.forEach((option, index) => {
            const button = document.createElement("button");
            button.className = "answer-button";
            button.textContent = option;
            button.addEventListener("click", () => {
                handleVocabAnswer(index, correctIndex, option, buttonsContainer, vocabContainer);
            });
            buttonsContainer.appendChild(button);
        });

        answersWrapper.appendChild(buttonsContainer);
        answersWrapper.appendChild(kidAvatar);

        vocabContainer.appendChild(questionWrapper);
        vocabContainer.appendChild(answersWrapper);

        chatLog.appendChild(vocabContainer);
        
        // Scroll to bottom after avatars are set up
        scrollToBottom();
    }

    // Handle vocabulary answer
    function handleVocabAnswer(selectedIndex, correctIndex, selectedOption, buttonsContainer, vocabContainer) {
        // Disable all buttons
        Array.from(buttonsContainer.children).forEach(btn => btn.disabled = true);

        // Highlight selected button and maintain its styling
        const selectedButton = buttonsContainer.children[selectedIndex];
        selectedButton.classList.add("selected");

        // Add checkmark to correct answer
        const correctButton = buttonsContainer.children[correctIndex];
        if (selectedIndex === correctIndex) {
            // User selected correct answer - keep purple selected style
            const checkmark = document.createElement("span");
            checkmark.className = "checkmark";
            checkmark.textContent = "✔";
            selectedButton.appendChild(checkmark);
        } else {
            // User selected wrong answer - show correct answer in green
            const checkmark = document.createElement("span");
            checkmark.className = "checkmark";
            checkmark.textContent = "✔";
            correctButton.appendChild(checkmark);
            correctButton.classList.add("correct");
        }

        // Show user's selection
        appendMessage("user", selectedOption);

        // Show feedback
        const feedback = selectedIndex === correctIndex 
            ? "Correct! Great job! 🎉" 
            : `Nice try! The correct answer was ${buttonsContainer.children[correctIndex].textContent}. You'll get it next time! 💪`;
        
        appendMessage("bot", feedback);

        // Keep vocab container visible (don't remove it)

        // Continue flow automatically after vocabulary answer
        setTimeout(() => {
            if (currentMode === 'funfacts') {
                continueAfterVocab();
            } else if (currentMode === 'storywriting') {
                // Send continue signal to check for more vocab or story completion
                sendContinueSignal();
            }
        }, 2000);
    }

    // Trigger vocabulary questions after story completion
    async function triggerVocabularyQuestions() {
        try {
            console.log("Sending vocab trigger request...");
            
            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: "start vocabulary", // Trigger vocabulary questions
                    mode: currentMode,
                    sessionData: sessionData[currentMode]
                })
            });

            const data = await response.json();
            
            // Handle response
            if (data.response) {
                appendMessage("bot", data.response);
            }
            
            // Update session data
            if (data.sessionData) {
                sessionData[currentMode] = data.sessionData;
            }
            
            // Theme switching now happens during "Thinking..." phase to prevent jarring UX
            // No longer handling backend theme suggestions here
            
            // Handle vocabulary questions
            if (data.vocabQuestion) {
                setTimeout(() => {
                    appendVocabQuestion(
                        data.vocabQuestion.question,
                        data.vocabQuestion.options,
                        data.vocabQuestion.correctIndex
                    );
                }, 1000);
            }

        } catch (err) {
            console.error("Error triggering vocabulary questions:", err);
            appendMessage("bot", "Let's move on to some vocabulary questions!");
        }
    }

    // Continue storywriting flow after vocabulary question
    async function sendContinueSignal() {
        try {
            // Send continue request to backend to check for more vocab or completion
            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: "continue", // Signal to continue
                    mode: currentMode,
                    sessionData: sessionData[currentMode]
                })
            });

            const data = await response.json();
            
            // Handle response
            if (data.response) {
                appendMessage("bot", data.response);
            }
            
            // Update session data
            if (data.sessionData) {
                sessionData[currentMode] = data.sessionData;
            }
            
            // Handle vocabulary questions
            if (data.vocabQuestion) {
                setTimeout(() => {
                    appendVocabQuestion(
                        data.vocabQuestion.question,
                        data.vocabQuestion.options,
                        data.vocabQuestion.correctIndex
                    );
                }, 1000);
            }

        } catch (err) {
            console.error("Error sending continue signal:", err);
            appendMessage("bot", "Let me check what comes next...");
        }
    }

    // Continue fun facts flow after vocabulary question
    async function continueAfterVocab() {
        try {
            // Show thinking message
            appendMessage("bot", "Let me share another cool fact...");

            // Send continue request to backend
            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: "continue", // Signal to continue
                    mode: currentMode,
                    sessionData: sessionData[currentMode]
                })
            });

            const data = await response.json();
            
            // Remove thinking message
            chatLog.removeChild(chatLog.lastChild);
            
            // Handle response
            if (data.response) {
                appendMessage("bot", data.response);
            }
            
            // Update session data
            if (data.sessionData) {
                sessionData[currentMode] = data.sessionData;
            }
            
            // Theme switching now happens during "Thinking..." phase to prevent jarring UX
            // No longer handling backend theme suggestions here
            
            // Handle vocabulary questions
            if (data.vocabQuestion) {
                // Only show vocabulary questions when appropriate:
                // - In fun facts mode: always show them
                // - In storywriting mode: only show when story is complete
                const shouldShowVocabQuestion = 
                    currentMode === 'funfacts' || 
                    (currentMode === 'storywriting' && data.sessionData && data.sessionData.isComplete);
                
                console.log(`Vocab question received. Mode: ${currentMode}, Story complete: ${data.sessionData?.isComplete}, Should show: ${shouldShowVocabQuestion}`);
                
                if (shouldShowVocabQuestion) {
                    setTimeout(() => {
                        appendVocabQuestion(
                            data.vocabQuestion.question,
                            data.vocabQuestion.options,
                            data.vocabQuestion.correctIndex
                        );
                    }, 1000);
                } else {
                    console.log("Vocab question suppressed - story not complete yet");
                }
            }

        } catch (err) {
            // Remove thinking message if it exists
            if (chatLog.lastChild && chatLog.lastChild.textContent.includes("thinking")) {
                chatLog.removeChild(chatLog.lastChild);
            }
            appendMessage("bot", "Sorry, I'm having trouble continuing right now. Please try again!");
        }
    }

    // Handle form submission
    chatForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const userMessage = chatInput.value.trim();
        if (!userMessage) return;

        appendMessage("user", userMessage);
        chatInput.value = "";

        // Show thinking message
        appendMessage("bot", "Thinking...");

        // Check for topic in user message and switch theme immediately (before backend response)
        // This prevents jarring simultaneous theme change + content scroll
        const detectedTopic = extractTopicFromMessage(userMessage);
        if (detectedTopic) {
            const suggestedTheme = getThemeSuggestion(detectedTopic);
            if (suggestedTheme !== currentTheme) {
                console.log(`Client-side topic "${detectedTopic}" detected, switching to ${suggestedTheme} theme during thinking phase`);
                switchTheme(suggestedTheme, true, 'topic'); // Mark as automatic topic-based switch
            }
        }

        try {
            // Send to backend
            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: userMessage,
                    mode: currentMode,
                    sessionData: sessionData[currentMode]
                })
            });

            const data = await response.json();
            
            // Remove thinking message
            chatLog.removeChild(chatLog.lastChild);
            
            // Handle response based on mode
            if (data.response) {
                appendMessage("bot", data.response);
            }
            
            // Update session data with backend response
            if (data.sessionData) {
                sessionData[currentMode] = data.sessionData;
                
                // Auto-trigger vocabulary questions when story is complete
                if (currentMode === 'storywriting' && data.sessionData.isComplete && !data.vocabQuestion) {
                    console.log("Story completed! Auto-triggering vocabulary questions...");
                    // Wait a bit for user to read "The end!" then trigger vocab
                    setTimeout(() => {
                        triggerVocabularyQuestions();
                    }, 2000);
                }
            }
            
            // Theme switching now happens during "Thinking..." phase to prevent jarring UX
            // No longer handling backend theme suggestions here
            
            // Handle vocabulary questions
            if (data.vocabQuestion) {
                // Only show vocabulary questions when appropriate:
                // - In fun facts mode: always show them
                // - In storywriting mode: only show when story is complete
                const shouldShowVocabQuestion = 
                    currentMode === 'funfacts' || 
                    (currentMode === 'storywriting' && data.sessionData && data.sessionData.isComplete);
                
                console.log(`Vocab question received. Mode: ${currentMode}, Story complete: ${data.sessionData?.isComplete}, Should show: ${shouldShowVocabQuestion}`);
                
                if (shouldShowVocabQuestion) {
                    setTimeout(() => {
                        appendVocabQuestion(
                            data.vocabQuestion.question,
                            data.vocabQuestion.options,
                            data.vocabQuestion.correctIndex
                        );
                    }, 1000);
                } else {
                    console.log("Vocab question suppressed - story not complete yet");
                }
            }

        } catch (err) {
            // Remove thinking message
            chatLog.removeChild(chatLog.lastChild);
            appendMessage("bot", "Sorry, I'm having trouble connecting right now. Please try again!");
        }
    });

    // Event listeners for mode buttons
    storywritingBtn.addEventListener("click", () => switchMode('storywriting'));
    funFactsBtn.addEventListener("click", () => switchMode('funfacts'));

    const body = document.body;

    // Character Avatar System with Individual Images
    function setupCharacterAvatar(avatarElement, characterType, theme) {
        // Use the character config system for easy image swapping
        const characterImage = getCharacterImage(characterType, theme);
        avatarElement.style.backgroundImage = `url('${characterImage}')`;
        
        // Set alt text for accessibility
        avatarElement.setAttribute('role', 'img');
        avatarElement.setAttribute('aria-label', characterType === "bear" ? "Bear Tutor" : "Kid");
    }

    // Unified Theme System
    let currentTheme = 'theme-space'; // Default theme
    let userManuallySelectedTheme = false; // Track if user manually chose a theme

    function switchTheme(themeName, isAutomatic = false, reason = 'manual') {
        // Only switch if it's actually a different theme
        if (currentTheme === themeName) return;
        
        // Smart auto-switching logic
        if (isAutomatic) {
            if (reason === 'topic') {
                // Always allow topic-based theme switching (when user chooses story topics)
                console.log(`Auto-switching to ${themeName} for topic selection - overriding manual preference`);
            } else if (userManuallySelectedTheme && localStorage.getItem('userSelectedTheme')) {
                // Block other automatic switching if user has manual preference
                console.log(`Auto-switch to ${themeName} skipped - user has manual preference (userManuallySelectedTheme: ${userManuallySelectedTheme}, localStorage: ${localStorage.getItem('userSelectedTheme')})`);
                return;
            }
        }
        
        // Remove all existing theme classes
        body.classList.remove('theme-space', 'theme-fantasy', 'theme-sports', 'theme-ocean', 'theme-whimsical', 'theme-fun', 'theme-food', 'theme-animals', 'theme-elegant', 'theme-creative');
        
        // Add new theme class
        body.classList.add(themeName);
        
        // Update theme button states
        updateThemeButtonStates(themeName);
        
        // Update all existing avatars to match the new theme
        updateAllAvatars(themeName);
        
        currentTheme = themeName;
        
        if (isAutomatic) {
            console.log(`Auto-switched to ${themeName} theme`);
        } else {
            console.log(`Manually switched to ${themeName} theme`);
            userManuallySelectedTheme = true;
            localStorage.setItem('userSelectedTheme', 'true');
            localStorage.setItem('preferredTheme', themeName);
        }
    }

    function updateThemeButtonStates(activeTheme) {
        // Remove active class from all theme buttons
        const themeButtons = document.querySelectorAll('.theme-btn');
        themeButtons.forEach(button => {
            button.classList.remove('active');
        });
        
        // Add active class to the current theme button
        const activeButton = document.querySelector(`.theme-btn[data-theme="${activeTheme}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
    }

    function updateAllAvatars(theme) {
        // Update all chat avatars (bot avatars)
        const chatAvatars = document.querySelectorAll('.chat-avatar');
        chatAvatars.forEach(avatar => {
            // Check if this is a bear avatar by looking at the aria-label or parent context
            const isBearAvatar = avatar.getAttribute('aria-label') === 'Bear Tutor' || 
                                avatar.closest('.chat-message.bot');
            setupCharacterAvatar(avatar, isBearAvatar ? "bear" : "boy", theme);
        });
        
        // Update all kid avatars (in vocab questions)
        const kidAvatars = document.querySelectorAll('.kid-avatar');
        kidAvatars.forEach(avatar => {
            setupCharacterAvatar(avatar, "boy", theme);
        });
    }

    // Random initial theme selection (Space or Ocean)
    function loadInitialTheme() {
        const savedTheme = localStorage.getItem('preferredTheme');
        const userHasPreference = localStorage.getItem('userSelectedTheme') === 'true';
        
        if (savedTheme && userHasPreference) {
            // User has manually selected a theme before, use it
            switchTheme(savedTheme);
            userManuallySelectedTheme = true;
        } else {
            // New user or no preference, randomly select Space or Ocean
            const initialThemes = ['theme-space', 'theme-ocean'];
            const randomTheme = initialThemes[Math.floor(Math.random() * initialThemes.length)];
            switchTheme(randomTheme, true, 'initial'); // Mark as automatic initial load
            console.log(`Welcome! Randomly selected ${randomTheme} as your starting theme`);
        }
    }

    // Handle automatic theme switching based on story topics (can accept topic or full theme name)
    function handleTopicThemeSwitch(topicOrTheme) {
        if (!topicOrTheme) return;
        
        // If it's already a full theme name (theme-*), use it directly
        let suggestedTheme;
        if (topicOrTheme.startsWith('theme-')) {
            suggestedTheme = topicOrTheme;
        } else {
            // Map topic to theme
            const topicThemeMap = {
                'fantasy': 'theme-fantasy',
                'sports': 'theme-sports', 
                'food': 'theme-food',
                'animals': 'theme-animals',
                'ocean': 'theme-ocean',
                'space': 'theme-space',
                'creative': 'theme-creative',
                'mystery': 'theme-elegant',
                'adventure': 'theme-elegant',
                'fun': 'theme-fun',
                'whimsical': 'theme-whimsical',
                'magical': 'theme-whimsical',
                'inventions': 'theme-space' // Default technical topics to space
            };
            
            suggestedTheme = topicThemeMap[topicOrTheme.toLowerCase()] || 'theme-space';
        }
        
        if (suggestedTheme !== currentTheme) {
            console.log(`Topic/Theme "${topicOrTheme}" detected, switching to ${suggestedTheme} theme`);
            switchTheme(suggestedTheme, true, 'topic'); // Mark as automatic topic-based switch
        } else {
            console.log(`Topic/Theme "${topicOrTheme}" suggestion matches current theme ${currentTheme} - no switch needed`);
        }
    }

    // Client-side topic extraction (mirrors backend logic)
    function extractTopicFromMessage(message) {
        const messageLower = message.toLowerCase();
        
        // Topic mapping (same as backend)
        const topicKeywords = {
            "space": ["space", "planet", "star", "rocket", "astronaut", "jupiter", "mars", "galaxy", "alien"],
            "animals": ["animal", "dog", "cat", "elephant", "lion", "whale", "bird", "creature"],
            "inventions": ["invention", "science", "technology", "robot", "computer"],
            "sports": ["sport", "soccer", "football", "basketball", "tennis", "baseball"],
            "food": ["food", "cooking", "eat", "pizza", "ice cream", "fruit"],
            "ocean": ["ocean", "sea", "fish", "shark", "whale", "coral", "water"],
            "fantasy": ["fantasy", "magic", "magical", "dragon", "unicorn", "wizard", "fairy", "enchanted", "mystical"],
            "mystery": ["mystery", "detective", "clue", "solve", "secret", "hidden"],
            "adventure": ["adventure", "explore", "journey", "quest", "travel"]
        };
        
        for (const [topic, keywords] of Object.entries(topicKeywords)) {
            if (keywords.some(keyword => messageLower.includes(keyword))) {
                return topic;
            }
        }
        
        // Default topic extraction - use first word that looks like a topic
        const words = message.split();
        return words[0] || "adventure";
    }

    // Client-side theme suggestion (mirrors backend logic)
    function getThemeSuggestion(topic) {
        const topicToTheme = {
            'fantasy': 'theme-fantasy',
            'sports': 'theme-sports', 
            'food': 'theme-food',
            'animals': 'theme-animals',
            'ocean': 'theme-ocean',
            'space': 'theme-space',
            'mystery': 'theme-elegant',
            'adventure': 'theme-elegant',
            'inventions': 'theme-space'  // Technical topics default to space
        };
        
        return topicToTheme[topic.toLowerCase()] || 'theme-space';
    }

    // Make theme switching available globally
    window.switchTheme = switchTheme;


    // Initialize the app
    loadInitialTheme(); // Load initial theme (random Space/Ocean for new users)
    switchMode('funfacts');
});