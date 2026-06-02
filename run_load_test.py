"""Run the VerdictOS API and Locust load test simultaneously."""
import subprocess
import time
import sys

def run_load_test():
    print("Starting API Server...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for API to boot
    time.sleep(5)
    
    print("Starting Locust Load Test (Headless, 10 users, 2 users/sec, 30s duration)...")
    locust_process = subprocess.Popen(
        [sys.executable, "-m", "locust", "-f", "tests/load/locustfile.py", "--headless", "-u", "10", "-r", "2", "-t", "30s", "--host", "http://127.0.0.1:8000"],
    )
    
    locust_process.communicate()
    
    print("Load test completed. Shutting down API Server...")
    api_process.terminate()
    api_process.wait()
    print("Done.")

if __name__ == "__main__":
    run_load_test()
