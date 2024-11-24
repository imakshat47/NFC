# Import necessary libraries
from flask import Flask, request, jsonify, render_template,session,redirect
import firebase_admin as fa 
from firebase_admin import credentials, firestore,auth
import joblib
import numpy as np
import pandas as pd
from threading import Timer
import uuid
from datetime import datetime

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = "secret_key"
# Load the trained model (ensure the model file path is correct)
cred = credentials.Certificate("firebase_credentials.json")
fa.initialize_app(cred)
db = firestore.client()
print(db)
try:
    model = joblib.load('model.pkl')
except FileNotFoundError:
    raise FileNotFoundError("The model file 'model.pkl' was not found. Ensure it exists in the correct path.")
pending_transactions = {}

# Function to remove expired transactions
def expire_transaction(tran_id):
    if tran_id in pending_transactions:
        del pending_transactions[tran_id]
@app.route("/")
def home():
    return render_template("index.html")

# @app.route('/dashbaord')
# def dashbaord():
#     return render_template("dashbaord.html")
# Login Route
@app.route('/login')

# Signup Route@app.route('/login')
def login():
    print("Login page accessed")
    return render_template("login.html")
print(pending_transactions)
# Signup Route
@app.route('/signup')
def signup():
    return render_template("signup.html")
@app.route('/transactions')
def transactions():
    return render_template("transaction.html")


@app.route('/getUsers', methods=['GET'])
def get_users():
    try:
        users = []
        docs = db.collection('users').stream()
        for doc in docs:
            user = doc.to_dict()
            if user['userId'] != session['uid']:
                users.append({
                    'user_id': user['userId'],
                    'fullname': user['fullName'],
                    'username': user['username'],
                })
        return jsonify(users), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching users', 'error': str(e)}), 500

@app.route('/getApprovalTransactions', methods=['GET'])
def get_approval_transactions():
    try:
        user_id = session['uid']
        transactions = []
        docs = db.collection('transactions').where('approval', '==', user_id).stream()
        
        for doc in docs:
            transaction = doc.to_dict()
            from_user_id = transaction['from_user']
            
            # Fetch full name of the 'from_user' (transaction initiator)
            user_doc = db.collection('users').document(from_user_id).get()
            if user_doc.exists:
                user = user_doc.to_dict()
                transaction['from_user_name'] = user['fullName']
            transactions.append(transaction)
        
        return jsonify(transactions), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching transactions', 'error': str(e)}), 500

@app.route('/createTransaction', methods=['POST'])
def create_transaction():
    try:
        data = request.json
        transaction_ref = db.collection('transactions').document()
        user_id = session['uid']
        approval = data['approval']
        transaction_type = data['type']
        payee = approval if transaction_type == 'debit' else user_id
        payer = user_id if transaction_type == 'debit' else approval

        transaction_ref.set({
            'transaction_id': transaction_ref.id,
            'from_user': user_id,
            'approval': approval,
            'amount': data['amount'],
            'type': transaction_type,
            'payee': payee,
            'payer': payer,
            'created_at': datetime.utcnow(),
            'status': 'pending'
        })
        return jsonify({'message': 'Transaction created successfully!', 'transaction_id': transaction_ref.id}), 200
    except Exception as e:
        return jsonify({'message': 'Error creating transaction', 'error': str(e)}), 500

@app.route('/approveTransaction', methods=['POST'])
def approve_transaction():
    try:
        data = request.json
        transaction_id = data['transaction_id']
        user_id = session['uid']
        transaction_ref = db.collection('transactions').document(transaction_id)
        transaction = transaction_ref.get()

        if not transaction.exists:
            return jsonify({'message': 'Transaction not found'}), 404

        transaction_data = transaction.to_dict()
        if transaction_data['approval'] != user_id:
            return jsonify({'message': 'Unauthorized approval attempt'}), 403

        # Move transaction to 'approved_transactions' collection
        db.collection('approved_transactions').document(transaction_id).set({
            **transaction_data,
            'approved_at': datetime.utcnow(),
            'status': 'approved'
        })

        # Update status in the 'transactions' collection to 'approved'
        transaction_ref.update({'status': 'approved'})
        
        return jsonify({'message': 'Transaction approved successfully!'}), 200
    except Exception as e:
        return jsonify({'message': 'Error approving transaction', 'error': str(e)}), 500


# Register Route
@app.route("/register", methods=["POST"])
def register():
    """Handle user registration."""
    try:
        print("Register route accessed")
        data = request.json
        print("Received Data:", data)

        # Extract data fields
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        phone = data.get("phone")
        fullname=data.get("fullname")
        # Create Firebase Authentication user
        try:
            user = auth.create_user(
                email=email,
                password=password,
                display_name=username
            )
        except Exception as e:
            print("Error creating user:", e)
            return jsonify({"message": str(e)}), 400

        # Save additional user details to Firestore
        db.collection("users").document(user.uid).set({
            "userId": user.uid,
            "fullName":fullname,
            "username": username,
            "email": email,
            "phone": phone,
            "currentBalance": 0,
            "score": 0,
            "totalBorrowed": 0,
            "totalLend":0,
            "totalTransaction":0,
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        print(user.uid)
        print(f"User {user.uid} registered successfully")
        session['uid']=user.uid
        return jsonify({"message": "User registered successfully!", "userId": user.uid}), 200
    except Exception as e:
        print("Error during registration:", e)
        return jsonify({"message": str(e)}), 500

# Dashboard Route
@app.route("/dashboard/<userId>")
def dashboard(userId):
    """Render the dashboard for the specific user based on userId."""
    try:
        print(f"Dashboard route accessed for userId: {userId}")

        # Fetch user document snapshot
        user_snapshot = db.collection("users").document(userId).get()

        # Check if the document exists
        if not user_snapshot.exists:
            print(f"No user found with userId: {userId}")
            return "User not found", 404

        # Convert the document snapshot to a dictionary
        user = user_snapshot.to_dict()
        print(f"Fetched user data: {user}")

        # Render the dashboard with user data
        return render_template("profile.html", user=user)
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return f"An error occurred: {e}", 500

# Profile Route (Reusing Dashboard Logic)
@app.route("/profile")
def profile():
    """Render the profile for the logged-in user."""
    print(session['uid'])
    if "uid" not in session:
        print("User not logged in")
        return redirect("/login")

    userId = session["uid"]  # Use session-stored UID
    print(f"Redirecting to dashboard for UID: {userId}")
    return redirect(f"/dashboard/{userId}")

# Set Session Route
@app.route("/set_session", methods=["POST"])
def set_session():
    """Set the user session after successful login."""
    data = request.json
    uid = data.get("uid")
    print(f"Set session called with UID: {uid}")  # Debug

    if uid:
        session["uid"] = uid
        print(f"Session set for UID: {session['uid']}")  # Debug
        return jsonify({"message": "Session set successfully!"}), 200
    return jsonify({"error": "UID not provided"}), 400

# Logout Route
@app.route("/logout")
def logout():
    """Log the user out."""
    session.pop("uid", None)  # Remove UID from session
    print("User logged out")
    return redirect("/login")
# In-memory data storage
users = []  # List of users
expenses = []  # List of expenses
balances = {}  # Balances between users

@app.route("/dashbaord")
def dashbaord():
    return render_template("home.html", users=users, balances=balances, expenses=expenses)

# Add a new user
@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form.get('name')
    
    if not name:
        return redirect(url_for('home', error="User name is required"))

    if name in users:
        return redirect(url_for('home', error="User already exists"))

    users.append(name)
    balances[name] = {}
    for user in users:
        if user != name:
            balances[name][user] = 0
            balances[user][name] = 0

    return redirect(url_for('home'))

# Add an expense
@app.route('/add_expense', methods=['POST'])
def add_expense():
    payer = request.form.get('payer')
    amount = float(request.form.get('amount'))
    participants = request.form.getlist('participants')

    if not payer or not amount or not participants:
        return redirect(url_for('home', error="All fields are required"))

    if payer not in users or any(p not in users for p in participants):
        return redirect(url_for('home', error="Invalid users"))

    # Split the amount equally
    split_amount = amount / len(participants)
    for participant in participants:
        if participant != payer:
            balances[payer][participant] += split_amount
            balances[participant][payer] -= split_amount

    expenses.append({'payer': payer, 'amount': amount, 'participants': participants})
    return redirect(url_for('home'))

@app.route('/reset', methods=['POST'])
def reset_balances():
    global balances
    balances = {user: {u: 0 for u in users if u != user} for user in users}
    return redirect(url_for('home'))


@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get the data from the request (JSON format)
        data = request.get_json(force=True)
        
        # Ensure all required fields are present in the input
        required_fields = ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing fields in input data'}), 400
        
        # Create a DataFrame for the input data
        new_data = pd.DataFrame([{
            'Age': data['f1'],
            'TotalDebt': data['f2'],
            'MonthlyExpenses': data['f3'],
            'NumberOfTransactions': data['f4'],
            'TotalAmountLent': data['f5'],
            'LastPaymentStatus': data['f6'],
            'Wallet': data['f7'],
        }])

        # Predict the credit score
        predicted_score = model.predict(new_data)
        
        # Return the prediction as a JSON response
        return jsonify({'credit_score': int(predicted_score[0])})
    
    except Exception as e:
        # Handle unexpected errors
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True)
