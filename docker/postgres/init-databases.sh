#!/usr/bin/env bash
set -e

# Create dev and test databases during initialisation.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER dontforget;

    CREATE DATABASE dontforget_dev;
    GRANT ALL PRIVILEGES ON DATABASE dontforget_dev TO dontforget;

    CREATE DATABASE dontforget_test;
    GRANT ALL PRIVILEGES ON DATABASE dontforget_test TO dontforget;
EOSQL
