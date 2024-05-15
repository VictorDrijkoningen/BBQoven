# pylint: skip-file
import matplotlib.pyplot as plt
import numpy




def curve1(runtime):
    time_section = [0,60, 90, 120, 300]
    temp_section = [0,150, 200, 250, 0]

    assert len(time_section) == len(temp_section)

    for i in range(len(time_section)):
        if runtime < time_section[i]:
            return  


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


