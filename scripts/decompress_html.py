"""Quick script to decompress and inspect HTML dump"""
import zlib
import sys
from pathlib import Path

html_file = Path("data/debug/html/mi_2024.html")
data = html_file.read_bytes()

print(f"File size: {len(data)} bytes")
print(f"First 20 bytes (hex): {data[:20].hex()}")
print(f"First 20 bytes (repr): {repr(data[:20])}")

# Try zlib/deflate decompression
try:
    html = zlib.decompress(data, -zlib.MAX_WBITS)
    print("\n[SUCCESS] Decompressed with zlib")
    print(f"Decompressed size: {len(html)} bytes")
    print("\nFirst 2000 chars of HTML:")
    print(html.decode('utf-8', errors='replace')[:2000])
except Exception as e:
    print(f"\n[FAILED] zlib decompression: {e}")

# Try gzip
try:
    import gzip
    html = gzip.decompress(data)
    print("\n[SUCCESS] Decompressed with gzip")
    print(f"Decompressed size: {len(html)} bytes")
    print("\nFirst 2000 chars of HTML:")
    print(html.decode('utf-8', errors='replace')[:2000])
except Exception as e:
    print(f"\n[FAILED] gzip decompression: {e}")

# Try as raw UTF-8
try:
    html = data.decode('utf-8', errors='replace')
    print("\n[INFO] Decoded as raw UTF-8 (with replacement chars)")
    print(f"First 2000 chars:")
    print(html[:2000])
except Exception as e:
    print(f"\n[FAILED] UTF-8 decode: {e}")
