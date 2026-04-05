const { Client, MessageMedia, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');
const path = require('path');

const QUEUE_FILE = path.join(__dirname, 'outreach_queue.json');
const LEADS_FILE = path.join(__dirname, 'leads.json');

// Session Reset Logic
if (process.argv.includes('--reset')) {
    const authPath = path.join(__dirname, '.wwebjs_auth');
    if (fs.existsSync(authPath)) {
        console.log('WHATSAPP: Resetting session... deleting ' + authPath);
        fs.rmSync(authPath, { recursive: true, force: true });
        console.log('WHATSAPP_RESET_COMPLETE');
    }
}

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        executablePath: "C:\\Users\\tasmi\\.cache\\puppeteer\\chrome\\win64-121.0.6167.85\\chrome-win64\\chrome.exe",
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', (qr) => console.log('QR_CODE_START:' + qr + ':QR_CODE_END'));
client.on('authenticated', () => console.log('WHATSAPP_AUTHENTICATED'));
client.on('ready', async () => {
    console.log('WHATSAPP_READY');
    startQueueListener();
});

async function startQueueListener() {
    console.log('WHATSAPP: Queue listener active.');
    setInterval(async () => {
        if (fs.existsSync(QUEUE_FILE)) {
            try {
                const queue = JSON.parse(fs.readFileSync(QUEUE_FILE, 'utf8'));
                if (queue.length > 0) {
                    const task = queue.shift();
                    fs.writeFileSync(QUEUE_FILE, JSON.stringify(queue, null, 2));
                    await processTask(task);
                }
            } catch (e) {
                console.error('Queue Error:', e.message);
            }
        }
    }, 2000);
}

async function processTask(task) {
    let phone = task.phone;
    let name = task.name;
    let videoPath = task.videoPath;

    // Fallback to leads.json if only index is provided
    if (task.index !== undefined) {
        try {
            const leads = JSON.parse(fs.readFileSync(LEADS_FILE, 'utf8'));
            const lead = leads[task.index];
            if (lead) {
                phone = phone || lead.phone;
                name = name || lead.name;
                const safeName = lead.name.replace(/ /g, '_').replace(/\//g, '_');
                videoPath = videoPath || path.join(__dirname, 'videos', `${safeName}.mp4`);
            }
        } catch (e) {
            console.error('Leads File Error:', e.message);
        }
    }

    if (!phone || !videoPath || !fs.existsSync(videoPath)) {
        console.error('Task Error: Missing phone or video file.', { phone, videoPath });
        return;
    }

    try {
        console.log(`Sending to ${name} (${phone})...`);
        const media = MessageMedia.fromFilePath(videoPath);
        let remoteId = phone.replace(/\D/g, '');
        if (remoteId.length === 10) remoteId = '91' + remoteId;
        remoteId += '@c.us';

        const message = `Hi! 👋

I noticed *${name}* doesn't have a website yet.
I built this *free demo* — check it out! 👆

Interested? Just reply YES! 😊`;

        await client.sendMessage(remoteId, media, { caption: message });
        console.log('WHATSAPP_SEND_SUCCESS');
    } catch (err) {
        console.error('WHATSAPP_SEND_ERROR:', err.message);
    }
}

client.initialize();
