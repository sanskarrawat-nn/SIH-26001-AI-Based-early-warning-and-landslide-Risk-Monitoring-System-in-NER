"""Validate source-labelled observations; train a separate candidate on an earlier time window.
Never replaces the operational model automatically. Run: python -m app.ml.observations file.csv
"""
import csv, io, json, hashlib
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from app.schemas.prediction import PredictionInput
from app.ml.feature_engineering import engineer_features, FEATURE_COLUMNS

COLUMNS=['location_id','observed_at','source','verified','landslide_occurred','latitude','longitude','rainfall_1h','rainfall_24h','rainfall_7d','soil_moisture','slope','elevation','terrain_roughness','vegetation_index']

def validate_csv(text):
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    missing=sorted(set(COLUMNS)-set(reader.fieldnames or []))
    if missing: raise ValueError('Missing columns: '+', '.join(missing))
    rows=[]; errors=[]; seen=set()
    for n,row in enumerate(reader,2):
        if n>50001: raise ValueError('Maximum 50,000 rows per dataset')
        try:
            timestamp=datetime.fromisoformat(row['observed_at'].replace('Z','+00:00'))
            if timestamp.tzinfo is None: raise ValueError('observed_at needs an explicit timezone')
            if row['verified'].strip().lower() not in ['true','1']: raise ValueError('Only verified observations are accepted')
            if len(row['source'].strip())<3: raise ValueError('A source reference is required')
            if row['landslide_occurred'] not in ['0','1']: raise ValueError('landslide_occurred must be 0 or 1')
            data=PredictionInput(**{k:row[k] for k in PredictionInput.model_fields if k in row})
            from datetime import timezone
            stamp=timestamp.astimezone(timezone.utc).isoformat()
            key=(data.location_id,stamp)
            if key in seen: raise ValueError('Duplicate location/time observation')
            seen.add(key)
            if data.rainfall_1h>data.rainfall_24h or data.rainfall_24h>data.rainfall_7d: raise ValueError('Rainfall must satisfy 1h <= 24h <= 7d')
            rows.append({**data.model_dump(),'observed_at':stamp,'source':row['source'].strip(),'landslide_occurred':int(row['landslide_occurred'])})
        except Exception as e:
            errors.append({'row':n,'error':str(e)[:350]})
    labels={str(k):sum(r['landslide_occurred']==k for r in rows) for k in [0,1]}
    return rows,{'valid':not errors and bool(rows),'rows':len(rows),'errors':errors[:100],'error_count':len(errors),'class_counts':labels,'sources':sorted({r['source'] for r in rows}),'warning':'Source and verification fields are declarations; independently audit provenance before use. Include confirmed non-event observations.'}

def train_candidate(text, output):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score,precision_score,recall_score,f1_score,roc_auc_score,confusion_matrix,brier_score_loss
    import joblib
    rows,summary=validate_csv(text)
    if not summary['valid']: raise ValueError(json.dumps(summary))
    rows=sorted(rows,key=lambda r:r['observed_at'])
    if len(rows)<100: raise ValueError('At least 100 audited observations required for candidate training')
    cutoff=rows[int(len(rows)*.8)]['observed_at']
    train=[r for r in rows if r['observed_at']<cutoff];test=[r for r in rows if r['observed_at']>=cutoff]
    if any(sum(r['landslide_occurred']==k for r in train)<5 for k in [0,1]) or any(sum(r['landslide_occurred']==k for r in test)<5 for k in [0,1]):
        raise ValueError('Both temporal partitions need at least five observations of each class')
    def matrix(rs): return pd.DataFrame([engineer_features(r) for r in rs])[FEATURE_COLUMNS]
    scaler=StandardScaler(); x=scaler.fit_transform(matrix(train));xt=scaler.transform(matrix(test))
    y=[r['landslide_occurred'] for r in train]; yt=[r['landslide_occurred'] for r in test]
    base=RandomForestClassifier(n_estimators=160,max_depth=12,min_samples_leaf=2,class_weight='balanced',random_state=42,n_jobs=-1)
    model=CalibratedClassifierCV(estimator=base,method='sigmoid',cv=5);model.fit(x,y);base.fit(x,y)
    yp=model.predict(xt);prob=model.predict_proba(xt)[:,1]
    metrics={'accuracy':accuracy_score(yt,yp),'precision':precision_score(yt,yp,zero_division=0),'recall':recall_score(yt,yp,zero_division=0),'f1_score':f1_score(yt,yp,zero_division=0),'roc_auc':roc_auc_score(yt,prob),'brier_score':brier_score_loss(yt,prob),'confusion_matrix':confusion_matrix(yt,yp).tolist(),'feature_importances':sorted(zip(FEATURE_COLUMNS,base.feature_importances_.tolist()),key=lambda x:-x[1]),'model_architecture':'Observational calibrated Random Forest candidate','training_rows':len(train),'test_rows':len(test),'split':'temporal holdout; calibration uses training partition only','cutoff':cutoff,'sources':summary['sources'],'dataset_sha256':hashlib.sha256(text.encode()).hexdigest(),'data_type':'USER_DECLARED_VERIFIED_OBSERVATIONS','deployment_status':'CANDIDATE_NOT_PROMOTED'}
    Path(output).mkdir(parents=True,exist_ok=True)
    joblib.dump({'model':model,'base_estimator':base,'scaler':scaler,'feature_columns':FEATURE_COLUMNS,'metrics':metrics},Path(output)/'candidate.joblib')
    (Path(output)/'evaluation.json').write_text(json.dumps(metrics,indent=2))
    return metrics

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('csv');parser.add_argument('--output',default='candidate-model');a=parser.parse_args()
    print(json.dumps(train_candidate(Path(a.csv).read_text(),a.output),indent=2))
