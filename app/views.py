# Licensed Materials - Property of IBM
# 5725I71-CC011829
# (C) Copyright IBM Corp. 2015, 2020. All Rights Reserved.
# US Government Users Restricted Rights - Use, duplication or
# disclosure restricted by GSA ADP Schedule Contract with IBM Corp.

# Python Standard Libraries
import os
import json
import ipaddress
import traceback

# Third-Party Libraries
import requests
from flask import (Blueprint, render_template, current_app,
                   Response, request, jsonify)
from ipwhois import IPWhois
from ipwhois.exceptions import IPDefinedError

# QRadar App SDK
from qpylib import qpylib

# pylint: disable=invalid-name
viewsbp = Blueprint('viewsbp', __name__, url_prefix='/')


# --- Main UI Routes ---

@viewsbp.route('/')
def index():
    """Renders the main application page."""
    return render_template('index.html')


@viewsbp.route('/favicon.ico')
def favicon():
    """Serves the application's favicon."""
    return send_from_directory(current_app.static_folder, 'favicon-16x16.png')


# --- Backend API Endpoints ---

@viewsbp.route('/get_ips')
def get_ips_from_ref_set():
    """Fetches a list of IPs from a QRadar Reference Set."""
    ref_set_name = 'IPReview_Pending_IPs'
    qradar_ip = os.environ.get('QRADAR_CONSOLE_IP')
    sec_token = os.environ.get('SEC_ADMIN_TOKEN')

    if not qradar_ip or not sec_token:
        qpylib.log("QRadar IP or SEC token not found.", level='ERROR')
        return jsonify({'error': 'App is not configured with QRadar credentials.'}), 500

    url = f'https://{qradar_ip}/api/reference_data/sets/{ref_set_name}'
    headers = {'SEC': sec_token}

    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)

        ref_set_data = response.json()
        ip_list = [item['value'] for item in ref_set_data.get('data', [])]
        return jsonify({'ips': ip_list})

    except requests.exceptions.RequestException as e:
        qpylib.log(f"API request failed for ref set '{ref_set_name}': {e}", level='ERROR')
        return jsonify({'error': 'Failed to retrieve IP list from QRadar'}), 500
    except Exception as e:
        qpylib.log(f"Unexpected error getting ref set '{ref_set_name}': {e}", level='ERROR')
        return jsonify({'error': 'An unexpected error occurred'}), 500


@viewsbp.route('/process_list', methods=['POST'])
def process_ip_list():
    """Intelligently processes a list of IPs one subnet at a time."""
    data = request.get_json()
    ip_list_str = data.get('ips', [])

    if not ip_list_str:
        return jsonify({'status': 'complete'})

    try:
        ip_list_obj = [ipaddress.ip_address(ip) for ip in ip_list_str]
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid IP address in list.'})

    current_ip_obj = ip_list_obj.pop(0)
    remaining_ips_str = [str(ip) for ip in ip_list_obj]

    if not current_ip_obj.is_global:
        qpylib.log(f"Skipping private/reserved IP {str(current_ip_obj)}", level='INFO')
        return jsonify({'status': 'error', 'message': f'Skipping private/reserved IP {str(current_ip_obj)}', 'remaining_ips': remaining_ips_str})

    try:
        whois_obj = IPWhois(str(current_ip_obj))
        whois_results = whois_obj.lookup_whois()
        
        subnet_str = whois_results.get('asn_cidr')
        if not subnet_str:
            raise ValueError("WHOIS result did not contain a CIDR subnet.")
        
        subnet_obj = ipaddress.ip_network(subnet_str, strict=False)
        owner = whois_results.get('asn_description')
        
        ips_in_subnet_count = 1
        remaining_ips_obj = []
        for ip in ip_list_obj:
            if ip in subnet_obj:
                ips_in_subnet_count += 1
            else:
                remaining_ips_obj.append(ip)
        
        remaining_ips_str = [str(ip) for ip in remaining_ips_obj]

        response_data = {
            'status': 'in_progress',
            'review_item': {
                'type': 'subnet',
                'value': str(subnet_obj),
                'owner': owner,
                'ip_count': ips_in_subnet_count
            },
            'remaining_ips': remaining_ips_str
        }
        return jsonify(response_data)

    except Exception as e:
        qpylib.log(f"Error processing IP {str(current_ip_obj)}: {e}", level='ERROR')
        return jsonify({'status': 'error', 'message': f'Failed to process {str(current_ip_obj)}', 'remaining_ips': remaining_ips_str})


@viewsbp.route('/block', methods=['POST'])
def add_to_blocklist():
    """Adds a single subnet to the blocklist file, checking for duplicates."""
    data = request.get_json()
    subnet_to_block = data.get('subnet')

    if not subnet_to_block:
        return Response("Missing 'subnet' in request body", status=400)

    blocklist_path = os.path.join('/opt/app-root/store', 'blocklist.txt')

    try:
        existing_subnets = set()
        if os.path.exists(blocklist_path):
            with open(blocklist_path, 'r') as f:
                existing_subnets = {line.strip() for line in f}
        
        if subnet_to_block not in existing_subnets:
            with open(blocklist_path, 'a') as f:
                f.write(subnet_to_block + '\n')
            return Response(f"Successfully added {subnet_to_block}", mimetype='text/plain')
        else:
            return Response(f"{subnet_to_block} is already in the blocklist.", mimetype='text/plain')

    except Exception as e:
        qpylib.log(f"Error writing to blocklist.txt: {e}", level='ERROR')
        return Response("Error writing to blocklist file.", status=500)


@viewsbp.route('/block_owner', methods=['POST'])
def block_owner():
    """Blocks all subnets associated with a given owner from the remaining IP list."""
    data = request.get_json()
    owner_to_block = data.get('owner')
    ip_list_str = data.get('ips', [])

    if not owner_to_block or not ip_list_str:
        return jsonify({'status': 'error', 'message': 'Missing owner or IP list.'})

    subnets_to_block = set()
    remaining_ips_str = []
    
    for ip_str in ip_list_str:
        try:
            if not ipaddress.ip_address(ip_str).is_global:
                remaining_ips_str.append(ip_str)
                continue

            whois_obj = IPWhois(ip_str)
            whois_results = whois_obj.lookup_whois()
            
            owner = whois_results.get('asn_description')
            subnet = whois_results.get('asn_cidr')
            
            if owner == owner_to_block and subnet:
                subnets_to_block.add(subnet)
            else:
                remaining_ips_str.append(ip_str)
        
        except Exception as e:
            qpylib.log(f"WHOIS lookup failed for {ip_str} during owner block: {e}", level='WARN')
            remaining_ips_str.append(ip_str)

    if subnets_to_block:
        blocklist_path = os.path.join('/opt/app-root/store', 'blocklist.txt')
        try:
            existing_subnets = set()
            if os.path.exists(blocklist_path):
                with open(blocklist_path, 'r') as f:
                    existing_subnets = {line.strip() for line in f}
            
            with open(blocklist_path, 'a') as f:
                for subnet in subnets_to_block:
                    if subnet not in existing_subnets:
                        f.write(subnet + '\n')
        except Exception as e:
            qpylib.log(f"Error writing to blocklist during owner block: {e}", level='ERROR')
    
    return jsonify({'status': 'success', 'remaining_ips': remaining_ips_str})


@viewsbp.route('/blocklist.txt')
def serve_blocklist():
    """Serves the blocklist file as plaintext."""
    blocklist_path = os.path.join('/opt/app-root/store', 'blocklist.txt')
    try:
        with open(blocklist_path, 'r') as f:
            content = f.read()
        return Response(content, mimetype='text/plain')
    except FileNotFoundError:
        return Response('', mimetype='text/plain')