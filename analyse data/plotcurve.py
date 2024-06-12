# pylint: skip-file
import matplotlib.pyplot as plt
import numpy




def curve(runtime):
    time_section = [0, 60,  150, 180, 210, 240, 270, 500]
    temp_section = [30,100, 150, 183, 235, 235, 183, 60]

    assert len(time_section) == len(temp_section)

    for i in range(len(time_section)):
        if runtime < time_section[i]:
            return  temp_section[i-1] + (temp_section[i] - temp_section[i-1])/(time_section[i]-time_section[i-1]) * (runtime-time_section[i-1])


x = list()
for i in range(600):
    x.append(i)
y = list()
for i in x:
    y.append(curve(i))

plt.plot(x,y)
plt.ylabel('temp')
plt.xlabel('time')
plt.show()


