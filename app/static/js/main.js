/**
 * StudyMate AI — main.js
 * Global JavaScript utilities
 */

// Auto-dismiss flash alerts after 5s
document.addEventListener('DOMContentLoaded', () => {
    const alerts = document.querySelectorAll('.flash-alert');
    alerts.forEach(alert => {
        setTimeout(() => {  
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Confirm delete actions
document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
        const msg = el.dataset.confirm || 'Are you sure?';
        if (!confirm(msg)) e.preventDefault();
    });
});
