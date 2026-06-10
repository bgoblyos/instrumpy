"""
Copyright (C) 2025 Bence Göblyös

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see https://www.gnu.org/licenses/.
"""

import pandas as pd
import numpy as np
import struct
import time
import logging

class SR830M():
    def __init__(self, rm, address):
        # Set up logger
        self.logger = logging.getLogger('instrumpy.SR830M')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")
        
        self.device = rm.open_resource(address)

        if "ASRL" in address:
            self.logger.info("Serial connection detected")
            self.device.baud_rate = 19200
            self.device.read_termination = '\r'
            self.device.write_termination = '\r\n'
            self.serial = True
        else:
            self.serial = False

        self.device.timeout = 100000

        self.bufferSize = 16383

        self.sensDF = pd.DataFrame(
            columns = ["i", "V", "Vstr", "I", "Istr"],
            data = [
                [0,  2.0e-09, "2 nV",   2.0e-15, "2 fA"   ],
                [1,  5.0e-09, "5 nV",   5.0e-15, "5 fA"   ],
                [2,  1.0e-08, "10 nV",  1.0e-14, "10 fA"  ],
                [3,  2.0e-08, "20 nV",  2.0e-14, "20 fA"  ],
                [4,  5.0e-08, "50 nV",  5.0e-14, "50 fA"  ],
                [5,  1.0e-07, "100 nV", 1.0e-13, "100 fA" ],
                [6,  2.0e-07, "200 nV", 2.0e-13, "200 fA" ],
                [7,  5.0e-07, "500 nV", 5.0e-13, "500 fA" ],
                [8,  1.0e-06, "1 uV",   1.0e-12, "1 pA"   ],
                [9,  2.0e-06, "2 uV",   2.0e-12, "2 pA"   ],
                [10, 5.0e-06, "5 uV",   5.0e-12, "5 pA"   ],
                [11, 1.0e-05, "10 uV",  1.0e-11, "10 pA"  ],
                [12, 2.0e-05, "20 uV",  2.0e-11, "20 pA"  ],
                [13, 5.0e-05, "50 uV",  5.0e-11, "50 pA"  ],
                [14, 1.0e-04, "100 uV", 1.0e-10, "100 pA" ],
                [15, 2.0e-04, "200 uV", 2.0e-10, "200 pA" ],
                [16, 5.0e-04, "500 uV", 5.0e-10, "500 pA" ],
                [17, 1.0e-03, "1 mV",   1.0e-09, "1 nA"   ],
                [18, 2.0e-03, "2 mV",   2.0e-09, "2 nA"   ],
                [19, 5.0e-03, "5 mV",   5.0e-09, "5 nA"   ],
                [20, 1.0e-02, "10 mV",  1.0e-08, "10 nA"  ],
                [21, 2.0e-02, "20 mV",  2.0e-08, "20 nA"  ],
                [22, 5.0e-02, "50 mV",  5.0e-08, "50 nA"  ],
                [23, 1.0e-01, "100 mV", 1.0e-07, "100 nA" ],
                [24, 2.0e-01, "200 mV", 2.0e-07, "200 nA" ],
                [25, 5.0e-01, "500 mV", 5.0e-07, "500 nA" ],
                [26, 1.0e+00, "1 V",    1.0e-06, "1 uA"   ]
            ]
        )
        
        self.tauDF = pd.DataFrame(
            columns = ["i", "t", "tstr"],
            data = [
                [0,  1.0e-05, "10 us"  ],
                [1,  3.0e-05, "30 us"  ],
                [2,  1.0e-04, "100 us" ],
                [3,  3.0e-04, "300 us" ],
                [4,  1.0e-03, "1 ms"   ],
                [5,  3.0e-03, "3 ms"   ],
                [6,  1.0e-02, "10 ms"  ],
                [7,  3.0e-02, "30 ms"  ],
                [8,  1.0e-01, "100 ms" ],
                [9,  3.0e-01, "300 ms" ],
                [10, 1.0e+00, "1 s"    ],
                [11, 3.0e+00, "3 s"    ],
                [12, 1.0e+01, "10 s"   ],
                [13, 3.0e+01, "30 s"   ],
                [14, 1.0e+02, "100 s"  ],
                [15, 3.0e+02, "300 s"  ],
                [16, 1.0e+03, "1 ks"   ],
                [17, 3.0e+03, "3 ks"   ],
                [18, 1.0e+04, "10 ks"  ],
                [19, 3.0e+04, "30 ks"  ]
            ]
        )

        self.srateDF = pd.DataFrame(
            columns = ["i", "srate", "sratestr"],
            data = [
                [0,  6.25e-02, "62.5 mHz" ],
                [1,  1.25e-01, "125 mHz"  ],
                [2,   2.5e-01, "250 mHz"  ],
                [3,   5.0e-01, "500 mHz"  ],
                [4,   1.0e+00, "1 Hz"     ],
                [5,   2.0e+00, "2 Hz"     ],
                [6,   4.0e+00, "4 Hz"     ],
                [7,   8.0e+00, "8 Hz"     ],
                [8,   1.6e+01, "16 Hz"    ],
                [9,   3.2e+01, "32 Hz"    ],
                [10,  6.4e+01, "64 Hz"    ],
                [11, 1.28e+02, "128 Hz"   ],
                [12, 2.56e+02, "256 Hz"   ],
                [13, 5.12e+02, "512 Hz"   ],
                [14,        0, "Trigger"  ]
            ]
        )
        
        self.disp1Dict = {
            "X": 0,
            "R": 1,
            "XN": 2,
            "XNOISE": 2,
            "A1": 3,
            "AUX1": 3,
            "A2": 4,
            "AUX2": 4,
        }
        
        self.disp2Dict = {
            "Y": 0,
            "THETA": 1,
            "Θ": 1,
            "YN": 2,
            "YNOISE": 2,
            "A3": 3,
            "AUX3": 3,
            "A4": 4,
            "AUX4": 4,
        }
        
        self.snapDict = {
             "X": 1,
             "Y": 2,
             "R": 3,
             "THETA": 4,
             "Θ": 4,
             "A1": 5,
             "AUX1": 5,
             "A2": 6,
             "AUX2": 6,
             "A3": 7,
             "AUX3": 7,
             "A4": 8,
             "AUX4": 8,
             "REF": 9,
             "FREQ": 9,
             "DISP1": 10,
             "D1": 10,
             "CH1": 10,
             "DISP2": 11,
             "D2": 11,
             "CH2": 11,
        }
       
    def setSensitivity(self, target, setMode = True):
        """
        Sets a specified sensitivity. 

        Parameters
        ----------
        target: str or int
            If str, try to parse it based on the translation table (see SR830M.sensDF).
            If int, set it directly (see translation table or instrument manual). Negative values indicate current measurement mode.
        
        setMode: Bool, default: True
            Whether to automatically set the input mode. Defaults to A in voltage mode and I (100 MΩ) in current mode. Set to False for more granular control.

        Returns
        -------
        sens: float
            Achieved sensitivity (float). -1 indicates an error.
        current: Bool
            Voltage (False) or current (True) mode
        """

        i = None
        current = False

        if type(target) is str:
            if target in self.sensDF.Vstr.values:
                row = np.argwhere(self.sensDF.Vstr == target)[0,0]
                i = self.sensDF.i[row]
            elif target in self.sensDF.Istr.values:
                row = np.argwhere(self.sensDF.Istr == target)[0,0]
                i = self.sensDF.i[row]
                current = True
            else:
                self.logger.error("Requested sensitivity string is invalid.")
                return -1, None

        elif type(target) is int:
            if target < 0:
                target = -target
                current = True

            if target in self.sensDF.i.values:
                i = target
            else:
                self.logger.error("Requested sensitivity index is invalid.")
                return -1, None
        
        else:
            self.logger.error("Requested sensitivity type is invalid.")
            return -1, None

        if current and setMode:
            self.setInputMode(3)
        elif setMode:
            self.setInputMode(0)

        self.device.write(f"SENS {i}")
        
        if current:
            return self.sensDF.I[np.argwhere(self.sensDF.i == i)[0,0]]
        else:
            return self.sensDF.V[np.argwhere(self.sensDF.i == i)[0,0]]

    def setSensitivityV(self, target, **kwargs):
        row = np.argmin(np.abs(self.sensDF.V - target))
        i = self.sensDF.i[row]
        return self.setSens(i, **kwargs)

    def setSensitivityA(self, target, **kwargs):
        row = np.argmin(np.abs(self.sensDF.I - target))
        i = self.sensDF.i[row]
        return self.setSens(-i, **kwargs)
    
    def getSensitivity(self):
        current = self.getInputMode() >= 2
        i = int(self.device.query("SENS?")) 
        row = np.argwhere(self.sensDF.i == i)[0,0]

        if current:
            return -i, np.sensDF.I[row]
        else:
            return i, np.sensDF.V[row]

    def setSampleRate(self, target = None):
        """
        Sets a specified sample rate for automatic acquisition.

        Parameters
        ----------
        target: None, str or int
            Target sample rate. If None, set highest rate that is meaninful with the current time constant.
            If str, try to parse it based on the translation table (see SR830M.srateDF).
            If int, set it directly (see translation table or instrument manual).

        Returns
        -------
        Achieved sample rate in Hz (float). Trigger mode corresponds to 0, while -1 indicates a failure.
        """
        if target is None:
            # Attempt to set automatically based on time constant
            _, t = self.getTau()
            maxfreq = 1/t
            candidates = self.srateDF.srate[self.srateDF.srate <= maxfreq]
            maxvalid = np.max(candidates)
            row = np.argwhere(self.srateDF.srate == maxvalid)[0,0]
            i = self.srateDF.i[row]
            self.device.write(f"SRAT {i}")
            return maxvalid
            
        if type(target) is str:
            res = np.argwhere(self.srateDF.sratestr == target)
            if res.shape[0] < 1:
                self.logger.error("Requested sample rate string is invalid.")
                return -1
            else:
                i = self.srateDF.i[res[0,0]]
                self.device.write(f"SRAT {i}")
                return self.srateDF.srate[res[0,0]]

        elif type(target) is int:
            if target in self.srateDF.i.values:
                self.device.write(f"SRAT {target}")
                return self.srateDF.srate[np.argwhere(self.srateDF.i == target)[0,0]]
            else:
                self.logger.error("Requested sample rate index is invalid.")
                return -1
            
        else:
            self.logger.error("Sample rate input type is invalid.")
            return -1

    def setSamplerateHz(self, target):
        row = np.argmin(np.abs(self.srateDF.srate - target))
        i = self.srateDF.i[row]
        self.device.write(f"SRAT {i}")
        return self.srateDF.srate[row]

    def getSamplerate(self):
        """
        Query the device for the currently set sampling rate.

        Returns
        -------
        (i, f): index and frequency in Hz
        """
        resp = int(self.device.query("SRAT?"))
        i = np.argwhere(self.srateDF.i == resp)[0,0]
        f = self.tauDF.srate[i]
        return resp, f

    def setTau(self, target):
        """
        Sets a specified time constant.

        Parameters
        ----------
        target: str or int
            If str, try to parse it based on the translation table (see SR830M.srateDF).
            If int, set it directly (see translation table or instrument manual).

        Returns
        -------
        Achieved time constant (float). -1 indicates an error.
        """
        if type(target) is str:
            res = np.argwhere(self.tauDF.tstr == target)
            if res.shape[0] < 1:
                self.logger.error("Requested time constant string is invalid.")
                return -1
            else:
                i = self.tauDF.i[res[0,0]]
                self.device.write(f"OFLT {i}")
                return self.tauDF.t[res[0,0]]

        elif type(target) is int:
            if target in self.tauDF.i:
                self.device.write(f"OFLT {target}")
                return self.tauDF.t[np.argwhere(self.tauDF.i == target)[0,0]]
            else:
                self.logger.error("Requested time constant index is invalid.")
                return -1
        else:
            self.logger.error("Time constant input type is invalid.")
            return -1

    def setTauS(self, target):
        row = np.argmin(np.abs(self.tauDF.t - target))
        i = self.tauDF.i[row]
        self.device.write(f"OFLT {i}")
        return self.tauDF.t[row]

    def getTau(self):
        """
        Query the device for the currently set time constant.

        Returns
        -------
        (i, t): index and time in seconds
        """
        resp = int(self.device.query("OFLT?"))
        i = np.argwhere(self.tauDF.i == resp)[0,0]
        t = self.tauDF.t[i]
        return resp, t


    # Oscillator settings
    def setLO(self, internal):
        """
        Set local oscillator source.

        Parameters
        ----------
        internal: Bool
            Set to True for internal, False for external source.
        
        """

        if internal:
            self.device.write("FMOD 1")
        else:
            self.device.write("FMOD 0")

    def getLO(self):
        """
        Query which frequency source is in use.

        Returns
        -------
        Bool: True for internal, False for external
        """

        resp = int(self.device.query("FMOD?"))
        
        return resp == 1

    def setFreq(self, freq):
        # TODO: Consider harmonic detection for bounds checking.
        if freq >= 0.001 and freq <= 102000:
            self.device.write(f"FREQ {freq}")
            return True
        else:
            self.logger.error("Requested LO frequency is out of bounds.")
            return False

    def getFreq(self):
        return float(self.device.query("FREQ?"))

    def setPhase(self, phase):
        p = phase % 360 # It's easier to just wrap it here
        self.device.write(f"PHAS {p}")

    def getPhase(self):
        return float(self.device.query("PHAS?"))

    # Input configuration
    def setInputMode(self, mode):
        """
        Sets the input mode of the device.

        Parameters
        ----------
        mode: int
            Possible values: 0 - A (voltage)
                             1 - A-B (differential voltage)
                             2 - I (1 MΩ)
                             3 - I (100 MΩ)
        
        Returns
        -------
        success: Bool
        """

        if mode in [0, 1, 2, 3]:
            self.device.write(f"ISRC {mode}")
            return True
        else:
            self.logger.error("Input mode must be one of [0, 1, 2, 3].")
            return False

    def getInputMode(self):
        """
        Gets the input mode of the device.

        
        Returns
        -------
        mode: int
            Possible values: 0 - A (voltage)
                             1 - A-B (differential voltage)
                             2 - I (1 MΩ)
                             3 - I (100 MΩ)
        """
        return int(self.device.query("ISRC?")) 

    def setInputFloat(self, floating):
        # TODO: Implement
        return None

    def getInputFloat(self):
        # TODO: implement
        return None

    def setInputCoupling(self, dc):
        # TODO: Implement
        return None

    def getInputCoupling(self):
        # TODO: implement
        return None

    def setInputFilter(self, line, line2):
        # TODO: Implement
        return None

    def getInputFilter(self):
        # TODO: implement
        return None

    # Display settings
    def setDisplay(self, disp, target, ratio = 0):
        """
        Sets a specified display on the lock-in to a given value.
        Required for automated data collection.

        Parameters
        ----------
        disp: int
        target : str
            Select value to be displayed.
            Possible values for display 1: "X", "R", "XNOISE", "AUX1", "AUX2".
            Possible values for display 2: "Y", "THETA", "YNOISE", "AUX3", "AUX4".
        ratio : int, optional
            Display ratio. 0 is none, 1 is AUX1, 2 is AUX2. The default is 0.

        Returns
        -------
        True on success, False on failure.
        """
        
        if disp not in [1, 2]:
            self.logger.error("Please select display 1 or 2.")
            return False
        
        dispDict = self.disp1Dict if disp == 1 else self.disp2Dict
        
        target = target.upper()
        if target in dispDict:
            i = dispDict[target]
            cmd = f"DDEF {disp},{i},{ratio}"
            self.device.write(cmd)
            return True
        else:
            available = ", ".join(dispDict.keys())
            self.logger.error(f"The requested value is invalid. Request: {target}. Available values: {available}")
            return False

    def getDisplay(self):
        #TODO: implement
        return None

    def snapshot(self, params):
        if type(params) == str:
            params = [params]
            
        if len(params) > 6:
            self.logger.error("At most 6 parameters may be read out at once.")
            return None
        elif len(params) < 1:
            self.logger.error("At least one parameter must be read out.")
            return None
        
        indices = []
        for p in params:
            P = p.upper()
            if P in self.snapDict:
                indices.append(str(self.snapDict[P]))
            else:
                available = ", ".join(self.snapDict.keys())
                self.logger.error(f"A requested value is invalid. Request: {P}. Available values: {available}")
                return 0
        
        if len(indices) == 1:
            indices.append(indices[0])
            joined = ",".join(indices)
            cmd = "SNAP? " + joined
            #self.logger.info(cmd)
            resp = self.device.query(cmd)
            return list(map(float, resp.split(',')))[0:1]

        else:
            joined = ",".join(indices)
            cmd = "SNAP? " + joined
            #self.logger.info(cmd)
            resp = self.device.query(cmd)
            return list(map(float, resp.split(',')))
    
    def readBinNum(self):
        res = self.device.query('SPTS?')
        return int(res)
    
    def queryBinary(self, param):
        # Increse timeout, otherwise the transfer takes too long
        oldTimeout = self.device.timeout
        self.device.timeout = 60000 # 1 minute
    
        self.device.write(param)
        response = self.device.read_raw()
    
        # Reset the timeout
        self.device.timeout = oldTimeout
    
        return response
    
    def queryASCIIFloat(self, param):
        # Increse timeout, otherwise the transfer takes too long
        oldTimeout = self.device.timeout
        self.device.timeout = 60000 # 1 minute
    
        resp = self.device.query(param)
        
        decoded = list(map(float, resp.strip(',').split(',')))
    
        # Reset the timeout
        self.device.timeout = oldTimeout
    
        return decoded

    def queryBinaryFloat(self, param):
        response = self.queryBinary(param)
        entries = len(response) // 4
        data = struct.unpack(f"{entries}f", response)
        return list(data)
    
    def readBuffer(self, buffer, firstPoint = 0, numPoints = 0):
        bufferSize = self.readBinNum()

        if bufferSize == 0:
            #logging.warning("The lock-in buffer is empty, nothing could be retrieved.")
            return None

        if numPoints <= 0:
            numPoints = bufferSize - firstPoint

        if (firstPoint >= bufferSize) or (firstPoint < 0):
            self.logger.error(f"Starting index is out of bounds (requested index {firstPoint} from {bufferSize} elements)")
            return None

        if (firstPoint + numPoints) > bufferSize:
            self.logger.info("Requested too many points, clamping it.")
            numPoints = bufferSize - firstPoint

        if self.serial:
            queryStr = f"TRCA ? {buffer}, {firstPoint}, {numPoints}"
            return self.queryASCIIFloat(queryStr)
        else:
            queryStr = f"TRCB ? {buffer}, {firstPoint}, {numPoints}"
            return self.queryBinaryFloat(queryStr)
   
    def resetBuffer(self):
        self.device.write("REST")
        
    def triggerBuffer(self):
        self.device.write("TRIG")
        
    def pauseBuffer(self):
        self.device.write("PAUS")

    def enableTrigger(self, state = True):
        if state:
            self.device.write("TSTR 1")
        else:
            self.device.write("TSTR 0")
   
    def multiRead(self, ch1 = None, ch2 = None, t = 1, srate = None, wait = False):
        """
        Capture the given data on each channel for an amount of time and return the results.

        Parameters
        ----------
        ch1 : str, optional
            Value to capture on channel 1. Possible values: "X", "R", "XNOISE", "AUX1", "AUX2".
            Use None to disable this channel. The default is None.
        ch2 : str, optional
            Value to capture on channel 1. Possible values: "Y", "THETA", "YNOISE", "AUX3", "AUX4".
            Use None to disable this channel. The default is None.
        t : float, optional
            Acqusition time in seconds. The default is 1.
        srate : float, optional
            Sampling rate in Hz. If set to None, the highest available sampling rate is selected for the current time constant.
            The default is None.
        wait : bool, optiona
            Whether to wait for all planned points to arrive.
            If True, it will extent the desired time if there are not enough points in the buffer.
            If False, will return all points gathered up until the desired timer is up.
            The default is False.

        Returns
        -------
        ch1
            Numpy array of floats containing the data from channel 1.
        ch2
            Numpy array of floats containing the data from channel 2.

        """
        readCh1 = False
        readCh2 = False
        
        if ch1 is not None:
           readCh1 = self.setDisplay(1, ch1)

        if ch2 is not None:
           readCh2 = self.setDisplay(2, ch2)
           
        if (not readCh1) and (not readCh2):
            return None, None
        
        if srate is None:
            srate = self.setSampleRate(None)
        else:
            srate = self.setSamplerateHz(srate)
            
        self.logger.info(f"Sample rate is {srate}")
            
        if srate <= 0:
            self.logger.error("Failed to set sample rate for acqusition.")
            return None, None
        
        if 1/srate > t:
            self.logger.error("Sampling is too slow for the selected time period.")
            return None, None
        
        n = np.floor(srate * t)
        
        self.pauseBuffer()
        self.resetBuffer()
        self.enableTrigger()
        self.triggerBuffer()
        
        time.sleep(t)
        
        if wait:
            for i in range(100):
                if self.readBinNum() >= n:
                    break
                else:
                    time.sleep(0.1)
            
        dataCh1 = None
        dataCh2 = None
        
        self.pauseBuffer()
        
        if readCh1:
            dataCh1 = self.readBuffer(1, 0, n)
        
        if readCh2:
            dataCh2 = self.readBuffer(2, 0, n)
            
        return dataCh1, dataCh2

class SR830(SR830M):
    pass

        
