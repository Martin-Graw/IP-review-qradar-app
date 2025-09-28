# IP Review App for QRadar

This is a custom QRadar application designed to streamline the investigation of suspicious IP addresses associated with failed login events. It provides a simple interface for a security analyst to enrich IP data and quickly add malicious subnets to a blocklist suitable for a firewall's External Dynamic List (EDL).

## Features

* **Bulk IP Input**: Allows an analyst to paste a list of IP addresses for review.
* **WHOIS Enrichment**: Automatically performs a real-time WHOIS lookup for each IP to identify its network owner and full CIDR subnet.
* **Analyst Decision Workflow**: Presents the enriched data to an analyst for a simple "Allow" or "Block" decision.
* **Plaintext Blocklist Generation**: Generates and serves a simple `blocklist.txt` file containing all blocked subnets, formatted for direct consumption by external systems like a Palo Alto firewall EDL.

## Development Setup

To set up this application for local development, you will need the QRadar App SDK v2, Docker, and Python 3.

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/Martin-Graw/IPReviewApp.git](https://github.com/Martin-Graw/IPReviewApp.git)
    cd IPReviewApp
    ```

2.  **Create a Python Virtual Environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    This app requires the `ipwhois` library. A build script is included to handle this automatically when the app's container is built.

4.  **Run Locally**
    Use the QRadar SDK to run the application locally for testing.
    ```bash
    qapp run -d
    ```
    The app will be available at the `http://localhost:<port>` address provided in the output.

5.  **Register with a QRadar Instance (for full UI testing)**
    To test the app inside a QRadar UI, follow the standard app registration workflow:
    * `qapp preregister`
    * `qapp run -d -q <qradar_ip>`
    * Start the SSH tunnel: `ssh -R <port>:localhost:<port> user@<qradar_ip>`
    * `qapp register`

## Packaging for Production

To create a distributable zip file for installation on a production QRadar server, run the following command from the project's root directory:

```bash
qapp package -p IPReviewApp.zip
```

## Author

Developed by Oliver Obradovic
