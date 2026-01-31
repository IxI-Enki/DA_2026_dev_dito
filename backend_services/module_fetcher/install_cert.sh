#!/bin/bash
# =============================================================================
# Install custom SSL certificate into container trust store
# =============================================================================
# The LeoWiki uses a certificate that may not be in the default CA bundle.
# This script copies it to the system cert store if available.

CERT_FILE="/config/secrets/ssl.cert"

if [ -f "$CERT_FILE" ]; then
    echo "[SSL] Installing custom certificate..."
    cp "$CERT_FILE" /usr/local/share/ca-certificates/leowiki.crt
    update-ca-certificates --fresh > /dev/null 2>&1
    
    # Also set for Python requests library
    export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
    export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
    
    echo "[SSL] Certificate installed successfully"
else
    echo "[SSL] No custom certificate found at $CERT_FILE"
fi
