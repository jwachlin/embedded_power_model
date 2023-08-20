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

import numpy as np
import matplotlib.pyplot as plt
plt.style.use('seaborn-whitegrid')

class Component:
  def __init__(self, name, mode_name, current_ma):
    self.name = name
    self.mode_name = mode_name
    self.current_ma = current_ma

class Stage:
  def __init__(self, delta_t_sec, components):
    self.delta_t_sec = delta_t_sec
    self.components = components

class Thread:
  def __init__(self, name, stages):
    self.name = name
    self.stages = stages
    self.num_stages = len(stages)
    self.last_stage_change_t = 0.0
    self.next_stage_change_t = self.last_stage_change_t + stages[0].delta_t_sec
    self.stage_index = 0

######### Generators Charge Sources #########

class SolarPanel:
  def __init__(self, rated_power_W, charge_efficiency=0.7, t_offset_sec = 0.0, 
      clouds_tau=3600.0, clouds_cover = 1.0):
    self.rated_power_W = rated_power_W
    self.charge_efficiency = charge_efficiency
    self.t_offset_sec = t_offset_sec
    self.clouds_tau = clouds_tau
    self.clouds_cover = clouds_cover
    self.random_walk_val = 0.0
    self.last_time_s = 0.0
    self.time = []
    self.power_history_W = []
    self.random_walk_vals = []

  def calculate_power(self, t):

    dt = t - self.last_time_s
    if(dt > 0.0):
      f = np.exp(-dt/self.clouds_tau)
      self.random_walk_val = f*self.random_walk_val + np.sqrt(1.0-f**2.0) * np.random.randn()

    power = self.rated_power_W*(1.0/0.65)*(np.sin(((2.0*np.pi)/86400)*(t+self.t_offset_sec)) - 0.35)
    if power < 0.0:
      power = 0.0

    # Calculate threshold based on normal distribution
    if np.abs(self.random_walk_val) > self.clouds_cover:
      power = 0.1*power

    self.time.append(t)
    self.power_history_W.append(power) 
    self.random_walk_vals.append(self.random_walk_val)
    self.last_time_s = t
    return power

  def capacity_factor(self):
    return np.mean(self.power_history_W)/self.rated_power_W


######### Sources #########

class Source:
  def __init__(self, name, number_cells, regulators, capacity_mAh, initial_charge_mAh, internal_resistance_ohm, energy_harvesting=None):
    self.name = name
    self.number_cells = number_cells
    self.regulators = regulators
    self.capacity_mAh = capacity_mAh
    self.initial_charge_mAh = initial_charge_mAh
    self.current_charge_mAh = initial_charge_mAh
    self.internal_resistance_ohm = internal_resistance_ohm
    self.energy_harvesting = energy_harvesting
    self.net_energy_J = 0.0
    self.time = []
    self.charge_history_time = []
    self.charge_history_mAh = []
    self.voltage_history = []
    self.current_history_ma = []

class LithiumBattery(Source):

  soc_table = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 95.0, 100.0]
  cell_voltage_table = [2.25, 3.5, 3.65, 3.72, 3.73, 3.75, 3.76, 3.77, 3.78, 3.85, 4.1, 4.25]

  def get_current_voltage(self, total_current_ma=0.0):
    soc = (self.current_charge_mAh / self.capacity_mAh)*100.0
    cell_voltage = self.cell_voltage_table[-1]
    for i in range(len(self.soc_table)-1):
      if (soc >= self.soc_table[i]) and (soc < self.soc_table[i+1]):
        cell_voltage = self.cell_voltage_table[i] + ((self.cell_voltage_table[i+1]-self.cell_voltage_table[i])/(self.soc_table[i+1]-self.soc_table[i])) * (soc-self.soc_table[i])
    
    cell_voltage = cell_voltage - self.internal_resistance_ohm*(total_current_ma*0.001)
    return self.number_cells * cell_voltage


######### Regulators Provide Voltage Rails #########

class VoltageRegulator:
  def __init__(self, name, output_voltage, threads, quiescent_current_ma, is_switching, efficiency=70.0, max_current_output_ma=None, dropout_voltage=None):
    self.name = name
    self.threads = threads
    self.quiescent_current_ma = quiescent_current_ma
    self.is_switching = is_switching
    self.output_voltage = output_voltage
    self.efficiency = efficiency
    self.max_current_output_ma = max_current_output_ma
    self.dropout_voltage = dropout_voltage
    self.total_regulator_output_current_ma = []

######### Embedded System is Highest Level #########
# Embedded system class has sources, which have regulators, which have threads, which have components
# In this way, even systems with multiple batteries, multiple power rails, and lots of components turning
# on and off can be analyzed easily

class EmbeddedSystem:
  def __init__(self, name, sources):
    self.name = name
    self.sources = sources
    self.time = []
    self.system_power_mW = []
    self.sim_time_sec = None

  def power_profile(self, sim_time_sec, record_time_history=False):
    self.sim_time_sec=sim_time_sec
    for source in self.sources:
      source.net_energy_J = 0.0
    current_t = 0.0

    while(current_t < sim_time_sec):
      
      # Determine increment
      shortest_dt = 1.0e6
      for source in self.sources:
        for regulator in source.regulators:
          for thread in regulator.threads:
            dt = thread.next_stage_change_t - current_t
            if dt < shortest_dt:
              shortest_dt = dt 
      
      # Calculate energy use by each thread
      total_system_power_mW = 0.0
      for source in self.sources:
        total_source_current_ma = 0.0
        for regulator in source.regulators:
          total_regulator_output_current_ma = 0.0
          for thread in regulator.threads:
            for component in thread.stages[thread.stage_index].components:
              total_regulator_output_current_ma = total_regulator_output_current_ma + component.current_ma
          
          # Check for violations of capability
          if regulator.max_current_output_ma is not None and total_regulator_output_current_ma > regulator.max_current_output_ma:
            print("Error: Regulator {0} cannot provide enough current, at t={1}".format(regulator.name, current_t))

          # Sum up over regulators, with quiescent current
          total_source_current_ma = total_source_current_ma + regulator.quiescent_current_ma 
          if regulator.is_switching:
            # Compute with efficiency
            # TODO not quite right due to lowered source voltage
            total_source_current_ma = total_source_current_ma + (regulator.output_voltage / (source.get_current_voltage(total_regulator_output_current_ma) * regulator.efficiency))*total_regulator_output_current_ma
            # TODO future do efficiency curve vs. current
          else:
            # Linear regulator, so output current is input current
            total_source_current_ma = total_source_current_ma + total_regulator_output_current_ma

          # Store per regulator
          if record_time_history:
            regulator.total_regulator_output_current_ma.append(total_regulator_output_current_ma)

        source_voltage = source.get_current_voltage(total_source_current_ma)
        # Calculate power in and out of sources
        total_system_power_mW = total_system_power_mW + (source_voltage * total_source_current_ma)

        # Log per source
        if record_time_history:
          source.time.append(current_t)
          source.charge_history_time.append(current_t)
          source.charge_history_mAh.append(source.current_charge_mAh)
          source.voltage_history.append(source_voltage)
          source.current_history_ma.append(total_source_current_ma)

      # Log for whole system
      if record_time_history:
        self.time.append(current_t)
        self.system_power_mW.append(total_system_power_mW)

      # Increment time
      current_t = current_t + shortest_dt

      # Log again after time increment to get correct square profiles on plots
      if record_time_history:
        self.time.append(current_t)
        self.system_power_mW.append(total_system_power_mW)

        for source in self.sources:
          for regulator in source.regulators:
            regulator.total_regulator_output_current_ma.append(regulator.total_regulator_output_current_ma[-1])
          source.time.append(current_t)
          source.voltage_history.append(source.voltage_history[-1])
          source.current_history_ma.append(source.current_history_ma[-1])

      # Energy harvesting if added, after logging
        if source.energy_harvesting is not None:
          harvested_power_W = source.energy_harvesting.calculate_power(current_t)
          if(source.current_charge_mAh < source.capacity_mAh):
            J_charged = source.energy_harvesting.charge_efficiency * shortest_dt * harvested_power_W
            source.net_energy_J = source.net_energy_J + J_charged
            source.current_charge_mAh = source.current_charge_mAh + (0.277778*J_charged/source_voltage)

        J_discharged = shortest_dt * source_voltage * (total_source_current_ma * 0.001)
        source.net_energy_J = source.net_energy_J - J_discharged
        source.current_charge_mAh = source.current_charge_mAh - (0.277778*J_discharged/source_voltage)

        if source.current_charge_mAh > source.capacity_mAh:
          source.current_charge_mAh = source.capacity_mAh

      # Update thread timing and stages
      for source in self.sources:
        for regulator in source.regulators:
          for thread in regulator.threads:
            # epsilon added for fpu reasons
            if current_t >= (thread.next_stage_change_t - 1e-7):
              thread.stage_index = thread.stage_index + 1
              thread.last_stage_change_t = current_t

              if(thread.stage_index >= thread.num_stages):
                thread.stage_index = 0 # cyclical

              thread.next_stage_change_t = current_t + thread.stages[thread.stage_index].delta_t_sec

        if source.current_charge_mAh <= 0.0:
          print("Error: Source {0} has reached an empty state of charge, at t={1}".format(source.name, current_t))
          break

  def plot(self):
    # TODO
    a = 0
  
  def print_summary(self):

    print(".........................................................")
    print("Source, Regulator, Regulator Output Voltage (V) , Regulator Total Current (mAh), Run Time (s)")
    for source in self.sources:
      for reg in source.regulators:
        current_total_mAh = 0.0
        for i in range(1,len(reg.total_regulator_output_current_ma)):
          current_total_mAh = current_total_mAh + (reg.total_regulator_output_current_ma[i])*(source.time[i] - source.time[i-1])/3600.0
        print("{0}, {1}, {2:.2f}, {3:.4f}, {4:.2f}".format(source.name, reg.name, reg.output_voltage, current_total_mAh, self.sim_time_sec))
    print(".........................................................")

    for source in self.sources:
      if source.energy_harvesting is not None:
        if source.current_charge_mAh > source.initial_charge_mAh:
          print("Charge of source {0} has increased by {1:.2f}% to {2:.2f}% total state of charge".format(source.name, 
                    100.0*(source.current_charge_mAh-source.initial_charge_mAh)/source.initial_charge_mAh, 100.0*source.current_charge_mAh/source.capacity_mAh))
        else:
          print("Charge of source {0} has decreased by {1:.2f}% to {2:.2f}% total state of charge".format(source.name, 
                    100.0*(source.initial_charge_mAh-source.current_charge_mAh)/source.current_charge_mAh, 100.0*source.current_charge_mAh/source.capacity_mAh))
          
      else:
        # Battery life is computed assuming this section is meaningfully long and we calculate
        # total battery life from a full battery
        drain_mAh_per_second = (source.initial_charge_mAh - source.current_charge_mAh) / self.sim_time_sec
        battery_life_seconds = source.capacity_mAh / drain_mAh_per_second
        if battery_life_seconds < 24*3600:
          print("Battery life is {0:.2f} hours".format(battery_life_seconds / 3600.0))
        elif battery_life_seconds < 365*24*3600:
          print("Battery life is {0:.2f} days".format(battery_life_seconds / (24.0*3600.0)))
        else:
          print("Battery life is {0:.2f} years".format(battery_life_seconds / (24.0*3600.0*365.0)))