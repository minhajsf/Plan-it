const openButtons = document.querySelectorAll("[data-setting-target]");
const closeButtons = document.querySelectorAll("[data-close-button]");
const overlay = document.getElementById("overlay");
const dateElements = document.querySelectorAll('.card-details.date');
const timeElements = document.querySelectorAll('.card-details.time');

document.addEventListener('DOMContentLoaded', () => {;
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

    dateElements.forEach(element => {
        const isoDate = element.textContent.trim().replace('Date: ', '');
        const date = new Date(isoDate).toLocaleDateString('en-US', {
            year: 'numeric', month: 'long', day: 'numeric'
        });
        element.textContent = 'Date: ' + date;
    });

    timeElements.forEach(element => {
        const isoTime = element.textContent.trim().replace('Time: ', '');
        const time = new Date(isoTime).toLocaleTimeString('en-US', {
            hour: '2-digit', minute: '2-digit', hour12: true
        });
        element.textContent = 'Time: ' + time;
    });

});