#!/usr/bin/env python3
"""
Setup script to download required NLTK data
Run this once on the server to fix XLSX upload issues
"""
import nltk
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_nltk_data():
    """Download all required NLTK data packages"""
    packages = [
        'punkt_tab',
        'punkt',
        'averaged_perceptron_tagger',
        'maxent_ne_chunker',
        'words'
    ]

    logger.info("Downloading NLTK data packages...")

    for package in packages:
        try:
            logger.info(f"Downloading {package}...")
            nltk.download(package, quiet=False)
            logger.info(f"✓ {package} downloaded successfully")
        except Exception as e:
            logger.warning(f"✗ Failed to download {package}: {str(e)}")

    logger.info("NLTK data download complete!")

if __name__ == "__main__":
    download_nltk_data()
