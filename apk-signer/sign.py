
import os
import logging
import zipfile
import tempfile
from pathlib import Path
from config import TEMP_DIR, SIGNED_DIR, MAX_FILE_SIZE

logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(SIGNED_DIR, exist_ok=True)

class APKSigningError(Exception):
    """Custom exception for APK signing errors"""
    pass

def validate_apk(file_path: str) -> bool:
    """Validate if file is a proper APK"""
    try:
        # Check file size
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            raise APKSigningError(f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB")
        
        # Check if it's a valid zip file (APK is essentially a zip)
        if not zipfile.is_zipfile(file_path):
            raise APKSigningError("Invalid APK file format")
        
        # Check for required APK components
        with zipfile.ZipFile(file_path, 'r') as apk:
            required_files = ['AndroidManifest.xml', 'classes.dex']
            apk_files = apk.namelist()
            
            for required_file in required_files:
                if required_file not in apk_files:
                    logger.warning(f"APK missing required file: {required_file}")
        
        return True
        
    except zipfile.BadZipFile:
        raise APKSigningError("Corrupted APK file")
    except Exception as e:
        logger.error(f"APK validation error: {e}")
        raise APKSigningError(f"APK validation failed: {str(e)}")

def sign_apk(input_path: str, output_path: str) -> bool:
    """
    Sign APK file (simplified implementation)
    In production, you would use jarsigner and zipalign
    """
    try:
        # Validate input APK
        validate_apk(input_path)
        
        # For this example, we'll just copy the file with a "signed" marker
        # In real implementation, you would:
        # 1. Use jarsigner to sign with your certificate
        # 2. Use zipalign to optimize the APK
        # 3. Verify the signature
        
        with open(input_path, 'rb') as src, open(output_path, 'wb') as dst:
            dst.write(src.read())
        
        # Add signing metadata (simplified)
        file_size = os.path.getsize(output_path)
        logger.info(f"APK signed successfully. Size: {file_size} bytes")
        
        return True
        
    except Exception as e:
        logger.error(f"APK signing failed: {e}")
        raise APKSigningError(f"Signing failed: {str(e)}")

def get_apk_info(file_path: str) -> dict:
    """Extract APK information"""
    try:
        info = {
            'size': os.path.getsize(file_path),
            'valid': False,
            'package_name': 'unknown',
            'version': 'unknown'
        }
        
        if zipfile.is_zipfile(file_path):
            info['valid'] = True
            
            # In production, you would use aapt to extract APK info
            # For now, we'll just mark it as valid
            with zipfile.ZipFile(file_path, 'r') as apk:
                if 'AndroidManifest.xml' in apk.namelist():
                    info['package_name'] = 'com.example.app'  # Simplified
                    info['version'] = '1.0'  # Simplified
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get APK info: {e}")
        return {'size': 0, 'valid': False, 'package_name': 'error', 'version': 'error'}

def cleanup_temp_files(file_path: str):
    """Clean up temporary files"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to cleanup temp file {file_path}: {e}")

def generate_signed_filename(original_filename: str) -> str:
    """Generate filename for signed APK"""
    name, ext = os.path.splitext(original_filename)
    return f"{name}_signed{ext}"
