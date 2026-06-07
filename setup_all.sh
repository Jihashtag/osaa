#!/bin/bash
# Unified OSINT Aggregator & Dependencies Setup
echo "Cloning and preparing OSINT toolkit..."

# 1. Clone projects
# Replace with your prefered git repo
git clone https://github.com/holehe-osint/holehe ../holehe
git clone https://github.com/Mr-Holmes-OSINT/MrHolmes ../python_holmes
git clone https://github.com/killswitch-GUI/Tookie-OSINT ../python_toolkie

# 2. Install Tor
sudo apt update && sudo apt install -y tor torsocks

# 3. Environment & Dep Setup
python3 -m venv venv
source venv/bin/activate
pip3 install --upgrade pip

pip3 install -r requirements.txt
pip3 install -r ../holehe/requirements.txt
pip3 install -r ../python_holmes/requirements.txt
pip3 install -r ../python_toolkie/requirements.txt

echo "Setup complete. Start Tor service before running osaa."
