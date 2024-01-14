#!/usr/bin/env python
__author__ = "Ben Goff"
__email__ = "bgoff@vmware.com"
__date__ = "2022-07-15"
__version__ = "0.1"

"""
This script searches for cbc devices that have not checked into the console in X days
Usage:
    python cbc_device_remover.py -d <DAYS TO SEARCH>
    OR
    python cbc_device_remover.py to be prompted for the days to search
Example:
    python cbc_device_remover.py -d 25
"""

import requests
import json
import sys
import argparse
import os
import time
import csv
from datetime import datetime, timedelta

class cbc_connection(object):
    def __init__(self):
        config = self.get_configs()
        self.backend = config["backend"]
        self.api_id = config["api_id"]
        self.api_key = config["api_key"]
        self.org_key = config["org_key"]
        self.session = self.get_session()

    def get_configs(self):
        ''' Get the configs from external file '''
        with open("config.json", "r") as f:
            config = json.load(f)
        return config

    def get_session(self):
        s = requests.Session()
        headers = {
            "X-Auth-Token": f"{self.api_key}/{self.api_id}",
            "Content-Type": "application/json"
            }
        s.headers.update(headers)
        return s

    def get_date_range(self, days):
        now = datetime.utcnow()
        days_ago = now - timedelta(days=int(days))
        end = datetime.strftime(days_ago, "%Y-%m-%dT%H:%M:%S.000Z")
        start = "2000-01-01T00:00:00.000Z"
        return start, end

    def find_devices(self, start, end):
        post_data = {
        "criteria": {
            "last_contact_time": {"start": start, "end": end},
            "staus": ["ACTIVE"]
        },
        "rows": 10000,
        "start": 0,
        "sort": [{"field": "last_contact_time", "order": "asc"}]
        }
        url = self.backend + f"/appservices/v6/orgs/{self.org_key}/devices/_search"
        r = self.session.post(url, json=post_data)
        if r.status_code < 300:
            device_ids = [[i["name"], i["id"], i["last_contact_time"]] for i in r.json()["results"]]
        else:
            print("API request failed, exiting without making any changes")
            sys.exit(1)
        return device_ids

    def deregister(self, devices):
        device_ids = [str(i[1]) for i in devices]
        post_data = {
        "action_type": "UNINSTALL_SENSOR",
        "device_id": device_ids,
        }
        url = self.backend + f"/appservices/v6/orgs/{self.org_key}/device_actions"
        r = self.session.post(url, json=post_data)
        if r.status_code > 299:
            print("API request to deregister sensors failed with status code = {r.status_code}.")
            print("Exiting without making any changes")
            sys.exit(1)
        return

    def delete(self, devices):
        device_ids = [str(i[1]) for i in devices]
        post_data = {
        "action_type": "DELETE_SENSOR",
        "device_id": device_ids,
        }
        url = self.backend + f"/appservices/v6/orgs/{self.org_key}/device_actions"
        r = self.session.post(url, json=post_data)
        if r.status_code > 299:
            print(f"API request to delete sensors failed with status code = {r.status_code}.")
            print("Exiting without making any changes")
            sys.exit(1)
        return

    def log(self, devices):
        now = int(time.time())
        header = ["Device Name", "Device ID", "Last Checkin Time"]
        with open(f"deletions_{now}_log.csv", "w") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(header)
            for i in devices:
                csv_writer.writerow(i)
        return f"deletions_{now}_log.csv"

def main(argv):
    # Script arguments
    description = "Find endpoints that havent checked into the console in X days. Usage is like: "
    description += f"{os.path.basename(__file__)} -n <number of days>"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-d", "--days", help="Days in the past to search for", type=int)
    args = parser.parse_args()
    if args.days is None:
        args.days = input("How many days ago should we search for? ")

    # Do the work
    cbc = cbc_connection()
    start, end = cbc.get_date_range(args.days)
    devices = cbc.find_devices(start, end)
    print(f"Found {len(devices)} that are older than {args.days} days and still active.")
    if not devices:
        print("Nothing to do, exiting")
        sys.exit(1)
    print("The following devices will be set to deregistered and then deleted:")
    for name, device_id, last_checkin in devices:
        print(f"    Name = {name}, Device_ID = {device_id}")
    proceed = input("Continue? (y/n) ")
    if proceed.lower() != "y":
        print("Exiting without making changes")
        sys.exit(1)
    print("Deregistering Sensors...")
    cbc.deregister(devices)
    print("Deleting Sensors...")
    cbc.delete(devices)
    filename = cbc.log(devices)
    print(f"Done! List of devices removed saved to {filename}")
    sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])
