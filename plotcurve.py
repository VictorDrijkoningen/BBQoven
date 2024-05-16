# pylint: skip-file
import matplotlib.pyplot as plt
import numpy




def curve1(runtime):
    time_section = [0,60, 90, 120, 150, 300]
    temp_section = [0,150, 200, 250, 250, 0]

    assert len(time_section) == len(temp_section)

    for i in range(len(time_section)):
        if runtime < time_section[i]:
            return  temp_section[i-1] + (temp_section[i] - temp_section[i-1])/(time_section[i]-time_section[i-1]) * (runtime-time_section[i-1])


x = list()
for i in range(300):
    x.append(i)
y = list()
for i in x:
    y.append(curve1(i))

plt.plot(x,y)
plt.ylabel('temp')
plt.xlabel('time')
plt.show()


