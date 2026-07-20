# Copyright (C) 2025-2026 Bence Göblyös
#
# This program is free software: you can redistribute it and/or modify it under
#  terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see https://www.gnu.org/licenses/.

"""
This module contains drivers for Stanford Research Systems devices.
Currently, this includes the SR830 and SR850 lock-in amplifier models.

The SR8x0 class contains common API elements, while the SR830 and SR850 classes implement device-specific functions.
"""

import pandas as pd
import numpy as np
import struct
import time
import logging
import datetime

class SR8x0():
    def _setSamplerateHz(self, target):
        """
        Sets the sample rate for automatic acquisition.

        Parameters
        ----------
        target: float
            Target sampling frequence is Hz.

        Returns
        -------
        achieved: int
            Index of closest achievable sampling frequency in Hz.
            This is the one that was set on the device.
        """
        row = np.argmin(np.abs(self._srateDF.srate - target))
        i = self._srateDF.i[row]
        self.device.write(f"SRAT {i}")
        return i

    def getSamplerate(self):
        """
        Query the device for the currently set sampling rate.

        Returns
        -------
        i: int
            Index of frequency setting
        f: float
            Sampling frequency in Hz.
        """
        resp = int(self.device.query("SRAT?"))
        i = np.argwhere(self._srateDF.i == resp)[0,0]
        f = self._srateDF.srate[i]
        return resp, f

    def _getSamplerateHz(self):
        resp, f = self.getSamplerate
        return f

    #: float: Gets or sets the sample rate in Hz.
    sampleRate = property(fget=_getSamplerateHz,fset=_setSamplerateHz)

    #: pandas.DataFrame: translation table for sensitivity settings
    _sensDF = pd.DataFrame(
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

    #: pandas.DataFrame: translation table for time constant settings
    _tauDF = pd.DataFrame(
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

    #: pandas.DataFrame: translation table for sample rate settings
    _srateDF = pd.DataFrame(
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
            If str, try to parse it based on the translation table (see SR830M._sensDF).
            If int, set it directly (see translation table or instrument manual). Negative values indicate current measurement mode.
        setMode: Bool, default: True
            Whether to automatically set the input mode. Defaults to A in voltage mode and I (100 MΩ) in current mode.
            Set to False for more granular control.

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
            if target in self._sensDF.Vstr.values:
                row = np.argwhere(self._sensDF.Vstr == target)[0,0]
                i = self._sensDF.i[row]
            elif target in self._sensDF.Istr.values:
                row = np.argwhere(self._sensDF.Istr == target)[0,0]
                i = self._sensDF.i[row]
                current = True
            else:
                self.logger.error("Requested sensitivity string is invalid.")
                return -1, None

        elif type(target) is int:
            if target < 0:
                target = -target
                current = True

            if target in self._sensDF.i.values:
                i = target
            else:
                self.logger.error("Requested sensitivity index is invalid.")
                return -1, None

        else:
            self.logger.error("Requested sensitivity type is invalid.")
            return -1, None

        if current and setMode:
            self._setInputMode(3)
        elif setMode:
            self._setInputMode(0)

        self.device.write(f"SENS {i}")

        if current:
            return self._sensDF.I[np.argwhere(self._sensDF.i == i)[0,0]]
        else:
            return self._sensDF.V[np.argwhere(self._sensDF.i == i)[0,0]]

    def setSensitivityV(self, target, **kwargs):
        """
        Sets the sensitivity in volts.

        Parameters
        ----------
        target: float
            Target sensitivity in V.
        setMode: Bool, default: True
            Whether to automatically set the input mode to voltage. Defaults to A mode if True.

        Returns
        -------
        sens: float
            Achieved sensitivity in volts or amperes. -1 indicates an error.
        current: Bool
            Voltage (False) or current (True) mode.
        """
        row = np.argmin(np.abs(self._sensDF.V - target))
        i = self._sensDF.i[row]
        return self.setSens(i, **kwargs)

    def setSensitivityA(self, target, **kwargs):
        """
        Sets the sensitivity in amperes.

        Parameters
        ----------
        target: float
            Target sensitivity in A.
        setMode: Bool, default: True
            Whether to automatically set the input mode to current. Defaults to 100 MΩ mode if True.

        Returns
        -------
        sens: float
            Achieved sensitivity in volts or amperes. -1 indicates an error.
        current: Bool
            Voltage (False) or current (True) mode.
        """
        row = np.argmin(np.abs(self._sensDF.I - target))
        i = self._sensDF.i[row]
        return self.setSens(-i, **kwargs)

    def getSensitivity(self):
        """
        Get the sensitivity of the device.

        Returns
        -------
        index: int
            Index of sensitvity setting. Negative values indicate current mode.
        sens: float
            Achieved sensitivity in volts or amperes.
        """
        current = self._getInputMode() >= 2
        i = int(self.device.query("SENS?"))
        row = np.argwhere(self._sensDF.i == i)[0,0]

        if current:
            return -i, np._sensDF.I[row]
        else:
            return i, np._sensDF.V[row]

    def setSampleRate(self, target = None):
        """
        Sets a specified sample rate for automatic acquisition.

        Parameters
        ----------
        target: None, str or int
            Target sample rate. If None, set highest rate that is meaninful with the current time constant.
            If str, try to parse it based on the translation table (see SR8x0M._srateDF).
            If int, set it directly (see translation table or instrument manual).

        Returns
        -------
        Achieved sample rate in Hz (float). Trigger mode corresponds to 0, while -1 indicates a failure.
        """
        if target is None:
            # Attempt to set automatically based on time constant
            _, t = self.getTau()
            maxfreq = 1/t
            candidates = self._srateDF.srate[self._srateDF.srate <= maxfreq]
            maxvalid = np.max(candidates)
            row = np.argwhere(self._srateDF.srate == maxvalid)[0,0]
            i = self._srateDF.i[row]
            self.device.write(f"SRAT {i}")
            return maxvalid

        if type(target) is str:
            res = np.argwhere(self._srateDF.sratestr == target)
            if res.shape[0] < 1:
                self.logger.error("Requested sample rate string is invalid.")
                return -1
            else:
                i = self._srateDF.i[res[0,0]]
                self.device.write(f"SRAT {i}")
                return self._srateDF.srate[res[0,0]]

        elif type(target) is int:
            if target in self._srateDF.i.values:
                self.device.write(f"SRAT {target}")
                return self._srateDF.srate[np.argwhere(self._srateDF.i == target)[0,0]]
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
            If str, try to parse it based on the translation table (see SR8x0M._srateDF).
            If int, set it directly (see translation table or instrument manual).

        Returns
        -------
        Achieved time constant (float). -1 indicates an error.
        """
        if type(target) is str:
            res = np.argwhere(self._tauDF.tstr == target)
            if res.shape[0] < 1:
                self.logger.error("Requested time constant string is invalid.")
                return -1
            else:
                i = self._tauDF.i[res[0,0]]
                self.device.write(f"OFLT {i}")
                return self._tauDF.t[res[0,0]]

        elif type(target) is int:
            if target in self._tauDF.i:
                self.device.write(f"OFLT {target}")
                return self._tauDF.t[np.argwhere(self._tauDF.i == target)[0,0]]
            else:
                self.logger.error("Requested time constant index is invalid.")
                return -1
        else:
            self.logger.error("Time constant input type is invalid.")
            return -1

    def _setTauS(self, target):
        """
        Sets the time constant in seconds.

        Parameters
        ----------
        target: float
            Target time constant in seconds.

        Returns
        -------
        achieved: float
            Achieved time constant.
            This value was set on the device.
        """
        row = np.argmin(np.abs(self._tauDF.t - target))
        i = self._tauDF.i[row]
        self.device.write(f"OFLT {i}")
        return self._tauDF.t[row]

    def getTau(self):
        """
        Query the device for the currently set time constant.

        Returns
        -------
        i: int
            Index of time constant setting.
        t: float
            Time constant in seconds.
        """
        resp = int(self.device.query("OFLT?"))
        i = np.argwhere(self._tauDF.i == resp)[0,0]
        t = self._tauDF.t[i]
        return resp, t

    def _getTauS(self):
        """
        Query the device for the currently set time constant.

        Returns
        -------
        i: int
            Index of time constant setting.
        t: float
            Time constant in seconds.
        """
        resp, t = self.getTau()
        return t

    #: float: Get or set the time constant in seconds
    tau = property(fget=_getTauS, fset=_setTauS)

    def setFreq(self, freq):
        """
        Set the internal oscillator frequency.

        Parameters
        ----------
        freq: float
            Target frequency.

        Returns
        -------
        success: bool
            True if successful.
        """
        # TODO: Consider harmonic detection for bounds checking.
        if freq >= 0.001 and freq <= 102000:
            self.device.write(f"FREQ {freq}")
            return True
        else:
            self.logger.error("Requested LO frequency is out of bounds.")
            return False

    def getFreq(self):
        """
        Get the internal oscillator frequency.

        Returns
        -------
        freq: float
            LO frequency.
        """
        return float(self.device.query("FREQ?"))

    #: float: Get or set the oscillator frequency in Hz
    freq = property(fget=getFreq, fset=setFreq)

    def _setPhase(self, phase):
        """
        Set the phase of the internal oscillator.

        Parameters
        ----------
        phase: float
            Oscillator phase in degrees.
        """
        p = phase % 360 # It's easier to just wrap it here
        self.device.write(f"PHAS {p}")

    def _getPhase(self):
        """
        Get the phase of the internal oscillator.

        Returns
        -------
        phase: float
            Oscillator phase in degrees.
        """
        return float(self.device.query("PHAS?"))

    #: float: Get or set the oscillator phase in degrees
    phase = property(fget=_getPhase, fset=_setPhase)

    def queryBinary(self, cmd):
        """
        Query a list of binary values from the device.

        Parameters
        ----------
        cmd: str
            Command to send to the device.

        Returns
        -------
        response: bytes
            A set of raw bytes returned by the instrument.
        """

        # Increse timeout, otherwise the transfer takes too long
        oldTimeout = self.device.timeout
        self.device.timeout = 10000 # 10 seconds

        self.device.write(cmd)
        response = self.device.read_raw()

        # Reset the timeout
        self.device.timeout = oldTimeout

        return response

    def queryASCIIFloat(self, cmd):
        """
        Query a list of float values from the device.
        Parse the response as ASCII floats.

        Parameters
        ----------
        cmd: str
            Command to send to the device.

        Returns
        -------
        response: list(float)
            A set of floating point values returned by the instrument.
        """

        # Increse timeout, otherwise the transfer takes too long
        oldTimeout = self.device.timeout
        self.device.timeout = 60000 # 1 minute

        resp = self.device.query(cmd)

        decoded = list(map(float, resp.strip(',').split(',')))

        # Reset the timeout
        self.device.timeout = oldTimeout

        return decoded

    def queryBinaryFloat(self, cmd):
        """
        Query a list of float values from the device.
        Parse the response as binary floats.

        Parameters
        ----------
        cmd: str
            Command to send to the device.

        Returns
        -------
        response: list(float)
            A set of floating point values returned by the instrument.
        """
        response = self.queryBinary(cmd)
        entries = len(response) // 4
        data = struct.unpack(f"{entries}f", response)
        return list(data)

    def resetBuffer(self):
        """
        Clear the automatic acquisition buffer
        """
        self.device.write("REST")

    def trigger(self):
        """
        Send a command equivalent to a hardware trigger
        """
        self.device.write("TRIG")

    def startBuffer(self):
        """
        Start automatic acquisition
        """
        self.device.write("STRT")

    def pauseBuffer(self):
        """
        Stop automatic acquisition
        """
        self.device.write("PAUS")

    def enableTrigger(self, state = True):
        """
        Enable back panel trigger for automatic acquisition

        Parameters
        ----------
        state: bool
            Whether or not back panel triggering is enabled.
        """
        if state:
            self.device.write("TSTR 1")
        else:
            self.device.write("TSTR 0")

    def _setGrounding(self, grounded = False):
        """
        Set grounded coupling

        Parameters
        ----------
        grounded: bool, default : False
            Whether or not the input's outer conductor is grounded.
            False means floating.
        """
        self.device.write(f'IGND {'1' if grounded else '0'}')

    def _getGrounding(self):
        """
        Get grounded coupling

        Returns
        -------
        grounded: bool
            Whether or not the input's outer conductor is grounded.
            False means floating.
        """
        resp = self.device.query('IGND?')
        return int(resp) == 1

    #: bool: Gets or sets grounded coupling. True is grounded, False is floating.
    grounding = property(fget=_getGrounding, fset=_setGrounding)

    def _setDC(self, DC = False):
        """
        Set DC coupling

        Parameters
        ----------
        DC: bool, default : False
            Whether the device is in DC coupling mode.
            True is DC, Flase is AC.
        """
        self.device.write(f'ICPL {'1' if DC else '0'}')

    def _getDC(self):
        """
        Get DC coupling

        Returns
        -------
        DC: bool, default : False
            Whether the device is in DC coupling mode.
            True is DC, Flase is AC.
        """
        resp = self.device.query('ICPL?')
        return int(resp) == 1

    #: bool: Gets or sets DC coupling. True is DC, False is AC.
    DC = property(fget=_getDC, fset=_setDC)

    def _setNotchFilter(self, setting = 0):
        """
        Set noth filter

        Parameters
        ----------
        setting: int, default : 0
            0 is neither, 1 is line, 2 is 2line, 3 is both
        """
        self.device.write(f'ILIN {setting}')

    def _getNotchFilter(self):
        """
        Set noth filter

        Returns
        -------
        setting: int
            0 is neither, 1 is line, 2 is 2line, 3 is both
        """
        resp = self.device.query('ILIN?')
        return int(resp)

    #: int: Gets or sets noth filter. 0 is neither, 1 is line, 2 is 2line, 3 is both.
    notchFilter = property(fget=_getNotchFilter, fset=_setNotchFilter)

    def _setSlope(self, slope = 0):
        self.device.write(f'OFSL {slope}')

    def _getSlope(self):
        resp = self.device.query('OFSL?')
        return int(resp)

    slope = property(fget=_getSlope, fset=_setSlope, doc="""
    int: Gets or sets the low pass filter slope. Possible values:

    ===== =========
    Value Slope
    ===== =========
    0     6 dB/oct
    1     12 dB/oct
    2     18 dB/oct
    3     24 dB/oct
    ===== =========
    """)

class SR830(SR8x0):
    """
    Driver class for SR830 and SR830M devices. Supports both GPIB and serial connections.
    For the latter, the device must be set to RS-323 mode at 19200 baud.
    """
    def __init__(self, rm, address):
        """
        Parameters
        ----------
        rm : pyvisa.ResourceManager
            Pass a pyvisa ResourceManager object to use for opening the device.
        address : str
            VISA address of the SR830 device.
        """

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

    #bufferSize = 16383 Not actually used anywhere

    _disp1Dict = {
        "X": 0,
        "R": 1,
        "XN": 2,
        "XNOISE": 2,
        "A1": 3,
        "AUX1": 3,
        "A2": 4,
        "AUX2": 4,
    }

    _disp2Dict = {
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

    _snapDict = {
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
    def _setSource(self, internal):
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

    def _getSource(self):
        """
        Query which frequency source is in use.

        Returns
        -------
        Bool: True for internal, False for external
        """

        resp = int(self.device.query("FMOD?"))

        return resp == 1

    #: bool: Gets or sets which frequency source is used. True is internal, False is external.
    source = property(fset=_setSource,fget=_getSource)

    def snapshot(self, *args):
        """
        Reads out at most 6 values simultaneously.

        Parameters
        ----------
        *args: str
            At most 6 str arguments, each representing a measured quantitiy.
            See SR830._snapDict for valid options. Notable examples include 'X', 'Y', 'R' and 'THETA'.

        Returns
        -------
        result: list(float)
            List of up to 6 values, corresponding to the passed arguments.
            None if a failure has occured.
        """
        params = list(args)

        if len(params) > 6:
            self.logger.error("At most 6 parameters may be read out at once.")
            return None
        elif len(params) < 1:
            self.logger.error("At least one parameter must be read out.")
            return None

        indices = []
        for p in params:
            P = p.upper()
            if P in self._snapDict:
                indices.append(str(self._snapDict[P]))
            else:
                available = ", ".join(self._snapDict.keys())
                self.logger.error(f"A requested value is invalid. Request: {P}. Available values: {available}")
                return None

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
    def _setInputMode(self, mode):
        """
        Sets the input mode of the device.

        Parameters
        ----------
        mode: int
            Possible values:

            ===== ==========================
            Value Description
            ===== ==========================
            0     A (voltage)
            1     A-B (differential voltage)
            2     I (1 MΩ)
            3     I (100 MΩ)
            ===== ==========================
        
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

    def _getInputMode(self):
        """
        Gets the input mode of the device.
        
        Returns
        -------
        mode: int
            Possible values:

            ===== ==========================
            Value Description
            ===== ==========================
            0     A (voltage)
            1     A-B (differential voltage)
            2     I (1 MΩ)
            3     I (100 MΩ)
            ===== ==========================
        """
        return int(self.device.query("ISRC?"))

    inputMode = property(fset=_setInputMode, fget=_getInputMode, doc = """
    int: Gets or sets the input mode of the device. Possible values:

    ===== ==========================
    Value Description
    ===== ==========================
    0     A (voltage)
    1     A-B (differential voltage)
    2     I (1 MΩ)
    3     I (100 MΩ)
    ===== ==========================
    """)

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
        success: bool
            True on success, False on failure.
        """
        
        if disp not in [1, 2]:
            self.logger.error("Please select display 1 or 2.")
            return False
        
        dispDict = self._disp1Dict if disp == 1 else self._disp2Dict
        
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

    def _getDisplay(self):
        #TODO: implement
        return None

    def getBinNum(self):
        """
        Read number of points stored in acquisition buffer.

        Returns
        -------
        num: int
            Number of elements in buffer.
        """
        res = self.device.query('SPTS?')
        return int(res)

    def readBuffer(self, buffer, start, length):
        """
        Read a buffer from the device.

        Parameters
        ----------
        i: int
            Buffer number. Must be one 1 or 2.
        start: int
            Starting index. Elements are indexed from 0.
        length: int
            Number of elements to read starting from index.

        Returns
        -------
        result: list(float)
            Buffer contents as a list of floats.
        """
        bufferSize = self.getBinNum()

        if bufferSize == 0:
            #logging.warning("The lock-in buffer is empty, nothing could be retrieved.")
            return None

        if start <= 0:
            start = bufferSize - start

        if (start >= bufferSize) or (start < 0):
            self.logger.error(f"Starting index is out of bounds (requested index {start} from {bufferSize} elements)")
            return None

        if (start + start) > bufferSize:
            self.logger.info("Requested too many points, clamping it.")
            start = bufferSize - start

        if self.serial:
            queryStr = f"TRCA ? {buffer}, {start}, {start}"
            return self.queryASCIIFloat(queryStr)
        else:
            queryStr = f"TRCB ? {buffer}, {start}, {length}"
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
        ch1: list(float)
            List of floats containing the data from channel 1.
            None if acquisition is disabled for this channel.
        ch2: list(float)
            List of floats containing the data from channel 2.
            None if acquisition is disabled for this channel.
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
            srate = self._setSamplerateHz(srate)
            
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
                if self.getBinNum() >= n:
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

    def _setReserve(self, reserve = 1):
        """
        Set reserve mode.

        Parameters
        ----------
        reserve: int, default: 1
            Reserve mode. 0 is high reserve, 1 is normal and 2 is low noise.
        """
        self.device.write(f'RMOD {reserve}')

    def _getReserve(self):
        """
        Get reserve mode.

        Returns
        -------
        reserve: int
            Reserve mode. 0 is high reserve, 1 is normal and 2 is low noise.
        """
        resp = self.device.query('RMOD?')
        return int(resp)

    #: int: Gets or sets reserve mode. 0 is high reserve, 1 is normal and 2 is low noise.
    reserve = property(fget=_getReserve, fset=_setReserve)

class SR850(SR8x0):
    def __init__(self, rm, address):
        """
        Parameters
        ----------
        rm : pyvisa.ResourceManager
            Pass a pyvisa ResourceManager object to use for opening the device.
        address : str
            VISA address of the SR850 device.
        """
        # Set up logger
        self.logger = logging.getLogger('instrumpy.SR850')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        self.device = rm.open_resource(address)
        self.device.write_termination = '\n'
        self.device.read_termination = '\n'

        self.device.write('OUTX 1')

        self._setDate()

        #self.device.timeout = 100000

    _snapDict = {
            "X": 1,
            "Y": 2,
            "R": 3,
            "THETA": 4,
            "Θ": 4,
            "REF": 5,
            "F": 5,
            "FREQ": 5,
    }

    _traceDict = {
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

    def _setDate(self):
        """
        Sets the lock-in's clock to follow the controlling computer's.
        """
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
        If syncronization is required, use multiRead.

        Parameters
        ----------
        *args: str
            Multiple str arguments, each representing a measured quantitiy.
            See SR850._snapDict for valid options. Notable examples include 'X', 'Y', 'R', 'THETA' and 'REF'.

        Returns
        -------
        result: list(float)
            List of floats, corresponding to the passed arguments.
            None if a failure has occured.
        """

        indices = []
        for p in params:
            P = p.upper()
            if P in self._snapDict:
                indices.append(self._snapDict[P])
            else:
                available = ", ".join(self._snapDict.keys())
                self.logger.error(f"A requested value is invalid. Request: {P}. Available values: {available}")
                return None

        resp = []
        for i in indices:
            if i == 5:
                resp.append(self.getFreq())
            else:
                cmd = f"OUTP? {i}"
                resp.append(float(self.device.query(cmd)))

        return resp

    def getTraceLength(self, i):
        """
        Get the length of a trace.

        Parameters
        ----------
        i: int,
            Trace number. Must be in 1-4.

        Returns
        -------
        num: int
            Number of values in the selected trace
        """

        cmd = f"SPTS? {i}"
        return int(self.device.query(cmd))

    def _setInputMode(self, mode):
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

    def _getInputMode(self):
        """
        Sets the input mode of the device.

        Returns
        -------
        mode: int
            Possible values: 0 - A (voltage)
                             1 - A-B (differential voltage)
                             2 - I (1 MΩ)
                             3 - I (100 MΩ)
        """
        isrc = int(self.device.query("ISRC?"))
        if isrc == 3:
            igan = int(self.device.query("IGAN?"))
            return isrc + igan
        else:
            return igan

    inputMode = property(fset=_setInputMode, fget=_getInputMode, doc = """
    int: Gets or sets the input mode of the device. Possible values:

    ===== ==========================
    Value Description
    ===== ==========================
    0     A (voltage)
    1     A-B (differential voltage)
    2     I (1 MΩ)
    3     I (100 MΩ)
    ===== ==========================
    """)

    def setTraceSource(self, i, target, multiply = 0, divide = 0, store = True):
        """
        Sets the trace source.

        Parameters
        ----------
        i: int
            Trace number. Must be in 1-4.
        target: int or str
            Value to be measured. If str, it will be decoded to the device's option index using SR850._traceDict.
            Notable examples include 'X', 'Y', 'R' and 'THETA'.
        multiply: int or str, default: 0
            Value to divide the target with. Works the same as target.
            The default value of 0 corresponds to unity ('1'), so no multiplication will be performed.
        divide: int or str, default: 0
            Value to divide the target with. Works the same as target.
            The default value of 0 corresponds to unity ('1'), so no division will be performed.
        """

        # TODO: Implement different dictionaries for multiply and divide values.
        if type(target) is int:
            j = target
        else:
            j = self._traceDict.get(target.upper(), None)
            if j is None:
                available = ", ".join(self._traceDict.keys())
                self.logger.error(f"The requested target is invalid. Request: {P}. Available values: {available}")
                return False

        if type(multiply) is int:
            k = multiply
        else:
            k = self._traceDict.get(target.upper(), None)
            if k is None:
                available = ", ".join(self._traceDict.keys())
                self.logger.error(f"The requested multiplier is invalid. Request: {P}. Available values: {available}")
                return False

        if type(divide) is int:
            l = divide
        else:
            l = self._traceDict.get(target.upper(), None)
            if l is None:
                available = ", ".join(self._traceDict.keys())
                self.logger.error(f"The requested divider is invalid. Request: {P}. Available values: {available}")
                return False

        self.device.write(f'TRCD {i},{j},{k},{l},{'1' if store else '0'}')

    def getTraceSource(self, i):
        """
        Get trace definition.

        Parameters
        ----------
        i: int
            Trace number. Must be in 1-4.

        Returns
        -------
        source: list(int):
            A list of 3 int values representing the source values.
            See SR850._traceDict for a conversion table.
        """
        resp = self.device.query(f'TRCD? {i}')
        return [int(x) for x in resp.split(',')]

    def startTrace(self):
        """
        Start a trace.
        Alias of startBuffer.
        """
        self.device.write('STRT')

    def pauseTrace(self):
        """
        Pause a trace.
        Alias of pauseBuffer.
        """
        self.device.write('PAUS')

    def resetTrace(self):
        """
        Reset a trace.
        Alias of resetBuffer.
        """
        self.device.write('REST')

    def readTrace(self, i, start, length):
        """
        Read a trace from the device.

        Parameters
        ----------
        i: int
            Trace number. Must be one of 1, 2, 3 or 4.
        start: int
            Starting index. Elements are indexed from 0
        length: int
            Number of elements to read starting from index.

        Returns
        -------
        result: list(float)
            Resulting trace as a list of floats.
        """
        self.pauseTrace()
        length = np.minimum(length, self.getTraceLength(i) - start)
        if length <= 0:
            self.logger.error(f'Start of readout ({start}) must be less than the number of points in the trace ({self.getTraceLength(i)})')
        return self.queryBinaryFloat(f'TRCB? {i},{start},{length}')

    def multiRead(self, tr1 = None, tr2 = None, tr3 = None, tr4 = None, t = 1.0, srate = None, wait = False):
        """
        Record a trace on up to 4 channels at a time.

        Parameters
        ----------
        tr1: str, optional
            Trace definition. If None, do not record anything on trace 1.
            For valid options, see the keys of SR850._traceDict. Notable examples include 'X', 'Y', 'R' and 'THETA'.
        tr2: str, optional
            Trace definition. Same as tr1, but for channel 2.
        tr3: str, optional
            Trace definition. Same as tr1, but for channel 3.
        tr4: str, optional
            Trace definition. Same as tr1, but for channel 4.
        t: float, default: 1.0
            Total acquisition time in seconds.
        srate: float, optional
            Acquisition sample rate.
            If none, the highest meaningful sample rate will be used for the given time constant.
            If the given value is too fast for the time constant, it will be clamped.
        wait: bool, default: False
            Whether to account for communication overhead when calculating wait time.
            When False, a few samples might be missing, especially at high sampling rates.

        Returns
        -------
        results: list(list(float))
            A list of results. The list contains 4 elements, corresponding to traces 1-4.and
            Each element is itself a list of floats, containing the trace data.
            If a given trace is disabled, its value will be None.
        """
        data = [None, None, None, None]

        readTraces = [tr is not None for tr in [tr1, tr2, tr3, tr4]]

        if not np.any(readTraces):
            self.logger.error("At least one trace must be configured for acquistion.")
            return data

        if srate is None:
            srate = self.setSampleRate(None)
        else:
            srate = self._setSamplerateHz(srate)

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
    def _setSource(self, source):
        """
        Set local oscillator source.

        Parameters
        ----------
        source: int
            0 is internal, 1 is internal sweep and 2 is external
        """

        self.device.write(f"FMOD {i}")

    def _getSource(self):
        """
        Query which frequency source is in use.

        Returns
        -------
        int: 0 is internal, 1 is internal sweep and 2 is external
        """

        return int(self.device.query("FMOD?"))

    #: int: Gets or sets the reference frequency source. 0 is internal, 1 is internal sweep and 2 is external.
    source = property(fget=_getSource,fset=_setSource)

    def _setReserve(self, reserve = 3):
        """
        Set reserve mode.

        Parameters
        ----------
        reserve: int, default: 3
            Reserve mode between 0 and 5 inclusive. 0 is minimum reserve, 5 is maximum.
        """
        # int between 0 and 5 inclusive, 0 is minimum reserve, 5 is maximum
        self.device.write('RMOD 1') # set manual reserve
        self.device.write(f'RSRV {reserve}')

    def _getReserve(self):
        """
        Get reserve mode.

        Returns
        -------
        reserve: int
            Reserve mode between 0 and 5 inclusive. 0 is minimum reserve, 5 is maximum.
        """
        resp = self.device.query('RSRV?')
        return int(resp)

    #: int: Gets or sets reserve mode. 0 is minimum reserve, 5 is maximum.
    reserve = property(fget=_getReserve, fset=_setReserve)
