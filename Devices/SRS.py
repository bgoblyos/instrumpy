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
import datetime

class SR8x0():
    def setSamplerateHz(self, target):
        row = np.argmin(np.abs(self.srateDF.srate - target))
        i = self.srateDF.i[row]
        self.device.write(f"SRAT {i}")
        return i

    def getSamplerate(self):
        """
        Query the device for the currently set sampling rate.

        Returns
        -------
        (i, f): index and frequency in Hz
        """
        resp = int(self.device.query("SRAT?"))
        i = np.argwhere(self.srateDF.i == resp)[0,0]
        f = self.srateDF.srate[i]
        return resp, f

    sensDF = pd.DataFrame(
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

    tauDF = pd.DataFrame(
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

    srateDF = pd.DataFrame(
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

    def queryBinary(self, param):
        # Increse timeout, otherwise the transfer takes too long
        oldTimeout = self.device.timeout
        self.device.timeout = 10000 # 10 seconds

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

    def resetBuffer(self):
        self.device.write("REST")

    def trigger(self):
        self.device.write("TRIG")

    def startBuffer(self):
        self.device.write("STRT")

    def pauseBuffer(self):
        self.device.write("PAUS")

    def enableTrigger(self, state = True):
        if state:
            self.device.write("TSTR 1")
        else:
            self.device.write("TSTR 0")

    def setGrounding(self, grounded = False):
        self.device.write(f'IGND {'1' if grounded else '0'}')

    def getGrounding(self):
        resp = self.device.query('IGND?')
        return int(resp) == 1

    grounding = property(fget=getGrounding, fset=setGrounding)

    def setDC(self, DC = False):
        self.device.write(f'ICPL {'1' if DC else '0'}')

    def getDC(self):
        resp = self.device.query('ICPL?')
        return int(resp) == 1

    DC = property(fget=getDC, fset=setDC)

    def setNotchFilter(self, setting = 0):
        # 0 is neither, 1 is line, 2 is line*2, 3 is both
        self.device.write(f'ILIN {setting}')

    def getNotchFilter(self):
        resp = self.device.query('ILIN?')
        return int(resp)

    notchFilter = property(fget=getNotchFilter, fset=setNotchFilter)

    def setReserve(self, reserve = 1):
        # 0 is high reserve, 1 is normal (or manual for SR850), 2 is low noise
        self.device.write(f'RMOD {reserve}')

    def getReserve(self):
        resp = self.device.query('RMOD?')
        return int(resp)

    reserve = property(fget=getReserve, fset=setReserve)

    def setSlope(self, slope = 0):
        self.device.write(f'OFSL {slope}')

    def getSlope(self):
        resp = self.device.query('OFSL?')
        return int(resp)

    slope = property(fget=getSlope, fset=setSlope)

class SR830(SR8x0):
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

    bufferSize = 16383

    disp1Dict = {
        "X": 0,
        "R": 1,
        "XN": 2,
        "XNOISE": 2,
        "A1": 3,
        "AUX1": 3,
        "A2": 4,
        "AUX2": 4,
    }

    disp2Dict = {
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

    snapDict = {
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
            cmd = "SNAP ? " + joined
            self.logger.info(cmd)
            resp = self.device.query(cmd)
            return list(map(float, resp.split(',')))[0:1]

        else:
            joined = ",".join(indices)
            cmd = "SNAP? " + joined
            #self.logger.info(cmd)
            resp = self.device.query(cmd)
            return list(map(float, resp.split(',')))

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

    def readBinNum(self):
        res = self.device.query('SPTS?')
        return int(res)

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
        self.startBuffer()
        
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

class SR850(SR8x0):
    def __init__(self, rm, address):
        # Set up logger
        self.logger = logging.getLogger('instrumpy.SR850')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        self.device = rm.open_resource(address)
        self.device.write_termination = '\n'
        self.device.read_termination = '\n'

        self.device.write('OUTX 1')

        self.setDate()

        #self.device.timeout = 100000

    snapDict = {
            "X": 1,
            "Y": 2,
            "R": 3,
            "THETA": 4,
            "Θ": 4,
            "REF": 5,
            "F": 5,
            "FREQ": 5,
    }

    traceDict = {
        '1': 0,
        "X": 1,
        "Y": 2,
        "R": 3,
        "THETA": 4,
        "Θ": 4,
        "REF": 14,
        "F": 14,
        "FREQ": 14,
    }

    def setDate(self):
        t = datetime.datetime.now()

        self.device.write(f'THRS {t.hour}')
        self.device.write(f'TMIN {t.minute}')
        self.device.write(f'TSEC {t.second}')
        self.device.write(f'DMTH {t.month}')
        self.device.write(f'DDAY {t.day}')
        self.device.write(f'DYRS {t.year % 100}')

    def snapshot(self, *params):
        """
        Emulates the snapshot function of the SR830.
        Does not actually guarantee that the samples are taken at the same time.
        """

        indices = []
        for p in params:
            P = p.upper()
            if P in self.snapDict:
                indices.append(self.snapDict[P])
            else:
                available = ", ".join(self.snapDict.keys())
                self.logger.error(f"A requested value is invalid. Request: {P}. Available values: {available}")
                return 0

        resp = []
        for i in indices:
            if i == 5:
                resp.append(self.getFreq())
            else:
                cmd = f"OUTP? {i}"
                resp.append(float(self.device.query(cmd)))

        return resp

    def getTraceLength(self, i):
        cmd = f"SPTS? {i}"
        return int(self.device.query(cmd))

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

        if mode in [0, 1]:
            self.device.write(f"ISRC {mode}")
            return True
        elif mode in [3, 4]:
            self.device.write("ISRC 3")
            self.device.write(f"IGAN {mode - 3}")
            return True
        else:
            self.logger.error("Input mode must be one of [0, 1, 2, 3].")
            return False

    def setTraceSource(self, i, target, multiply = 0, divide = 0, store = True):
        if type(target) is int:
            j = target
        else:
            j = self.traceDict.get(target.upper(), None)
            if j is None:
                available = ", ".join(self.traceDict.keys())
                self.logger.error(f"The requested target is invalid. Request: {P}. Available values: {available}")
                return False

        if type(multiply) is int:
            k = multiply
        else:
            k = self.traceDict.get(target.upper(), None)
            if k is None:
                available = ", ".join(self.traceDict.keys())
                self.logger.error(f"The requested multiplier is invalid. Request: {P}. Available values: {available}")
                return False

        if type(divide) is int:
            l = divide
        else:
            l = self.traceDict.get(target.upper(), None)
            if l is None:
                available = ", ".join(self.traceDict.keys())
                self.logger.error(f"The requested divider is invalid. Request: {P}. Available values: {available}")
                return False

        self.device.write(f'TRCD {i},{j},{k},{l},{'1' if store else '0'}')

    def getTraceSource(self, i):
        resp = self.device.query(f'TRCD? {i}')
        return [int(x) for x in resp.split(',')]

    def startTrace(self):
        self.device.write('STRT')

    def pauseTrace(self):
        self.device.write('PAUS')

    def resetTrace(self):
        self.device.write('REST')

    def readTrace(self, i, start, length):
        self.pauseTrace()
        length = np.minimum(length, self.getTraceLength(i) - start)
        if length <= 0:
            self.logger.error(f'Start of readout ({start}) must be less than the number of points in the trace ({self.getTraceLength(i)})')
        return self.queryBinaryFloat(f'TRCB? {i},{start},{length}')

    def multiRead(self, tr1 = None, tr2 = None, tr3 = None, tr4 = None, t = 1, srate = None, wait = False):

        data = [None, None, None, None]

        readTraces = [tr is not None for tr in [tr1, tr2, tr3, tr4]]

        if not np.any(readTraces):
            self.logger.error("At least one trace must be configured for acquistion.")
            return data

        if srate is None:
            srate = self.setSampleRate(None)
        else:
            srate = self.setSamplerateHz(srate)

        self.logger.info(f"Sample rate is {srate}")

        if srate <= 0:
            self.logger.error("Failed to set sample rate for acqusition.")
            return data

        if 1/srate > t:
            self.logger.error("Sampling is too slow for the selected time period.")
            return data

        n = np.floor(srate * t)

        self.pauseTrace()
        self.resetTrace()

        for i, tr in enumerate([tr1, tr2, tr3, tr4]):
            if tr is None:
                self.setTraceSource(i + 1, target = 0, store = False)
            else:
                self.setTraceSource(i + 1, target = tr, store = True)

        self.startTrace()
        time.sleep(t)

        if wait:
            time.sleep(1)

        self.pauseTrace()

        for i in range(4):
            if readTraces[i]:
                print(f'Reading trace for {i+1}')
                data[i] = self.readTrace(i+1, 0, n)

        return data

    # Oscillator settings
    def setLO(self, source):
        """
        Set local oscillator source.

        Parameters
        ----------
        source: int
            0 is internal, 1 is internal sweep and 2 is external
        """

        self.device.write(f"FMOD {i}")

    def getLO(self):
        """
        Query which frequency source is in use.

        Returns
        -------
        int: 0 is internal, 1 is internal sweep and 2 is external
        """

        return int(self.device.query("FMOD?"))

    def setReserve(self, reserve = 3):
        # int between 0 and 5 inclusive, 0 is minimum reserve, 5 is maximum
        self.device.write('RMOD 1') # set manual reserve
        self.device.write(f'RSRV {reserve}')

    def getReserve(self):
        resp = self.device.query('RSRV?')
        return int(resp)

    reserve = property(fget=getReserve, fset=setReserve)
