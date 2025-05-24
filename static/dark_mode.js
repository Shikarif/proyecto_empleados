document.addEventListener('DOMContentLoaded', function() {
    const darkModeSwitch = document.getElementById('darkModeSwitch');
    
    // Cargar preferencia guardada
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
        darkModeSwitch.checked = true;
    }

    // Manejar cambio de tema
    darkModeSwitch.addEventListener('change', function() {
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('darkMode', this.checked);
    });
}); 