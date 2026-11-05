"""Synthetic bike-share data with seeded traps. Seeded, stdlib only; no real people or places."""
import csv, random, datetime as dt, sys
from zoneinfo import ZoneInfo
R = random.Random(20261105); TZ = ZoneInfo("America/Denver"); UTC = dt.timezone.utc
out = sys.argv[1]
ST = []
for i in range(30):
    d = "Central" if i < 14 else "North" if i < 24 else "East"
    ST.append(dict(id=f"S{i+1:03d}", d=d, cap=R.choice([15, 19, 23, 27]), drain=R.uniform(.5, 1.6) * (1.25 if d == "Central" else 1)))
START, END, HOLD = dt.date(2025, 1, 1), dt.date(2026, 9, 30), dt.date(2026, 7, 1)
def poisson(l):
    n, k, p = 0, pow(2.718281828, -l), 1.0
    while True:
        p *= R.random()
        if p <= k: return n
        n += 1
days = [START + dt.timedelta(i) for i in range((END - START).days + 1)]
rain = {d: R.random() < .22 for d in days}
temp = {d: 10 + 14 * __import__("math").sin((d.timetuple().tm_yday - 100) / 58.1) + R.gauss(0, 4) for d in days}
with open(f"{out}/stations.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow("station_id name district capacity effective_from".split())
    for i, s in enumerate(ST):
        w.writerow([s["id"], f"Dock {s['id'][1:]}", s["d"], s["cap"], "2023-04-01"])
        if i % 4 == 0:  # moved or resized: a second row, and a join on station_id fans out
            w.writerow([s["id"], f"Dock {s['id'][1:]} (moved)", s["d"], s["cap"] + 4, "2025-09-15"])
        if i % 12 == 0:
            w.writerow([s["id"], f"Dock {s['id'][1:]} (rebuilt)", s["d"], s["cap"] + 2, "2026-02-01"])
with open(f"{out}/weather.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["ts_local", "temp_c", "rain_mm"])
    for d in days:
        for h in range(24):
            t = -999 if R.random() < .012 else round(temp[d] + 5 * __import__("math").sin((h - 9) / 3.8) + R.gauss(0, .8), 1)
            w.writerow([f"{d} {h:02d}:00", t, round(R.uniform(.3, 6), 1) if rain[d] and 5 <= h <= 18 and R.random() < .6 else 0])
sf = open(f"{out}/status.csv", "w", newline=""); hf = open(f"{out}/holdout/status_2026Q3.csv", "w", newline="")
sw, hw = csv.writer(sf), csv.writer(hf); hdr = ["ts", "station_id", "bikes_available", "docks_available", "status"]; sw.writerow(hdr); hw.writerow(hdr)
visits, daily, truth = [], {}, []
for s in ST:
    for d in days:
        wk = d.weekday() < 5; e = (1.3 if d >= dt.date(2026, 3, 1) and s["d"] == "Central" else 1) * (.6 if rain[d] else 1) * (1.1 if temp[d] > 12 else .7)
        b = round(s["cap"] * R.uniform(.25, .9)); mn = b; trips = 0; empty = False; busy = 0
        off_until = -1; visit = None
        for h in range(24):
            local = dt.datetime(d.year, d.month, d.day, h, tzinfo=TZ)
            if 6 <= h < 10: rate = (2.6 if wk else .7) * s["drain"] * e
            elif 16 <= h < 19: rate = 1.3 * e
            else: rate = .35 * e
            out_n, in_n = poisson(rate), poisson(.55 if 6 <= h < 10 else .9 if 16 <= h < 19 else .4)
            b = min(s["cap"], max(0, b - out_n + in_n)); trips += out_n
            busy = rate > 2.5
            if h > off_until and R.random() < (.09 if busy and b <= 2 else .004): off_until = h + R.randint(1, 3)
            off = h <= off_until
            if 7 <= h < 9 and wk and b == 0: empty = True
            if h == 10 and empty and R.random() < .75: visit = 10 + R.randint(0, 2)
            if visit == h: b = min(s["cap"], b + R.randint(6, 10)); visits.append([local.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"), s["id"], "restock"])
            mn = min(mn, b)
            if s["d"] == "East" and R.random() < .3: continue  # thin reporting from the old controllers
            row = [local.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"), s["id"], 0 if off else b, 0 if off else s["cap"] - b, "OFFLINE" if off else "OK"]
            (hw if d >= HOLD else sw).writerow(row)
        if d < HOLD: daily[(s["id"], d)] = [s["id"], d, trips, sum(1 for v in visits[-3:] if v[1] == s["id"] and v[0][:10] == str(d)), mn, round(temp[d], 1), int(rain[d])]
        truth.append([s["id"], d, s["d"], int(empty)])
sf.close(); hf.close()
with open(f"{out}/rebalancing_log.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["ts", "station_id", "action"]); w.writerows(v for v in visits if v[0][:10] < str(HOLD))
with open(f"{out}/daily_features.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow("station_id date trips_today visits_today min_bikes_today temp_avg rain_flag".split()); w.writerows(daily.values())
with open(sys.argv[2], "w", newline="") as f:
    w = csv.writer(f); w.writerow("station_id date district truly_empty_7_9_local".split()); w.writerows(truth)
