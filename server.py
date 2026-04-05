from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import subprocess
import json
import os
import sys
import threading
import time
import re
from collections import deque

app = FastAPI()

# Enable CORS for the local dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Log Queue
LOG_QUEUE = deque(maxlen=100)

def add_log(msg):
    timestamp = time.strftime("%H:%M:%S")
    LOG_QUEUE.append(f"[{timestamp}] {msg}")
    print(f"Server LOG: {msg}")

# Serve sites and videos folders
os.makedirs("sites", exist_ok=True)
os.makedirs("videos", exist_ok=True)
app.mount("/sites", StaticFiles(directory="sites"), name="sites")
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

LEADS_FILE = "leads.json"
WHATSAPP_STATUS = {"status": "disconnected", "qr": None}
WHATSAPP_PROCESS = None

def get_leads_data():
    if not os.path.exists(LEADS_FILE):
        return []
    with open(LEADS_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return []

# --- WhatsApp Background Manager ---
def run_whatsapp_manager():
    global WHATSAPP_STATUS, WHATSAPP_PROCESS
    add_log("Starting Flxbee WhatsApp AI...")
    WHATSAPP_STATUS["status"] = "initializing"
    WHATSAPP_STATUS["qr"] = None
    
    cmd = ["node", "send_whatsapp.js", "--init"]
    WHATSAPP_PROCESS = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    
    for line in iter(WHATSAPP_PROCESS.stdout.readline, ""):
        line_clean = line.strip()
        if not line_clean: continue
        add_log(f"WhatsApp: {line_clean}")
        
        # Parse QR Code
        qr_match = re.search(r"QR_CODE_START:(.*?):QR_CODE_END", line_clean)
        if qr_match:
            WHATSAPP_STATUS["qr"] = qr_match.group(1)
            WHATSAPP_STATUS["status"] = "scanning"
            
        # Parse Statuses
        if "WHATSAPP_AUTHENTICATED" in line_clean:
            WHATSAPP_STATUS["status"] = "authenticated"
            WHATSAPP_STATUS["qr"] = None
        if "WHATSAPP_READY" in line_clean:
            WHATSAPP_STATUS["status"] = "connected"
            WHATSAPP_STATUS["qr"] = None
        if "WHATSAPP_AUTH_FAILURE" in line_clean:
            WHATSAPP_STATUS["status"] = "auth_failure"
        if "WHATSAPP_DISCONNECTED" in line_clean:
            WHATSAPP_STATUS["status"] = "disconnected"
    
    WHATSAPP_PROCESS.stdout.close()
    WHATSAPP_PROCESS.wait()
    WHATSAPP_STATUS["status"] = "disconnected"
    WHATSAPP_PROCESS = None

# Start WhatsApp thread on startup
try:
    threading.Thread(target=run_whatsapp_manager, daemon=True).start()
except Exception as e:
    add_log(f"CRITICAL: Failed to start WhatsApp thread: {e}")

@app.get("/")
async def read_index():
    return FileResponse('dashboard.html')

@app.get("/leads")
async def get_leads():
    return get_leads_data()

@app.get("/logs")
async def get_logs():
    return {"logs": list(LOG_QUEUE)}

@app.get("/whatsapp/status")
async def get_whatsapp_status():
    return WHATSAPP_STATUS

@app.post("/whatsapp/reset")
async def reset_whatsapp():
    global WHATSAPP_PROCESS
    add_log("WHATSAPP: Initializing hard reset...")
    
    # 1. Kill existing process
    if WHATSAPP_PROCESS:
        add_log("WHATSAPP: Terminating current process...")
        WHATSAPP_PROCESS.terminate()
        try:
            WHATSAPP_PROCESS.wait(timeout=5)
        except:
            WHATSAPP_PROCESS.kill()
    
    # 2. Run reset script to clear auth folder
    add_log("WHATSAPP: Clearing session data...")
    subprocess.run(["node", "send_whatsapp.js", "--reset"])
    
    # 3. Restart manager
    threading.Thread(target=run_whatsapp_manager, daemon=True).start()
    return {"status": "success", "message": "WhatsApp reset initiated."}

def run_proc_live(cmd, name):
    """Runs a process and streams logs to the queue"""
    add_log(f"Starting {name}...")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in iter(process.stdout.readline, ""):
        add_log(f"{name}: {line.strip()}")
    process.stdout.close()
    return process.wait()

@app.post("/scrape")
async def scrape_leads(query: str = "Dentists in Mumbai"):
    def run():
        run_proc_live([sys.executable, "scrape_leads.py", query, "5"], "Scraper")
    
    threading.Thread(target=run).start()
    return {"status": "success", "message": "Scraping started in background."}

@app.post("/generate/{lead_index}")
async def generate_site(lead_index: int):
    leads = get_leads_data()
    if lead_index >= len(leads):
        return {"status": "error", "message": "Lead not found"}
    
    lead_name = leads[lead_index]['name']
    def run():
        add_log(f"[WORKFLOW_STEP_1] Building custom website for {lead_name}...")
        run_proc_live([sys.executable, "generate_site.py", "--index", str(lead_index)], "Generator")
    
    threading.Thread(target=run).start()
    return {"status": "success", "message": "Site building started."}

@app.post("/record/{lead_index}")
async def record_site(lead_index: int):
    leads = get_leads_data()
    if lead_index >= len(leads):
        return {"status": "error", "message": "Lead not found"}
    
    lead = leads[lead_index]
    safe_name = lead['name'].replace(" ", "_").replace("/", "_")
    html_file = lead.get('html_file')
    
    if not html_file:
        return {"status": "error", "message": "Site not built yet. Build the site first."}

    def run():
        add_log(f"[WORKFLOW_STEP_2] Initializing video recording for {lead['name']}...")
        ret = run_proc_live(["node", "record.js", html_file, safe_name], "Recorder")
        if ret == 0:
            add_log(f"[SUCCESS] Video demo recorded: {safe_name}.mp4")
            # Refresh data with video path
            all_leads = get_leads_data()
            all_leads[lead_index]['video_file'] = f"videos/{safe_name}.mp4"
            with open(LEADS_FILE, "w") as f:
                json.dump(all_leads, f, indent=2)
        else:
            add_log(f"[ERROR] Recording failed for {lead['name']}. Check Chrome/Puppeteer logs.")
    
    threading.Thread(target=run).start()
    return {"status": "success", "message": "Recording started."}

@app.post("/send/{lead_index}")
async def send_whatsapp(lead_index: int):
    queue_file = "outreach_queue.json"
    queue = []
    if os.path.exists(queue_file):
        with open(queue_file, "r") as f:
            queue = json.load(f)
    lead = all_leads[lead_index]
    safe_name = lead['name'].replace(" ", "_").replace("/", "_")
    video_path = os.path.abspath(f"videos/{safe_name}.mp4")
    
    queue.append({
        "index": lead_index,
        "phone": lead['phone'],
        "name": lead['name'],
        "videoPath": video_path
    })
    with open(queue_file, "w") as f:
        json.dump(queue, f, indent=2)
    add_log(f"Queued outreach for lead {lead['name']}")
    return {"status": "success", "message": "Outreach queued."}

@app.post("/demo")
async def run_demo(phone: str):
    def run():
        add_log(f"[DEMO] Starting One-Click Demo for {phone}...")
        run_proc_live([sys.executable, "demo_flow.py", phone], "DemoFlow")
    
    threading.Thread(target=run).start()
    return {"status": "success", "message": "Demo started! Check WhatsApp soon."}

if __name__ == "__main__":
    import uvicorn
    # Start server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
