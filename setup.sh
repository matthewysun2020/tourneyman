#!/bin/bash

# Check if Node.js is installed
if ! command -v node &> /dev/null
then
    echo "Node.js not found. Installing..."
    # Install Node.js (example using nvm, but you could use any method appropriate for your system)
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
    source ~/.nvm/nvm.sh
    nvm install node
else
    echo "Node.js is already installed."
fi

# Check if Localtunnel is installed
if ! command -v lt &> /dev/null
then
    echo "Localtunnel not found. Installing..."
    npm install -g localtunnel
else
    echo "Localtunnel is already installed."
fi
