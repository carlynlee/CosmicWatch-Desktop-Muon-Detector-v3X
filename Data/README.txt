
import_data.py
This python script will allow you to record data from your detector to the computer.
The benefit is that each event is additionally given a time stamp from your computer.

Running it requires one library:
	1. pyserial (used to read data through the serial port)	

After installing library, simply plug the detector into a USB port, run import_data.py
>> python import_data.py
python script, and you will be prompted you to select the serial port you want to record data from.


import_data_to_elasticsearch.py
This script allows you to record data from your detector and optionally upload 
it directly to Elasticsearch, mapping CosmicWatch column data directly to fields. 
This enables real-time data collection for analysis and federated learning systems.

Required libraries:
	1. pyserial (used to read data through the serial port)
	2. elasticsearch (for Elasticsearch upload)

Install dependencies:
	pip install pyserial elasticsearch

Environment Variables (for Elasticsearch upload):
	ES_HOST      - Elasticsearch host URL (default: https://localhost:9200)
	ES_USER      - Elasticsearch username (default: elastic)
	ES_PASS      - Elasticsearch password (REQUIRED when ES_ENABLED=true)
	ES_INDEX     - Elasticsearch index name (default: credo-detections)
	ES_ENABLED   - Set to 'true' to enable Elasticsearch upload (default: false)

Usage Examples:

1. Save to file only (no Elasticsearch):
	python3 import_data_to_elasticsearch.py
	When prompted, answer "n" to "Save to file too?"

2. Upload to Elasticsearch only (no file):
	# IMPORTANT: Set up port-forward FIRST (in a separate terminal)
	# Use the HTTP service for reliable connections:
	kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200 &
	
	# Keep that terminal running! Then in a NEW terminal:
	cd /path/to/CosmicWatch-Desktop-Muon-Detector-v3X/Data
	
	# Set environment variables
	export ES_HOST="https://localhost:9200"
	export ES_USER="elastic"
	export ES_PASS="your-elasticsearch-password"
	export ES_INDEX="credo-detections"
	export ES_ENABLED="true" 
	
	# Run the script
	python3 import_data_to_elasticsearch.py
	
	# When prompted:
	# - Select port: [enter the number for your detector port]
	# - Enter detector ID: [enter ID or press Enter for default]
	# - Save to file too? n  (answer "n" to skip file writing)
	
	# Verify data is being posted:
	# Wait 30 seconds, then check document count:
	curl -k -u "elastic:YOUR_PASSWORD" "https://localhost:9200/credo-detections/_count" \
	  -H "Content-Type: application/json" \
	  -d '{"query": {"term": {"source": "cosmicwatch-v3x"}}}'
	
	# If count increases, data is being posted successfully!

3. Upload to Elasticsearch AND save to file:
	Follow setup for option 2, but answer "y" when asked "Save to file too?"

The script will:
	- Read data from your CosmicWatch detector in real-time
	- Map CosmicWatch column data directly to Elasticsearch fields
	- Upload each detection to Elasticsearch immediately (if ES_ENABLED=true)
	- Optionally save raw data to a text file

Data Format:
	CosmicWatch columns are mapped directly to Elasticsearch fields:
	- Event → event (event number)
	- Timestamp[s] → pico_timestamp_s (Pico timestamp in seconds)
	- Flag → coincidence_flag, coincident (coincidence flag 0/1 and boolean)
	- ADC[12b] → adc_value (ADC value 0-4095)
	- SiPM[mV] → sipm_mv (SiPM voltage in millivolts)
	- Deadtime[s] → deadtime_s (deadtime in seconds)
	- Temp[C] → temperature_c (temperature in Celsius)
	- Press[Pa] → pressure_pa (pressure in Pascals)
	- Accel(X:Y:Z)[g] → accel_x_g, accel_y_g, accel_z_g (acceleration in g)
	- Gyro(X:Y:Z)[deg/sec] → gyro_x_degs, gyro_y_degs, gyro_z_degs (angular velocity)
	- Name → detector_name (detector name)
	- Time → comp_time (computer time string)
	- Date → comp_date (computer date string)
	- Additional: timestamp_ms, timestamp (computed timestamp in milliseconds)

Security:
	- No credentials are hardcoded in this script
	- All sensitive information must be provided via environment variables
	- Safe for public GitHub repositories


Checking Your Data in Elasticsearch:

After uploading data to Elasticsearch, you can check it using several methods:

1. Quick Check (using curl):
	# Make sure port-forward is running (use HTTP service):
	kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200
	
	# Get total document count:
	curl -k -u "elastic:PASSWORD" "https://localhost:9200/credo-detections/_count" \
	  -H "Content-Type: application/json" \
	  -d '{"query": {"term": {"source": "cosmicwatch-v3x"}}}'
	
	# Get latest 5 detections:
	curl -k -u "elastic:PASSWORD" https://localhost:9200/credo-detections/_search \
	  -H "Content-Type: application/json" \
	  -d '{
	    "query": {"match_all": {}},
	    "sort": [{"timestamp": {"order": "desc"}}],
	    "size": 5
	  }'
	
    # Get CosmicWatch data only:
	curl -k -u "elastic:PASSWORD" https://localhost:9200/credo-detections/_search \
	  -H "Content-Type: application/json" \
	  -d '{
	    "query": {"term": {"source": "cosmicwatch-v3x"}},
	    "sort": [{"timestamp": {"order": "desc"}}],
	    "size": 10
	  }'
	
	# Get specific field values:
	curl -k -u "elastic:PASSWORD" https://localhost:9200/credo-detections/_search \
	  -H "Content-Type: application/json" \
	  -d '{
	    "query": {"term": {"source": "cosmicwatch-v3x"}},
	    "_source": ["event", "adc_value", "temperature_c", "coincident", "timestamp_ms"],
	    "sort": [{"timestamp": {"order": "desc"}}],
	    "size": 10
	  }'

2. Using the helper script:
	From the credo-api-tools directory:
	./check_elasticsearch_data.sh
	
	This script shows:
	- Total document count
	- CosmicWatch-specific data count
	- Latest 5 detections
	- Data breakdown by device_id
	- Recent detections (last hour)

3. Using Kibana (if available):
	# Port-forward Kibana:
	kubectl port-forward -n cblee-credo svc/credo-kibana-kb-http 5601:5601
	
	# Open in browser:
	http://localhost:5601
	
	# Navigate to:
	- Stack Management > Index Patterns > Create index pattern: "credo-detections"
	- Discover > View your data

4. Using Python:
	from elasticsearch import Elasticsearch
	
	es = Elasticsearch(['https://localhost:9200'],
	                  basic_auth=('elastic', 'PASSWORD'),
	                  verify_certs=False)
	
	# Count CosmicWatch documents
	result = es.count(index='credo-detections',
	                 body={'query': {'term': {'source': 'cosmicwatch-v3x'}}})
	print(f"Total CosmicWatch documents: {result['count']}")
	
	# Get latest documents with direct column mapping fields
	result = es.search(index='credo-detections',
	                  body={'query': {'term': {'source': 'cosmicwatch-v3x'}},
	                        'sort': [{'timestamp': {'order': 'desc'}}],
	                        'size': 10})
	for hit in result['hits']['hits']:
	    doc = hit['_source']
	    print(f"Event {doc.get('event', 'N/A')}: device={doc.get('device_id', 'N/A')}, "
	          f"ADC={doc.get('adc_value', 'N/A')}, "
	          f"Temp={doc.get('temperature_c', 'N/A')}C, "
	          f"Coincident={doc.get('coincident', 'N/A')}")

Note: Replace "PASSWORD" with your actual Elasticsearch password from:
	kubectl get secret credo-elasticsearch-es-elastic-user -n cblee-credo \
	  -o jsonpath='{.data.elastic}' | base64 -d
