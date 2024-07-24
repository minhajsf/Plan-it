/*
Put this script tag at the end of the <head> tag

<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.min.js"></script>
*/

const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const outputText = document.getElementById('outputText');
const promptInput = document.getElementById('prompt');
const chatBox = document.getElementById('chatBox');
const recordingIndicator = document.querySelector('.recording-indicator');
const openButtons = document.querySelectorAll("[data-setting-target]");
const closeButtons = document.querySelectorAll("[data-close-button]");
const overlay = document.getElementById("overlay");
const socket = io();


let response = "";

        // Correct punctuation for the transcript
const correctPunctuation = (transcript) => {
    transcript = transcript.trim();
    transcript = transcript.charAt(0).toUpperCase() + transcript.slice(1);
    if (!/[.!?]$/.test(transcript)) {
        transcript += '.';
    }
    transcript = transcript.replace(/\s([,.!?])/g, '$1');
    transcript = transcript.replace(/([.!?]\s)([a-z])/g, (match, p1, p2) => p1 + p2.toUpperCase());
    transcript = transcript.replace(/([.!?])([A-Z])/g, '$1 $2');
    transcript = transcript.replace(/(\b[aA]\.[mM]\.|\b[pP]\.[mM]\.)(\s+[A-Z])/g, (match, p1, p2) => p1 + p2.toLowerCase());
    return transcript;
};

if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = true;

    // Handle speech recognition results
    recognition.onresult = (event) => {
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                response += transcript + ' ';
            } else {
                interimTranscript += transcript;
            }
        }
        // Display interim and final results in the input box
        promptInput.value = response + interimTranscript;
    };

    // Handle errors
    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
    };

    // Start recording
    startButton.addEventListener('click', () => {
        response = ""; 
        recognition.start();
        startButton.style.display = 'none';
        stopButton.style.display = 'inline-block';
        recordingIndicator.style.display = 'flex';
                
    });

    // Stop recording
    stopButton.addEventListener('click', () => {
        recognition.stop();
        startButton.style.display = 'inline-block';
        stopButton.style.display = 'none';
        recordingIndicator.style.display = 'none';
                
    });

    // Handle end of recognition
    recognition.onend = () => {
        const correctedResponse = correctPunctuation(response.trim());
        promptInput.value = correctedResponse;
        outputText.textContent = correctedResponse;
    };

} else {
    outputText.textContent = "Speech recognition not supported in this browser.";
}

// Handle socket connection
socket.on('connect', () => {
    console.log('Connected to server');
    const chatBox = document.getElementById('chatBox');
    chatBox.scrollTop = chatBox.scrollHeight;
});

// Handle socket disconnection
socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

// Handle server response
socket.on('server_response', (response) => {
    console.log('Server:', response);
    appendMessage(response, 'server');
    
});

// GOOGLE CALENDAR EVENTS
socket.on('receiver', (data) => {
    const message = data.message;
    appendMessage(message, 'server');
   
});

// Handle redirection from server
socket.on('redirect_to_app', (data) => {
    window.location.href = data.url;
});

function sendPrompt() {
    if (startButton.style.display === 'none') {
                
        stopButton.click(); 
    }

    // After ensuring mic is off, proceed to send the message
    const prompt = promptInput.value.trim();
    if (prompt !== '') {
        socket.emit('user_prompt', prompt);
        appendMessage(prompt, 'user');
        promptInput.value = ''; 
    }
}

promptInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault(); // Prevent default Enter key behavior (e.g., newline in text area)
        sendPrompt();
    }
});

//Append message to chat box
function appendMessage(message, sender) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message', sender);
    messageElement.textContent = message;
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
    chatHistory(); 
}


// saving chat history
function chatHistory() {
    let chatHistory = chatBox.innerHTML;

    localStorage.setItem('chatHistory', chatHistory);
}

const generalButtonHandler = function(status){
    const toDiv = document.querySelector('#to-field').value;
    const subjectDiv = document.querySelector('#subject-field').value;
    const bodyDiv = document.querySelector('#body-field').value;

    const response = {
        'status': status,
        'email': {
            'to': toDiv,
            'subject': subjectDiv,
            'body': bodyDiv
        }
    };

    // Emit the socket event
    socket.emit('approval-request-response', response);
};

// Button handlers
const quitButtonHandler = function() {
    generalButtonHandler('quit');
};
const saveButtonHandler = function() {
    generalButtonHandler('save');
};
const sendButtonHandler = function() {
    generalButtonHandler('send');
};

// Create email div
function createEmailDiv(fields) {
    // Create the container div
    const container = document.createElement('div');

    // Create the To field
    const toDiv = document.createElement('div');
    toDiv.className = 'to-input-field';
    toDiv.innerHTML = `
        <label for="to-field">To:</label>
        <input type="text" id="to-field" name="to-field" value="${fields.to}">
    `;

    // Create the Subject field
    const subjectDiv = document.createElement('div');
    subjectDiv.className = 'subject-input-field';
    subjectDiv.innerHTML = `
        <label for="subject-field">Subject:</label>
        <input type="text" id="subject-field" name="subject-field" value="${fields.subject}">
    `;

    // Create the Body field
    const bodyDiv = document.createElement('div');
    bodyDiv.className = 'body-input-field';
    bodyDiv.innerHTML = `
        <label for="body-field">Body:</label>
        <input type="text" id="body-field" name="body-field" value="${fields.body}">
    `;

    // Create the Button container
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'button-container';
    buttonContainer.innerHTML = `
        <button class="quit-button">Quit</button>
        <button class="save-button">Save</button>
        <button class="send-button">Send</button>
        `;

    // Append all divs to the container
    container.appendChild(toDiv);
    container.appendChild(subjectDiv);
    container.appendChild(bodyDiv);
    container.appendChild(buttonContainer);

    // Attach event listeners to buttons in the newly created div
    buttonContainer.querySelector('.quit-button').addEventListener('click', quitButtonHandler);
    buttonContainer.querySelector('.save-button').addEventListener('click', saveButtonHandler);
    buttonContainer.querySelector('.send-button').addEventListener('click', sendButtonHandler);

    container.classList.add('chat-message', 'server');
    chatBox.appendChild(container);
    console.log(container)
}

// Function to clear existing email containers and their event listeners
function clearEmailContainers() {
    const chatBox = document.querySelector('#chatBox');

    // Remove all children from chatBox and their event listeners
    while (chatBox.firstChild) {
        // Remove event listeners from all buttons within the removed element
        const buttons = chatBox.firstChild.querySelectorAll('button');
        buttons.forEach(button => {
            button.removeEventListener('click', quitButtonHandler);
            button.removeEventListener('click', saveButtonHandler);
            button.removeEventListener('click', sendButtonHandler);
        });

        chatBox.removeChild(chatBox.firstChild);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    
    const chatHistory = localStorage.getItem('chatHistory');
    if (chatHistory) {
        chatBox.innerHTML = chatHistory;
    }
    
    startButton.style.display = 'inline-block';
    stopButton.style.display = 'none';
    recordingIndicator.style.display = 'none';
    // Toggle modal visibility
    openButtons.forEach(button => {
        button.addEventListener("click", () => {
            const modal = document.querySelector(button.dataset.settingTarget);
            openModal(modal);
        });
    });

    closeButtons.forEach(button => {
        button.addEventListener("click", () => {
            const modal = button.closest(".popup");
            closeModal(modal);
        });
    });

    overlay.addEventListener("click", () => {
        const modals = document.querySelectorAll(".popup.active");
        modals.forEach(modal => closeModal(modal));
    });

    function openModal(modal) {
        if (modal == null) return;
        modal.classList.add("active");
        overlay.classList.add("active");
    }

    function closeModal(modal) {
        if (modal == null) return;
        modal.classList.remove("active");
        overlay.classList.remove("active");
    }

    socket.on('request-approval', (email_json) => {
        // clearEmailContainers(); // Clear existing email containers before adding a new one
        console.log(email_json)
        createEmailDiv(email_json);
});

});


