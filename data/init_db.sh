#!/bin/bash
set -e

clickhouse-client -n --user "${CLICKHOUSE_DEFAULT_USER:-default}" \
                --password "${CLICKHOUSE_PASSWORD:-}" \
                --query "CREATE DATABASE IF NOT EXISTS ${CLICKHOUSE_DATABASE:-chipchip_db};"