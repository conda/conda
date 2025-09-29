#!/bin/bash
# Script to generate test keys for witness policy signing and attestation

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
KEYS_DIR="${SCRIPT_DIR}/keys"

echo "Generating test keys for witness integration..."

# Create keys directory if it doesn't exist
mkdir -p "${KEYS_DIR}"

# Function to generate a key pair
generate_key_pair() {
    local key_name=$1
    local key_size=${2:-2048}
    
    echo "Generating ${key_name} key pair (${key_size} bits)..."
    
    # Generate private key
    openssl genrsa -out "${KEYS_DIR}/${key_name}.pem" ${key_size} 2>/dev/null
    
    # Generate public key
    openssl rsa -in "${KEYS_DIR}/${key_name}.pem" -pubout -out "${KEYS_DIR}/${key_name}.pub" 2>/dev/null
    
    # Set appropriate permissions
    chmod 600 "${KEYS_DIR}/${key_name}.pem"
    chmod 644 "${KEYS_DIR}/${key_name}.pub"
    
    echo "  ✓ Generated ${key_name}.pem (private key)"
    echo "  ✓ Generated ${key_name}.pub (public key)"
}

# Generate keys for different purposes
generate_key_pair "policy-key" 2048      # For signing policies
generate_key_pair "test-key" 2048        # For test attestations
generate_key_pair "build-key" 2048       # For build attestations
generate_key_pair "functionary-key" 2048 # For functionary identity

# Generate an Ed25519 key pair (alternative to RSA)
echo "Generating Ed25519 key pair..."
openssl genpkey -algorithm ed25519 -out "${KEYS_DIR}/ed25519-key.pem" 2>/dev/null
openssl pkey -in "${KEYS_DIR}/ed25519-key.pem" -pubout -out "${KEYS_DIR}/ed25519-key.pub" 2>/dev/null
chmod 600 "${KEYS_DIR}/ed25519-key.pem"
chmod 644 "${KEYS_DIR}/ed25519-key.pub"
echo "  ✓ Generated ed25519-key.pem (private key)"
echo "  ✓ Generated ed25519-key.pub (public key)"

# Create a sample certificate (for x.509 policy signing)
echo "Generating self-signed certificate..."
openssl req -new -x509 -days 3650 -key "${KEYS_DIR}/policy-key.pem" \
    -out "${KEYS_DIR}/policy-cert.pem" \
    -subj "/C=US/ST=State/L=City/O=TestOrg/CN=conda-witness-test" 2>/dev/null
chmod 644 "${KEYS_DIR}/policy-cert.pem"
echo "  ✓ Generated policy-cert.pem (self-signed certificate)"

# Display key information
echo ""
echo "Generated keys summary:"
echo "======================"
ls -la "${KEYS_DIR}/"

echo ""
echo "Key fingerprints:"
for pubkey in "${KEYS_DIR}"/*.pub; do
    if [ -f "$pubkey" ]; then
        key_name=$(basename "$pubkey" .pub)
        fingerprint=$(openssl pkey -pubin -in "$pubkey" -outform DER 2>/dev/null | openssl dgst -sha256 -binary | base64)
        echo "  ${key_name}: ${fingerprint}"
    fi
done

echo ""
echo "✅ Test keys generated successfully!"
echo ""
echo "Usage examples:"
echo "  Sign a policy:    witness sign --key ${KEYS_DIR}/policy-key.pem policy.yaml"
echo "  Run with signing: witness run --key ${KEYS_DIR}/test-key.pem --command 'build.sh'"
echo "  Verify:          conda verify --publickey ${KEYS_DIR}/policy-key.pub --policy signed-policy.yaml"

# Create a .gitignore to prevent accidentally committing private keys
cat > "${KEYS_DIR}/.gitignore" << EOF
# Ignore all private keys
*.pem
!.gitignore

# Keep public keys and certificates
!*.pub
!*-cert.pem
EOF

echo ""
echo "⚠️  Note: Private keys (*.pem) are gitignored for security."