#!/bin/bash

# Set environment variable to indicate we're running in Docker
export DOCKER=true

# Execute the command passed to the script
exec "$@"
