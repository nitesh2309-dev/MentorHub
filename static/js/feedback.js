document.addEventListener('DOMContentLoaded', function() {
    // Initialize feedback forms
    if (document.getElementById('feedbackForm')) {
        initializeFeedbackForm();
    }
    
    // Display ratings
    document.querySelectorAll('.rating-display').forEach(displayRating);
});

function initializeFeedbackForm() {
    const feedbackForm = document.getElementById('feedbackForm');
    const ratingInput = feedbackForm.querySelector('[name="rating"]');
    const ratingStars = document.querySelectorAll('.rating-star');
    
    // Set up star rating selection
    ratingStars.forEach(star => {
        star.addEventListener('click', function() {
            const rating = parseInt(this.getAttribute('data-rating'));
            ratingInput.value = rating;
            
            // Update stars UI
            ratingStars.forEach(s => {
                const starRating = parseInt(s.getAttribute('data-rating'));
                if (starRating <= rating) {
                    s.classList.remove('empty');
                    s.classList.add('filled');
                } else {
                    s.classList.remove('filled');
                    s.classList.add('empty');
                }
            });
        });
    });
    
    // Form validation
    feedbackForm.addEventListener('submit', function(e) {
        if (!ratingInput.value || ratingInput.value === '0') {
            e.preventDefault();
            alert('Please select a rating');
            return false;
        }
        
        return true;
    });
}

function displayRating(ratingElement) {
    const rating = parseInt(ratingElement.getAttribute('data-rating'));
    const maxRating = 5;
    let starsHtml = '';
    
    for (let i = 1; i <= maxRating; i++) {
        if (i <= rating) {
            starsHtml += '<i class="fas fa-star filled"></i>';
        } else {
            starsHtml += '<i class="far fa-star empty"></i>';
        }
    }
    
    ratingElement.innerHTML = starsHtml;
}
