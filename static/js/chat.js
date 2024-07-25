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
const textarea = document.getElementById('prompt');
const charCount = document.getElementById('charCount');
const maxLength = parseInt(textarea.getAttribute('maxlength'));
let socket = io();


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

    
    const prompt = promptInput.value.trim();
    if (prompt !== '') {
        socket.emit('user_prompt', prompt);
        appendMessage(prompt, 'user');
        promptInput.value = ''; 
    }
}

promptInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault(); 
        sendPrompt();
    }
});

function formatMessage(message) {
    message = message.replace(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2})?/g, function (match) {
       
        const date = new Date(match);
        
        const options = { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric', 
            hour: 'numeric', 
            minute: 'numeric', 
            second: 'numeric', 
            hour12: true 
        };
        return date.toLocaleString(undefined, options);
    });

    // Replace newlines with <br> for HTML
    return message.replace(/\n/g, '<br>');
}

//Append message to chat box
function appendMessage(message, sender) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message', sender);
    messageElement.innerHTML = formatMessage(message);
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
}


// saving chat history
function chatHistory() {
    let chatHistory = chatBox.innerHTML;

    localStorage.setItem('chatHistory', chatHistory);
}

const generalButtonHandler = function(status){
   
    if (!chatBox.lastElementChild) return;

    const emailContainer = chatBox.lastElementChild;

    console.log("email container" + emailContainer);

    if (!emailContainer.lastElementChild) return;

    const buttonContainer = emailContainer.lastElementChild;
    
    if (buttonContainer.children.length >= 3) {
        buttonContainer.children[0].removeEventListener('click', quitButtonHandler);
        buttonContainer.children[1].removeEventListener('click', saveButtonHandler);
        buttonContainer.children[2].removeEventListener('click', sendButtonHandler);

        buttonContainer.children[0].classList.add('disabled-button');
        buttonContainer.children[1].classList.add('disabled-button');
        buttonContainer.children[2].classList.add('disabled-button');
    } else {
        console.error('Button container does not have the expected buttons.');
        return;
    }

    if (emailContainer.children.length >= 3) {
       
        const toDiv = emailContainer.children[0].children[0].lastElementChild;
        const subjectDiv = emailContainer.children[1].children[0].lastElementChild;
        const bodyDiv = emailContainer.children[2].children[0];


        if (toDiv && subjectDiv && bodyDiv) {
            console.log("1");
            
            if (toDiv.tagName === 'INPUT' || toDiv.tagName === 'TEXTAREA') toDiv.setAttribute('readonly', true);
            if (subjectDiv.tagName === 'INPUT' || subjectDiv.tagName === 'TEXTAREA') subjectDiv.setAttribute('readonly', true);
            if (bodyDiv.tagName === 'INPUT' || bodyDiv.tagName === 'TEXTAREA') bodyDiv.setAttribute('readonly', true);

            console.log("2");

            console.log("to" + toDiv.value);
            console.log("subject" + subjectDiv.value);
            console.log("body" + bodyDiv.value);


            const response = {
                'status': status,
                'email': {
                    'to': toDiv.value,
                    'subject': subjectDiv.value,
                    'body': bodyDiv.value
                }
            };
            console.log(response)
            socket.emit('approval-request-response', response);

            console.log(response)
            
        } else {
            console.error('Expected form elements not found.');
        }
    } else {
        console.error('Email container does not have the expected children.');
    }

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
        <div class = "wrapper">
            <label for="to-field">To:</label>

            <input type="text" id="to-field" name="to-field" placeholder: "To" value="${fields.to}" required>

        </div>
    `;

    // Create the Subject field
    const subjectDiv = document.createElement('div');
    subjectDiv.className = 'subject-input-field';
    subjectDiv.innerHTML = `
        <div class = "wrapper">
        <label for="subject-field">Subject:</label>
        <input type="text" id="subject-field" name="subject-field" placeholder = "Subject" value="${fields.subject}">
        </div>
    `;

    // Create the Body field
    const bodyDiv = document.createElement('div');
    bodyDiv.className = 'body-input-field';
    bodyDiv.innerHTML = `

        <textarea id="body-field" name="body-field" placeholder="Type your body...">${fields.body}</textarea>

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
    chatBox.scrollTop = chatBox.scrollHeight;

}

document.addEventListener('DOMContentLoaded', async () => {
    
    const response = await fetch('/chat-history');
    if (response.ok) {
        const chatHistory = await response.json();
        chatHistory.reverse().forEach(entry => {
            appendMessage(entry.user_prompt, 'user');
            entry.chat_responses.forEach(response => {
                appendMessage(response.response, 'server');
            });
        });
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
        createEmailDiv(email_json);
});


});

// this code is for the settings "clear" button
document.getElementById('clearBtn').addEventListener('click', async function() {
    document.getElementById('confirmationDialog').style.display = 'block';
});

document.getElementById('confirmYes').addEventListener('click', async function() {
    console.log('Confirmed');
    document.getElementById('confirmationDialog').style.display = 'none';
    
    document.getElementById('secondDialog').style.display = 'block';

    try {
        const response = await fetch('/clear-history', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();
        if (response.ok) {
            console.log(result.message);
            chatBox.innerHTML = '';
        } else {
            console.error('Failed to clear history:', result.error);
        }
    } catch (error) {
        console.error('Error clearing history:', error);
    }

    document.getElementById('secondDialog').style.display = 'none';
});

document.getElementById('confirmNo').addEventListener('click', function() {
    document.getElementById('confirmationDialog').style.display = 'none';
});


document.getElementById('okBtn').addEventListener('click', function() {
    document.getElementById('secondDialog').style.display = 'none';
});

//this is for the textbox to type, it will expand vertically
document.addEventListener('input', function (event) {
    if (event.target.id === 'prompt') {
        event.target.style.height = 'auto'; // Reset height to auto to calculate the new height
        event.target.style.height = event.target.scrollHeight + 'px'; // Set the height to the scrollHeight
    }
});

//error if user reaches character limit
textarea.addEventListener('input', function () {
    const length = textarea.value.length;
    const remaining = maxLength - length;
    if (remaining <= 0) {
        charCount.textContent = `0 characters remaining`;
        charCount.classList.add('error');
    } else if (remaining <= 20) {
        charCount.textContent = `${remaining} characters remaining`;
        charCount.classList.add('warning');
        charCount.classList.remove('error');
    } else {
        charCount.textContent = `${remaining} characters remaining`;
        charCount.classList.remove('warning', 'error');
    }
});


charCount.textContent = `${maxLength} characters remaining`;

