# instrumpy

Collection of python scripts for interfacing with scientific instrumentation. Intended for use with IPython.

Supported devices:
 - SR830(M) lock-in amplifier
 - HP83752A (and similar) analog microwave sweeper
 - Kuhne MKU LO 8-13 PLL micorwave oscillator
 - [pico-pulse](https://github.com/bgoblyos/pico-pulse) sequence synthesizer
 - Phase Matrix 25B frequency counter

Preprogrammed experiments:
 - Optically detected magnetic resonance (ODMR):
   - Continous wave frequency sweep
   - T<sub>1</sub> relaxation measurement
   - Rabi oscillation measurement
   - Ramsey experiment
