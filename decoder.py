import struct
from dataclasses import dataclass
from typing import Tuple
from pathlib import Path

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
    
    # Unpack all fields
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
        time_ms=time_ms,
        temp_cC=temp_cC,
        pressPa=pressPa,
        mag_x=mag_x, mag_y=mag_y, mag_z=mag_z,
        accel_x=accel_x, accel_y=accel_y, accel_z=accel_z,
        gyro_x=gyro_x, gyro_y=gyro_y, gyro_z=gyro_z,
        altitude_cm=altitude_cm,
        lat_1e7=lat_1e7,
        lon_1e7=lon_1e7,
        flags=flags
    )

def clean_hex_string(raw_hex: str) -> str:
    return ''.join(c for c in raw_hex if c.lower() in '0123456789abcdef')

def process_hex_file(input_file: str, output_file: str):
    try:
        with open(input_file, 'r') as f:
            raw_data = f.read()
        
        clean_hex = clean_hex_string(raw_data)
        total_len = len(clean_hex)
        packet_count = total_len // 72
        
        if total_len % 72 != 0:
            print(f"Warning: Truncated {total_len % 72} hex characters at the end")
            clean_hex = clean_hex[:packet_count * 72]
        
        print(f"Processing {packet_count} packets from {input_file}...")
        
        with open(output_file, 'w') as out_f:
            # Write header
            out_f.write("time_ms;temp_cC;pressPa;")
            out_f.write("mag_x;mag_y;mag_z;")
            out_f.write("accel_x;accel_y;accel_z;")
            out_f.write("gyro_x;gyro_y;gyro_z;")
            out_f.write("altitude_cm;lat_1e7;lon_1e7;flags\n")
            
            for i in range(packet_count):
                start = i * 72
                packet_hex = clean_hex[start:start+72]
                
                try:
                    data = bytes.fromhex(packet_hex)
                    packet = parse_telemetry_packet(data)
                    
                    # Write data line
                    out_f.write(f"{packet.time_ms};{packet.temp_cC};{packet.pressPa};")
                    out_f.write(f"{packet.mag_x};{packet.mag_y};{packet.mag_z};")
                    out_f.write(f"{packet.accel_x};{packet.accel_y};{packet.accel_z};")
                    out_f.write(f"{packet.gyro_x};{packet.gyro_y};{packet.gyro_z};")
                    out_f.write(f"{packet.altitude_cm};{packet.lat_1e7};{packet.lon_1e7};{packet.flags}\n")
                    
                    if (i+1) % 100 == 0:
                        print(f"Processed {i+1} packets...")
                
                except Exception as e:
                    print(f"Error in packet {i+1}: {e}")
        
        print(f"Successfully processed {packet_count} packets. Results saved to {output_file}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python telemetry_parser.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    process_hex_file(input_file, output_file)