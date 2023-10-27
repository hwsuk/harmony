#!/usr/bin/env bash

set -emuo pipefail

echo "Starting Vault"

# Start vault
vault server -config /data/config.hcl &

# Export values
export VAULT_ADDR='http://0.0.0.0:8200'
export VAULT_SKIP_VERIFY='true'

sleep 5

if [ ! -f "/data/generated_keys.txt" ]; then
  vault operator init > /data/generated_keys.txt
fi

# Parse unsealed keys
mapfile -t keyArray < <( grep "Unseal Key " < /data/generated_keys.txt  | cut -c15- )

vault operator unseal "${keyArray[0]}"
vault operator unseal "${keyArray[1]}"
vault operator unseal "${keyArray[2]}"

# Get root token
mapfile -t rootToken < <(grep "Initial Root Token: " < /data/generated_keys.txt  | cut -c21- )
export VAULT_TOKEN=${rootToken[0]}

# Enable kv
vault secrets enable -version=1 kv

# Enable userpass and add default user
vault auth enable userpass
vault policy write kv-policy /data/policy.hcl
vault write "auth/userpass/users/${ADMIN_USERNAME}" password="${ADMIN_PASSWORD}" policies=kv-policy

fg