"""Raw -> station-day table (7:00 Denver prediction point) -> model -> metrics.
Usage: python -I build.py <datadir> <outdir>.  Never opens holdout/."""
import sys, json
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score

data, out = sys.argv[1], sys.argv[2]
TZ = "America/Denver"

# --- status: controller clock is UTC (see REPORT); convert to local ---
s = pd.read_csv(f"{data}/status.csv")
s["ts"] = pd.to_datetime(s["ts"]).dt.tz_localize("UTC").dt.tz_convert(TZ)
n0 = len(s)
s = s.drop_duplicates(["ts", "station_id"])
print("dup rows dropped", n0 - len(s))
s["date"] = s.ts.dt.tz_localize(None).dt.normalize()
s["hour"] = s.ts.dt.hour
# OFFLINE reports 0 bikes: unknown, not a stockout
s.loc[s.status != "OK", "bikes_available"] = np.nan

# capacity as of date
st = pd.read_csv(f"{data}/stations.csv", parse_dates=["effective_from"]).sort_values("effective_from")
s = s.sort_values("date")
s = pd.merge_asof(s, st[["station_id","capacity","district","effective_from"]], left_on="date",
                  right_on="effective_from", by="station_id")
assert s.capacity.notna().all()

# label: any OK reading with 0 bikes at local 7,8,9; unknown if no OK reading in window
w = s[s.hour.isin([7, 8, 9])]
lab = w.groupby(["station_id","date"]).bikes_available.agg(lambda x: np.nan if x.isna().all() else float((x == 0).any())).rename("y").reset_index()

# features: only local hours <= 6 on the same date, or earlier days
f = s[s.hour <= 6].pivot_table(index=["station_id","date"], columns="hour", values="bikes_available")
f.columns = [f"b{h}" for h in f.columns]
f["bmin"] = f.min(axis=1)
f = f.reset_index()
cap = s.groupby(["station_id","date"]).agg(capacity=("capacity","last"), district=("district","last")).reset_index()
df = lab.merge(f, on=["station_id","date"], how="left").merge(cap, on=["station_id","date"], how="left")
df["fill6"] = df.b6 / df.capacity
df = df.sort_values(["station_id","date"])
# station history known by 7am: prior days' outcomes (window ended 9am the day before)
g = df.groupby("station_id").y
df["prev_y"] = g.shift(1)
df["rate14"] = g.transform(lambda x: x.shift(1).rolling(14, min_periods=5).mean())
df["rate_all"] = g.transform(lambda x: x.shift(1).expanding(10).mean())
df["dow"] = df.date.dt.dayofweek
df["doy"] = df.date.dt.dayofyear
df["district"] = df.district.astype("category").cat.codes

# weather: local, -999 sentinel; only hours <= 6 today and yesterday's rain
wx = pd.read_csv(f"{data}/weather.csv", parse_dates=["ts_local"])
wx.loc[wx.temp_c < -90, "temp_c"] = np.nan
wx["date"] = wx.ts_local.dt.normalize(); wx["hour"] = wx.ts_local.dt.hour
t6 = wx[wx.hour == 6].set_index("date").temp_c.rename("temp6")
r6 = wx[wx.hour <= 6].groupby("date").rain_mm.sum().rename("rain_0_6")
rprev = wx.groupby("date").rain_mm.sum().shift(1).rename("rain_prev")  # assumes full prior day present
df = df.merge(t6, on="date", how="left").merge(r6, on="date", how="left").merge(rprev, on="date", how="left")

# weekdays only (the service); unlabeled rows dropped
df = df[df.dow < 5]
print("station-days weekday:", len(df), " unlabeled:", df.y.isna().sum())
df = df[df.y.notna()].copy()
df.to_csv(f"{out}/station_days.csv", index=False)

feats = ["b0","b3","b5","b6","bmin","fill6","capacity","district","prev_y","rate14","rate_all","dow","doy","temp6","rain_0_6","rain_prev"]
train = df[df.date < "2026-01-01"]; val = df[df.date >= "2026-01-01"]
print("train", len(train), train.y.mean().round(3), "val", len(val), val.y.mean().round(3))

def cost(day, p, thr=40/90, cap=8):
    """Per-day policy: stop at top-8 stations with p>thr. Cost = $40/stop + $90/missed stockout (stop assumed to prevent it)."""
    tot = 0.0
    for _, d in day.groupby("date"):
        top = d.assign(p=p[d.index.map(day.index.get_loc)] if False else d["p"]).nlargest(cap, "p")
        top = top[top.p > thr]
        tot += 40*len(top) + 90*(d.y.sum() - top.y.sum())
    return tot

def evalset(name, p, v):
    v = v.assign(p=p)
    days = v.date.nunique()
    r = dict(name=name, auc=roc_auc_score(v.y, p), ap=average_precision_score(v.y, p),
             cost_per_day=cost(v, p)/days)
    return r

def fit(feats, tr, seed):
    m = HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=200, random_state=seed)
    return m.fit(tr[feats], tr.y)

res = []
days = val.date.nunique()
res.append(dict(name="no action", auc=np.nan, ap=np.nan, cost_per_day=90*val.y.sum()/days))
# baseline: station x calendar-month rate from training (climatology)
clim = train.assign(m=train.date.dt.month).groupby(["station_id","m"]).y.mean()
pc = val.apply(lambda r: clim.get((r.station_id, r.date.month), train.y.mean()), axis=1).values
res.append(evalset("baseline: station x month rate", pc, val))
# baseline: low bikes at 6am (fill fraction)
res.append(evalset("baseline: 6am fill (low=risk)", (1 - val.fill6.fillna(val.fill6.median())).values, val))
# baseline: persistence
res.append(evalset("baseline: yesterday's stockout", val.prev_y.fillna(0).values, val))
aucs = []; ps = []
for seed in range(5):
    p = fit(feats, train, seed).predict_proba(val[feats])[:,1]
    ps.append(p); aucs.append(roc_auc_score(val.y, p))
pm = np.mean(ps, axis=0)
r = evalset("HGB (5-seed mean)", pm, val); r["auc_seed_range"] = [min(aucs), max(aucs)]
res.append(r)
# day-block bootstrap of cost saving vs no-action and vs climatology
vv = val.assign(p=pm, pc=pc)
dd = {k: g for k, g in vv.groupby("date")}
def daycost(g, col):
    top = g.nlargest(8, col); top = top[top[col] > 40/90]
    return 40*len(top) + 90*(g.y.sum() - top.y.sum()), 90*g.y.sum()
arr = np.array([[*daycost(g, "p"), *daycost(g, "pc")[:1]] for g in dd.values()])
rng = np.random.default_rng(0); sv = []; sc = []
for _ in range(2000):
    i = rng.integers(0, len(arr), len(arr)); a = arr[i].mean(0)
    sv.append(a[1]-a[0]); sc.append(a[2]-a[0])
print("saving/day vs no action: %.0f [%.0f, %.0f]" % (np.mean(sv), *np.percentile(sv,[2.5,97.5])))
print("saving/day vs climatology policy: %.0f [%.0f, %.0f]" % (np.mean(sc), *np.percentile(sc,[2.5,97.5])))
# calibration + stops/day + recall of stockouts caught
bins = pd.cut(pm, [0,.1,.2,.3,.4,.5,.6,.8,1.0]); print(vv.assign(b=bins).groupby("b",observed=True).y.agg(["mean","size"]))
stops = [min(8, (g.p > 40/90).sum()) for g in dd.values()]
print("mean stops/day", np.mean(stops), " mean stockouts/day", vv.y.sum()/days)
# slice: district, month
vv["month"] = vv.date.dt.month
for k in ["district","month"]:
    print(vv.groupby(k).apply(lambda g: pd.Series(dict(n=len(g), rate=g.y.mean(), auc=roc_auc_score(g.y,g.p) if g.y.nunique()>1 else np.nan))).round(3))
print(pd.DataFrame(res).to_string())
json.dump(res, open(f"{out}/results.json","w"), default=float, indent=1)
