import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def calc(filesfolder, datafilename):
    df = pd.read_csv(os.path.join(filesfolder,datafilename))

    df['t1'] = df.t1.shift(-6)

    df = df.drop(df[df.target_temp < 110].index)
    df = df.drop('fan_duty', axis=1)
    df = df.drop('time', axis=1)
    df = df.drop('t2', axis=1)
    df = df.drop('heating_duty', axis=1)
    df = df.drop('cooling_pos', axis=1)


    print(df)
    maxv = max(df.target_temp - df.t1)
    minv = min(df.target_temp - df.t1)
    print(maxv)
    print(minv)
    indxx = df[(df.target_temp - df.t1) >= maxv].index
    print(df.loc[indxx])

    # print(df)
    return round(((df.target_temp - df.t1) ** 2).mean() ** .5, 1)


FOLDER = "data"
for filename in os.listdir(FOLDER):
    if ".csv" in filename:
        print(filename)
        print(calc(FOLDER, filename))
