document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Bet amount formatter
    const betInputs = document.querySelectorAll('.bet-input');
    betInputs.forEach(input => {
        input.addEventListener('input', function() {
            let value = this.value.replace(/[^0-9]/g, '');
            if (value) {
                value = parseInt(value, 10);
                this.value = value;
            } else {
                this.value = '';
            }
        });
    });
    
    // Add 'max' bet button functionality
    const maxBetButtons = document.querySelectorAll('.max-bet-btn');
    maxBetButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetInput = document.querySelector(this.dataset.target);
            const maxAmount = parseInt(this.dataset.max, 10);
            if (targetInput && maxAmount) {
                targetInput.value = maxAmount;
            }
        });
    });
    
    // Timer functions for cooldowns
    function updateCooldowns() {
        const cooldownElements = document.querySelectorAll('.cooldown-timer');
        cooldownElements.forEach(element => {
            const targetTime = new Date(element.dataset.target).getTime();
            const now = new Date().getTime();
            const distance = targetTime - now;
            
            if (distance <= 0) {
                element.innerHTML = 'Available now!';
                element.classList.remove('text-danger');
                element.classList.add('text-success');
                const btn = document.querySelector(`#${element.dataset.btnId}`);
                if (btn) {
                    btn.disabled = false;
                }
            } else {
                const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((distance % (1000 * 60)) / 1000);
                element.innerHTML = `${minutes}m ${seconds}s`;
                element.classList.remove('text-success');
                element.classList.add('text-danger');
            }
        });
    }
    
    // Update cooldowns every second if there are any on the page
    if (document.querySelectorAll('.cooldown-timer').length > 0) {
        updateCooldowns();
        setInterval(updateCooldowns, 1000);
    }
    
    // Handle toast notifications
    const toastElList = [].slice.call(document.querySelectorAll('.toast'));
    toastElList.map(function (toastEl) {
        return new bootstrap.Toast(toastEl, {
            delay: 5000
        }).show();
    });
});

// Utility functions
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = formatNumber(Math.floor(progress * (end - start) + start));
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// Currency display formatter
document.querySelectorAll('.currency-value').forEach(el => {
    el.textContent = formatNumber(parseInt(el.textContent));
});
