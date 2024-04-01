import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js'
import { initializeAppCheck, ReCaptchaEnterpriseProvider } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app-check.js";

const firebaseConfig = {
	apiKey: "AIzaSyDgTSxuRWpfCKRLSFkurPSPx6ks8egLzME",
	authDomain: "madboulder.firebaseapp.com",
	databaseURL: "https://madboulder.firebaseio.com",
	projectId: "madboulder",
	storageBucket: "madboulder.appspot.com",
	messagingSenderId: "724331539515",
	appId: "1:724331539515:web:e8b4375814f1932a58801e",
	measurementId: "G-G8SP0G58JB"
};

if (location.hostname === "127.0.0.1") {
	self.FIREBASE_APPCHECK_DEBUG_TOKEN = true;
}

const app = initializeApp(firebaseConfig);
const appCheck = initializeAppCheck(app, {
	provider: new ReCaptchaEnterpriseProvider("6Ld3_aopAAAAABnAhZxwyF3ZLRVUJCk1gqFdTGX0"),
	isTokenAutoRefreshEnabled: true // Set to true to allow auto-refresh.
});