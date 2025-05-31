document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const body = document.body;
    // Cargar preferencia guardada
    if (localStorage.getItem('darkMode') === 'true') {
        body.classList.add('dark-mode');
        themeToggle.classList.add('dark');
    } else {
        body.classList.remove('dark-mode');
        themeToggle.classList.remove('dark');
    }
    // Alternar modo oscuro al hacer click
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            body.classList.toggle('dark-mode');
            const isDark = body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDark);
            themeToggle.classList.toggle('dark', isDark);
        });
    }
}); 