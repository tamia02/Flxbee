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

# Force UTF-8 for Windows terminals to handle Indian characters
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

def safe_json_read(filepath):
    """Safe read with retry and error handling."""
    if not os.path.exists(filepath):
        return []
    for _ in range(3):
        try:
            with open(filepath, "r") as f:
                content = f.read().strip()
                if not content: return []
                return json.loads(content)
        except (PermissionError, json.JSONDecodeError, OSError):
            time.sleep(0.5)
    return []

def safe_json_write(filepath, data):
    """Write to a temporary file first, then move it (atomic write) to avoid corruption."""
    temp_path = filepath + ".tmp"
    for _ in range(3):
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            # Atomic rename
            os.replace(temp_path, filepath)
            return True
        except (PermissionError, OSError) as e:
            add_log(f"WRITER_ERROR: {e}")
            time.sleep(0.5)
    return False

def get_leads_data():
    return safe_json_read(LEADS_FILE)

def update_lead_status(index, status):
    leads = get_leads_data()
    if index < len(leads):
        leads[index]['status'] = status
        safe_json_write(LEADS_FILE, leads)

# --- WhatsApp Background Manager ---
def run_whatsapp_manager():
    global WHATSAPP_STATUS, WHATSAPP_PROCESS
    add_log("Starting Flxbee WhatsApp AI...")
    WHATSAPP_STATUS["status"] = "initializing"
    WHATSAPP_STATUS["qr"] = None
    
    cmd = ["node", os.path.join(BASE_DIR, "send_whatsapp.js"), "--init"]
    WHATSAPP_PROCESS = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=BASE_DIR, encoding='utf-8')
    
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
            add_log("SERVER: WhatsApp is READY and listening for tasks.")
        if "WHATSAPP_AUTH_FAILURE" in line_clean:
            WHATSAPP_STATUS["status"] = "auth_failure"
        if "WHATSAPP_DISCONNECTED" in line_clean:
            WHATSAPP_STATUS["status"] = "disconnected"
        
        # Parse Send Success: WHATSAPP_SEND_SUCCESS:Name:Index
        if "WHATSAPP_SEND_SUCCESS" in line_clean:
            try:
                parts = line_clean.split(":")
                if len(parts) >= 3:
                    lead_index = int(parts[2])
                    update_lead_reached_status(lead_index)
                    update_lead_status(lead_index, "completed")
            except Exception as e:
                add_log(f"Manager Error parsing success: {e}")
    
    WHATSAPP_PROCESS.stdout.close()
    WHATSAPP_PROCESS.wait()
    WHATSAPP_STATUS["status"] = "disconnected"
    WHATSAPP_PROCESS = None

@app.on_event("startup")
async def startup_event():
    add_log("SERVER: Application startup sequence initiated.")
    try:
        threading.Thread(target=run_whatsapp_manager, daemon=True).start()
        add_log("SERVER: WhatsApp background manager started.")
    except Exception as e:
        add_log(f"CRITICAL: Failed to start WhatsApp thread: {e}")

DASHBOARD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')

@app.get("/")
async def read_index():
    if not os.path.exists(DASHBOARD_PATH):
        add_log(f"CRITICAL: {DASHBOARD_PATH} not found!")
        raise HTTPException(status_code=404, detail="Dashboard file missing on server")
    return FileResponse(DASHBOARD_PATH, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})

@app.get("/index.html")
async def read_dashboard():
    return FileResponse(DASHBOARD_PATH, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})

@app.get("/leads")
async def get_leads():
    return get_leads_data()

@app.get("/logs")
async def get_logs():
    return list(LOG_QUEUE)

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
    subprocess.run(["node", os.path.join(BASE_DIR, "send_whatsapp.js"), "--reset"], cwd=BASE_DIR)
    
    # 3. Force kill any zombie chrome/node instances to unlock files
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "node.exe", "/T"], capture_output=True)
    
    # 4. Restart manager
    threading.Thread(target=run_whatsapp_manager, daemon=True).start()
    return {"status": "success", "message": "WhatsApp hard reset complete."}

def run_proc_live(cmd, name):
    """Runs a process and streams logs to the queue"""
    add_log(f"Starting {name}...")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=BASE_DIR, encoding='utf-8', env=env)
    for line in iter(process.stdout.readline, ""):
        add_log(f"{name}: {line.strip()}")
    process.stdout.close()
    return process.wait()

@app.post("/scrape")
async def scrape_leads(query: str = "Dentists in Mumbai", live: bool = False):
    def run():
        cmd = [sys.executable, os.path.join(BASE_DIR, "scrape_leads.py"), query, "5"]
        if live:
            cmd.append("--live")
            add_log(f"[SCRAPER] Starting Live Master Scrape for {query}...")
        else:
            add_log(f"Starting Scraper for {query}...")
        
        run_proc_live(cmd, "Scraper")
    
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
        run_proc_live([sys.executable, os.path.join(BASE_DIR, "generate_site.py"), "--index", str(lead_index)], "Generator")
    
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
        ret = run_proc_live(["node", os.path.join(BASE_DIR, "record.js"), html_file, safe_name], "Recorder")
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
    leads = get_leads_data()
    if lead_index >= len(leads):
        return {"status": "error", "message": "Lead not found"}
    lead = leads[lead_index]
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
        run_proc_live([sys.executable, os.path.join(BASE_DIR, "demo_flow.py"), phone], "DemoFlow")
    threading.Thread(target=run).start()
    return {"status": "success", "message": "Demo started! Check WhatsApp soon."}

def safe_queue_add(task):
    """Safely adds a task to outreach_queue.json with atomic write."""
    queue_file = "outreach_queue.json"
    queue = safe_json_read(queue_file)
    queue.append(task)
    if safe_json_write(queue_file, queue):
        add_log(f"SUCCESS: Queued outreach for {task.get('name')}")
        return True
    return False

@app.post("/run/{lead_index}")
async def run_mission(lead_index: int):
    """Run full automation for a single lead: Build -> Record -> Queue Send."""
    def run():
        try:
            leads = safe_json_read(LEADS_FILE)
            if not leads or lead_index >= len(leads):
                raise Exception(f"Lead index {lead_index} not found.")
            
            lead = leads[lead_index]
            lead_name = lead['name']
            
            add_log(f"[MISSION] Starting automation for {lead_name}...")
            update_lead_status(lead_index, "building")
            
            # 1. Build
            add_log(f"[MISSION] Step 1/3: Generating Site for {lead_name}...")
            # Use run_proc_live for streaming logs and to avoid buffer deadlocks
            res_build = run_proc_live([sys.executable, os.path.join(BASE_DIR, "generate_site.py"), "--index", str(lead_index)], "Generator")
            if res_build != 0:
                raise Exception(f"Site gen failed with code {res_build}")
            
            # Explicit verification of generated HTML file
            leads_fresh = safe_json_read(LEADS_FILE)
            lead = leads_fresh[lead_index]
            html_file = lead.get('html_file', f"sites/{lead['name'].replace(' ', '_').replace('/', '_')}.html")
            if not os.path.exists(os.path.join(BASE_DIR, html_file)):
                raise Exception(f"HTML file missing after generation: {html_file}")
            
            # 2. Record
            update_lead_status(lead_index, "recording")
            add_log(f"[MISSION] Step 2/3: Recording Demo for {lead_name}...")
            # Reload to get fresh html_file path from generation step
            leads_fresh = safe_json_read(LEADS_FILE)
            lead = leads_fresh[lead_index]
            html_file = lead.get('html_file', f"sites/{lead['name'].replace(' ', '_').replace('/', '_')}.html")
            safe_name = lead['name'].replace(" ", "_").replace("/", "_")
            
            # Use run_proc_live instead of subprocess.run for recording
            res_record = run_proc_live(["node", os.path.join(BASE_DIR, "record.js"), html_file, safe_name], "Recorder")
            if res_record != 0:
                raise Exception(f"Recording failed with code {res_record}")
            
            # Explicit verification of video file
            video_path = os.path.abspath(os.path.join(BASE_DIR, f"videos/{safe_name}.mp4"))
            if not os.path.exists(video_path):
                raise Exception(f"Video file missing after recording: {video_path}")
            
            # 3. Send (Queue)
            update_lead_status(lead_index, "queuing")
            add_log(f"[MISSION] Step 3/3: Queuing Outreach for {lead_name}...")
            # Reload to get fresh paths
            leads_fresh = safe_json_read(LEADS_FILE)
            lead = leads_fresh[lead_index]
            
            safe_name = lead['name'].replace(" ", "_").replace("/", "_")
            video_path = os.path.abspath(f"videos/{safe_name}.mp4")
            
            task = {
                "index": lead_index,
                "phone": lead['phone'],
                "name": lead['name'],
                "videoPath": video_path
            }
            
            if safe_queue_add(task):
                add_log(f"[SUCCESS] Mission queued for {lead_name}")
            else:
                raise Exception("Failed to write to outreach_queue.json")
            
        except Exception as e:
            update_lead_status(lead_index, f"failed: {str(e)}")
            add_log(f"[ERROR] Mission failed for lead {lead_index}: {e}")
            
    threading.Thread(target=run).start()
    return {"status": "success", "message": "Mission started."}

@app.post("/run_all")
async def run_all_missions():
    """Run full automation for ALL leads sequentially."""
    def run():
        try:
            leads = safe_json_read(LEADS_FILE)
            if not leads:
                add_log("[MASTER] No leads found to process.")
                return
            
            add_log(f"[MASTER] Starting Master Automation for {len(leads)} leads...")
            for i in range(len(leads)):
                lead = leads[i]
                lead_name = lead['name']
                add_log(f"[MASTER] Processing {i+1}/{len(leads)}: {lead_name}")
                
                update_lead_status(i, "building")
                # 1. Build
                res_build = run_proc_live([sys.executable, os.path.join(BASE_DIR, "generate_site.py"), "--index", str(i)], "Generator")
                if res_build != 0:
                    add_log(f"[ERROR] Build failed for {lead_name}")
                    continue
                
                # 2. Record
                update_lead_status(i, "recording")
                leads_fresh = safe_json_read(LEADS_FILE)
                lead = leads_fresh[i]
                html_file = lead.get('html_file', f"sites/{lead['name'].replace(' ', '_').replace('/', '_')}.html")
                safe_name = lead['name'].replace(" ", "_").replace("/", "_")
                
                res_record = run_proc_live(["node", os.path.join(BASE_DIR, "record.js"), html_file, safe_name], "Recorder")
                if res_record != 0:
                    add_log(f"[ERROR] Record failed for {lead_name}")
                    continue
                
                # 3. Queue send
                update_lead_status(i, "queuing")
                v_path = os.path.abspath(f"videos/{safe_name}.mp4")
                task = {"index": i, "phone": lead['phone'], "name": lead['name'], "videoPath": v_path}
                
                if safe_queue_add(task):
                    update_lead_status(i, "completed")
                    add_log(f"[MASTER] {lead_name} mission complete.")
                else:
                    add_log(f"[ERROR] Failed to queue {lead_name}")
                
                add_log(f"[MASTER] Pausing for stability...")
                time.sleep(5)
                
            add_log(f"[SUCCESS] Master Automation finished.")
        except Exception as e:
            add_log(f"[ERROR] Master Automation failed: {e}")

    threading.Thread(target=run).start()
    return {"status": "success", "message": "Master Automation started."}

@app.post("/add_lead")
async def add_lead(lead: dict):
    """Add a lead from scraper and trigger auto-mission."""
    try:
        leads = safe_json_read(LEADS_FILE)
        
        # Exact Name Duplicate Check
        if any(l['name'].strip().lower() == lead['name'].strip().lower() for l in leads):
            add_log(f"[SCRAPER] Skipped duplicate: {lead['name']}")
            return {"status": "exists"}

        lead_index = len(leads)
        lead['qualified'] = True 
        lead['status'] = 'discovered'
        leads.append(lead)
        
        if safe_json_write(LEADS_FILE, leads):
            add_log(f"[SCRAPER] New Elite Lead: {lead['name']}... triggering auto-mission.")
            # Standard mission runner (Build -> Record -> Send)
            threading.Thread(target=run_mission_sync, args=(lead_index,), daemon=True).start()
            return {"status": "success", "index": lead_index}
        else:
            raise Exception("Atomic write failure on leads.json")
    except Exception as e:
        add_log(f"[ERROR] Add Lead Failed: {e}")
        return {"status": "error", "message": str(e)}

def run_mission_sync(index):
    # Wrapper for thread to avoid async context issues
    import asyncio
    asyncio.run(run_mission_async(index))

async def run_mission_async(index):
    # This matches the endpoint but is used by the background thread
    await run_mission_logic(index)

async def run_mission_logic(lead_index):
    try:
        leads = safe_json_read(LEADS_FILE)
        if not leads or lead_index >= len(leads): return
        
        lead = leads[lead_index]
        lead_name = lead['name']
        
        add_log(f"[MISSION] 🚀 Starting Elite Mission: {lead_name}")
        
        # 1. Build
        update_lead_status(lead_index, "building")
        res = run_proc_live([sys.executable, "generate_site.py", "--index", str(lead_index)], "Builder")
        if res != 0: raise Exception("Builder failure")

        # 2. Record
        update_lead_status(lead_index, "recording")
        leads = safe_json_read(LEADS_FILE)
        lead = leads[lead_index]
        s_name = lead['name'].replace(" ", "_").replace("/", "_")
        h_file = lead.get('html_file', f"sites/{s_name}.html")
        res = run_proc_live(["node", "record.js", h_file, s_name], "Recorder")
        if res != 0: raise Exception("Recorder failure")

        # 3. Reach
        update_lead_status(lead_index, "queuing")
        v_path = os.path.abspath(f"videos/{s_name}.mp4")
        task = {"index": lead_index, "phone": lead['phone'], "name": lead['name'], "videoPath": v_path}
        if safe_queue_add(task):
            # DO NOT set 'completed' here. The WhatsApp manager will do it upon confirmation.
            add_log(f"[MISSION] 📥 Queued for outreach: {lead_name}")
        else:
            raise Exception("Queue failure")
            
    except Exception as e:
        update_lead_status(lead_index, f"failed: {str(e)}")
        add_log(f"[MISSION] ❌ FAILED for {lead_index}: {e}")

@app.post("/run/{lead_index}")
async def start_manual_mission(lead_index: int):
    threading.Thread(target=run_mission_sync, args=(lead_index,), daemon=True).start()
    return {"status": "success"}
@app.delete("/leads/{index}")
async def delete_lead(index: int):
    leads = get_leads_data()
    if 0 <= index < len(leads):
        removed = leads.pop(index)
        safe_json_write(LEADS_FILE, leads)
        add_log(f"ADMIN: Deleted lead {removed.get('name')}")
        return {"status": "success"}
    return {"status": "error", "message": "Index out of range"}

@app.post("/logs/clear")
async def clear_logs():
    global LOG_QUEUE
    LOG_QUEUE.clear()
    add_log("ADMIN: System logs cleared.")
    return {"status": "success"}

def update_lead_reached_status(index):
    leads = get_leads_data()
    if 0 <= index < len(leads):
        leads[index]["reached"] = True
        safe_json_write(LEADS_FILE, leads)
        add_log(f"DATABASE: Lead at index {index} marked as REACHED.")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    try:
        # Start server on dynamic port
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        with open("critical_error.log", "w") as f:
            f.write(str(e))
        print(f"CRITICAL STARTUP ERROR: {e}")
