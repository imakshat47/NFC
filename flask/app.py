# Import necessary libraries
from flask import Flask, request, jsonify
import joblib
import numpy as np

# Initialize the Flask app
app = Flask(__name__)

# Load the trained model (assuming it's saved as 'model.pkl')
# model = joblib.load('model.pkl')

@app.route('/predict', methods=['POST'])
def predict():
    # Get the data from the request (JSON format)
    data = request.get_json(force=True)
    
    # Make a prediction
    # prediction = model.predict(features)
    
    # Return the prediction as a JSON response prediction[0]
    return jsonify({'prediction': data['f1']})

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True)
