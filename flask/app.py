# Import necessary libraries
from flask import Flask, request, jsonify
import joblib
import numpy as np
import pandas as pd

# Initialize the Flask app
app = Flask(__name__)

# Load the trained model (assuming it's saved as 'model.pkl')
model = joblib.load('model.pkl')

@app.route('/predict', methods=['POST'])
def predict():
    # Get the data from the request (JSON format)
    data = request.get_json(force=True)
    
    # Make a prediction
    new_data = pd.DataFrame({
        'Age': data['f1'],
        'TotalDebt': data['f2'],
        'MonthlyExpenses': data['f3'],
        'NumberOfTransactions': data['f4'],
        'TotalAmountLent': data['f5'],
        'LastPaymentStatus':data['f6'],
        'Wallet': data['f7'],
    })

    # Predict the credit score
    predicted_score = model.predict(new_data)
    # model.predict(features)
    
    # Return the prediction as a JSON response
    return jsonify({'credit_score': predicted_score[0]})

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True)
