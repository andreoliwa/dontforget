#!/usr/bin/env bash
set -e

# Create dev and test databases during initialisation.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE dontforget_dev;
    CREATE DATABASE dontforget_test;
EOSQL
