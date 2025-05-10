/**
 * Initialize and render the sessions chart
 * @param {Array} data - Array of session data with week and count properties
 */
function initializeSessionsChart(data) {
    const ctx = document.getElementById('sessionsChart').getContext('2d');
    
    // Extract labels and data from the provided sessions data
    const labels = data.map(item => item.week);
    const counts = data.map(item => item.count);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Completed Sessions',
                data: counts,
                fill: true,
                backgroundColor: 'rgba(var(--bs-primary-rgb), 0.1)',
                borderColor: 'var(--bs-primary)',
                tension: 0.4,
                pointBackgroundColor: 'var(--bs-primary)',
                pointBorderColor: '#fff',
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    titleFont: {
                        size: 14
                    },
                    bodyFont: {
                        size: 14
                    },
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            let value = context.parsed.y;
                            return `${label}: ${value}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Set up event handlers for session request buttons
 */
function setupSessionRequestButtons() {
    // Handle approve buttons
    document.querySelectorAll('form [name="action"][value="approve"]').forEach(function(button) {
        button.closest('form').addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to approve this session request?')) {
                e.preventDefault();
            }
        });
    });
    
    // Handle reject buttons
    document.querySelectorAll('form [name="action"][value="reject"]').forEach(function(button) {
        button.closest('form').addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to reject this session request?')) {
                e.preventDefault();
            }
        });
    });
    
    // Handle complete buttons
    document.querySelectorAll('form [name="action"][value="complete"]').forEach(function(button) {
        button.closest('form').addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to mark this session as completed?')) {
                e.preventDefault();
            }
        });
    });
}