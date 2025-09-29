# IP Review & Automation App for QRadar

This is a custom QRadar application designed to streamline and automate the investigation of suspicious IP addresses from failed login events. The app intelligently groups IPs by subnet and learns from analyst decisions within a session to automatically handle known malicious owners, significantly speeding up the review process.

## Features

* **Load from QRadar**: Ingests a list of IP addresses directly from a QRadar Reference Set.
* **Intelligent Grouping**: Automatically processes the IP list to group individual IPs by their parent CIDR subnet, reducing the number of items an analyst needs to manually review.
* **WHOIS Enrichment**: Performs a real-time WHOIS lookup for each unique subnet to identify its network owner.
* **Session-Based Smart Blocking**: "Learns" from an analyst's decisions. If an analyst blocks a subnet from a particular owner, the app will automatically block all other subnets from that same owner for the rest of the review session.
* **Dynamic UI**: The user interface updates in real-time, showing the current blocklist as it's built and displaying the grouped subnets for review.
* **Plaintext Blocklist Generation**: Generates and serves a simple `blocklist.txt` file containing all blocked subnets, formatted for direct consumption by external systems like a Palo Alto firewall's External Dynamic List (EDL).

## Development Setup

To set up this application for local development, you will need the QRadar App SDK v2, Docker, and Python 3.

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Martin-Graw/IP-review-qradar-app
    cd IPReviewApp
    ```

2.  **Create and Activate Virtual Environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    Create a `requirements.txt` file with the following content:
    ```
    Flask
    ipwhois
    requests
    ```
    Then, install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run Locally**
    Use the QRadar SDK to run the application locally for testing basic UI and backend functionality.
    ```bash
    qapp run -d
    ```

5.  **Register with a QRadar Instance**
    To test the full functionality, you must register the app with a QRadar development instance using the standard registration workflow (`preregister`, `run -q`, `ssh` tunnel, `register`).

## Packaging for Production

To create a distributable zip file for installation on a QRadar server, run the following command:

```bash
qapp package -p IPReviewApp.zip
```
This package can then be deployed using the `qapp deploy` command.

## Author

Developed by Oliver Obradovic
