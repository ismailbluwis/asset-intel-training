from hdbcli import dbapi
import pandas as pd
from datetime import datetime

# HANA connection
conn = dbapi.connect(
    address="48e539b6-6ba6-4891-9538-727dd496988b.hna1.prod-us10.hanacloud.ondemand.com",
    port=443,
    user="DBADMIN",
    password="Admin123",
    encrypt=True,
    sslValidateCertificate=True
)
cur = conn.cursor()

# Read assets
cur.execute('SELECT ASSET_ID, INSTALL_DATE, EXPECTED_LIFE_YEARS, STATUS FROM "ASSET_MASTER"."ASSETS"')
assets = pd.DataFrame(cur.fetchall(), columns=["ASSET_ID","INSTALL_DATE","EXPECTED_LIFE_YEARS","STATUS"])

# Read latest sensor readings per asset
cur.execute('''
    SELECT ASSET_ID, TAG_NAME, AVG(TAG_VALUE) AS AVG_VAL
    FROM "IOT_SENSOR"."SENSOR_READINGS"
    GROUP BY ASSET_ID, TAG_NAME
''')
sensors = pd.DataFrame(cur.fetchall(), columns=["ASSET_ID","TAG_NAME","AVG_VAL"])

# Read work orders per asset
cur.execute('SELECT ASSET_ID, COUNT(*) AS WO_COUNT FROM "EAM_PM"."WORK_ORDERS" GROUP BY ASSET_ID')
wo = pd.DataFrame(cur.fetchall(), columns=["ASSET_ID","WO_COUNT"])

# Read failure history per asset
cur.execute('SELECT ASSET_ID, COUNT(*) AS FAIL_COUNT, AVG(REPAIR_COST) AS AVG_COST FROM "EAM_PM"."FAILURE_HISTORY" GROUP BY ASSET_ID')
fh = pd.DataFrame(cur.fetchall(), columns=["ASSET_ID","FAIL_COUNT","AVG_COST"])

today = datetime.today()

rows = []
for _, a in assets.iterrows():
    aid = a["ASSET_ID"]

    # Age score (0-100, older = lower)
    try:
        install = pd.to_datetime(a["INSTALL_DATE"])
        age_years = (today - install).days / 365
        life = float(a["EXPECTED_LIFE_YEARS"]) if a["EXPECTED_LIFE_YEARS"] else 20
        age_score = max(0, round(100 * (1 - age_years / life), 2))
        rul_days = max(0, int((life - age_years) * 365))
    except:
        age_score, rul_days = 50.0, 3000

    # Sensor score
    asset_sensors = sensors[sensors["ASSET_ID"] == aid]
    temp = asset_sensors[asset_sensors["TAG_NAME"].str.contains("TEMP", case=False)]["AVG_VAL"].mean()
    vib  = asset_sensors[asset_sensors["TAG_NAME"].str.contains("VIB",  case=False)]["AVG_VAL"].mean()
    pres = asset_sensors[asset_sensors["TAG_NAME"].str.contains("PRES", case=False)]["AVG_VAL"].mean()
    temp = round(float(temp), 2) if pd.notna(temp) else 50.0
    vib  = round(float(vib),  4) if pd.notna(vib)  else 1.0
    pres = round(float(pres), 2) if pd.notna(pres) else 80.0
    sensor_score = round(max(0, min(100, 100 - (vib * 10))), 2)

    # Maintenance score
    wo_count = int(wo[wo["ASSET_ID"] == aid]["WO_COUNT"].values[0]) if aid in wo["ASSET_ID"].values else 0
    maint_score = round(max(0, 100 - wo_count * 10), 2)

    # Failure score
    fail_count = int(fh[fh["ASSET_ID"] == aid]["FAIL_COUNT"].values[0]) if aid in fh["ASSET_ID"].values else 0
    failure_score = round(max(0, 100 - fail_count * 25), 2)

    # Overall health score (weighted average)
    health_score = int(round(
        0.3 * sensor_score +
        0.25 * maint_score +
        0.25 * failure_score +
        0.2  * age_score
    ))

    # Failure probability (inverse of health)
    failure_prob = round(max(0.01, min(0.99, 1 - health_score / 100)), 4)

    # Status
    if health_score >= 80:
        status = "Healthy"
    elif health_score >= 65:
        status = "Monitored"
    elif health_score >= 45:
        status = "At Risk"
    else:
        status = "Critical"

    rows.append((aid, health_score, sensor_score, maint_score, failure_score,
                 age_score, failure_prob, rul_days, status, temp, vib, pres, "FORMULA"))

# Clear and reload
cur.execute('DELETE FROM "ASSET_MASTER"."ASSET_HEALTH_SCORES"')
for r in rows:
    cur.execute('''
        INSERT INTO "ASSET_MASTER"."ASSET_HEALTH_SCORES"
        (ASSET_ID, HEALTH_SCORE, SENSOR_SCORE, MAINT_SCORE, FAILURE_SCORE,
         AGE_SCORE, FAILURE_PROB, RUL_DAYS, STATUS, LATEST_TEMP, LATEST_VIB,
         LATEST_PRES, SCORE_ENGINE)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', r)

conn.commit()
print(f"Scored {len(rows)} assets and wrote to ASSET_HEALTH_SCORES.")
cur.close()
conn.close()
