import subprocess
import json
import os
import sys

print("""
========================================
   LEAD GEN AUTOMATION SYSTEM
========================================
""")

# Step 1: Generate all websites
print("STEP 1: Generating websites with AI...")
result = subprocess.run([sys.executable, "generate_site.py"], capture_output=False)
if result.returncode != 0:
    print("ERROR: Website generation failed. Check your Claude API key.")
    exit(1)

# Step 2: Record videos for each lead
print("\nSTEP 2: Recording videos...")
with open("leads.json") as f:
    leads = json.load(f)

os.makedirs("videos", exist_ok=True)

for lead in leads:
    safe_name = lead['name'].replace(" ", "_").replace("/", "_")
    html_file = f"sites/{safe_name}.html"
    
    if not os.path.exists(html_file):
        print(f"  SKIP: No HTML file for {lead['name']}")
        continue
    
    print(f"  Recording {lead['name']}...")
    # Use 'node' to run the script
    result = subprocess.run(
        ["node", "record.js", html_file, safe_name],
        capture_output=False
    )
    
    if result.returncode != 0:
        print(f"  WARNING: Recording may have failed for {lead['name']}")

# Step 3: Send WhatsApp messages with videos
print("\nSTEP 3: Sending WhatsApp messages...")
print("You will need to scan a QR code with your phone (one time only)")
input("Press ENTER when ready to start WhatsApp sending...")

subprocess.run(["node", "send_whatsapp.js"])
