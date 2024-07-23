// Function to remove flash messages after a few seconds
function removeFlashMessages() {
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach((message) => {
        setTimeout(() => {
            message.style.display = 'none';
        }, 2000); // 3000 milliseconds = 3 seconds
    });
}

// Run the function to remove flash messages
document.addEventListener('DOMContentLoaded', removeFlashMessages);