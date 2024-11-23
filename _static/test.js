// Import Firebase modules
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.23.0/firebase-app.js";
import { getAuth, signInWithEmailAndPassword } from "https://www.gstatic.com/firebasejs/9.23.0/firebase-auth.js";

// Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyAg-bCY1rimrwDD-Kjy7yRZmlNluhWAlYE",
    authDomain: "nfcnexfinco.firebaseapp.com",
    projectId: "nfcnexfinco",
    storageBucket: "nfcnexfinco.appspot.com",
    messagingSenderId: "815012236908",
    appId: "1:815012236908:web:a52ecf0655af61f0829249",
    measurementId: "G-B2WKLRQE32"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Handle login form submission
document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault(); // Prevent default form submission
    console.log(document.getElementById("credentials_identity"))
    const email = document.getElementById("credentials_identity").value;
    const password = document.getElementById("credentials_password").value;
    console.log(email)
    console.log(password)
    try {
        // Sign in with Firebase Authentication
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        console.log("Logged in:", userCredential.user);

        // Send the email to Flask backend to set the session
        const response = await fetch("/set_session", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",  // Ensure correct Content-Type
            },
            body: JSON.stringify({ uid: userCredential.user.uid })  // Serialize email as JSON
        });

        if (response.ok) {
            window.location.href = "/profile";  // Redirect to dashboard
        } else {
            console.error("Failed to set session:", await response.json());
        }
    } catch (error) {
        console.error("Login failed:", error.message);
        alert("Login failed: " + error.message);
    }
});