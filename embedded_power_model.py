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

import numpy as np

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

    power = self.rated_power_W*(1.0/0.65)*(np.sin(((2.0*np.pi)/86400)*(t-self.t_offset_sec)) - 0.35)
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

class LithiumBattery:

  soc_table = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 95.0, 100.0]
  cell_voltage_table = [2.25, 3.5, 3.65, 3.72, 3.73, 3.75, 3.76, 3.77, 3.78, 3.85, 4.1, 4.25]

  def __init__(self, number_cells, capacity_mAh, current_charge_mAh, internal_resistance_ohm):
    self.number_cells = number_cells
    self.capacity_mAh = capacity_mAh
    self.current_charge_mAh = current_charge_mAh
    self.internal_resistance_ohm = internal_resistance_ohm
    self.net_energy_J = 0.0
    self.time = []
    self.charge_history_mAh = []
    self.voltage_history = []
    self.current_history_ma = []

  def get_current_voltage(self, total_current_ma=0.0):
    soc = (self.current_charge_mAh / self.capacity_mAh)*100.0
    cell_voltage = self.cell_voltage_table[-1]
    for i in range(len(self.soc_table)-1):
      if (soc >= self.soc_table[i]) and (soc < self.soc_table[i+1]):
        cell_voltage = self.cell_voltage_table[i] + ((self.cell_voltage_table[i+1]-self.cell_voltage_table[i])/(self.soc_table[i+1]-self.soc_table[i])) * (soc-self.soc_table[i])
    
    cell_voltage = cell_voltage - self.internal_resistance_ohm*(total_current_ma*0.001)
    return self.number_cells * cell_voltage

class VoltageRegulator:
  def __init__(self, efficiency=0.0, max_current_output_ma=5000.0, dropout_voltage=0.0):
    self.efficiency = efficiency
    self.max_current_output_ma = max_current_output_ma
    self.dropout_voltage = dropout_voltage

class EmbeddedSystem:
  def __init__(self, name, threads, energy_storage, voltage_reg = VoltageRegulator(),
      nominal_voltage=3.3, energy_harvesting=None):
    self.name = name
    self.threads = threads
    self.energy_storage = energy_storage
    self.voltage_reg = voltage_reg
    self.nominal_voltage = nominal_voltage
    self.energy_harvesting = energy_harvesting
    self.total_system_current_ma = 0.0
    self.total_battery_current_ma = 0.0
    self.power_time = []
    self.system_power_mW = []

  def power_profile(self, sim_time_sec, record_time_history=False):
    self.energy_storage.net_energy_J = 0.0
    current_t = 0.0

    while(current_t < sim_time_sec):
      
      # Determine increment
      shortest_dt = 1.0e6
      for thread in self.threads:
        dt = thread.next_stage_change_t - current_t
        if dt < shortest_dt:
          shortest_dt = dt 
      
      # Calculate energy use by each thread
      total_system_power_mW = 0.0
      self.total_system_current_ma = 0.0
      self.total_battery_current_ma = 0.0
      for thread in self.threads:
        total_thread_current_ma = 0.0
        for component in thread.stages[thread.stage_index].components:
          total_thread_current_ma = total_thread_current_ma + component.current_ma

        self.total_system_current_ma = self.total_system_current_ma + total_thread_current_ma

        thread_battery_current = total_thread_current_ma + total_thread_current_ma*((self.nominal_voltage / self.energy_storage.get_current_voltage(0.0)) - 1.0)*self.voltage_reg.efficiency
        self.total_battery_current_ma = self.total_battery_current_ma + thread_battery_current

        total_system_power_mW = total_system_power_mW + (self.nominal_voltage * total_thread_current_ma)

        J_discharged = shortest_dt * self.energy_storage.get_current_voltage(0.0) * (thread_battery_current * 0.001)
        self.energy_storage.net_energy_J = self.energy_storage.net_energy_J - J_discharged
        self.energy_storage.current_charge_mAh = self.energy_storage.current_charge_mAh - 0.277778*J_discharged

      # Energy harvesting if added
      if self.energy_harvesting is not None:
        harvested_power_W = self.energy_harvesting.calculate_power(current_t)
        if(self.energy_storage.current_charge_mAh < self.energy_storage.capacity_mAh):
          J_charged = self.energy_harvesting.charge_efficiency * shortest_dt * harvested_power_W
          self.energy_storage.net_energy_J = self.energy_storage.net_energy_J + J_charged
          self.energy_storage.current_charge_mAh = self.energy_storage.current_charge_mAh + 0.277778*(J_charged)

      # Log data if requested
      if record_time_history:
        self.power_time.append(current_t)
        self.system_power_mW.append(total_system_power_mW)

        self.energy_storage.time.append(current_t)
        self.energy_storage.charge_history_mAh.append(self.energy_storage.current_charge_mAh)
        self.energy_storage.voltage_history.append(self.energy_storage.get_current_voltage(self.total_battery_current_ma))
        self.energy_storage.current_history_ma.append(self.total_battery_current_ma)

      # Increment time
      current_t = current_t + shortest_dt

      # Log again after time increment to get correct square profiles on plots
      if record_time_history:
        self.power_time.append(current_t)
        self.system_power_mW.append(total_system_power_mW)

        self.energy_storage.time.append(current_t)
        self.energy_storage.charge_history_mAh.append(self.energy_storage.current_charge_mAh)
        self.energy_storage.voltage_history.append(self.energy_storage.get_current_voltage(self.total_battery_current_ma))
        self.energy_storage.current_history_ma.append(self.total_battery_current_ma)

      # Update thread timing and stages
      for thread in self.threads:
        # epsilon added for fpu reasons
        if current_t >= (thread.next_stage_change_t - 1e-7):
          thread.stage_index = thread.stage_index + 1
          thread.last_stage_change_t = current_t

          if(thread.stage_index >= thread.num_stages):
            thread.stage_index = 0 # cyclical

          thread.next_stage_change_t = current_t + thread.stages[thread.stage_index].delta_t_sec

      if self.energy_storage.current_charge_mAh <= 0.0:
        break