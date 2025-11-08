"""
CosmicWatch Data Import with Elasticsearch Support

This script reads data from CosmicWatch Desktop Muon Detector v3X and optionally
uploads it directly to Elasticsearch, mapping the column data directly to fields.

Required libraries:
    pip install pyserial elasticsearch

Environment Variables (required when ES_ENABLED=true):
    ES_HOST      - Elasticsearch host URL (default: https://localhost:9200)
    ES_USER      - Elasticsearch username (default: elastic)
    ES_PASS      - Elasticsearch password (REQUIRED when ES_ENABLED=true)
    ES_INDEX     - Elasticsearch index name (default: credo-detections)
    ES_ENABLED   - Set to 'true' to enable Elasticsearch upload (default: false)

Usage:
    # Local file only (no Elasticsearch)
    python3 import_data_to_elasticsearch.py

    # With Elasticsearch upload
    export ES_HOST="https://localhost:9200"
    export ES_USER="elastic"
    export ES_PASS="your-password"
    export ES_ENABLED="true"
    python3 import_data_to_elasticsearch.py

Security:
    - No credentials are hardcoded in this script
    - All sensitive information must be provided via environment variables
    - Safe for public GitHub repositories
"""

from __future__ import print_function
import serial 
import time
import glob
import sys
import os
import os.path
import signal
from datetime import datetime
import platform

# Elasticsearch imports
try:
    from elasticsearch import Elasticsearch
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False
    print("Warning: elasticsearch library not installed. Install with: pip install elasticsearch")

print('Operating System: ',platform.system())

# Elasticsearch configuration
# All credentials must be provided via environment variables for security
ES_HOST = os.getenv('ES_HOST', 'https://localhost:9200')
ES_USER = os.getenv('ES_USER', 'elastic')
ES_PASS = os.getenv('ES_PASS')  # Must be provided via environment variable
ES_INDEX = os.getenv('ES_INDEX', 'credo-detections')
ES_ENABLED = os.getenv('ES_ENABLED', 'false').lower() == 'true'

# Check if password is provided when Elasticsearch is enabled
if ES_ENABLED and not ES_PASS:
    print("Error: ES_PASS environment variable is required when ES_ENABLED=true")
    print("Please set ES_PASS before running this script:")
    print("  export ES_PASS='your-elasticsearch-password'")
    sys.exit(1)

# Initialize Elasticsearch client
es = None
if ES_AVAILABLE and ES_ENABLED:
    try:
        es = Elasticsearch([ES_HOST], 
                          basic_auth=(ES_USER, ES_PASS),
                          verify_certs=False, 
                          ssl_show_warn=False, 
                          sniff_on_start=False)
        # Test connection
        es.info()
        print(f'✓ Connected to Elasticsearch at {ES_HOST}')
    except Exception as e:
        print(f'✗ Failed to connect to Elasticsearch: {e}')
        print('   Continuing without Elasticsearch...')
        es = None
elif ES_ENABLED and not ES_AVAILABLE:
    print('✗ Elasticsearch library not available. Install with: pip install elasticsearch')
    print('   Continuing without Elasticsearch...')
    es = None

def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    for i in range(nDetectors):
        try:
            globals()['Det%s' % str(i)].close()
        except:
            pass
    if 'file' in globals():
        file.close() 
    sys.exit(0)

def serial_ports():
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')
        sys.exit(0)
    result = []
    for port in ports:
        try: 
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

def convert_to_elasticsearch_format(data, detector_id='cosmicwatch-001'):
    """Convert CosmicWatch data directly to Elasticsearch"""
    try:
        # Map CosmicWatch columns directly to Elasticsearch fields
        # Column format: Event, Timestamp[s], Flag, ADC[12b], SiPM[mV], Deadtime[s], 
        #                Temp[C], Press[Pa], Accel(X:Y:Z)[g], Gyro(X:Y:Z)[deg/sec], Name, Time, Date
        
        event_num = int(data[0])
        pico_timestamp_s = float(data[1])
        flag = int(data[2])  # Coincidence flag (0 or 1)
        adc_value = int(data[3])
        sipm_mv = float(data[4])
        deadtime_s = float(data[5])
        temp_c = float(data[6]) if len(data) > 6 and data[6] else None
        pressure_pa = float(data[7]) if len(data) > 7 and data[7] else None
        
        # Parse accelerometer data (format: X:Y:Z)
        accel_str = data[8] if len(data) > 8 else None
        accel_x = None
        accel_y = None
        accel_z = None
        if accel_str:
            try:
                accel_parts = accel_str.split(':')
                if len(accel_parts) == 3:
                    accel_x = float(accel_parts[0])
                    accel_y = float(accel_parts[1])
                    accel_z = float(accel_parts[2])
            except:
                pass
        
        # Parse gyroscope data (format: X:Y:Z)
        gyro_str = data[9] if len(data) > 9 else None
        gyro_x = None
        gyro_y = None
        gyro_z = None
        if gyro_str:
            try:
                gyro_parts = gyro_str.split(':')
                if len(gyro_parts) == 3:
                    gyro_x = float(gyro_parts[0])
                    gyro_y = float(gyro_parts[1])
                    gyro_z = float(gyro_parts[2])
            except:
                pass
        
        # Parse detector name, computer time, and date
        detector_name = data[10] if len(data) > 10 else None
        comp_time_str = data[11] if len(data) > 11 else None
        comp_date_str = data[12] if len(data) > 12 else None
        
        # Convert computer time to timestamp in milliseconds
        # Prioritize current system time to ensure data appears in recent Kibana filters
        timestamp_ms = int(time.time() * 1000)  # Use current system time
        
        # Optionally parse detector computer time for reference (but don't use for timestamp)
        if comp_date_str and comp_time_str:
            try:
                date_parts = comp_date_str.split('/')
                time_parts = comp_time_str.split(':')
                if len(date_parts) == 3 and len(time_parts) >= 2:
                    dt = datetime(
                        int(date_parts[2]), int(date_parts[1]), int(date_parts[0]),
                        int(time_parts[0]), int(time_parts[1]), int(float(time_parts[2]))
                    )
                    detector_timestamp_ms = int(dt.timestamp() * 1000)
                    # Only use detector time if it's recent (within last hour)
                    current_time_ms = int(time.time() * 1000)
                    if abs(current_time_ms - detector_timestamp_ms) < 3600000:  # Within 1 hour
                        timestamp_ms = detector_timestamp_ms
            except:
                pass
        
        # Create document with direct column mapping
        doc = {
            'event': event_num,
            'pico_timestamp_s': pico_timestamp_s,
            'coincidence_flag': flag,
            'coincident': bool(flag == 1),
            'adc_value': adc_value,
            'sipm_mv': sipm_mv,
            'deadtime_s': deadtime_s,
            'temperature_c': temp_c,
            'pressure_pa': pressure_pa,
            'device_id': detector_id,
            'detector_name': detector_name,
            'timestamp_ms': timestamp_ms,
            'timestamp': timestamp_ms,  # Also add as 'timestamp' for date type compatibility
            'comp_time': comp_time_str,
            'comp_date': comp_date_str,
            # Acceleration fields
            'accel_x_g': accel_x,
            'accel_y_g': accel_y,
            'accel_z_g': accel_z,
            # Gyroscope fields
            'gyro_x_degs': gyro_x,
            'gyro_y_degs': gyro_y,
            'gyro_z_degs': gyro_z,
            # Metadata
            'source': 'cosmicwatch-v3x',
        }
        
        # Remove None values to keep document clean
        doc = {k: v for k, v in doc.items() if v is not None}
        
        return doc
    except Exception as e:
        print(f"Error converting data: {e}")
        import traceback
        traceback.print_exc()
        return None

def send_to_elasticsearch(doc):
    """Send document to Elasticsearch"""
    if es is None:
        return False
    try:
        # Use document parameter for newer elasticsearch-py versions
        # Falls back to body parameter for older versions
        try:
            result = es.index(index=ES_INDEX, document=doc)
        except TypeError:
            # Fallback for older elasticsearch-py versions
            result = es.index(index=ES_INDEX, body=doc)
        return True
    except Exception as e:
        print(f"Error sending to Elasticsearch: {e}")
        return False

t1 = time.time()
port_list = serial_ports()
if (time.time()-t1)>2:
    print('Listing ports is taking unusually long...')

print('\nWhich ports do you want to read from?')
for i in range(len(port_list)):
    print('  ['+str(i+1)+'] ' + str(port_list[i]))

if sys.version_info[:3] > (3,0):
    ArduinoPort = input("Select port: ")
    ArduinoPort = ArduinoPort.split(',')
elif sys.version_info[:3] > (2,5,2):
    ArduinoPort = raw_input("Select port(s): ")
    ArduinoPort = ArduinoPort.split(',')

nDetectors = len(ArduinoPort)

port_name_list = []
for i in range(len(ArduinoPort)):
    port_name_list.append(str(port_list[int(ArduinoPort[i])-1]))

# Ask for detector ID
cwd = os.getcwd()
print('')
default_detector_id = "cosmicwatch-001"
if sys.version_info[:3] > (3,0):
    detector_id = input(f"Enter detector ID (press Enter for default: {default_detector_id}):")
elif sys.version_info[:3] > (2,5,2):
    detector_id = raw_input(f"Enter detector ID (press Enter for default: {default_detector_id}):")
if detector_id == '':
    detector_id = default_detector_id

# Ask if saving to file too
save_to_file = True
if sys.version_info[:3] > (3,0):
    save_file_choice = input("Save to file too? (y/n, default: y): ")
elif sys.version_info[:3] > (2,5,2):
    save_file_choice = raw_input("Save to file too? (y/n, default: y): ")
if save_file_choice.lower() == 'n':
    save_to_file = False

# Ask for file name if saving to file
fname = None
if save_to_file:
    default_fname = cwd+"/CW_data.txt"
    if sys.version_info[:3] > (3,0):
        fname = input("Enter file name (press Enter for default: "+default_fname+"):")
    elif sys.version_info[:3] > (2,5,2):
        fname = raw_input("Enter file name (press Enter for default: "+default_fname+"):")
    if fname == '':
        fname = default_fname
    elif '/' not in fname and '\\' not in fname:
        fname = os.path.join(cwd, fname)
    print(' -- Saving data to: '+fname)

print()
for i in range(nDetectors):
    time.sleep(0.1)
    port = port_name_list[i]
    baudrate = 115200
    globals()['Det%s' % str(i)] = serial.Serial(port,baudrate)
    time.sleep(0.1)

if save_to_file:
    file = open(fname, "w")
    file.write("###########################################################################################################################################################\n")
    file.write("#                                                          CosmicWatch: The Desktop Muon Detector v3X\n")
    file.write("#                                                                   Questions? saxani@udel.edu\n")
    file.write("# Event  Timestamp[s]  Flag  ADC[12b]  SiPM[mV]  Deadtime[s]  Temp[C]  Press[Pa]  Accel(X:Y:Z)[g]  Gyro(X:Y:Z)[deg/sec]  Name  Time  Date\n")
    file.write("###########################################################################################################################################################\n")

# Create Elasticsearch index if needed
if es is not None:
    try:
        es.indices.create(index=ES_INDEX, body={
            "settings": {"index": {"number_of_shards": 12, "number_of_replicas": 0}},
            "mappings": {
                "properties": {
                    "event": {"type": "long"},
                    "pico_timestamp_s": {"type": "float"},
                    "coincidence_flag": {"type": "integer"},
                    "coincident": {"type": "boolean"},
                    "adc_value": {"type": "integer"},
                    "sipm_mv": {"type": "float"},
                    "deadtime_s": {"type": "float"},
                    "temperature_c": {"type": "float"},
                    "pressure_pa": {"type": "float"},
                    "device_id": {"type": "keyword"},
                    "detector_name": {"type": "keyword"},
                    "timestamp_ms": {"type": "long"},
                    "timestamp": {"type": "date"},
                    "comp_time": {"type": "keyword"},
                    "comp_date": {"type": "keyword"},
                    "accel_x_g": {"type": "float"},
                    "accel_y_g": {"type": "float"},
                    "accel_z_g": {"type": "float"},
                    "gyro_x_degs": {"type": "float"},
                    "gyro_y_degs": {"type": "float"},
                    "gyro_z_degs": {"type": "float"},
                    "source": {"type": "keyword"},
                }
            }
        }, ignore=400)
        print(f'✓ Elasticsearch index "{ES_INDEX}" ready')
    except Exception as e:
        print(f'✗ Error creating Elasticsearch index: {e}')

print("\nTaking data ...")
if platform.system() == "Windows":
    print("ctrl+break to terminate process")
else:
    print("Press ctl+c to terminate process")

if es is not None:
    print(f"  → Uploading to Elasticsearch: {ES_HOST}")
if save_to_file:
    print(f"  → Saving to file: {fname}")

event_count = 0
es_count = 0

while True:
    for i in range(nDetectors):
        if globals()['Det%s' % str(i)].inWaiting():
            data = globals()['Det%s' % str(i)].readline().decode().replace('\r\n','')
            print(data)
            data = data.split("\t")
            
            ti = str(datetime.now()).split(" ")
            comp_time = ti[-1]
            data.append(comp_time)
            comp_date = ti[0].split('-')
            data.append(comp_date[2] + '/' +comp_date[1] + '/' + comp_date[0])
            
            # Save to file if enabled
            if save_to_file:
                file.write('\t'.join(filter(None, data)) + '\n')
                file.write("\n")
                if int(data[0]) % 10 == 0:
                    file.flush()
            
            # Send to Elasticsearch
            if es is not None:
                doc = convert_to_elasticsearch_format(data, detector_id)
                if doc:
                    if send_to_elasticsearch(doc):
                        es_count += 1
                        if es_count % 10 == 0:
                            print(f"  → Uploaded {es_count} events to Elasticsearch")
            
            event_count += 1

for i in range(nDetectors):
    try:
        globals()['Det%s' % str(i)].close()
    except:
        pass
if save_to_file:
    file.close()

if es is not None:
    print(f"\n✓ Uploaded {es_count} events to Elasticsearch")

