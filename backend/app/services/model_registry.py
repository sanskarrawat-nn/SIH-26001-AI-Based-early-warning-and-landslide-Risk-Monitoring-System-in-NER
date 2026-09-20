"""Only server-installed artifacts are eligible. No model binary upload endpoint."""
import hashlib,json,os,threading
from pathlib import Path
from app.core.config import settings
LOCK=threading.RLock()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def versions():
    root=Path(settings.MODEL_DIR).resolve();paths=[root/settings.MODEL_FILE_NAME]
    paths+=list((root/'candidates').glob('*.joblib')) if (root/'candidates').exists() else []
    found={}
    for p in paths:
        if p.is_file() and p.resolve().is_relative_to(root):
            sha=digest(p);found[sha]={'id':sha,'name':p.name,'path':p.resolve()}
    return found
def pointer():return Path(settings.MODEL_DIR)/'active-model.json'
def active_path():
    p=pointer()
    if p.exists():
        config=json.loads(p.read_text());root=Path(settings.MODEL_DIR).resolve();target=(root/config['relative_path']).resolve()
        if not target.is_relative_to(root) or not target.is_file() or digest(target)!=config['sha256']:raise ValueError('Active model integrity check failed')
        return str(target)
    return str(Path(settings.MODEL_DIR)/settings.MODEL_FILE_NAME)
def activate(ident):
    import joblib
    import pandas as pd
    from app.ml.feature_engineering import FEATURE_COLUMNS,engineer_features
    options=versions()
    if ident not in options:raise ValueError('Only server-installed candidate artifacts can be activated')
    target=options[ident]['path']
    # Pickle/joblib can execute code. Files must be installed by a trusted server operator.
    artifact=joblib.load(target)
    if artifact['feature_columns']!=FEATURE_COLUMNS:raise ValueError('Candidate feature schema is incompatible')
    sample=engineer_features({'rainfall_1h':1,'rainfall_24h':10,'rainfall_7d':30,'soil_moisture':30,'slope':20,'elevation':100,'terrain_roughness':10,'vegetation_index':.5})
    x=artifact['scaler'].transform(pd.DataFrame([{k:sample[k] for k in FEATURE_COLUMNS}]))
    probs=artifact['model'].predict_proba(x)
    import numpy as np
    if probs.shape!=(1,2) or not np.isfinite(probs).all() or not np.array_equal(artifact['model'].classes_,[0,1]):raise ValueError('Candidate inference validation failed')
    if not hasattr(artifact['base_estimator'],'estimators_'):raise ValueError('Candidate explanation estimator missing')
    with LOCK:
        dest=pointer();temp=dest.with_suffix('.tmp')
        temp.write_text(json.dumps({'sha256':ident,'relative_path':str(target.relative_to(Path(settings.MODEL_DIR).resolve()))}));os.replace(temp,dest)
    return ident
