document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatLog = document.getElementById("chat-log");

    // Conversation states
    const storySegments = [
        `Awesome choice! Space adventures are incredible! 🚀
Here's how our story begins:
Captain Zoe strapped herself into the gleaming spacecraft and checked all the controls. Her mission was to explore a mysterious new planet that scientists had discovered last week. As the rocket engines roared to life, she felt both nervous and excited about what extraordinary creatures she might encounter among the stars.
Now it's your turn! What happens next in our space adventure? Tell me what Captain Zoe sees or does when she reaches the mysterious planet!`,

        `That's a great idea! Let me help you make that sentence even better. Instead of "She finds an alien," you could write "She discovers an alien" or "She encounters a strange alien creature." The word "discovers" sounds more exciting for an adventure story!
Here's what happens next:
Captain Zoe's eyes widened as she spotted a peculiar creature with purple fur and three glowing eyes. The friendly alien was bouncing around some crystalline rocks, making musical sounds that echoed across the planet's surface. "Hello there!" Zoe called out through her helmet's speaker, wondering if this amazing being could communicate with humans.
What do you think the alien does when it hears Captain Zoe? Does it respond, hide, or do something completely unexpected?`,

        `Good addition to the story! You could make that sentence even more descriptive by saying "The alien quickly hides behind the rocks" or "It darts away and hides." Adding a little more detail makes the story come alive!
Here's what happens next:
The alien vanished behind a cluster of sparkling crystals, leaving only tiny purple footprints in the silver dust. Captain Zoe approached slowly, not wanting to frighten her new friend. She pulled out a small bag of Earth cookies from her backpack and placed one on a nearby rock, hoping the sweet treat might convince the shy creature to come out.
What happens next? Does the alien come back for the cookie, or does Captain Zoe try a different way to make friends?`,

        `Great continuation! To make your writing even stronger, you could say "The alien comes back for the cookie" or "The alien emerges to get the cookie." Adding "back" or "emerges" gives us more detail about the action!
Here's what happens next:
One purple paw slowly emerged from behind the crystal, followed by a curious glowing eye peeking out. The alien crept forward and sniffed the cookie with its tiny blue nose. After taking a small bite, it began to shimmer with joy and made happy chirping sounds! Captain Zoe smiled as the brave little creature stepped closer, no longer afraid.
"We did it!" Captain Zoe thought. "We made first contact!" The alien offered her a beautiful glowing crystal as a gift of friendship, and together they explored the magnificent planet, discovering singing flowers and rainbow waterfalls.
THE END`
    ];

    const vocabQuestion = {
        question: 'What does the word emerged mean?\n"One purple paw slowly emerged from behind the crystal."',
        options: [
            'a) Ran quickly',
            'b) Came out slowly',
            'c) Jumped high',
            'd) Fell down'
        ],
        correctIndex: 1
    };

    let storyStep = 0;
    let storyDone = false;
    let vocabShown = false;

function appendMessage(sender, text) {
    const msgWrapper = document.createElement("div");
    msgWrapper.className = sender === "user" ? "chat-message user" : "chat-message bot";

    const avatar = document.createElement("img");
    avatar.className = "chat-avatar";
    if (sender === "user") {
        avatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f466.png"; // kid avatar
        avatar.alt = "Kid";
    } else {
        avatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f99d.png"; // raccoon avatar
        avatar.alt = "Raccoon Coach";
    }

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.textContent = text;

    msgWrapper.appendChild(avatar);
    msgWrapper.appendChild(bubble);

    chatLog.appendChild(msgWrapper);
    chatLog.scrollTop = chatLog.scrollHeight;
}

function appendVocabQuestion() {
    // Create container for vocab question UI
    const vocabContainer = document.createElement("div");
    vocabContainer.className = "vocab-question-container";

    // Create question bubble with raccoon avatar
    const questionWrapper = document.createElement("div");
    questionWrapper.className = "chat-message bot";

    const avatar = document.createElement("img");
    avatar.className = "chat-avatar";
    avatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f99d.png"; // raccoon avatar
    avatar.alt = "Raccoon Coach";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.textContent = vocabQuestion.question;

    questionWrapper.appendChild(avatar);
    questionWrapper.appendChild(bubble);

    // Create answers container with kid avatar
    const answersWrapper = document.createElement("div");
    answersWrapper.className = "vocab-answers-wrapper";

    const kidAvatar = document.createElement("img");
    kidAvatar.className = "kid-avatar";
    kidAvatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f466.png"; // kid avatar
    kidAvatar.alt = "Kid";

    const buttonsContainer = document.createElement("div");
    buttonsContainer.className = "answer-buttons-container";

    vocabQuestion.options.forEach((option, index) => {
        const button = document.createElement("button");
        button.className = "answer-button";
        button.textContent = option;
        button.addEventListener("click", () => {
            // Disable all buttons after selection
            Array.from(buttonsContainer.children).forEach(btn => btn.disabled = true);

            // Highlight selected button
            button.classList.add("selected");
            // Add checkmark to selected button
            const checkmark = document.createElement("span");
            checkmark.className = "checkmark";
            checkmark.textContent = "✔";
            button.appendChild(checkmark);

            // Append user's selected answer as chat bubble
            appendMessage("user", option);

            // Append chatbot follow-up message
            appendMessage("bot", getFollowUpMessage(index));

            // Remove vocab container after selection
            vocabContainer.remove();
        });
        buttonsContainer.appendChild(button);
    });

    answersWrapper.appendChild(buttonsContainer);
    answersWrapper.appendChild(kidAvatar);

    vocabContainer.appendChild(questionWrapper);
    vocabContainer.appendChild(answersWrapper);

    chatLog.appendChild(vocabContainer);
    chatLog.scrollTop = chatLog.scrollHeight;
}

// Sample follow-up messages for each answer option
function getFollowUpMessage(selectedIndex) {
    switch (selectedIndex) {
        case 0:
            return "Not quite. 'Ran quickly' is not the meaning of 'emerged'. Try again next time!";
        case 1:
            return "Correct! 'Came out slowly' is the right meaning of 'emerged'. Great job!";
        case 2:
            return "That's not right. 'Jumped high' is not the meaning of 'emerged'. Keep trying!";
        case 3:
            return "Nope. 'Fell down' is not the meaning of 'emerged'. You'll get it next time!";
        default:
            return "";
    }
}

    chatForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const userMessage = chatInput.value.trim();
        if (!userMessage) return;

        appendMessage("user", userMessage);
        chatInput.value = "";

        if (!storyDone) {
            // Append chatbot story response for current step
            appendMessage("bot", storySegments[storyStep]);
            storyStep++;
            if (storyStep >= storySegments.length) {
                storyDone = true;
                // Immediately show vocab question after story ends
                appendVocabQuestion();
                vocabShown = true;
            }
        } else if (!vocabShown) {
            // Show vocab question after story (fallback)
            appendVocabQuestion();
            vocabShown = true;
        } else {
            // After vocab question, just echo user input for now
            appendMessage("bot", "Thanks for your input!");
            // Show Jupiter fact and vocabulary question again
            appendVocabQuestion();
            vocabShown = true;
        }
    });

// Start conversation with first story segment only if storyStep is 0
if (storyStep === 0) {
    appendMessage("bot", storySegments[storyStep]);
    storyStep++;
}
});
