import sys;sys.path.insert(0,'/tmp/pk-r4/work')
import prep,pandas as pd,numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier as G
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,brier_score_loss
def dataset(path):
    s=prep.load(path);w=prep.weather();ok=s[s.status=='OK'].copy()
    capd=(ok.bikes_available+ok.docks_available).groupby(ok.station_id).max()
    d=prep.build(s,w,lambda a,b:capd[a]);d['cap']=d.station_id.map(capd);d['fill']=d.b6/d.cap;d['wk']=(d.dow<5).astype(int);return d
F=['b6','b5','b1','bmin','fill','cap','off_n','dow','month','t6','rain_n','srate']
def addrate(tr,te):
    r=tr[tr.dow<5].groupby('station_id').y.mean();return tr.station_id.map(r).fillna(0),te.station_id.map(r).fillna(tr.y.mean())
def fit(tr):
    tr=tr.copy();tr['srate'],_=addrate(tr,tr)
    return G(max_iter=150,learning_rate=.05,max_depth=4,random_state=0).fit(tr[F],tr.y)
def pred(m,tr,te):
    te=te.copy();_,te['srate']=addrate(tr,te);return m.predict_proba(te[F])[:,1]
def policy(te,p,k=8,thr=40/90):
    te=te.assign(p=p);cost_do=0;stops=0;caught=0
    tot_so=te.y.sum()
    for _,g in te.groupby('date'):
        g=g[g.p>thr].nlargest(k,'p');stops+=len(g);caught+=g.y.sum()
    return dict(stockouts=int(tot_so),stops=stops,caught=int(caught),cost_none=90*tot_so,cost_model=90*(tot_so-caught)+40*stops)
def report(te,p,name):
    print(name,'AUC %.3f Brier %.3f base %.3f'%(roc_auc_score(te.y,p),brier_score_loss(te.y,p),brier_score_loss(te.y,np.full(len(te),te.y.mean()))),policy(te,p))
if __name__=='__main__':
    d=dataset(prep.D+'status.csv');d.to_pickle('d.pkl')
    tr=d[d.date<'2026-01-01'];va=d[d.date>='2026-01-01']   # time split inside training data
    m=fit(tr);p=pred(m,tr,va);report(va,p,'GBM val')
    # baselines
    _,sr=addrate(tr,va);report(va,sr*(va.dow<5),'station-rate')
    report(va,(va.b6<=3).astype(float)*.9,'rule b6<=3')
    for t in (2,3,4,5):print(t,(va.b6<=t).mean(),va[va.b6<=t].y.mean())
    # calibration
    va=va.assign(p=p);print(va.groupby(pd.cut(va.p,[0,.1,.2,.3,.45,.6,.8,1])).y.agg(['mean','size']))
    print(va.groupby('wk').y.mean())
    print('daily candidates >thr:',va[va.p>.444].groupby('date').size().describe())
