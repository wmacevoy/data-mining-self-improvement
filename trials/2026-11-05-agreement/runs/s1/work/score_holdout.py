"""ONE-SHOT sign-off look. Run by a human, once, and record it. Trains on all of status.csv (to 2026-07-01), scores the holdout file.
Usage: python -I score_holdout.py /tmp/pk-s1/data/holdout/status_2026Q3.csv"""
import sys; sys.path.insert(0,'/tmp/pk-s1/work')
from model import *
h=sys.argv[1]
a=pd.read_csv('/tmp/pk-s1/data/status.csv'); b=pd.read_csv(h)
allp=pd.concat([a,b]); allp.to_csv('/tmp/holdout_concat.csv',index=False)  # history needed for lag features
d=prep.build('/tmp/holdout_concat.csv'); d=prep_split(d)
tr=d[d.date<'2026-07-01']; te=d[d.date>='2026-07-01']
p=fit_predict(tr,te,0)
print('n',len(te),'rate',te.y.mean(),'AUC',roc_auc_score(te.y,p),'brier',brier_score_loss(te.y,p))
print('$/day model, stops/day',policy_value(te,p),'| b6 rule',policy_value(te,(1-te.b6.clip(upper=10)/10).values),'| oracle',oracle(te))
