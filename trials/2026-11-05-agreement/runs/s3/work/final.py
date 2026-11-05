"""Fit the deployed model (HGB, same config as validation) on all data through 2026-06-30 and save it."""
import pandas as pd,pickle
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from model import FEATS,log
r=pd.read_pickle('dev.pkl').dropna(subset=['label'])
m=HGB(max_iter=200,learning_rate=0.05,max_depth=4,random_state=0).fit(r[FEATS].astype(float),r.label)
pickle.dump({'model':m,'feats':FEATS,'threshold':40/130,'max_stops':8},open('model.pkl','wb'))
log('final_fit','all_through_2026-06-30',n=len(r))
print(len(r))
