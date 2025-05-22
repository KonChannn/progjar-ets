import os
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_test_file(size_mb: int, filename: str) -> None:
    """Generate a random file of specified size"""
    try:
        size_bytes = size_mb * 1024 * 1024
        with open(filename, 'wb') as f:
            f.write(os.urandom(size_bytes))
        logging.info(f"Generated test file {filename} of size {size_mb}MB")
    except Exception as e:
        logging.error(f"Error generating {filename}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Generate test files for stress testing')
    parser.add_argument('--output-dir', default='files',
                      help='Directory to store test files (default: files)')
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # Define test files to generate
    test_files = [
        ('test_10mb.bin', 10),
        ('test_50mb.bin', 50),
        ('test_100mb.bin', 100)
    ]

    # Generate each test file
    for filename, size_mb in test_files:
        filepath = os.path.join(args.output_dir, filename)
        generate_test_file(size_mb, filepath)

if __name__ == "__main__":
    main() 