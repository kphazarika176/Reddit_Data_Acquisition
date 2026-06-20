#!/usr/bin/env python3
import ssl
import socket

host = "ac-iigyl00-shard-00-00.8prdlwg.mongodb.net"
port = 27017

print(f"Testing SSL connection to {host}:{port}...")
print(f"Python version: {__import__('sys').version}")
print(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
print(f"Certifi version: {__import__('certifi').__version__}")
print()

try:
    # Test 1: Raw TCP connection
    print("1. Testing raw TCP connection...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((host, port))
    print(f"   ✓ TCP connection successful")
    sock.close()
except Exception as e:
    print(f"   ✗ TCP connection failed: {e}")
    exit(1)

try:
    # Test 2: SSL connection with verification disabled
    print("\n2. Testing SSL connection (verification disabled)...")
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    conn = context.wrap_socket(sock, server_hostname=host)
    conn.connect((host, port))
    print(f"   ✓ SSL connection successful")
    print(f"   Protocol: {conn.version()}")
    print(f"   Cipher: {conn.cipher()}")
    conn.close()
except Exception as e:
    print(f"   ✗ SSL connection failed: {e}")
    import traceback
    traceback.print_exc()

try:
    # Test 3: SSL connection with verification enabled
    print("\n3. Testing SSL connection (verification enabled)...")
    import certifi
    
    context = ssl.create_default_context(cafile=certifi.where())
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    conn = context.wrap_socket(sock, server_hostname=host)
    conn.connect((host, port))
    print(f"   ✓ SSL connection successful")
    print(f"   Protocol: {conn.version()}")
    print(f"   Cipher: {conn.cipher()}")
    conn.close()
except Exception as e:
    print(f"   ✗ SSL connection failed: {e}")

print("\n✓ Diagnosis complete")
