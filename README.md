
# CosmicWatch-Desktop-Muon-Detector-v3X

The CosmicWatch Detector v3X is a compact, low-power (0.5 W) muon telescope that uses a plastic scintillator and silicon photomultiplier to record cosmic-ray muons with high sensitivity and timing precision. It supports standalone data logging to microSD or live USB streaming, offers coincidence mode with a second detector for background suppression, and logs rich event metadata (timestamp, ADC value, coincident flag, temperature, pressure, acceleration). Almost fully open-source with detailed build instructions and provided Python analysis scripts, v3X is great for education, outreach, citizen science, and more advanced cosmic-ray studies.

![Alt text](Pictures/CW_arraw.jpg)

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

You may build and modify this project for personal or educational use, but **commercial use and redistribution is prohibited** without explicit permission from the author.

© 2025 [University of Delaware, Prof. Spencer N.G. Axani]

[![License: CC BY-NC 4.0](https://licensebuttons.net/l/by-nc/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc/4.0/)

## Data Collection with Elasticsearch

### Quick Start: Import Data to Elasticsearch

The `Data/import_data_to_elasticsearch.py` script allows you to collect data from your CosmicWatch detector and upload it directly to Elasticsearch for real-time analysis.

#### Prerequisites

1. **Install dependencies:**
   ```bash
   pip install pyserial elasticsearch
   ```

2. **Set up Elasticsearch port-forwarding** (in a separate terminal):
   ```bash
   kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200
   ```
   **Important:** Keep this terminal running! The port-forward must be active for data upload.

#### Step-by-Step Instructions

1. **Navigate to the Data directory:**
   ```bash
   cd CosmicWatch-Desktop-Muon-Detector-v3X/Data
   ```

2. **Set environment variables** (REQUIRED):
   ```bash
   export ES_HOST="https://localhost:9200"
   export ES_USER="elastic"
   export ES_PASS="your-elasticsearch-password"
   export ES_INDEX="credo-detections"
   export ES_ENABLED="true"  # ← CRITICAL: Must be "true" to enable upload!
   ```

3. **Connect your CosmicWatch detector** to your computer via USB.

4. **Run the import script:**
   ```bash
   python3 import_data_to_elasticsearch.py
   ```

5. **Follow the prompts:**
   - Select port: Enter the number corresponding to your detector's USB port
   - Enter detector ID: Enter an ID (or press Enter for default)
   - Save to file too? Answer `n` for Elasticsearch-only, or `y` to also save to file

6. **Verify data is being posted:**
   Wait 30 seconds, then check the document count:
   ```bash
   curl -k -u "elastic:YOUR_PASSWORD" "https://localhost:9200/credo-detections/_count" \
     -H "Content-Type: application/json" \
     -d '{"query": {"term": {"source": "cosmicwatch-v3x"}}}'
   ```
   If the count increases, data is being posted successfully!

#### Troubleshooting

**No data appearing in Elasticsearch:**
- Verify `ES_ENABLED="true"` is set (this is the most common issue!)
- Check that port-forwarding is still active: `kubectl get pods -n cblee-credo | grep elasticsearch`
- Verify environment variables are set: `env | grep ES_`
- Check the script output for connection errors

**Connection errors:**
- Ensure port-forwarding is running: `kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200`
- Use the HTTP service (`credo-elasticsearch-es-http`) not the default service
- Verify `ES_HOST="https://localhost:9200"` (HTTPS required, not HTTP)

**Data not visible in Kibana:**
- Adjust the time range in Kibana (data may have timestamps in the future)
- Check that the index pattern includes `credo-detections`
- Verify documents exist: Use the curl command above to check document count

#### Viewing Data

**In Kibana:**
1. Access Kibana: https://credo-kibana.nrp-nautilus.io
2. Navigate to Discover
3. Select index pattern: `credo-detections*`
4. Add filter: `source: cosmicwatch-v3x`
5. Adjust time range if needed (try "Last 7 days" or "Last 30 days")

**Using curl:**
```bash
# Get latest 5 documents
curl -k -u "elastic:YOUR_PASSWORD" "https://localhost:9200/credo-detections/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"term": {"source": "cosmicwatch-v3x"}},
    "sort": [{"timestamp": {"order": "desc"}}],
    "size": 5
  }'
```

#### Complete Documentation

For detailed information, see: [Data/README.txt](Data/README.txt)

