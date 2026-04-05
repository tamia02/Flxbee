import subprocess
import json
import sys
import os
import time

def add_log(msg):
    print(f"DEMO_FLOW: {msg}")

def run_cmd(cmd, name):
    add_log(f"Running {name}...")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode == 0:
            add_log(f"{name} completed successfully.")
            return True
        else:
            add_log(f"{name} failed: {result.stdout}")
            return False
    except Exception as e:
        add_log(f"Error running {name}: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python demo_flow.py <phone_number>")
        return

    phone = sys.argv[1].replace("+", "").replace(" ", "")
    
    # Select a lead or use a placeholder
    leads_file = "leads.json"
    leads = []
    if os.path.exists(leads_file):
        with open(leads_file, "r") as f:
            leads = json.load(f)
    
    if not leads:
        add_log("No leads found. Please scrape some leads first.")
        return

    # Use the first lead, but update their phone to the demo target
    lead = leads[0]
    lead_index = 0
    original_phone = lead['phone']
    lead['phone'] = phone
    
    # Temporary update for demo
    with open(leads_file, "w") as f:
        json.dump(leads, f, indent=2)
    
    try:
        # Step 1: Build Site
        if not run_cmd([sys.executable, "generate_site.py", "--index", str(lead_index)], "Site Builder"):
            return

        # Get safe name for recording
        safe_name = lead['name'].replace(" ", "_").replace("/", "_")
        html_file = f"sites/{safe_name}.html"
        
        # Step 2: Record Video
        if not run_cmd(["node", "record.js", html_file, safe_name], "Video Recorder"):
            return
            
        # Step 3: Send via WhatsApp (Queue based)
        add_log("Queuing WhatsApp outreach...")
        queue_file = "outreach_queue.json"
        
        # Determine paths
        safe_name = lead['name'].replace(" ", "_").replace("/", "_")
        video_path = os.path.abspath(f"videos/{safe_name}.mp4")
        
        queue = []
        if os.path.exists(queue_file):
            try:
                with open(queue_file, "r") as f:
                    queue = json.load(f)
            except:
                queue = []
        
        queue.append({
            "index": lead_index,
            "phone": phone,
            "name": lead['name'],
            "videoPath": video_path
        })
        
        with open(queue_file, "w") as f:
            json.dump(queue, f, indent=2)
            
        add_log("SUCCESS: One-Click Demo queued! Check your WhatsApp.")
        
    finally:
        # Restore original phone
        lead['phone'] = original_phone
        with open(leads_file, "w") as f:
            json.dump(leads, f, indent=2)

if __name__ == "__main__":
    main()
