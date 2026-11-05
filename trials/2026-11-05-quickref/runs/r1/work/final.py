import pandas as pd,numpy as np
from evalh import *
from prep import *
D='/tmp/pk-r1/data/'
dev=pd.read_pickle('dev.pkl');dev=dev[(dev.dow<5)&dev.stockout.notna()].reset_index(drop=True)
tr=dev[dev.date<'2026-01-01'];va=dev[dev.date>='2026-01-01'].reset_index(drop=True)
def ci(df,pa,pb):
    a=np.array([policy_cost(g,pa[g.index])['cost_per_day'] for _,g in df.groupby('date')]);b=np.array([policy_cost(g,pb[g.index])['cost_per_day'] for _,g in df.groupby('date')])
    rng=np.random.default_rng(0);x=[(a[i]-b[i]).mean() for i in (rng.integers(0,len(a),len(a)) for _ in range(500))]
    return np.percentile(x,[2.5,97.5]).round(1)
pg=fit_predict(tr,va,'gbm');pr=fit_predict(tr,va,'rule_b06');pn=fit_predict(tr,va,'none')
print('VAL gbm-rule',ci(va,pg,pr),'gbm-none',ci(va,pg,pn))
# holdout: single look. build on concatenated raw so history features have prior days
s=pd.concat([load_status(D+'status.csv'),load_status(D+'holdout/status_2026Q3.csv')]);s=s.drop_duplicates(['ts','station_id'])
w=pd.read_csv(D+'weather.csv');allx=build(s,stations(D+'stations.csv'),w)
ho=allx[(allx.date>='2026-07-01')&(allx.dow<5)&allx.stockout.notna()&(allx.date<='2026-09-30')].reset_index(drop=True)
full=dev
print('holdout days',ho.date.nunique(),'rows',len(ho),'rate',ho.stockout.mean(), 'excluded unknown label',allx[(allx.date>='2026-07-01')&(allx.dow<5)].stockout.isna().sum())
P={k:fit_predict(full,ho,k) for k in ['none','yesterday','rate28','rule_b06','logit','gbm']}
print(pd.DataFrame([report(k,ho,P[k]) for k in P]).round(3).to_string())
print('HO gbm-rule',ci(ho,P['gbm'],P['rule_b06']),'gbm-none',ci(ho,P['gbm'],P['none']),'gbm-logit',ci(ho,P['gbm'],P['logit']))
ho['p']=P['gbm']
print(ho.groupby('district').apply(lambda g:pd.Series(dict(n=len(g),rate=g.stockout.mean(),auc=roc_auc_score(g.stockout,g.p)))).round(3))
print(ho.groupby(ho.date.dt.month).apply(lambda g:pd.Series(dict(rate=g.stockout.mean(),pred=g.p.mean()))).round(3))
# calibration
ho['bin']=pd.cut(ho.p,[0,.1,.3,.5,.7,.9,1],include_lowest=True);print(ho.groupby('bin',observed=True).stockout.agg(['mean','count']).round(3))
# precision of daily top picks
top=ho.sort_values(['date','p'],ascending=[True,False]).groupby('date').head(8);print('top8 precision',top.stockout.mean(),'picked p>.44 share',(ho.p>40/90).mean())
