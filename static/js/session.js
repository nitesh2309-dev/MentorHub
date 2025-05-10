document.addEventListener('DOMContentLoaded', function() {
    // Initialize session request forms
    if (document.querySelector('.session-request-form')) {
        initializeSessionRequestForms();
    }
    
    // Initialize session action buttons
    document.querySelectorAll('.session-action-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const form = this.closest('form');
            const action = this.getAttribute('data-action');
            
            let confirmMessage = 'Are you sure?';
            if (action === 'approve') {
                confirmMessage = 'Approve this session request?';
            } else if (action === 'reject') {
                confirmMessage = 'Reject this session request?';
            } else if (action === 'complete') {
                confirmMessage = 'Mark this session as completed?';
            }
            
            if (confirm(confirmMessage)) {
                form.submit();
            }
        });
    });
});

function initializeSessionRequestForms() {
    document.querySelectorAll('.session-request-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const mentorSelect = this.querySelector('[name="mentor_id"]');
            const dateInput = this.querySelector('[name="session_date"]');
            const slotSelect = this.querySelector('[name="slot_id"]');
            
            let isValid = true;
            
            // Validate mentor selection
            if (mentorSelect && mentorSelect.value === '') {
                alert('Please select a mentor');
                isValid = false;
            }
            
            // Validate date selection
            if (dateInput && dateInput.value === '') {
                alert('Please select a date for the session');
                isValid = false;
            } else if (dateInput) {
                const selectedDate = new Date(dateInput.value);
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                
                if (selectedDate < today) {
                    alert('Please select a future date');
                    isValid = false;
                }
            }
            
            // Validate slot selection
            if (slotSelect && slotSelect.value === '') {
                alert('Please select a time slot');
                isValid = false;
            }
            
            if (!isValid) {
                e.preventDefault();
                return false;
            }
            
            return true;
        });
    });
    
    // Date input should not allow past dates
    document.querySelectorAll('input[type="date"]').forEach(input => {
        const today = new Date();
        const yyyy = today.getFullYear();
        let mm = today.getMonth() + 1;
        let dd = today.getDate();
        
        if (mm < 10) mm = '0' + mm;
        if (dd < 10) dd = '0' + dd;
        
        const todayString = yyyy + '-' + mm + '-' + dd;
        input.setAttribute('min', todayString);
    });
}
