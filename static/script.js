function setupFormValidation(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', (e) => {
        const inputs = form.querySelectorAll('input[required]');
        const empty = [...inputs].some(i => !i.value.trim());

        if (empty) {
            e.preventDefault();
            alert("Please fill in all fields.");
        }
    });
}

// listeners for login and register
document.addEventListener('DOMContentLoaded', () => {
    setupFormValidation('registerForm');
    setupFormValidation('loginForm');
});



function openPlayerStats(url) {
    window.open(url, '_blank');
}
