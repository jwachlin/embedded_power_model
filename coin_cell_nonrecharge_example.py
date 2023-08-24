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
    baro_thread = epm.Thread(name="Barometer", stages=[
        epm.Stage(delta_t_sec=0.002,components=[
            epm.Component(name="Barometer-BMP390",mode_name="Sample",current_ma=0.660),
            epm.Component(name="Microcontroller-ATSAML21",mode_name="Active",current_ma=0.6),
        ]),
        epm.Stage(delta_t_sec=0.03,components=[
            epm.Component(name="Barometer-BMP390",mode_name="Sleep",current_ma=0.0014),
            epm.Component(name="Microcontroller-ATSAML21",mode_name="Active",current_ma=0.6),
        ]),
        epm.Stage(delta_t_sec=10.0,components=[
            epm.Component(name="Barometer-BMP390",mode_name="Sleep",current_ma=0.0014),
            epm.Component(name="Microcontroller-ATSAML21",mode_name="Standby",current_ma=0.0025),
        ])
    ])

    # Next, define all power rails based on their voltage regulators
    # Consider TPS7A02
    reg_1v8 = epm.VoltageRegulator(name = "1.8V Rail", output_voltage=1.8, is_switching=False, threads=[baro_thread], quiescent_current_ma = 0.000025, max_current_output_ma=200.0)

    # Then, set up all sources and energy harvesting
    source = epm.LithiumCoinCellBattery(name = "210mAh, CR2032", number_cells=1,regulators=[reg_1v8],capacity_mAh=210.0,initial_charge_mAh=210.0, 
                                internal_resistance_ohm=60.0)


    this_sys = epm.EmbeddedSystem(name="Coin Cell Example", sources = [source])

    
    this_sys.power_profile(sim_time_sec=10*86400.0, record_time_history=True)

    this_sys.print_summary()

    this_sys.plot()