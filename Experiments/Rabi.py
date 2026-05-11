"""
Copyright (C) 2026 Bence Göblyös

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see https://www.gnu.org/licenses/.
"""

import pyvisa
import pandas as pd
import numpy as np
import time
from tqdm.notebook import tqdm
from Devices.LockIn import SR830M
from Devices.LO import KuhnePLL
from Devices.PicoPulse import PicoPulse

class Rabi():
    def __init__(self, lo_addr, lock_addr, pico_addr, pico_pins):
        """
        Initialize Rabi experiment.
    
        Parameters
        ----------
        lo_addr : str
            VISA address of the microwave oscillator.
        lock_addr : str
            VISA address of the lock-in amplifier.
        pico_addr : str
            VISA address of the pico-pulse device.
        pico_pins : dict
            Pin definitions for the pico-pulse device. Must map the keys
            'lockin', 'laser', 'I' and 'Q' to their respective channels.
    
        Returns
        -------
        None.
    
        """
        self.lo_addr = lo_addr
        self.lock_addr = lock_addr
        self.pico_addr = pico_addr
        self.pico_pins = pico_pins
        self.setupDevices()
        self.idleSeq()
        
        
    def __del__(self):
        self.unloadDevices()
        
    def setupDevices(self):
        self.rm = pyvisa.ResourceManager()
        self.lo = KuhnePLL(self.lo_addr)
        self.lock = SR830M(self.rm, self.lock_addr)
        self.pico = PicoPulse(self.rm, self.pico_addr, self.pico_pins)
        
    def unloadDevices(self):
        self.idleSeq() # Turn off laser before unloading the device
        self.lo = None
        self.lock = None
        self.pico = None
        self.rm.close()
        self.rm = None
        
    def refreshDevices(self):
        self.unloadDevices()
        self.setupDevices()
        
    def idleSeq(self, freq = 500):
        halft = round(1e9/(freq*2))
        seq = pd.DataFrame(
            columns = ["time", "lockin", "laser", "I", "Q"],
            data = [
                [halft, 1, 0, 0, 0],
                [halft, 0, 0, 0, 0]
            ]
        )
        
        self.pico.sendSequence(seq, cycle = False)
        self.idle = True
             
    def rabiSeq(self, tau, inner_halft = 100e3, laser_duty_cycle = 0.9, loops = 100):
        """
        Generate and send Rabi sequence.


        Parameters
        ----------
        tau : int
            Microwave excitation length in nanoseconds.
        inner_halft : int, optional
            Length of an elementray sequence period in nanoseconds. The default is 100e3.
        laser_duty_cycle : float, optional
            The laser spends this proportion of the elementary period turned on.
            Higher values have been shown to reduce noise. The default is 0.9.
        loops : int, optional
            The number of times the lementary sequence should be repeated per
            lock-in half period. Higher values allow more averaging with lower lock-in
            reference frequencies. The default is 100.

        Raises
        ------
        Exception
            An exception is raised if the desired sequence cannot be
            constructed because the padding length would become negative.

        Returns
        -------
        None.

        """
        
        if laser_duty_cycle <= 0 or laser_duty_cycle >= 1:
            raise Exception('Laser duty cycle must be between 0 and 1 (exclusive).')
        
        if loops <= 0:
            raise Exception('There must be at least one loop.')
        elif loops * 6 >= (1<<16):
            raise Exception('The generated sequence will not fin in the memory of the pico-pulse device. Reduce the number of loops.')

        laser_on = round(inner_halft*laser_duty_cycle)
        laser_off = round(inner_halft - laser_on)
        tpad = laser_off - tau
        if tpad < 20:
            raise Exception('Cannot generate Rabi sequence, padding is too short. Consider increasing the inner period time or reducing the laser duty cycle.')
        
        # Note: the sequence contains redundant pulses. This is to compensate any rounding errors.
        temp = []
        
        # Microwave cycle
        for i in range(loops):
            temp.append([tpad,     1, 0, 0, 0])
            temp.append([tau,      1, 0, 1, 1])
            temp.append([laser_on, 1, 1, 0, 0])
            
        # Reference cycle
        for i in range(loops):
            temp.append([tpad,     0, 0, 0, 0])
            temp.append([tau,      0, 0, 0, 0])
            temp.append([laser_on, 0, 1, 0, 0])
        
        seq = pd.DataFrame(
            columns = ["time", "lockin", "laser", "I", "Q"],
            data = temp
        )
         
        self.pico.sendSequence(seq, cycle = False)
        self.idle = False
        
    def measureRabi(self, tau, inner_halft = 100e3, laser_duty_cycle = 0.9, loops = 100,
                    mw_freq = None, settle = 1, integrate = 5, srate = None, comment = ""):
        """
        Measure a single Rabi sequence.

        Parameters
        ----------
        tau : int
            Microwave excitation length in nanoseconds.
        inner_halft : int, optional
            Length of an elementray sequence period in nanoseconds. The default is 100e3.
        laser_duty_cycle : float, optional
            The laser spends this proportion of the elementary period turned on.
            Higher values have been shown to reduce noise. The default is 0.9.
        loops : int, optional
            The number of times the lementary sequence should be repeated per
            lock-in half period. Higher values allow more averaging with lower lock-in
            reference frequencies. The default is 100.
        mw_freq: float, optinal
            Set microwave frequence in GHz. If None, do not set it. The default is None.
        settle : float, optional
            Amount of time in seconds to wait before starting data acquisition. The default is 1.
        integrate : float, optional
            Duration of data acqusition is seconds. The default is 5.
        srate : float, optional
            Sampling rate of the lock-in amplifier. Set to None for automatic. The default is None.
        comment : str, optional
            Attach a comment to the data point. The default is "".

        Returns
        -------
        dict
            Dictionary containing results and supplementary info.

        """
        
        
        returnToIdle = self.idle
        
        if mw_freq is not None:
            self.lo.setGHz(mw_freq)
            
        self.RabiSeq(tau, inner_halft = inner_halft, laser_duty_cycle = laser_duty_cycle, loops = loops)
        
        time.sleep(settle)
        Rs, thetas = self.lock.multiRead(ch1 = "R", ch2 = "THETA", t = integrate, srate = srate)
        
        lockin_freq_measured = self.lock.getFreq()
        
        if returnToIdle:
            self.idleSeq(lockin_freq_measured)
        
        return {
            "tau_ns": tau,
            "inner_halft_ns": inner_halft,
            "laser_duty_cycle": laser_duty_cycle,
            "loops": loops,
            "Rs_V": Rs,
            "Rmean": np.mean(Rs),
            "Rstd":  np.std(Rs),
            "thetas_deg": thetas,
            "settle_s": settle,
            "measure_s": integrate,
            "timestamp": time.time(),
            "lockin_freq_measured_Hz": lockin_freq_measured,
            "comment": comment
        }

    def iterateRabi(self, taus, inner_halft = 100e3, laser_duty_cycle = 0.9, loops = 100,
                    mw_freq = None, savedir = None, savename = "Rabi", shuffle = False, **kwargs):
        """
        Iterate over an array of taus and measure Rabi signal at them.

        Parameters
        ----------
        tau : int
            Microwave excitation length in nanoseconds.
        inner_halft : int, optional
            Length of an elementray sequence period in nanoseconds. The default is 100e3.
        laser_duty_cycle : float, optional
            The laser spends this proportion of the elementary period turned on.
            Higher values have been shown to reduce noise. The default is 0.9.
        loops : int, optional
            The number of times the lementary sequence should be repeated per
            lock-in half period. Higher values allow more averaging with lower lock-in
            reference frequencies. The default is 100.
        mw_freq: float, optinal
            Set microwave frequence in GHz. If None, do not set it. The default is None.
        savedir : str, optional
            Save directory. If not None, dump result into a JSON file at the given directory. The default is None.
        savename : str, optional
            String to append to saved filename. The default is "T1".
        lockin_freq : float, optional
            Set lock-in reference frequency in Hz. The default is 64.
        shuffle : Bool, optional
            Whether or not to shuffle the array beforehand. Useful for eliminating centrain measurement artifacts. The default is False.
        **kwargs : TYPE
            Pass arguments to T1.measureT1(). The valid arguments are "settle", "integrate", "srate" and "comment".

        Returns
        -------
        df : pandas.DataFrame
            DataFrame with each row representing a measurement.

        """
        
        if round((1-laser_duty_cycle)*inner_halft) - np.max(taus) < 20:
            raise Exception('At least one value of tau is too large for the given parameters.')
            
        if mw_freq is not None:
            self.lo.setGHz(mw_freq)
 
        tmp = []
        
        if shuffle:
            np.random.shuffle(taus)
            
        
        for tau in tqdm(taus):
            tmp.append(self.measureRabi(tau, inner_halft = 100e3, laser_duty_cycle = 0.9, loops = 100, mw_freq = None, **kwargs))
        
        df = pd.DataFrame.from_dict(tmp)
        tmp = None
        
        if savedir is not None:
            ts = round(time.time())
            fname = f"{savedir}/{ts}_{savename}"
            df.to_json(fname)
        
        self.idleSeq(1e9/(inner_halft*loops*2))
        return df