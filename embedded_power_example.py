# Copyright 2023  Jacob Wachlin
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

import embedded_power_model as epm

if __name__ == "__main__":

    # First, define all threads. This is how we define which components are on, how much current
    # they need, and how long they are on in different modes. All threads are periodic and run forever
    accel_thread = epm.Thread(name="Accelerometer Sampling", stages=[
        epm.Stage(delta_t_sec=2.5,components=[
            epm.Component(name="ESP32",mode_name="Active",current_ma=100.0),
            epm.Component(name="Accelerometer",mode_name="Active",current_ma=1.5)
        ]),
        epm.Stage(delta_t_sec=20.0,components=[
            epm.Component(name="ESP32",mode_name="Sleep",current_ma=0.05),
            epm.Component(name="Accelerometer",mode_name="Sleep",current_ma=0.001)
        ])
    ])

    led_thread = epm.Thread(name="LED", stages=[
        epm.Stage(delta_t_sec=0.5,components=[
            epm.Component(name="LED",mode_name="On",current_ma=5.0)
        ]),
        epm.Stage(delta_t_sec=4.9,components=[
            epm.Component(name="LED",mode_name="Off",current_ma=0.0)
        ])
    ])

    baro_thread = epm.Thread(name="Barometer", stages=[
        epm.Stage(delta_t_sec=0.5,components=[
            epm.Component(name="Barometer",mode_name="On",current_ma=0.1)
        ]),
        epm.Stage(delta_t_sec=5.0,components=[
            epm.Component(name="Barometer",mode_name="Off",current_ma=0.005)
        ])
    ])

    # Next, define all power rails based on their voltage regulators
    reg_3v3 = epm.VoltageRegulator(name = "3.3V Rail", output_voltage=3.3, is_switching=True, efficiency=0.9, threads=[accel_thread,led_thread], quiescent_current_ma = 0.1)
    reg_1v8 = epm.VoltageRegulator(name = "1.8V Rail", output_voltage=1.8, is_switching=False, threads=[baro_thread], quiescent_current_ma = 0.06)

    # Then, set up all sources and energy harvesting
    source = epm.LithiumIonBattery(name = "1Ah, 2S Li-ion", number_cells=2,regulators=[reg_1v8, reg_3v3],capacity_mAh=1000.0,initial_charge_mAh=750.0, 
                                internal_resistance_ohm=0.065, energy_harvesting=epm.SolarPanel(rated_power_W=1.5,t_offset_sec=30000.0))


    this_sys = epm.EmbeddedSystem(name="Example", sources = [source])

    
    this_sys.power_profile(sim_time_sec=3*86400.0, record_time_history=True)

    this_sys.print_summary()

    this_sys.plot()