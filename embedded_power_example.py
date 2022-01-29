# Copyright 2022  Jacob Wachlin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software 
# and associated documentation files (the "Software"), to deal in the Software without restriction, 
# including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, 
# subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all copies or 
#  substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT 
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import matplotlib.pyplot as plt
plt.style.use('seaborn-whitegrid')
import numpy as np
import embedded_power_model as epm

if __name__ == "__main__":

    accel_thread = epm.Thread(name="Accelerometer Sampling", stages=[
        epm.Stage(delta_t_sec=0.5,components=[
            epm.Component(name="ESP32",mode_name="Active",current_ma=100.0),
            epm.Component(name="Accelerometer",mode_name="Active",current_ma=1.5)
        ]),
        epm.Stage(delta_t_sec=20.0,components=[
            epm.Component(name="ESP32",mode_name="Sleep",current_ma=0.05),
            epm.Component(name="Accelerometer",mode_name="Sleep",current_ma=0.001)
        ])
    ])

    led_thread = epm.Thread(name="LED", stages=[
        epm.Stage(delta_t_sec=0.1,components=[
            epm.Component(name="LED",mode_name="On",current_ma=5.0)
        ]),
        epm.Stage(delta_t_sec=4.9,components=[
            epm.Component(name="LED",mode_name="Off",current_ma=0.0)
        ])
    ])

    this_sys = epm.EmbeddedSystem(name="Test", threads=[accel_thread,led_thread], 
        energy_storage=epm.LithiumBattery(number_cells=1,capacity_mAh=1000.0,current_charge_mAh=500.0,internal_resistance_ohm=0.065),
        voltage_reg=epm.VoltageRegulator(efficiency=0.8),nominal_voltage=3.3,
        energy_harvesting=epm.SolarPanel(rated_power_W=1.5,t_offset_sec=0.0))

    
    this_sys.power_profile(3*86400.0, True)

    fig = plt.figure()
    ax = plt.axes()
    ax.plot(this_sys.energy_harvesting.time, this_sys.energy_harvesting.power_history_W)
    plt.title("Solar Power Available. Capacity Factor: " + str(this_sys.energy_harvesting.capacity_factor()))
    plt.xlabel("Time, s")
    plt.ylabel("Power, W")

    fig = plt.figure()
    ax = plt.axes()
    ax.plot(this_sys.energy_harvesting.time, this_sys.energy_harvesting.random_walk_vals)
    plt.title("Random Walk")
    plt.xlabel("Time, s")
    plt.ylabel("Random Walk Val")
    
    fig = plt.figure()
    ax = plt.axes()
    ax.plot(this_sys.power_time, this_sys.system_power_mW, label="System Power")
    battery_power = np.multiply(np.array(this_sys.energy_storage.current_history_ma),np.array(this_sys.energy_storage.voltage_history))
    plt.plot(this_sys.energy_storage.time, battery_power, label = "Battery Power")
    plt.legend()
    plt.title("Net Energy: " + str(this_sys.energy_storage.net_energy_J) + "J")
    plt.xlabel("Time, s")
    plt.ylabel("Power, mW")

    fig = plt.figure()
    ax = plt.axes()
    ax.plot(this_sys.energy_storage.time, this_sys.energy_storage.charge_history_mAh)
    plt.title("Net Energy: " + str(this_sys.energy_storage.net_energy_J) + "J")
    plt.xlabel("Time, s")
    plt.ylabel("Energy Capacity, mAh")

    fig = plt.figure()
    ax = plt.axes()
    ax.plot(this_sys.energy_storage.time, this_sys.energy_storage.voltage_history)
    plt.title("Net Energy: " + str(this_sys.energy_storage.net_energy_J) + "J")
    plt.xlabel("Time, s")
    plt.ylabel("Battery Voltage, V")

    fig = plt.figure()
    ax = plt.axes()
    ax.plot(this_sys.energy_storage.time, this_sys.energy_storage.current_history_ma)
    plt.title("Net Energy: " + str(this_sys.energy_storage.net_energy_J) + "J")
    plt.xlabel("Time, s")
    plt.ylabel("Battery Current, mA")

    plt.show()