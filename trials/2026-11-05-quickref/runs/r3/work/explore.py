from prep import *
s=load(D+'status.csv'); f=build(s)
print(len(f), f.y.mean(), f.n_known.value_counts().to_dict())
print(f.groupby('dow').y.mean().round(3).to_dict()); print(f.groupby('month').y.mean().round(3).to_dict())
print(f.groupby('station_id').y.mean().round(2).describe())
# gap check: stations with missing rows
print(f.groupby('station_id').size().describe())
f.to_pickle('train.pkl')
