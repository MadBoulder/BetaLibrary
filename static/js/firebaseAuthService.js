import { getAuth, sendPasswordResetEmail, GoogleAuthProvider, signInWithPopup, signInWithEmailAndPassword } from 'https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js';

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

export const signInWithGoogle = (profileCompleteUrl) => {
    const provider = new GoogleAuthProvider();
	const auth = getAuth();
    return signInWithPopup(auth, provider)
        .then(userCredential => userCredential.user.getIdToken())
        .then(idToken => verifyTokenWithServer(idToken))
        .then(() => checkUserProfileCompletion())
        .then(isComplete => {
			if (isComplete) {
                window.location.href = profileCompleteUrl;
            } else {
				window.location.href = '/complete-profile';
            }
        });
}


export const verifyTokenWithServer = (idToken) => {
    return fetch('/verify-token', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + idToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.message !== "Token verified") {
            throw new Error(data.error || 'Token verification failed');
        }
    });
}


export const checkUserProfileCompletion = () => {
    return fetch('/check-profile-completion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => data.isComplete);

}