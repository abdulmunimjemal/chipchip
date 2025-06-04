#!/bin/bash
set -e

clickhouse-client -n --query "CREATE DATABASE IF NOT EXISTS ${CLICKHOUSE_DATABASE:-chipchip_db};"