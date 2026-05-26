import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import pickle, json, os

data_path = '/app/data/ml_training_data.csv'
model_path = '/app/model'

df = pd.read_csv(data_path)
features = ['AVG_TEMPERATURE','AVG_VIBRATION','AVG_PRESSURE','WORK_ORDER_COUNT','FAILURE_COUNT','AVG_INSPECTION_SCORE','ASSET_AGE_YEARS','MAINTENANCE_FREQ']
X = df[features].fillna(0)
y = df['FAILURE_LABEL']

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = LogisticRegression()
model.fit(X_scaled, y)

os.makedirs(model_path, exist_ok=True)
with open(f'{model_path}/model.pkl', 'wb') as f:
    pickle.dump({'model': model, 'scaler': scaler}, f)

print("Training complete. Model saved.")
