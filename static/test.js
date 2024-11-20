
const firebaseConfig = {
    apiKey: "AIzaSyAg-bCY1rimrwDD-Kjy7yRZmlNluhWAlYE",
authDomain: "nfcnexfinco.firebaseapp.com",
projectId: "nfcnexfinco",
storageBucket: "nfcnexfinco.appspot.com",
messagingSenderId: "815012236908",
appId: "1:815012236908:web:a52ecf0655af61f0829249",
measurementId: "G-B2WKLRQE32"
};
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

// Login Form Submission
document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault(); // Prevent form submission

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        // Sign in with Firebase Authentication
        const userCredential = await auth.signInWithEmailAndPassword(email, password);
        console.log("Logged in:", userCredential.user);

        // Send the email to the Flask backend to set the session
        const response = await fetch("/set_session", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email: userCredential.user.email })
        });

        if (response.ok) {
            // Redirect to the dashboard
            window.location.href = "/test";
        } else {
            console.error("Failed to set session:", await response.json());
        }
    } catch (error) {
        console.error("Error:", error.message);
        alert("Login failed: " + error.message);
    }
});