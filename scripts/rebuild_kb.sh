#!/usr/bin/env bash
set -euo pipefail
curl -s -X POST http://localhost:5002/rebuild | jq .
