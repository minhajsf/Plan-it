/*
Put this script tag at the end of the <head> tag

<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.min.js"></script>
*/

// Place in script tags or serve this .js file with ioExample.html
// Example usages below

const socket = io();

socket.on('connect', () => {
    console.log('Connected to server')
})

socket.on('disconnect', () => {
    console.log('Disconnected to server')
})

socket.on('server_response', (response) => {
            console.log('Server:', response);
        });

const message = document.querySelector('#message_box')
socket.emit('user-message', message)
