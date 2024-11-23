# Copyright 2024  Jacob Wachlin
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

# This example is meant to mimic the Nanosleeper hardware running the example
# open source firmware running it to demonstrate its low power sleep capabilities.
# See more on Nanosleeper here: https://www.tindie.com/products/energylabs/nanosleeper-100na-ultra-low-power-dev-board/ 
# See the firmware here: https://github.com/jwachlin/Nanosleeper

import embedded_power_model as epm

if __name__ == "__main__":

    # First, define all threads. This is how we define which components are on, how much current
    # they need, and how long they are on in different modes. All threads are periodic and run forever
    main_thread = epm.Thread(name="Main", stages=[
        epm.Stage(delta_t_sec=5.0,components=[
            epm.Component(name="RTC-RV-3028-C7",mode_name="Timekeeping",current_ma=0.000045),
            epm.Component(name="LED 1",mode_name="On",current_ma=0.08),
            epm.Component(name="LED 2",mode_name="On",current_ma=0.08),
            epm.Component(name="Load Switch-TPS22917",mode_name="Quiescent",current_ma=0.000010),
            epm.Component(name="Microcontroller-STM32L412",mode_name="Active",current_ma=0.590),
        ]),
        epm.Stage(delta_t_sec=2.0,components=[
            epm.Component(name="RTC-RV-3028-C7",mode_name="Timekeeping",current_ma=0.000045),
            epm.Component(name="LED 1",mode_name="Off",current_ma=0.0),
            epm.Component(name="LED 2",mode_name="Off",current_ma=0.0),
            epm.Component(name="Load Switch-TPS22917",mode_name="Quiescent",current_ma=0.000010),
            epm.Component(name="Microcontroller-STM32L412",mode_name="Active",current_ma=0.590),
        ]),
        epm.Stage(delta_t_sec=15.0,components=[
            epm.Component(name="RTC-RV-3028-C7",mode_name="Timekeeping",current_ma=0.000045),
            epm.Component(name="LED 1",mode_name="Off",current_ma=0.0),
            epm.Component(name="LED 2",mode_name="Off",current_ma=0.0),
            epm.Component(name="Load Switch-TPS22917",mode_name="Quiescent",current_ma=0.000010),
            epm.Component(name="Microcontroller-STM32L412",mode_name="Shutdown",current_ma=0.000018),
        ])
    ])

    # Next, define all power rails based on their voltage regulators
    # Consider TPS7A02
    reg_1v8 = epm.VoltageRegulator(name = "1.8V Rail", output_voltage=1.8, is_switching=False, threads=[main_thread], quiescent_current_ma = 0.000025, max_current_output_ma=200.0)

    # Then, set up all sources and energy harvesting
    source = epm.LithiumCoinCellBattery(name = "210mAh, CR2032", number_cells=1,regulators=[reg_1v8],capacity_mAh=210.0,initial_charge_mAh=210.0, 
                                internal_resistance_ohm=60.0)


    this_sys = epm.EmbeddedSystem(name="Coin Cell Example", sources = [source])

    
    this_sys.power_profile(sim_time_sec=300, record_time_history=True)

    this_sys.export_to_csv("Nanosleeper_sim.csv")
    this_sys.print_summary()

    this_sys.plot()