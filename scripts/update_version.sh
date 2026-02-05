#!/bin/bash

# Update version file with current git commit hash (short)
git rev-parse --short HEAD > VERSION
echo "Updated VERSION to $(cat VERSION)"
