export const completeUserProfile = (name, isContributor, wantsNewsletter) => {
    return fetch('/complete-profile-info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, isContributor, wantsNewsletter })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to complete profile.');
        }
        return response.json();
    })
    .catch(error => {
        console.error("Error completing profile:", error);
        throw error;
    });
}