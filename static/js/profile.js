/**
 * Initialize the availability form functionality
 */
function initializeAvailabilityForms() {
    console.log('Initializing availability forms...');

    // Get all the forms for deleting availability slots
    const deleteAvailabilityForms = document.querySelectorAll('form[action^="/availability/delete/"]');

    // Add confirmation dialog to each delete form
    deleteAvailabilityForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this availability slot?')) {
                e.preventDefault();
            }
        });
    });

    // Handle form validations
    const availabilityForm = document.querySelector('form[action="/availability/add"]');
    console.log('Found availability form:', availabilityForm);

    if (availabilityForm) {
        // Get form elements
        const dayOfWeekSelect = availabilityForm.querySelector('select[name="day_of_week"]');
        const startTimeInput = availabilityForm.querySelector('input[name="start_time"]');
        const endTimeInput = availabilityForm.querySelector('input[name="end_time"]');
        const submitButton = availabilityForm.querySelector('#submit-availability');

        console.log('Form elements:', {
            dayOfWeekSelect,
            startTimeInput,
            endTimeInput,
            submitButton
        });

        // Ensure time inputs have proper type
        if (startTimeInput) {
            startTimeInput.type = 'time';
            startTimeInput.required = true;
        }

        if (endTimeInput) {
            endTimeInput.type = 'time';
            endTimeInput.required = true;
        }

        // Add form submission validation
        availabilityForm.addEventListener('submit', function(e) {
            console.log('Form submit event triggered');

            // Prevent default to validate first
            e.preventDefault();

            // Validate form
            if (!validateAvailabilityForm(availabilityForm)) {
                return;
            }

            // If validation passes, submit the form
            console.log('Form validation passed, submitting form...');
            availabilityForm.submit();
        });

        // Add "Add New" button functionality
        const addNewButton = document.querySelector('[data-bs-target="#newAvailabilityForm"]');
        if (addNewButton) {
            addNewButton.addEventListener('click', function() {
                console.log('Add New button clicked');
                // Reset form when opening
                availabilityForm.reset();
            });
        }
    }
}

/**
 * Validate the availability form
 */
function validateAvailabilityForm(form) {
    const dayOfWeekSelect = form.querySelector('select[name="day_of_week"]');
    const startTimeInput = form.querySelector('input[name="start_time"]');
    const endTimeInput = form.querySelector('input[name="end_time"]');

    // Check if day of week is selected
    if (!dayOfWeekSelect.value) {
        alert('Please select a day of the week');
        dayOfWeekSelect.focus();
        return false;
    }

    // Check if times are provided
    if (!startTimeInput.value) {
        alert('Please provide a start time');
        startTimeInput.focus();
        return false;
    }

    if (!endTimeInput.value) {
        alert('Please provide an end time');
        endTimeInput.focus();
        return false;
    }

    // Check if end time is after start time
    if (startTimeInput.value >= endTimeInput.value) {
        alert('End time must be after start time');
        endTimeInput.focus();
        return false;
    }

    return true;
}

// Initialize all functionality when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing forms...');
    initializeAvailabilityForms();
});