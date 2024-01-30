#%%
import pandas as pd
import math
import hmmlearn
from hmmlearn import hmm
import numpy as np
#%%
columns = ['0:56:register', '1:0:coil', '1:2:coil', '2:3:register',
       '2:4:register']
#%%
def get_addr(row):
    register = "register" if not math.isnan(row.response_data) else "coil"
    addr = f"{row.unit_id}:{row.address}:{register}"
    return addr
def get_value(row):
    register = row.response_data if not math.isnan(row.response_data) else row.response_coils

    return register

trans = pd.read_json("./modbus_transaction_parser/benign.jsonl", lines=True)
trans["addr"] = trans.apply(get_addr, 1)
trans["reg"] = trans.apply(get_value, 1)
#%%
trans = trans.set_index(pd.to_datetime(trans["time"], unit='s'))
# %%
registers = trans[~trans.response_data.isna()]
coils = trans[~trans.response_coils.isna()]
# %%
ts = trans[['addr','reg']].groupby("addr").resample('10S').mean()
ts = ts.reset_index().set_index("time")


ts_df = pd.DataFrame(index=ts.index)
for key in ts.groupby("addr").indices.keys():
    ts_df[key] = ts[ts["addr"] == key]["reg"]
ts_df = ts_df[columns]
ts_df = ts_df.dropna()
ts_df.head()
# %%
best_score = best_model = None
for idx in range(10):
    model = hmm.GaussianHMM(n_components=2,n_iter=10000, init_params="mcs")
    model.transmat_ = np.array([np.random.dirichlet([0.9, 0.1]),
                                np.random.dirichlet([0.1, 0.9])])

    model.fit(ts_df.iloc[500:-500][columns])
    score = model.score(ts_df.iloc[-500:])
    print(f'Model #{idx}\tScore: {score}')
    if best_score is None or score > best_score:
        best_model = model
        best_score = score
# %%

attack = pd.read_json("./modbus_transaction_parser/small_att.jsonl", lines=True)

attack = attack.set_index(pd.to_datetime(attack["time"], unit='s'))
attack["addr"] = attack.apply(get_addr, 1)
attack["reg"] = attack.apply(get_value, 1)
#%%
ts = attack[['addr','reg']].groupby("addr").resample('10S').mean()
ts = ts.reset_index().set_index("time")


att_ts_df = pd.DataFrame(index=ts.index)
for key in ts.groupby("addr").indices.keys():
    att_ts_df[key] = ts[ts["addr"] == key]["reg"]
att_ts_df = att_ts_df.dropna(axis=1)[columns]

# %%
ts_df['score'] = model.predict(ts_df[columns])
ts_df['att_prob'] = ts_df['score']\
    .resample('5T', label='right', closed='right')\
        .mean().resample('10S').interpolate()*200

att_ts_df['score'] = model.predict(att_ts_df[columns])
att_ts_df['att_prob'] = att_ts_df['score']\
    .resample('5T', label='right', closed='right')\
        .mean().resample('10S').interpolate()*200

combined = pd.concat([ts_df.iloc[9000:][columns + ['att_prob']].resample('1T', label='right', closed='right').mean(), att_ts_df[columns + ['att_prob']].resample('1T', label='right', closed='right').mean()])

combined[["0:56:register","2:4:register", "att_prob"]].reset_index().drop("time", axis=1)\
    .plot(title="HMM attack probabilities", ylabel="Register value", xlabel="Seconds since simulation start")
# %%
