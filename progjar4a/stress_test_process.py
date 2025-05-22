import argparse
import logging
import time
import os
import csv
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple
from file_client_cli import remote_get, remote_upload
import multiprocessing
import gc

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Worker pool configurations
CLIENT_WORKER_POOLS = [1, 5, 50]
SERVER_WORKER_POOLS = [1, 5, 50]

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
            # Generate file in chunks to reduce memory usage
            chunk_size = 1024 * 1024  # 1MB chunks
            with open(filename, 'wb') as f:
                for _ in range(size_mb):
                    f.write(os.urandom(chunk_size))
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
            
        # Get file size without loading entire file into memory
        file_size = os.path.getsize(filename)
                
        time_taken = time.time() - start_time
        logging.info(f"Worker {worker_id} completed {operation} in {time_taken:.2f} seconds")
        
        # Force garbage collection
        gc.collect()
        
        return success, time_taken, file_size
            
    except Exception as e:
        logging.error(f"Worker {worker_id} error during {operation}: {str(e)}")
        return False, time.time() - start_time, 0

def run_concurrent_test(
    operation: str,
    filename: str,
    num_clients: int,
    server_workers: int
) -> Dict:
    """Run concurrent test with specified parameters using processes"""
    start_time = time.time()
    results = []
    
    try:
        with ProcessPoolExecutor(max_workers=num_clients) as executor:
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
        
        # Force garbage collection
        gc.collect()
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    successful_workers = sum(1 for success, _, _ in results if success)
    failed_workers = num_clients - successful_workers
    total_bytes = sum(bytes_transferred for _, _, bytes_transferred in results)
    
    # Calculate per-client metrics
    total_time_per_client = total_time / num_clients
    throughput_per_client = total_bytes / total_time if total_time > 0 else 0
    
    return {
        "operation": operation,
        "filename": filename,
        "num_clients": num_clients,
        "num_server_workers": server_workers,
        "total_time": total_time,
        "total_time_per_client": total_time_per_client,
        "throughput_per_client": throughput_per_client,
        "successful_workers": successful_workers,
        "failed_workers": failed_workers,
        "total_bytes_transferred": total_bytes
    }

def save_results_to_csv(results: List[Dict], filename: str = None) -> None:
    """Save stress test results to a CSV file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stress_test_process_results_{timestamp}.csv"
    
    headers = [
        "Nomor",
        "Operasi",
        "Volume",
        "Jumlah Client Worker Pool",
        "Jumlah Server Worker Pool",
        "Waktu Total per Client (seconds)",
        "Throughput per Client (bytes/second)",
        "Client Workers Sukses",
        "Client Workers Gagal"
    ]
    
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for idx, result in enumerate(results, 1):
                row = {
                    "Nomor": idx,
                    "Operasi": result['operation'],
                    "Volume": result['filename'],
                    "Jumlah Client Worker Pool": result['num_clients'],
                    "Jumlah Server Worker Pool": result['num_server_workers'],
                    "Waktu Total per Client (seconds)": f"{result['total_time_per_client']:.2f}",
                    "Throughput per Client (bytes/second)": f"{result['throughput_per_client']:.2f}",
                    "Client Workers Sukses": result['successful_workers'],
                    "Client Workers Gagal": result['failed_workers']
                }
                writer.writerow(row)
                
        logging.info(f"Results saved to {filename}")
        
    except Exception as e:
        logging.error(f"Error saving results to CSV: {str(e)}")

def main():
    # Set process start method to 'spawn' for better memory management
    multiprocessing.set_start_method('spawn')
    
    # Generate test files if they don't exist
    generate_test_files()
    
    # Test configurations
    operations = ['download', 'upload']
    file_sizes = ['test_10mb.bin', 'test_50mb.bin', 'test_100mb.bin']
    
    results = []
    
    # Run all combinations
    for operation in operations:
        for filename in file_sizes:
            for num_clients in CLIENT_WORKER_POOLS:
                for server_workers in SERVER_WORKER_POOLS:
                    logging.info(f"Testing {operation} of {filename} with {num_clients} client workers and {server_workers} server workers")
                    
                    result = run_concurrent_test(
                        operation, 
                        filename, 
                        num_clients,
                        server_workers
                    )
                    results.append(result)
                    
                    print(f"\nProcess Results for {operation} {filename}:")
                    print(f"Client Workers: {num_clients}, Server Workers: {server_workers}")
                    print(f"Total Time per Client: {result['total_time_per_client']:.2f} seconds")
                    print(f"Throughput per Client: {result['throughput_per_client']/1024/1024:.2f} MB/s")
                    print(f"Successful Workers: {result['successful_workers']}")
                    print(f"Failed Workers: {result['failed_workers']}")
                    print("-" * 80)
                    
                    # Force garbage collection between tests
                    gc.collect()
    
    # Save results to CSV
    save_results_to_csv(results)

if __name__ == "__main__":
    main() 