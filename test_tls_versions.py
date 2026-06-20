#!/usr/bin/env python3
import ssl
import socket

host = "ac-iigyl00-shard-00-00.8prdlwg.mongodb.net"
port = 27017

# Test different TLS versions
tls_versions = [
    (ssl.TLSVersion.TLSv1_2, "TLS 1.2"),
    (ssl.TLSVersion.TLSv1_3, "TLS 1.3"),
]

for tls_version, name in tls_versions:
    try:
        print(f"Testing {name}...")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = tls_version
        context.maximum_version = tls_version
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        conn = context.wrap_socket(sock, server_hostname=host)
        conn.connect((host, port))
        print(f"  ✓ {name} successful!")
        print(f"  Protocol: {conn.version()}")
        conn.close()
        break
    except Exception as e:
        print(f"  ✗ {name} failed: {str(e)[:60]}")

print("\nNote: If all TLS versions fail, this might be a firewall/proxy issue")
print("or the MongoDB server might be experiencing issues.")
