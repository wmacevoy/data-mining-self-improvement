from model import *
from prep import *
import warnings; warnings.filterwarnings('ignore')
s=pd.concat([load(D+'status.csv'),load(D+'holdout/status_2026Q3.csv')])
f=build(s); f.to_pickle('all.pkl')
f=prep(f); tr=f[f.date<'2026-07-01']; te=f[f.date>='2026-07-01']
print('holdout rows',len(te),'base rate',round(te.y.mean(),3),'train',len(tr))
res={}
for nm,feats in [('full',FE),('conservative_to_05h',[x for x in FE if x not in('b6','last','frac')])]:
    p=np.mean([fit(tr,seed=k,feats=feats).predict_proba(te[feats])[:,1] for k in range(3)],axis=0)
    res[nm]=p; print(nm,report(nm,te,p))
for k,v in baselines(tr,te).items(): print(k,report(k,te,v)); res[k]=v
# oracle & do-nothing
orc=te.y.values; print('oracle',report('oracle',te,orc)); print('nothing: cost',-90*te.groupby('date').y.sum().mean())
# bootstrap by day: gbm vs best baseline value
p=res['full']; d=te.assign(p=p)
days=d.date.unique(); 
def perday(p,thr=40/90):
    d=te.assign(p=p); out={}
    for dt,g in d.groupby('date'):
        t=g[g.p>thr].nlargest(8,'p'); out[dt]=(90*t.y.sum()-40*len(t),len(t),int(t.y.sum()),int(g.y.sum()))
    return pd.DataFrame(out,index=['v','stops','hits','stockouts']).T
G=perday(p); B=perday(res['last28'])
print(G.mean().round(2).to_dict()); print('precision of stops',G.hits.sum()/G.stops.sum(),'recall',G.hits.sum()/G.stockouts.sum())
rng=np.random.default_rng(0); n=len(G)
bs=[(G.v.values[i]-B.v.values[i]).mean() for i in (rng.integers(0,n,n) for _ in range(2000))]
print('gbm-last28 value/day CI',np.percentile(bs,[2.5,97.5]).round(1))
bs=[G.v.values[i].mean() for i in (rng.integers(0,n,n) for _ in range(2000))]
print('gbm value/day CI',np.percentile(bs,[2.5,97.5]).round(1))
# threshold sensitivity & calibration
for thr in (.3,.444,.6): print('thr',thr,perday(p,thr).v.mean().round(1))
d['bin']=pd.cut(d.p,[0,.1,.3,.5,.7,.9,1.0],include_lowest=True); print(d.groupby('bin').agg(n=('y','size'),pred=('p','mean'),obs=('y','mean')).round(3))
# slices
d['district']=d.station_id.map(f.groupby('station_id').district.last())
for k,g in d.groupby('district'): print(k,len(g),round(roc_auc_score(g.y,g.p),3),round(g.y.mean(),3),round(g.p.mean(),3))
print(d.assign(m=d.date.dt.month).groupby('m').apply(lambda g:pd.Series(dict(auc=roc_auc_score(g.y,g.p),obs=g.y.mean(),pred=g.p.mean()))).round(3))
