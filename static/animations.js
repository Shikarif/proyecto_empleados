// Funciones para manejar animaciones y microinteracciones

// Función para crear skeleton loaders
function createSkeletonLoader(element, rows = 3) {
    const skeletonHTML = Array(rows).fill(`
        <div class="skeleton-loader" style="height: 20px; margin: 10px 0;"></div>
    `).join('');
    
    element.innerHTML = skeletonHTML;
}

// Función para remover skeleton loaders
function removeSkeletonLoader(element) {
    element.innerHTML = '';
}

// Función para animar elementos al hacer scroll
function animateOnScroll() {
    const elements = document.querySelectorAll('.animate-on-scroll');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });

    elements.forEach(element => {
        observer.observe(element);
    });
}

// Función para manejar animaciones de carga en tablas
function handleTableLoading(tableId, isLoading) {
    const table = document.getElementById(tableId);
    if (!table) return;

    if (isLoading) {
        const tbody = table.querySelector('tbody');
        createSkeletonLoader(tbody, 5);
    } else {
        const tbody = table.querySelector('tbody');
        removeSkeletonLoader(tbody);
    }
}

// Función para animar mensajes flash
function animateFlashMessage(messageElement) {
    messageElement.classList.add('fade-in');
    setTimeout(() => {
        messageElement.style.opacity = '0';
        messageElement.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            messageElement.remove();
        }, 300);
    }, 3000);
}

// Inicializar animaciones cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar animaciones al scroll
    animateOnScroll();

    // Manejar animaciones de mensajes flash
    document.querySelectorAll('.alert').forEach(alert => {
        animateFlashMessage(alert);
    });

    // Añadir clase para animación al scroll a elementos específicos
    document.querySelectorAll('.card, .table, .form-group').forEach(element => {
        element.classList.add('animate-on-scroll');
    });
});

// Exportar funciones para uso en otros archivos
window.animations = {
    createSkeletonLoader,
    removeSkeletonLoader,
    handleTableLoading,
    animateFlashMessage
}; 