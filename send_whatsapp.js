const { Client, MessageMedia, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const QUEUE_FILE = path.join(__dirname, 'outreach_queue.json');
const LEADS_FILE = path.join(__dirname, 'leads.json');
const AUTH_DIR = path.join(__dirname, '.wwebjs_auth');

// ── HARD RESET HANDLER ──────────────────────────────────────────────────
if (process.argv.includes('--reset')) {
    console.log('WHATSAPP: Deleting session data...');
    try {
        if (fs.existsSync(AUTH_DIR)) {
            fs.rmSync(AUTH_DIR, { recursive: true, force: true });
            console.log('WHATSAPP: Session data cleared.');
        } else {
            console.log('WHATSAPP: No session data found to clear.');
        }
    } catch (e) {
        console.error('WHATSAPP_RESET_ERROR:', e.message);
    }
    process.exit(0);
}

(async () => {
    console.log('WHATSAPP: Starting outreach client...');

    // Exact path verified by dir and Test-Path
    const chromePath = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";

    try {
        const client = new Client({
            authStrategy: new LocalAuth(),
            webVersionCache: {
                type: 'remote',
                remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
            },
            puppeteer: {
                headless: 'shell',
                executablePath: chromePath,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            }
        });

        client.on('qr', (qr) => console.log('QR_CODE_START:' + qr + ':QR_CODE_END'));
        client.on('authenticated', () => console.log('WHATSAPP_AUTHENTICATED'));
        client.on('ready', () => {
            console.log('WHATSAPP_READY');
            startQueueListener(client);
        });

        client.initialize().catch(err => {
            console.error('WHATSAPP_INIT_ERROR:', err.message);
            process.exit(1);
        });

    } catch (e) {
        console.error('CRITICAL_STARTUP_ERROR:', e.message);
    }
})();

function startQueueListener(client) {
    console.log('WHATSAPP: Queue listener active.');
    setInterval(async () => {
        if (!fs.existsSync(QUEUE_FILE)) return;
        try {
            // Safe Read
            const data = fs.readFileSync(QUEUE_FILE, 'utf8');
            if (!data || !data.trim()) return;
            const queue = JSON.parse(data);
            
            if (queue.length > 0) {
                const task = queue.shift();
                // Safe Write
                fs.writeFileSync(QUEUE_FILE, JSON.stringify(queue, null, 2));
                console.log(`WHATSAPP_PROCESSING_TASK:${task.name}`);
                await processTask(client, task);
            }
        } catch (e) {
            // Ignore common file access errors during polling
            if (e.code === 'EBUSY' || e.code === 'EPERM') return;
            console.error('Queue Error:', e.message);
        }
    }, 2000); // Poll every 2 seconds
}

async function processTask(client, task) {
    let phone = task.phone;
    let name = task.name;
    let videoPath = task.videoPath;
    let leadIndex = task.index;

    // ── DE-DUPLICATION CHECK ────────────────────────────────────────────────
    try {
        const leads = JSON.parse(fs.readFileSync(LEADS_FILE, 'utf8'));
        const lead = leads[leadIndex];
        if (lead && lead.reached) {
            console.log(`WHATSAPP_SKIP: Lead ${name} already reached. Not sending again.`);
            return;
        }
    } catch (e) {
        console.error('Check Error:', e.message);
    }

    if (leadIndex !== undefined) {
        try {
            const leads = JSON.parse(fs.readFileSync(LEADS_FILE, 'utf8'));
            const lead = leads[leadIndex];
            if (lead) {
                phone = phone || lead.phone;
                name = name || lead.name;
                const safeName = lead.name.replace(/ /g, '_').replace(/\//g, '_');
                videoPath = videoPath || path.join(__dirname, 'videos', `${safeName}.mp4`);
            }
        } catch (e) { console.error('Leads Error:', e.message); }
    }

    if (!phone || !videoPath || !fs.existsSync(videoPath)) {
        console.error('Task Skip: Missing phone or video.', { phone, videoPath });
        return;
    }

    try {
        console.log(`WHATSAPP_DEBUG: Formatting phone: ${phone}`);
        let remoteId = phone.replace(/\D/g, '');
        if (remoteId.startsWith('0') && remoteId.length > 10) remoteId = remoteId.substring(1);
        if (remoteId.length === 10) remoteId = '91' + remoteId;
        if (!remoteId.endsWith('@c.us')) remoteId += '@c.us';

        console.log(`WHATSAPP_DEBUG: Loading media: ${videoPath}`);
        const media = MessageMedia.fromFilePath(videoPath);
        
        // ── NEW NATURAL MESSAGE TEMPLATE ──────────────────────────────────────
        const leads = JSON.parse(fs.readFileSync(LEADS_FILE, 'utf8'));
        const lead = leads[leadIndex] || {};
        const message = buildDefaultMessage(lead);

        await client.sendMessage(remoteId, media, { caption: message });
        console.log(`WHATSAPP_SEND_SUCCESS:${name}:${leadIndex}`);
    } catch (err) {
        console.error('WHATSAPP_SEND_ERROR:', err.message);
    }
}

function buildDefaultMessage(lead) {
    const name = lead.name || 'your business';
    const niche = lead.niche || 'business';
    const city = lead.city || 'your area';

    return `Hi! 👋\n\n` +
           `I was looking up ${niche}s in ${city} on Google and came across *${name}*. \n` +
           `You have amazing reviews — really impressive! ⭐\n\n` +
           `I noticed you don't have a website yet. I went ahead and built a *free demo* \n` +
           `just to show you what it could look like. Check the video above 👆\n\n` +
           `No pressure at all — if you like it and want it live, we can talk. \n` +
           `If not, totally fine too! 😊\n\n` +
           `Interested? Just reply *YES* and I'll share the details.`;
}
