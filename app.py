# Import necessary libraries
from flask import Flask, request, jsonify, render_template,session
import joblib
import numpy as np
import pandas as pd

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = "secret_key"
# Load the trained model (ensure the model file path is correct)
try:
    model = joblib.load('model.pkl')
except FileNotFoundError:
    raise FileNotFoundError("The model file 'model.pkl' was not found. Ensure it exists in the correct path.")

@app.route("/")
def home():
    return render_template("index.html")

# @app.route('/dashbaord')
# def dashbaord():
#     return render_template("dashbaord.html")

@app.route('/login')
def login():
    return render_template("login1.html")

@app.route("/test")
def test():
    """Render the dashboard for logged-in users."""
    # Check if the user is logged in
    if "email" not in session:
        alert("You need to log in first.", "danger")
        return redirect(url_for("home"))
    return render_template("test.html", email=session["email"])

@app.route("/set_session", methods=["POST"])
def set_session():
    """
    Set the user session after successful login from Firebase.
    This route expects a JSON payload with an 'email' field.
    """
    # Get the JSON data from the request
    data = request.json 
    # This assumes the request body is JSON
    email = data.get("email")

    if email:
        session["email"] = email  # Set email in session
        return {"message": "Session set successfully"} ,200
    return {"error": "Email not provided"}, 400

@app.route("/logout")
def logout():
    """Log the user out."""
    session.pop("email", None)  # Remove email from session
    #flash("You have been logged out.", "info")
    return  render_template("index.html")
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
