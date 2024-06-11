import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt




def calc(filesfolder, datafilename1, datafilename2, move1):
    df1 = pd.read_csv(os.path.join(filesfolder,datafilename1))
    df2 = pd.read_csv(os.path.join(filesfolder,datafilename2))

    df1 = df1.drop(df1[df1.target_temp < 110].index)
    df1 = df1.drop(df1[df1.t1 > 125].index)
    df1 = df1.drop('fan_duty', axis=1)
    df1 = df1.drop('target_temp', axis=1)
    df1 = df1.drop('time', axis=1)
    df1 = df1.drop('t2', axis=1)
    df1 = df1.drop('heating_duty', axis=1)
    df1 = df1.drop('cooling_pos', axis=1)
    df1.reset_index(drop=True, inplace=True)
    df1['t1'] = df1.t1.shift(move)

    df2 = df2.drop(df2[df2.target_temp < 110].index)
    df2 = df2.drop(df2[df2.t1 > 125].index)
    df2 = df2.drop('fan_duty', axis=1)
    df2 = df2.drop('target_temp', axis=1)
    df2 = df2.drop('time', axis=1)
    df2 = df2.drop('t2', axis=1)
    df2 = df2.drop('heating_duty', axis=1)
    df2 = df2.drop('cooling_pos', axis=1)
    df2.reset_index(drop=True, inplace=True)

    diff = df1.subtract(df2, fill_value=0)
    diff = diff.drop(diff[diff.t1 > 50].index)
    diff = diff.drop(diff[diff.t1 < -50].index)
    print(diff)


    return round(((diff.t1) ** 2).mean() ** .5, 1)


file1 = "Temp data 5-6-2024 14-9-42-meting 13-.csv"
file2 = "Temp data 5-6-2024 15-44-53-meting 14-.csv"
datafolder = "data"
lowest = 10000
moved = 0
for i in range (20):
    move = (i - 10)
    
    out = calc(datafolder, file1, file2, move)
    if out < lowest:
        moved = move
        lowest = out

print(moved)
print(lowest)
