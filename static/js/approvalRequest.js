// const socket = io();
// General button handler
const generalButtonHandler = function(status) {
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

    return container;
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


// Socket event listener
socket.on('request-approval', (email_json) => {
    clearEmailContainers(); // Clear existing email containers before adding a new one
    const chatBox = document.querySelector('#chatBox');
    const emailContainer = createEmailDiv(email_json);
    chatBox.appendChild(emailContainer);
});
