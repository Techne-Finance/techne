/**
 * Filter Click Handler - Works with CreditsManager
 * Only shows toast when user has insufficient credits
 */

document.addEventListener('DOMContentLoaded', () => {
    // Apply Filters button
    const applyBtn = document.getElementById('applyFiltersBtn');
    if (applyBtn) {
        applyBtn.addEventListener('click', (e) => {
            // Check if user has enough credits
            if (!window.CreditsManager?.tryUseFilter()) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
            // Has credits - proceed with filter
        });
    }

    // Note: Individual filter buttons don't trigger toast anymore
    // Only the "Apply Filters" button checks credits
});
