import struct
import matplotlib.pyplot as plt
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

@dataclass
class TelemetryPacket:
    time_ms: int
    temp_cC: int
    pressPa: int
    mag_x: int
    mag_y: int
    mag_z: int
    accel_x: int
    accel_y: int
    accel_z: int
    gyro_x: int
    gyro_y: int
    gyro_z: int
    altitude_cm: int
    lat_1e7: int
    lon_1e7: int
    flags: int

def parse_telemetry_packet(data: bytes) -> TelemetryPacket:
    if len(data) != 36:
        raise ValueError(f"Expected 36 bytes, got {len(data)}")
    
    time_ms = int.from_bytes(data[0:3], 'little')
    
    temp_press = int.from_bytes(data[3:5], 'little')
    temp_cC = temp_press & 0x3FFF
    if temp_cC >= 0x2000:
        temp_cC -= 0x4000
    
    press_p1 = (temp_press >> 14) & 0x03
    press_p2 = int.from_bytes(data[5:7], 'little')
    pressPa = (press_p2 << 2) | press_p1
    
    mag_x, mag_y, mag_z = struct.unpack('<3h', data[7:13])
    accel_x, accel_y, accel_z = struct.unpack('<3h', data[13:19])
    gyro_x, gyro_y, gyro_z = struct.unpack('<3h', data[19:25])
    
    alt_lat1 = int.from_bytes(data[25:29], 'little')
    altitude_cm = alt_lat1 & 0xFFFFF
    if altitude_cm >= 0x80000:
        altitude_cm -= 0x100000
    
    lat_lon1 = int.from_bytes(data[28:32], 'little')
    lat_1e7 = ((lat_lon1 & 0x3FFFFFF) << 4) | (alt_lat1 >> 20)
    if lat_1e7 >= 0x20000000:
        lat_1e7 -= 0x40000000
    
    lon_flags = int.from_bytes(data[32:36], 'little')
    lon_1e7 = (lon_flags >> 8) | ((lat_lon1 >> 26) << 24)
    if lon_1e7 >= 0x20000000:
        lon_1e7 -= 0x40000000
    
    flags = lon_flags & 0xFF
    
    return TelemetryPacket(
        time_ms, temp_cC, pressPa,
        mag_x, mag_y, mag_z,
        accel_x, accel_y, accel_z,
        gyro_x, gyro_y, gyro_z,
        altitude_cm, lat_1e7, lon_1e7, flags
    )

def clean_hex_string(raw_hex: str) -> str:
    return ''.join(c for c in raw_hex if c.lower() in '0123456789abcdef')

def process_hex_file(input_file: str, output_csv: str):
    try:
        with open(input_file, 'r') as f:
            raw_data = f.read()
        
        clean_hex = clean_hex_string(raw_data)
        total_len = len(clean_hex)
        packet_count = total_len // 72
        
        if total_len % 72 != 0:
            print(f"Warning: Truncated {total_len % 72} hex characters")
            clean_hex = clean_hex[:packet_count * 72]
        
        print(f"Processing {packet_count} packets...")
        
        packets = []
        for i in range(packet_count):
            packet_hex = clean_hex[i*72:(i+1)*72]
            try:
                data = bytes.fromhex(packet_hex)
                packets.append(parse_telemetry_packet(data))
            except Exception as e:
                print(f"Error in packet {i+1}: {e}")
        
        # Create DataFrame
        df = pd.DataFrame([vars(p) for p in packets])
        
        # Convert time to seconds
        df['time_s'] = df['time_ms'] / 1000
        
        # Save to CSV
        df.to_csv(output_csv, index=False)
        print(f"Data saved to {output_csv}")
        
        return df
    
    except Exception as e:
        print(f"Error: {e}")
        return None

def plot_telemetry_data(df, output_dir="plots"):
    Path(output_dir).mkdir(exist_ok=True)
    
    # Prepare data
    df['temp_C'] = df['temp_cC'] / 100
    df['pressure'] = 60000 + df['pressPa']
    df['altitude_m'] = df['altitude_cm'] / 100
    df['gyro_x_dps'] = df['gyro_x'] / 10
    df['gyro_y_dps'] = df['gyro_y'] / 10
    df['gyro_z_dps'] = df['gyro_z'] / 10
    
    # Create plots
    plt.figure(figsize=(12, 6))
    
    # Temperature plot
    plt.subplot(2, 3, 1)
    plt.plot(df['time_s'], df['temp_C'])
    plt.title('Temperature (°C)')
    plt.xlabel('Time (s)')
    plt.grid(True)
    
    # Pressure plot
    plt.subplot(2, 3, 2)
    plt.plot(df['time_s'], df['pressure'])
    plt.title('Pressure (Pa)')
    plt.xlabel('Time (s)')
    plt.grid(True)
    
    # Altitude plot
    plt.subplot(2, 3, 3)
    plt.plot(df['time_s'], df['altitude_m'])
    plt.title('Altitude (m)')
    plt.xlabel('Time (s)')
    plt.grid(True)
    
    # Magnetometer plot
    plt.subplot(2, 3, 4)
    plt.plot(df['time_s'], df['mag_x'], label='X')
    plt.plot(df['time_s'], df['mag_y'], label='Y')
    plt.plot(df['time_s'], df['mag_z'], label='Z')
    plt.title('Magnetometer (mG)')
    plt.xlabel('Time (s)')
    plt.legend()
    plt.grid(True)
    
    # Accelerometer plot
    plt.subplot(2, 3, 5)
    plt.plot(df['time_s'], df['accel_x'], label='X')
    plt.plot(df['time_s'], df['accel_y'], label='Y')
    plt.plot(df['time_s'], df['accel_z'], label='Z')
    plt.title('Accelerometer (mG)')
    plt.xlabel('Time (s)')
    plt.legend()
    plt.grid(True)
    
    # Gyroscope plot
    plt.subplot(2, 3, 6)
    plt.plot(df['time_s'], df['gyro_x_dps'], label='X')
    plt.plot(df['time_s'], df['gyro_y_dps'], label='Y')
    plt.plot(df['time_s'], df['gyro_z_dps'], label='Z')
    plt.title('Gyroscope (dps)')
    plt.xlabel('Time (s)')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plot_path = f"{output_dir}/telemetry_summary.png"
    plt.savefig(plot_path)
    print(f"Summary plot saved to {plot_path}")
    plt.close()
    
    # Additional individual plots
    plot_individual_graphs(df, output_dir)

def plot_individual_graphs(df, output_dir):
    # Temperature
    plt.figure()
    plt.plot(df['time_s'], df['temp_cC']/100)
    plt.title('Temperature vs Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Temperature (°C)')
    plt.grid(True)
    plt.savefig(f"{output_dir}/temperature.png")
    plt.close()
    
    # Pressure
    plt.figure()
    plt.plot(df['time_s'], 60000 + df['pressPa'])
    plt.title('Pressure vs Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Pressure (Pa)')
    plt.grid(True)
    plt.savefig(f"{output_dir}/pressure.png")
    plt.close()
    
    # Altitude
    plt.figure()
    plt.plot(df['time_s'], df['altitude_cm']/100)
    plt.title('Altitude vs Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Altitude (m)')
    plt.grid(True)
    plt.savefig(f"{output_dir}/altitude.png")
    plt.close()
    
    # Magnetometer
    plt.figure(figsize=(10, 6))
    for axis in ['x', 'y', 'z']:
        plt.plot(df['time_s'], df[f'mag_{axis}'], label=f'Axis {axis.upper()}')
    plt.title('Magnetometer Readings vs Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Magnetic Field (mG)')
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{output_dir}/magnetometer.png")
    plt.close()
    
    # Accelerometer
    plt.figure(figsize=(10, 6))
    for axis in ['x', 'y', 'z']:
        plt.plot(df['time_s'], df[f'accel_{axis}'], label=f'Axis {axis.upper()}')
    plt.title('Accelerometer Readings vs Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Acceleration (mG)')
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{output_dir}/accelerometer.png")
    plt.close()
    
    # Gyroscope
    plt.figure(figsize=(10, 6))
    for axis in ['x', 'y', 'z']:
        plt.plot(df['time_s'], df[f'gyro_{axis}']/10, label=f'Axis {axis.upper()}')
    plt.title('Gyroscope Readings vs Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Rotation Rate (dps)')
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{output_dir}/gyroscope.png")
    plt.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python telemetry_parser.py <input_file> <output_csv>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_csv = sys.argv[2]
    
    df = process_hex_file(input_file, output_csv)
    if df is not None:
        plot_telemetry_data(df)