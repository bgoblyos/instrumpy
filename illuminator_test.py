import pyvisa
import time

# Initialize resource manager
rm = pyvisa.ResourceManager()

# Open the GPIB connection (replace '4' with your dip-switch address)
instrument_address = 'GPIB0::4::INSTR'
luminator = rm.open_resource(instrument_address)

# Configure Oriel termination criteria
luminator.read_termination = '\r\n'
luminator.write_termination = '\r\n'

# Verify connection
print("Device ID:", luminator.query("*IDN?"))

# Move to a specified wavelength
target_wavelength = 600
print(f"Moving to {target_wavelength} nm...")
luminator.write(f"GOWAVE {target_wavelength}")

# Wait for travel time
time.sleep(2)

# Confirm final position
current_wave = luminator.query("WAVE?")
print(f"Current Wavelength: {current_wave} nm")

# Clean up
luminator.close()
