import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def create(filesfolder, datafilename, solidworksfilename=None):
    df = pd.read_csv(os.path.join(filesfolder,datafilename))

    title = filename.split("-")

    timetotal = df[["time"]].values
    timerela = timetotal - timetotal[0]


    temps = df[["target_temp","t1","t2"]].values
    heatingduty = df[["heating_duty"]].values/1023*100
    fanduty = df[["fan_duty"]].values/1023*100
    coolingpos = (df[["cooling_pos"]].values -35)/115*100


    if solidworksfilename is not None:
        sw = pd.read_excel(solidworksfilename)
        sw = sw.tail(-1)

        swtime = sw.iloc[:, 1]
        swtemp = sw.iloc[:, 2]


    fig, ax1 = plt.subplots()

    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Temperature (°C)')

    ax1.plot(timerela, temps[:,0], color='red',     label='Temp target' )
    ax1.plot(timerela, temps[:,1], color='blue',    label='Temp 1',     marker='.')
    ax1.plot(timerela, temps[:,2], color='green',   label='Temp 2',     marker='.')

    if solidworksfilename is not None:
        ax1.plot(swtime, swtemp, color='gray',     label='Temp sw' )

    ax1.set_ylim((0,np.max(temps)+10))
    ax1.set_xlim((0,np.max(timerela)+5))


    ax2 = ax1.twinx()
    ax2.set_ylabel('%')
    ax2.plot(timerela, heatingduty, color='orange', linestyle='dotted', label='Heating duty')
    ax2.plot(timerela, fanduty,     color='black', linestyle='dotted', label='Fan duty'    )
    ax2.plot(timerela, coolingpos,  color='cyan', linestyle='dotted', label='Cooling Pos' )
    ax2.set_ylim((0,100))
    ax2.legend(loc="upper right")
    plt.title(title[-2])



    ax1.legend(loc="upper left")
    fig.tight_layout()

    fig.set_size_inches(20,15)
    fig.show()
    plt.savefig(os.path.join(filesfolder,os.path.splitext(datafilename)[0]+'.png'), dpi=200)


folder = "analyse data/data"
for filename in os.listdir(folder):
    if ".csv" in filename:
        print(filename)
        create(folder, filename)
    