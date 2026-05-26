import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import pickle, os

data_path = '/app/data/ml_training_data.csv'
model_path = '/tmp/model'

df = pd.read_csv(data_path)
features = ['AGE_YRS','DAYS_SINCE_PM','N_FAILURES','TOTAL_DOWNTIME_HRS','AVG_TEMP','AVG_VIB','AVG_PRES']
X = df[features].fillna(0)
y = df['FAILED_WITHIN_30D']

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = LogisticRegression()
model.fit(X_scaled, y)

os.makedirs(model_path, exist_ok=True)
with open(f'{model_path}/model.pkl', 'wb') as f:
    pickle.dump({'model': model, 'scaler': scaler}, f)

print("Training complete. Model saved to /tmp/model/model.pkl")
