# Import necessary libraries
import firebase_admin as fa 
from firebase_admin import credentials, firestore,auth
from flask import Flask, request, jsonify, render_template,session,redirect
import joblib
import numpy as np
import pandas as pd
from threading import Timer
import uuid
import os
from datetime import datetime

# Initialize the Flask app
app = Flask(__name__,static_folder="assets")
app.secret_key = "secret_key"
# Load the trained model (ensure the model file path is correct)
cred = credentials.Certificate("firebase_credentials.json")
fa.initialize_app(cred)
db = firestore.client()
pending_transactions = {}
def expire_transaction(tran_id):
    if tran_id in pending_transactions:
        del pending_transactions[tran_id]

user_id=None

try:
    model = joblib.load('model.pkl')
except FileNotFoundError:
    raise FileNotFoundError("The model file 'model.pkl' was not found. Ensure it exists in the correct path.")

@app.route("/")
def home():
    user_id = session.get('uid')  # Safely get 'uid' from session
    if user_id:  # Check if user_id exists
        return redirect(f"/dashboard/{user_id}")
    return render_template("index.html")

@app.route('/getApprovalTransactions', methods=['GET'])
def get_approval_transactions():
    try:
        user_id = session.get('uid')
        transactions = []

        # Fetch only pending transactions for the logged-in user
        docs = (
            db.collection('pending_transactions')
            .where('approval', '==', user_id)
            .where('status', '==', 'pending')
            .stream()
        )

        for doc in docs:
            transaction = doc.to_dict()
            from_user_id = transaction['from_user']

            # Fetch full name of the 'from_user' (transaction initiator)
            user_doc = db.collection('users').document(from_user_id).get()
            if user_doc.exists:
                user = user_doc.to_dict()
                transaction['from_user_name'] = user['fullName']
            else:
                transaction['from_user_name'] = 'Unknown'

            transactions.append(transaction)

        return jsonify(transactions), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching transactions', 'error': str(e)}), 500
    
# @app.route('/dashbaord')
# def dashbaord():
#     return render_template("dashbaord.html")

# Login Route
@app.route('/login')
def login():
    user_id = session.get('uid')  # Safely get 'uid' from session
    if user_id:  # Check if user_id exists
        return redirect(f"/dashboard/{user_id}")
    return render_template("login.html")
    # return render_template("login.html") 

@app.route('/creditProfiling')
def creditProfiling():
    try:
        userId=session['uid']
        print(f"Dashboard route accessed for userId: {userId}")

        # Fetch the user document snapshot
        user_snapshot = db.collection("users").document(userId).get()

        # Check if the document exists
        if not user_snapshot.exists:
            print(f"No user found with userId: {userId}")
            return render_template("credit_profiling.html", error="User not found")

        # Convert the document snapshot to a dictionary
        user_data = user_snapshot.to_dict()
        print(f"Fetched user data: {user_data}")

        # Render the credit profiling page with user data
        return render_template("creditProfiling.html", user=user_data)
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return render_template("creditProfiling.html", error=f"An error occurred: {e}")



# Signup Route
@app.route('/signup')
def signup():
    user_id = session.get('uid')  # Safely get 'uid' from session
    if user_id:  # Check if user_id exists
        return redirect(f"/dashboard/{user_id}")
    return render_template("signup.html")

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
        age=data.get("age")
        fullName=data.get('fullName')
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
            "username": username,
            "email": email,
            "phone": phone,
            "currentBalance": 0,
            "totalTransaction": 0,
            'age':age,
            "totalLend":0,
            "score": 0,
            'fullName': fullName,
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        #print(user.uid)
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

@app.route('/transactions')
def transactions():
    return render_template("transaction.html", user=session['uid'])

@app.route('/getUsers', methods=['GET'])
def get_users():
    try:
        users = []
        docs = db.collection('users').stream()
        for doc in docs:
            user = doc.to_dict()
            if user['userId'] != session['uid']:  # Exclude logged-in user
                users.append({
                    'user_id': user['userId'],
                    'fullname': user['fullName'],
                    'username': user['username'],
                })
        return jsonify(users), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching users', 'error': str(e)}), 500

# Create a new transaction (store in pending_transactions)
@app.route('/createTransaction', methods=['POST'])
def create_transaction():
    try:
        data = request.json
        transaction_ref = db.collection('pending_transactions').document()
        transaction_ref.set({
            'transaction_id': transaction_ref.id,
            'from_user': session['uid'],
            'approval': data['approval'],
            'amount': data['amount'],
            'type': data['type'],
            'created_at': datetime.utcnow(),
            'status': 'pending',
        })
        return jsonify({'message': 'Transaction stored in pending_transactions!', 'transaction_id': transaction_ref.id}), 200
    except Exception as e:
        return jsonify({'message': 'Error creating transaction', 'error': str(e)}), 500

# Approve a transaction
@app.route('/approveTransaction', methods=['POST'])
def approve_transaction():
    try:
        data = request.json
        transaction_id = data['transaction_id']
        user_id = session.get('uid')  # Safely get 'uid' from session

        # Fetch the transaction from pending_transactions
        transaction_ref = db.collection('pending_transactions').document(transaction_id)
        transaction = transaction_ref.get()
       
      
        transaction_data = transaction.to_dict()
        
        
        # Ensure only the designated approver can approve
        if transaction_data['approval'] != user_id:
            return jsonify({'message': 'Unauthorized approval attempt'}), 403
        print(transaction_data)
        # Determine payer and payee based on transaction type
        if transaction_data['type'] == 'Lend':
            payer_ref = db.collection('users').document(transaction_data['from_user'])
            payee_ref = db.collection('users').document(transaction_data['approval'])
        elif transaction_data['type'] == 'Borrow':
            payer_ref = db.collection('users').document(transaction_data['approval'])
            payee_ref = db.collection('users').document(transaction_data['from_user'])
        else:
            return jsonify({'message': 'Invalid transaction type'}), 400

        # Fetch and validate payer and payee documents
        payer_doc = payer_ref.get()
        payee_doc = payee_ref.get()
      

        payer_data = payer_doc.to_dict()
        payee_data = payee_doc.to_dict()
        
        # Update the payer's and payee's balances and stats
        if transaction_data['type'] == 'Borrow':
            updated_payer_data = {
                'currentBalance': int(payer_data['currentBalance']) - int(transaction_data['amount']),
                'totalTransaction': int(payer_data['totalTransaction']) + 1,
                'totalLend': int(payer_data['totalLend']) + int(transaction_data['amount']),
            }
            updated_payee_data = {
                'currentBalance': int(payee_data['currentBalance']) + int(transaction_data['amount']),
                'totalTransaction': int(payee_data['totalTransaction']) + 1,
                'totalBorrowed': int(payee_data['totalBorrowed']) + int(transaction_data['amount']),
            }
        elif transaction_data['type'] == 'Lend':
            updated_payer_data = {
                'currentBalance': int(payer_data['currentBalance']) - int(transaction_data['amount']),
                'totalTransaction': int(payer_data['totalTransaction']) + 1,
                'totalBorrowed': int(payer_data['totalBorrowed']) + int(transaction_data['amount']),
            }
            updated_payee_data = {
                'currentBalance': int(payee_data['currentBalance']) + int(transaction_data['amount']),
                'totalTransaction': int(payee_data['totalTransaction']) + 1,
                'totalLend': int(payee_data['totalLend']) + int(transaction_data['amount']),
            }

        # Apply updates
        payer_ref.update(updated_payer_data)
        payee_ref.update(updated_payee_data)
        print(payer_ref)
        # Move transaction to approved_transactions
        db.collection('approved_transactions').document(transaction_id).set({
            **transaction_data,
            'approved_at': datetime.utcnow(),
            'status': 'approved',
             'payer': payer_data.get('userId'),
            'payee': payee_data.get('userId'),
        })

        # Remove transaction from pending_transactions
        transaction_ref.delete()

        return jsonify({'message': 'Transaction approved and moved to approved_transactions collection!'}), 200

    except Exception as e:
        print(str(e))
        return jsonify({'message': 'Error approving transaction', 'error': str(e)}), 500

# Ledger route
@app.route('/ledger', methods=['GET'])
def ledger():
    try:
        user_id = session.get('uid')
        approved_transactions = db.collection('approved_transactions').stream()
        print(approved_transactions)
        ledger_entries = []
        for doc in approved_transactions:
            transaction = doc.to_dict()
            print(transaction)
            #print(transaction)
            if transaction['payer'] == user_id or transaction['payee'] == user_id:
                # Fetch payer and payee names
                payer = db.collection('users').document(transaction['payer']).get().to_dict()
                payee = db.collection('users').document(transaction['payee']).get().to_dict()

                ledger_entries.append({
                    'amount': transaction['amount'],
                    'type': transaction['type'],
                    'date': transaction['approved_at'],
                    'from_user': f"{payer['fullName']} ({payer['username']})",
                    'to_user': f"{payee['fullName']} ({payee['username']})"
                })
        print(ledger_entries)
        return jsonify(ledger_entries), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching ledger data', 'error': str(e)}), 500

@app.route('/ledgerPage')
def ledgerPage():
    return render_template('ledger.html', user=session['uid'])

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
        print(data)
        # Ensure all required fields are present in the input
        required_fields = ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing fields in input data'}), 400
        print(data)
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
        print(new_data)

        # Predict the credit score
        predicted_score = model.predict(new_data)
        print(predicted_score)
        # Return the prediction as a JSON response
        return jsonify({'credit_score': int(predicted_score[0])})
    
    except Exception as e:
        # Handle unexpected errors
        return jsonify({'error': str(e)}), 500

    # try:
    #     # Get the data from the request (JSON format)
        
    #     data = request.get_json(force=True)
    #     print(data)
    #     # Ensure all required fields are present in the input
    #     required_fields = ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7']
    #     if not all(field in data for field in required_fields):
    #         return jsonify({'error': 'Missing fields in input data'}), 400
        
    #     # Create a DataFrame for the input data
    #     new_data = pd.DataFrame([{
    #         'Age': data['f1'],
    #         'TotalDebt': data['f2'],
    #         'MonthlyExpenses': data['f3'],
    #         'NumberOfTransactions': data['f4'],
    #         'TotalAmountLent': data['f5'],
    #         'LastPaymentStatus': data['f6'],
    #         'Wallet': data['f7'],
    #     }])

    #     # Predict the credit score
    #     predicted_score = model.predict(new_data)
        
    #     # Return the prediction as a JSON response
    #     return jsonify({'credit_score': int(predicted_score[0])})
    
    # except Exception as e:
    #     # Handle unexpected errors
    #     return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run the Flask app
    # app.run(debug=True)
    port = int(os.environ.get('PORT', 5000))  # Use PORT environment variable or default to 4000
    app.run(host='0.0.0.0', port=port)
