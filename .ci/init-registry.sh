#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
umask 077
mkdir -p registry

if [[ -e registry/htpasswd || -e registry/server.key || -e registry/ca.crt ]]; then
    echo "Registry files already exist in .ci/registry"
    exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT

openssl req -x509 -newkey rsa:3072 -nodes -days 365 \
    -subj '/CN=Auction Lab CI CA' -keyout "$tmp/ca.key" -out "$tmp/ca.crt"
openssl req -new -newkey rsa:3072 -nodes -subj '/CN=registry' \
    -keyout "$tmp/server.key" -out "$tmp/server.csr"
printf '%s\n' 'subjectAltName=DNS:registry,DNS:localhost,IP:127.0.0.1' \
    'extendedKeyUsage=serverAuth' > "$tmp/server.ext"
openssl x509 -req -in "$tmp/server.csr" -CA "$tmp/ca.crt" -CAkey "$tmp/ca.key" \
    -CAcreateserial -days 365 -extfile "$tmp/server.ext" -out "$tmp/server.crt"

read -r -s -p 'Registry password for ci-publisher (at least 20 characters): ' password
printf '\n'
if (( ${#password} < 20 )); then
    echo 'Password is too short'
    exit 1
fi
printf '%s\n' "$password" | docker run --rm -i --entrypoint htpasswd httpd:2.4-alpine -niB ci-publisher > "$tmp/htpasswd"
unset password
chmod 0644 "$tmp/ca.crt" "$tmp/server.crt"
mv "$tmp/htpasswd" "$tmp/server.key" "$tmp/server.crt" "$tmp/ca.crt" registry/
