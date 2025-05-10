/**
 * Initializes the FullCalendar component
 */
function initializeCalendar() {
    console.log('Initializing calendar...');
    const calendarEl = document.getElementById('calendar');

    if (!calendarEl) {
        console.error('Calendar element not found!');
        return;
    }

    // Check if FullCalendar is loaded
    if (typeof FullCalendar === 'undefined') {
        console.error('FullCalendar library not loaded!');
        calendarEl.innerHTML = '<div class="alert alert-danger">Calendar library failed to load. Please refresh the page.</div>';
        return;
    }

    console.log('Creating calendar instance...');

    // Create a new calendar instance
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek'
        },
        height: 'auto',
        eventTimeFormat: {
            hour: 'numeric',
            minute: '2-digit',
            meridiem: 'short'
        },
        eventClick: function(info) {
            console.log('Event clicked:', info.event);
            handleEventClick(info.event);
        },
        events: function(info, successCallback, failureCallback) {
            console.log('Fetching events for range:', info.startStr, 'to', info.endStr);

            // Fetch events from the API
            fetch(`/api/calendar-events?start=${info.startStr}&end=${info.endStr}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(events => {
                    console.log('Events received:', events);
                    successCallback(events);
                })
                .catch(error => {
                    console.error('Error fetching events:', error);
                    failureCallback(error);
                    calendarEl.innerHTML += `<div class="alert alert-danger mt-3">Error loading events: ${error.message}</div>`;
                });
        },
        loading: function(isLoading) {
            console.log('Calendar loading state:', isLoading);
            // Show loading indicator
            if (isLoading) {
                calendarEl.classList.add('opacity-50');
            } else {
                calendarEl.classList.remove('opacity-50');
            }
        }
    });

    // Render the calendar
    console.log('Rendering calendar...');
    calendar.render();
    console.log('Calendar rendered');
}

/**
 * Handles clicks on calendar events
 * @param {Object} event - The FullCalendar event object
 */
function handleEventClick(event) {
    try {
        console.log('Handling event click:', event);

        // Check if event has extendedProps
        if (!event.extendedProps) {
            console.error('Event does not have extendedProps:', event);
            return;
        }

        const eventType = event.extendedProps.type;
        console.log('Event type:', eventType);

        if (eventType === 'session') {
            // For sessions, show session details
            if (event.extendedProps.sessionId) {
                showSessionDetails(event.extendedProps.sessionId);
            } else {
                console.error('Session event does not have sessionId:', event);
            }
        } else if (eventType === 'availability') {
            // For availability slots, show booking modal for mentees
            const mentorRole = document.querySelector('body').getAttribute('data-role');
            console.log('User role:', mentorRole);

            if (mentorRole !== 'mentor') {
                showBookingModal(event);
            } else {
                console.log('Mentor cannot book their own availability slot');
            }
        } else {
            console.warn('Unknown event type:', eventType);
        }
    } catch (error) {
        console.error('Error handling event click:', error);
    }
}

/**
 * Shows the session details modal
 * @param {number} sessionId - The ID of the session to display
 */
function showSessionDetails(sessionId) {
    // Reset the modal content
    document.getElementById('sessionModalBody').innerHTML = `
        <p class="text-center">
            <i class="fas fa-spinner fa-spin fa-2x"></i>
            <span class="d-block mt-2">Loading session details...</span>
        </p>
    `;

    // Show the modal
    const sessionModal = new bootstrap.Modal(document.getElementById('sessionModal'));
    sessionModal.show();

    // Fetch the session details from the server
    fetch(`/session/${sessionId}/template`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load session details');
            }
            return response.text();
        })
        .then(html => {
            document.getElementById('sessionModalBody').innerHTML = html;
        })
        .catch(error => {
            document.getElementById('sessionModalBody').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    Error loading session details: ${error.message}
                </div>
            `;
        });
}

/**
 * Shows the booking modal for mentees
 * @param {Object} event - The FullCalendar event object
 */
function showBookingModal(event) {
    // Get the event details
    const slotId = event.extendedProps.slotId;
    const title = event.title;
    const startDate = event.start;
    const endDate = event.end;

    // Extract the mentor info from the event
    const mentorId = event._def.resourceIds[0] || '';
    const mentorName = event._def.extendedProps.mentorName || 'Unknown';

    // Format the time range
    const startTime = startDate.toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'});
    const endTime = endDate.toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'});
    const timeRange = `${startTime} - ${endTime}`;

    // Set the form values
    document.getElementById('mentor_id').value = mentorId;
    document.getElementById('slot_id').value = slotId;
    document.getElementById('mentor_name').value = mentorName;
    document.getElementById('session_time').value = timeRange;

    // Set the date to the clicked date
    const dateInput = document.getElementById('session_date');
    const formattedDate = startDate.toISOString().split('T')[0];
    dateInput.value = formattedDate;

    // Show the modal
    const bookingModal = new bootstrap.Modal(document.getElementById('bookSessionModal'));
    bookingModal.show();
}