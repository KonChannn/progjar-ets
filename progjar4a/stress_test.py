import argparse
import logging
import time
import os
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict, List, Tuple
from file_client_cli import remote_get, remote_upload

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Server configuration
SERVER_HOST = '172.16.16.101'
SERVER_PORT = 8889
SERVER_WORKERS = 50  # Fixed server worker count

def generate_test_files():
    """Generate test files of different sizes"""
    sizes = {
        'test_10mb.bin': 10,
        'test_50mb.bin': 50,
        'test_100mb.bin': 100
    }
    
    for filename, size_mb in sizes.items():
        if not os.path.exists(filename):
            size_bytes = size_mb * 1024 * 1024
            with open(filename, 'wb') as f:
                f.write(os.urandom(size_bytes))
            logging.info(f"Generated test file {filename} of size {size_mb}MB")

def test_worker(operation: str, filename: str, worker_id: int) -> Tuple[bool, float, int]:
    """Worker function that executes a single test operation"""
    start_time = time.time()
    try:
        logging.info(f"Worker {worker_id} starting {operation} of {filename}")
        
        if operation == 'download':
            success = remote_get(filename)
        else:  # upload
            success = remote_upload(filename)
            
        # Get file size for bytes transferred
        with open(filename, 'rb') as f:
            bytes_transferred = len(f.read())
                
        time_taken = time.time() - start_time
        logging.info(f"Worker {worker_id} completed {operation} in {time_taken:.2f} seconds")
        return success, time_taken, bytes_transferred
            
    except Exception as e:
        logging.error(f"Worker {worker_id} error during {operation}: {str(e)}")
        return False, time.time() - start_time, 0

def run_concurrent_test(
    operation: str,
    filename: str,
    num_clients: int,
    worker_type: str = 'thread'
) -> Dict:
    """Run concurrent test with specified parameters"""
    start_time = time.time()
    results = []
    
    try:
        if worker_type == 'process':
            with ProcessPoolExecutor(max_workers=num_clients) as executor:
                futures = [executor.submit(test_worker, operation, filename, i) 
                          for i in range(num_clients)]
                results = [future.result() for future in futures]
        else:  # thread mode
            with ThreadPoolExecutor(max_workers=num_clients) as executor:
                futures = [executor.submit(test_worker, operation, filename, i) 
                          for i in range(num_clients)]
                results = [future.result() for future in futures]
    
    finally:
        # Clean up downloaded files
        if operation == 'download':
            try:
                os.remove(filename)
            except:
                pass
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    successful_workers = sum(1 for success, _, _ in results if success)
    failed_workers = num_clients - successful_workers
    total_bytes = sum(bytes_transferred for _, _, bytes_transferred in results)
    throughput = total_bytes / total_time if total_time > 0 else 0
    
    return {
        "operation": operation,
        "filename": filename,
        "num_clients": num_clients,
        "num_server_workers": SERVER_WORKERS,
        "worker_type": worker_type,
        "total_time": total_time,
        "throughput_bytes_per_second": throughput,
        "successful_workers": successful_workers,
        "failed_workers": failed_workers,
        "total_bytes_transferred": total_bytes
    }

def save_results_to_csv(results: List[Dict], filename: str = None) -> None:
    """Save stress test results to a CSV file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stress_test_results_{timestamp}.csv"
    
    headers = [
        "Nomor",
        "Operasi",
        "Volume",
        "Jumlah Client Worker Pool",
        "Jumlah Server Worker Pool",
        "Waktu Total per Client",
        "Throughput per Client (MB/s)",
        "Client Workers Sukses",
        "Client Workers Gagal"
    ]
    
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for idx, result in enumerate(results, 1):
                total_time_per_client = result['total_time'] / result['num_clients']
                throughput_per_client = (result['throughput_bytes_per_second'] / result['num_clients']) / (1024 * 1024)
                
                row = {
                    "Nomor": idx,
                    "Operasi": result['operation'],
                    "Volume": result['filename'],
                    "Jumlah Client Worker Pool": result['num_clients'],
                    "Jumlah Server Worker Pool": result['num_server_workers'],
                    "Waktu Total per Client": f"{total_time_per_client:.2f}",
                    "Throughput per Client (MB/s)": f"{throughput_per_client:.2f}",
                    "Client Workers Sukses": result['successful_workers'],
                    "Client Workers Gagal": result['failed_workers']
                }
                writer.writerow(row)
                
        logging.info(f"Results saved to {filename}")
        
    except Exception as e:
        logging.error(f"Error saving results to CSV: {str(e)}")

def main():
    # Generate test files if they don't exist
    generate_test_files()
    
    # Test configurations
    operations = ['download', 'upload']
    file_sizes = ['test_10mb.bin', 'test_50mb.bin', 'test_100mb.bin']
    client_worker_counts = [1, 5, 50]  # Client worker counts to test
    worker_types = ['thread', 'process']
    
    # Update server address
    from file_client_cli import server_address
    server_address = (SERVER_HOST, SERVER_PORT)
    
    results = []
    
    # Run all combinations
    for operation in operations:
        for filename in file_sizes:
            for num_clients in client_worker_counts:
                for worker_type in worker_types:
                    logging.info(f"Testing {operation} of {filename} with {num_clients} {worker_type} workers")
                    
                    result = run_concurrent_test(
                        operation, 
                        filename, 
                        num_clients,
                        worker_type
                    )
                    results.append(result)
                    
                    print(f"\n{worker_type.capitalize()} Results for {operation} {filename}:")
                    print(f"Total Time: {result['total_time']:.2f} seconds")
                    print(f"Throughput: {result['throughput_bytes_per_second']/1024/1024:.2f} MB/s")
                    print(f"Successful Workers: {result['successful_workers']}")
                    print(f"Failed Workers: {result['failed_workers']}")
                    print("-" * 80)
    
    # Save results to CSV
    save_results_to_csv(results)

if __name__ == "__main__":
    main() 