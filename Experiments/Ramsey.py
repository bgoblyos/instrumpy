import pyvisa
import pandas as pd
import numpy as np
import time
from tqdm.notebook import tqdm
from Devices.LockIn import SR830M
from Devices.LO import KuhnePLL
from Devices.PicoPulse import PicoPulse

class Ramsey():
    def __init__(self, lo_addr, lock_addr, pico_addr, pico_pins):
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
             
    def ramseySeq(self, tau, taumax, rabi_period, init = 45e3, read = 10e3, loops = 100):
        pad = taumax - tau
        r90 = rabi_period / 4
        r270 = 3 * rabi_period / 4
        seq = pd.DataFrame(
            columns = ["time", "lockin", "laser", "I"],
            data = [
                [init, 1, 1, 0],
                [r90,  1, 0, 1],
                [tau,  1, 0, 0],
                [r270, 1, 0, 1],
                [read, 1, 1, 0],
                [pad,  1, 0, 0]
            ] * loops + [
                [init, 0, 1, 0],
                [r90,  0, 0, 0],
                [tau,  0, 0, 0],
                [r270, 0, 0, 0],
                [read, 0, 1, 0],
                [pad,  0, 0, 0]
            ] * loops

        self.pico.sendSequence(seq, cycle = False)
        self.idle = False

    def measureRamsey(self, tau, tau_max, rabi_period, mw_freq = None, init = 45e3, read = 10e3, loops, settle = 1, integrate = 5, srate=None, comment = ""):
        returnToIdle = self.idle
        
        if mw_freq is not None and type(mw_freq) != str:
            self.lo.setGHz(mw_freq)

        self.ramseySeq(tau, tau_max, rabi_period, init=init, read=read, loops=loops)
        
        Rs, thetas = self.lock.multiRead(ch1 = "R", ch2 = "THETA", t = integrate, srate = srate)

        lockin_freq_measured = self.lock.getFreq()

        return {
            "tau_ns": tau,
            "pad_target": tau_max,
            "init": init,
            "read": read,
            "mw_freq": mw_freq,
            "rabi_period": rabi_period,
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

    def iterateRamsey(self, taus, rabi_period, mw_freq = None, savedir = None, savename = "Ramsey", shuffle = False, **kwargs):
        if mw_freq is not None:
            self.lo.setGHz(mw_freq)

        taumax = np.max(taus) + 100

        tmp = []
        
        if shuffle:
            np.random.shuffle(taus)
            
        
        for tau in tqdm(taus):
            tmp.append(self.measureRamsey(tau, taumax, rabi_period, mw_freq = str(mw_freq), **kwargs))
        
        df = pd.DataFrame.from_dict(tmp)
        tmp = None
        
        if savedir is not None:
            ts = round(time.time())
            fname = f"{savedir}/{ts}_{savename}"
            df.to_json(fname)
        
        self.idleSeq()
        return df

