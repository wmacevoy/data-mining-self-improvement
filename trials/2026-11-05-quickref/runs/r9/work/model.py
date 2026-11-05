import sys;sys.path.insert(0,'/tmp/pk-r9/work')
from load import *
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.metrics import roc_auc_score, average_precision_score
s=pd.concat([load('status.csv'),load('holdout/status_2026Q3.csv')]);s['h']=s.lts.dt.hour;s['d']=s.lts.dt.normalize()
s['b']=s.bikes_available.where(s.status=='OK')   # OFFLINE zeros are not real counts
def at(h,name): return s[s.h==h].set_index(['station_id','d']).b.rename(name)
win=s[s.h.isin([7,8,9])].groupby(['station_id','d']).agg(mn=('b','min'),off=('status',lambda x:(x=='OFFLINE').any()),nobs=('b','count'))
X=win.join([at(6,'b6'),at(5,'b5'),at(23,'b23')])
y1=s[s.h.isin([21,22,23])].groupby(['station_id','d']).b.min().rename('eve_min')  # same-day evening (before NEXT morning) -> shift
X=X.reset_index()
X=X.merge(y1.reset_index().assign(d=lambda t:t.d+pd.Timedelta('1D')),how='left')  # prior evening min
X=X.sort_values(['station_id','d'])
X['prev_mn']=X.groupby('station_id').mn.shift(1)
X['prev_off']=X.groupby('station_id').off.shift(1)
X['dow']=X.d.dt.dayofweek
X=X.merge(pd.read_csv(D+'rebalancing_log.csv',parse_dates=['ts']).assign(d=lambda t:t.ts.dt.normalize()+pd.Timedelta('1D'),restocked=1)[['station_id','d','restocked']].drop_duplicates(),how='left')
X['restocked']=X.restocked.fillna(0)
w=pd.read_csv(D+'weather.csv',parse_dates=['ts_local']);w.loc[w.temp_c<-100,'temp_c']=np.nan
w=w[w.ts_local.dt.hour<=6].groupby(w.ts_local.dt.normalize()).agg(t=('temp_c','mean'),r=('rain_mm','sum')).reset_index().rename(columns={'ts_local':'d'})
X=X.merge(w,how='left')
X['real']=(X.mn==0).astype(int); X['low']=(X.mn<=2).astype(int)
feats=['b6','b5','eve_min','prev_mn','prev_off','dow','restocked','t','r']
X[feats]=X[feats].astype(float)
tr=X[X.d<'2026-07-01'];te=X[X.d>='2026-07-01']
print('rows',len(tr),len(te))
for tgt in ['real','low']:
    print(tgt,'train pos',tr[tgt].sum(),'holdout pos',te[tgt].sum())
    m=H(max_iter=100,learning_rate=.05,max_depth=3).fit(tr[feats],tr[tgt])
    p=m.predict_proba(te[feats])[:,1]
    print(' AUC %.3f AP %.4f base %.4f maxp %.3f  n(p>.44)=%d'%(roc_auc_score(te[tgt],p),average_precision_score(te[tgt],p),te[tgt].mean(),p.max(),(p>.44).sum()))
# costs on holdout (weekday-only, real target); cost per day
wd=te[te.d.dt.dayofweek<5]
print('weekdays',wd.d.nunique(),'real stockouts',wd.real.sum(),'(excl. offline-day artefacts) offline station-days',wd.off.sum())
print('never visit cost',wd.real.sum()*90,'visit-all-30/day (cap 8)',wd.d.nunique()*8*40)
tw=X[(X.d.dt.dayofweek<5)];print('train+hold weekday positives',tw.real.sum(),len(tw),tw.real.mean())
print('offline rate',tw.off.mean(),'P(off|prev off)',tw[tw.prev_off==1].off.mean())
X.to_pickle('X.pkl')
