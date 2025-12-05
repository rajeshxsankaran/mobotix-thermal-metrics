import argparse
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from select import select
import timeout_decorator
import numpy as np
import csv
import glob
from waggle.plugin import Plugin


# camera image fetch timeout (seconds)
DEFAULT_CAMERA_TIMEOUT = 120

def delete_all_files(folder_path):
    if not os.path.isdir(folder_path):
        return

    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    if not files:
        return

    for f in files:
        file_path = os.path.join(folder_path, f)
        try:
            os.remove(file_path)
        except Exception:
            pass

@timeout_decorator.timeout(DEFAULT_CAMERA_TIMEOUT, use_signals=False)
def get_camera_frames(ip, user, password, workdir="/data", frames=1):
    cmd = [
        "/thermal-raw",
        "--url",
        ip,
        "--user",
        user,
        "--password",
        password,
        "--dir",
        workdir,
    ]
    logging.info(f"Calling camera interface: {cmd}")
    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as process:
        while True:
            pollresults = select([process.stdout], [], [], 5)[0]
            if not pollresults:
                logging.warning("Timeout waiting for camera interface output")
                continue
            output = pollresults[0].readline()
            if not output:
                logging.warning("No data from camera interface output")
                continue
            m = re.search(r"frame\s#(\d+)", output.strip().decode())
            logging.info(output.strip().decode())
            if m and int(m.groups()[0]) > frames:
                logging.info("Max frame count reached, closing camera capture")
                return

def load_thermal_csv(filepath):
    """Load thermal CSV file, skipping metadata lines."""
    data_lines = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f, delimiter=';')
        for row in reader:
            # Skip metadata (non-numeric first element)
            if not row or not row[0].replace('.', '', 1).isdigit():
                continue
            data_lines.append([float(x) for x in row if x.strip() != ''])
    return np.array(data_lines)

def analyze_thermal_data(data):
    """Compute variability and fog-related uniformity metrics."""
    timestamp = time.time_ns()
    mean_val = np.mean(data)
    std_val = np.std(data)
    min_val = np.min(data)
    max_val = np.max(data)

    metrics = {
        'mean_temperature': mean_val,
        'std_dev': std_val,
        'min_temperature': min_val,
        'max_temperature': max_val,
    }
    with Plugin() as plugin:
        plugin.publish("thermal.mean.c", mean_val, timestamp=timestamp)
        plugin.publish("thermal.stddev.c", std_val, timestamp=timestamp)
        plugin.publish("thermal.max.c", max_val, timestamp=timestamp)
        plugin.publish("thermal.min.c", min_val, timestamp=timestamp)

    return metrics

def process_thermal_data():
    """Processes the thermal CSV files and publishes metrics."""
    pattern = "/data/*_336x252_14bit.thermal.celsius.csv"
    files = sorted(glob.glob(pattern))
    if not files:
        logging.warning("No thermal CSV files found.")
        return

    for filepath in files:
        # upload the raw file for further analysis
        with Plugin() as plugin:
            plugin.upload_file(filepath, timestamp=timestamp)
        data = load_thermal_csv(filepath)
        metrics = analyze_thermal_data(data)
        print(f"Data shape: {data.shape}")
        for k, v in metrics.items():
            print(f"{k:30s}: {v:.6f}")

def main():
    parser = argparse.ArgumentParser(description="Thermal camera data capture and analysis")
    parser.add_argument("--ip", type=str, default="camera-pt-rgbt-mobotix", help="Camera IP or hostname")
    args = parser.parse_args()

    # Read credentials from environment variables
    password = os.getenv("mobotpassword")
    user = os.getenv("mobotuser")

    if not user or not password:
        logging.error("Missing environment variables: CAMERA_USER and CAMERA_PASSWORD must be set.")
        sys.exit(1)

    delete_all_files("/data/")
    get_camera_frames(ip=args.ip, user=user, password=password)
    process_thermal_data()

if __name__ == "__main__":
    main()
