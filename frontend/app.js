document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatLog = document.getElementById("chat-log");
    const storywritingBtn = document.getElementById("storywriting-btn");
    const funFactsBtn = document.getElementById("fun-facts-btn");

    // App state
    let currentMode = 'storywriting'; // 'storywriting' or 'funfacts'
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
        
        // Reset to default space theme when switching modes
        switchTheme('space');
        
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

        const avatar = document.createElement("img");
        avatar.className = "chat-avatar";
        if (sender === "user") {
            avatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f9d2.png";
            avatar.alt = "Kid";
        } else {
            avatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f43b.png";
            avatar.alt = "Bear Tutor";
        }

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        
        // Replace **word** with colored spans for vocabulary highlighting
        const processedText = text.replace(/\*\*(.*?)\*\*/g, '<span class="vocab-word">$1</span>');
        bubble.innerHTML = processedText;

        msgWrapper.appendChild(avatar);
        msgWrapper.appendChild(bubble);

        chatLog.appendChild(msgWrapper);
        
        // Wait for images to load before scrolling
        avatar.onload = () => scrollToBottom();
        avatar.onerror = () => scrollToBottom();
        
        // Also scroll immediately in case image is cached
        scrollToBottom();
    }

    // Create vocabulary question UI
    function appendVocabQuestion(question, options, correctIndex) {
        const vocabContainer = document.createElement("div");
        vocabContainer.className = "vocab-question-container";

        // Question bubble
        const questionWrapper = document.createElement("div");
        questionWrapper.className = "chat-message bot";

        const avatar = document.createElement("img");
        avatar.className = "chat-avatar";
        avatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f43b.png";
        avatar.alt = "Bear Tutor";

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

        const kidAvatar = document.createElement("img");
        kidAvatar.className = "kid-avatar";
        kidAvatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f9d2.png";
        kidAvatar.alt = "Kid";

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
        
        // Wait for all avatars to load before scrolling
        const avatars = [avatar, kidAvatar];
        let loadedCount = 0;
        const checkAllLoaded = () => {
            loadedCount++;
            if (loadedCount >= avatars.length) {
                scrollToBottom();
            }
        };
        
        avatars.forEach(img => {
            img.onload = checkAllLoaded;
            img.onerror = checkAllLoaded;
        });
        
        // Also scroll immediately in case images are cached
        scrollToBottom();
    }

    // Handle vocabulary answer
    function handleVocabAnswer(selectedIndex, correctIndex, selectedOption, buttonsContainer, vocabContainer) {
        // Disable all buttons
        Array.from(buttonsContainer.children).forEach(btn => btn.disabled = true);

        // Highlight selected button
        const selectedButton = buttonsContainer.children[selectedIndex];
        selectedButton.classList.add("selected");

        // Add checkmark to correct answer
        const correctButton = buttonsContainer.children[correctIndex];
        if (selectedIndex === correctIndex) {
            const checkmark = document.createElement("span");
            checkmark.className = "checkmark";
            checkmark.textContent = "✔";
            selectedButton.appendChild(checkmark);
        } else {
            const checkmark = document.createElement("span");
            checkmark.className = "checkmark";
            checkmark.textContent = "✔";
            correctButton.appendChild(checkmark);
            correctButton.style.background = "#2cb67d";
        }

        // Show user's selection
        appendMessage("user", selectedOption);

        // Show feedback
        const feedback = selectedIndex === correctIndex 
            ? "Correct! Great job! 🎉" 
            : `Nice try! The correct answer was ${buttonsContainer.children[correctIndex].textContent}. You'll get it next time! 💪`;
        
        appendMessage("bot", feedback);

        // Remove vocab container
        setTimeout(() => {
            vocabContainer.remove();
        }, 1000);

        // Continue fun facts flow automatically
        if (currentMode === 'funfacts') {
            setTimeout(() => {
                continueAfterVocab();
            }, 2000);
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
                
                // Check if topic was set and switch theme accordingly
                if (data.sessionData.topic) {
                    console.log(`Topic detected in continue: ${data.sessionData.topic}`);
                    switchThemeForTopic(data.sessionData.topic);
                }
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
                
                // Check if topic was set and switch theme accordingly
                if (data.sessionData.topic) {
                    console.log(`Topic detected: ${data.sessionData.topic}`);
                    switchThemeForTopic(data.sessionData.topic);
                }
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
            // Remove thinking message
            chatLog.removeChild(chatLog.lastChild);
            appendMessage("bot", "Sorry, I'm having trouble connecting right now. Please try again!");
        }
    });

    // Event listeners for mode buttons
    storywritingBtn.addEventListener("click", () => switchMode('storywriting'));
    funFactsBtn.addEventListener("click", () => switchMode('funfacts'));

    const body = document.body;

    // Theme switching functionality (automatic only)
    
    // Current theme tracking
    let currentTheme = 'space';

    function switchTheme(themeName) {
        // Only switch if it's actually a different theme
        if (currentTheme === themeName) return;
        
        // Add fade effect during transition
        body.style.opacity = '0.95';
        
        setTimeout(() => {
            // Remove all existing theme classes
            body.classList.remove('space-theme', 'ocean-theme', 'fantasy-theme', 'adventure-theme', 'sports-theme', 'food-theme', 'space-bg');
            
            // Add new theme class
            body.classList.add(`${themeName}-theme`);
            
            currentTheme = themeName;
            console.log(`Automatically switched to ${themeName} theme`);
            
            // Restore opacity
            setTimeout(() => {
                body.style.opacity = '1';
            }, 100);
        }, 200);
    }

    // Map topics to themes
    function getThemeForTopic(topic) {
        const themeMap = {
            'space': 'space',
            'animals': 'ocean', // Default animals to ocean for now
            'ocean': 'ocean',
            'fantasy': 'fantasy',
            'mystery': 'adventure',
            'adventure': 'adventure',
            'sports': 'sports', // Use dedicated sports theme
            'food': 'food', // Use dedicated food theme
            'inventions': 'space' // Use space theme for inventions
        };
        
        return themeMap[topic] || 'space'; // Default to space
    }

    // Dynamic theme switching based on topic
    function switchThemeForTopic(topic) {
        const newTheme = getThemeForTopic(topic);
        if (newTheme !== currentTheme) {
            console.log(`Topic "${topic}" detected, switching to ${newTheme} theme`);
            switchTheme(newTheme);
        }
    }


    // Initialize the app
    switchMode('storywriting');
});