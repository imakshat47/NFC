# Steps
1. python -m venv nfc
2. .\nfc\Scripts\activate
3. Install Requirements 
pip install flask
pip install joblib
pip install numpy
pip install scikit-learn
pip install pandas
pip install firebase_admin

4. python app.py
Keep Server Running.

5. Open a new cmd window:
Invoke-WebRequest -Uri "http://127.0.0.1:5000/predict" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"f1": 10, "f2": false}'

Last Modified:
26/11 8:45