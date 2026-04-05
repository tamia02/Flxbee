const puppeteer = require('puppeteer');
const { PuppeteerScreenRecorder } = require('puppeteer-screen-recorder');
const path = require('path');
const fs = require('fs');
const ffmpeg = require('ffmpeg-static');

async function recordSite(htmlFile, outputName) {
    if (!fs.existsSync(htmlFile)) {
        console.error(`Error: HTML file not found: ${htmlFile}`);
        process.exit(1);
    }
    console.log(`  Recording: ${outputName}`);

    const executablePath = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe";
    console.log(`  Using browser: ${executablePath}`);

    const browser = await puppeteer.launch({
        headless: true,
        executablePath: executablePath,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });

    // Make videos folder
    if (!fs.existsSync('videos')) fs.mkdirSync('videos');

    const recorder = new PuppeteerScreenRecorder(page, {
        followNewTab: false,
        fps: 25,
        ffmpeg_Path: ffmpeg,
        videoFrame: { width: 1280, height: 720 },
        videoCrf: 18,
        videoCodec: 'libx264',
        videoPreset: 'ultrafast',
        autopad: { color: 'black' }
    });

    const videoPath = `videos/${outputName}.mp4`;
    await recorder.start(videoPath);

    // Load the website
    const fullPath = path.resolve(htmlFile);
    await page.goto(`file://${fullPath}`, { waitUntil: 'networkidle0' });

    // Wait for page to fully load
    await new Promise(r => setTimeout(r, 2000));

    // Hover over navigation items
    try {
        const navLinks = await page.$$('nav a');
        for (const link of navLinks.slice(0, 4)) {
            await link.hover();
            await new Promise(r => setTimeout(r, 500));
        }
    } catch (e) { }

    // Smooth scroll down slowly (like a human showing off the site)
    await page.evaluate(async () => {
        await new Promise(r => {
            let y = 0;
            const pageHeight = document.body.scrollHeight - window.innerHeight;
            const timer = setInterval(() => {
                window.scrollBy(0, 3);
                y += 3;
                if (y >= pageHeight) {
                    clearInterval(timer);
                    r();
                }
            }, 25); // scroll every 25ms = smooth
        });
    });

    // Wait at bottom
    await new Promise(r => setTimeout(r, 1500));

    // Scroll back to top
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
    await new Promise(r => setTimeout(r, 1500));

    await recorder.stop();
    await browser.close();

    console.log(`  Video saved: ${videoPath}`);
    return videoPath;
}

// Run from command line: node record.js "sites/Sharma_Dental.html" "Sharma_Dental"
const htmlFile = process.argv[2];
const outputName = process.argv[3];

if (htmlFile && outputName) {
    recordSite(htmlFile, outputName).catch(console.error);
} else {
    console.log('Usage: node record.js <html-file> <output-name>');
}
