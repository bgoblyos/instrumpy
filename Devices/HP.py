class HP83752A():
    def __init__(self, rm, address):
        self.device = rm.open_resource(address)
        self.freqRange = (0.01,20)
        self.powerRange = (-80,20)
        self.timeRange = (0,100)

    def setupSweep(self, min, max, time):
        self.device.write("FREQ:MODE SWE")
        self.device.write(f"FREQ:STAR {min} GHZ")
        self.device.write(f"FREQ:STOP {max} GHZ")
        self.device.write(f"SWE:TIME {time} s")

    def readSweepParams(self):
        start = float(self.device.query("FREQ:STAR?"))/1e9
        end = float(self.device.query("FREQ:STOP?"))/1e9
        time = float(self.device.query("SWE:TIME?"))
        return (start, end, time)

    def readSweepTime(self):
        return float(self.device.query("SWE:TIME?"))

    def resetMarkers(self):
        self.device.write("MARK:AOFF")
    
    def setMarker(self, markNum, freq):
        self.device.write(f"MARK{markNum}:STATE ON; FREQ {freq} GHz")

    def setPowerLevel(self, level):
        self.device.write(f"POWER:LEV {level} DBM")

    def readPowerLevel(self):
        return float(self.device.query("POWER:LEV?"))

    def powerOn(self):
        self.device.write("POW:STATE ON")

    def powerOff(self):
        self.device.write("POW:STATE OFF")

    def setContSweep(self, cont):
        if cont:
            self.device.write("INIT:CONT ON")
        else:
            self.device.write("INIT:CONT OFF")

    def startSweep(self):
        self.device.write("INIT:IMM;*TRG")

    def stopSweep(self):
        self.device.write("ABORT")
        
    def getCW(self):
        resp = self.device.query("FREQ:CW?")
        return float(resp)
    
    def setCW(self, freq_GHz):
        resp = self.device.write(f"FREQ:CW {freq_GHz} GHz")
        return float(resp)

    model = "HP83752A"

# TODO: implement the other models we have as well with inheritance
