import sys; sys.path.insert(0,'/tmp/pk-s1/work')
from model import *
d = prep_split(prep.build('/tmp/pk-s1/data/status.csv'))
tr=d[d.date<'2026-04-01']; te=d[d.date>='2026-04-01'].copy()
te['p']=fit_predict(tr,te,0)
rng=np.random.default_rng(0); days=te.date.unique()
res=[]
for _ in range(300):
    ds=rng.choice(days,len(days)); b=pd.concat([te[te.date==x] for x in ds])
    b=b.assign(date=np.repeat(np.arange(len(ds)),[ (te.date==x).sum() for x in ds]))
    res.append((policy_value(b,b.p.values)[0], policy_value(b,(1-b.b6.clip(upper=10)/10).values)[0]))
r=np.array(res); print('model $/day 95%',np.percentile(r[:,0],[2.5,97.5]).round(0),'b6',np.percentile(r[:,1],[2.5,97.5]).round(0),'diff',np.percentile(r[:,0]-r[:,1],[2.5,97.5]).round(0))
te['east']=te.station_id>='S025'
for k,g in te.groupby('district'): print(k,len(g),'rate',g.y.mean().round(3),'AUC',round(roc_auc_score(g.y,g.p),3))
te['bin']=pd.cut(te.p,[0,.1,.3,.44,.7,.9,1]); print(te.groupby('bin',observed=True).agg(n=('y','size'),obs=('y','mean'),pred=('p','mean')).round(3))
# threshold choice: the cost ratio says 0.444; check realised value by threshold
for t in [.3,.44,.6]: print('thr',t,[round(x,1) for x in policy_value(te,te.p.values,thr=t)])
# DST weeks
x=te[(te.date>='2026-03-08')]; 
