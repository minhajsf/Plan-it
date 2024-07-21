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
                response = ""; // Reset the response for a new recording session
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

            document.addEventListener('DOMContentLoaded', () => {
                startButton.style.display = 'inline-block';
                stopButton.style.display = 'none';
                recordingIndicator.style.display = 'none';
            });


        } else {
            outputText.textContent = "Speech recognition not supported in this browser.";
        }

        // Handle socket connection
        socket.on('connect', () => {
            console.log('Connected to server');
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

        //Append message to chat box
            function appendMessage(message, sender) {
            const messageElement = document.createElement('div');
            messageElement.classList.add('chat-message', sender);
            messageElement.textContent = message;
            chatBox.appendChild(messageElement);
            chatBox.scrollTop = chatBox.scrollHeight; 
        }

        // Add this code to handle Enter key press
        promptInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent default Enter key behavior (e.g., newline in text area)
                sendPrompt();
            }
        });