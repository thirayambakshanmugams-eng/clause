/**
 * ClauseGuard — Localhost Landing Page & App Server
 * Pure Node.js standard library (no external npm dependencies required)
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 5000;
const BASE_DIR = __dirname;

const MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.ttf': 'font/ttf'
};

const server = http.createServer((req, res) => {
    const parsedUrl = new URL(req.url, `http://localhost:${PORT}`);
    let reqPath = decodeURI(parsedUrl.pathname);

    // ── Authentication POST Handling ─────────────────────────────
    if (req.method === 'POST' && (reqPath === '/login' || reqPath === '/register' || reqPath === '/signin')) {
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', () => {
            console.log(`[Auth] ${req.method} ${reqPath} received, redirecting to /app dashboard...`);
            
            // Check if JSON request
            const acceptHeader = req.headers['accept'] || '';
            const contentType = req.headers['content-type'] || '';
            if (acceptHeader.includes('application/json') || contentType.includes('application/json')) {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true, redirect: '/app' }));
                return;
            }

            // Standard HTML form submission -> Redirect 302 to /app
            res.writeHead(302, {
                'Location': '/app',
                'Set-Cookie': 'cg_session=1; Path=/; HttpOnly; Max-Age=28800'
            });
            res.end();
        });
        return;
    }

    // ── GET Route Handling ───────────────────────────────────────
    if (reqPath === '/' || reqPath === '/landing' || reqPath === '/login' || reqPath === '/register') {
        const filePath = path.join(BASE_DIR, 'templates', 'login.html');
        fs.readFile(filePath, 'utf8', (err, data) => {
            if (err) {
                res.writeHead(500, { 'Content-Type': 'text/plain' });
                res.end('Error loading landing page: ' + err.message);
                return;
            }
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(data);
        });
        return;
    }

    if (reqPath === '/signin') {
        const filePath = path.join(BASE_DIR, 'templates', 'signin.html');
        fs.readFile(filePath, 'utf8', (err, data) => {
            if (err) {
                res.writeHead(500, { 'Content-Type': 'text/plain' });
                res.end('Error loading sign in: ' + err.message);
                return;
            }
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(data);
        });
        return;
    }

    if (reqPath === '/logout') {
        res.writeHead(302, {
            'Location': '/',
            'Set-Cookie': 'cg_session=; Path=/; Max-Age=0'
        });
        res.end();
        return;
    }

    if (reqPath === '/app' || reqPath === '/dashboard') {
        const filePath = path.join(BASE_DIR, 'templates', 'index.html');
        fs.readFile(filePath, 'utf8', (err, data) => {
            if (err) {
                res.writeHead(500, { 'Content-Type': 'text/plain' });
                res.end('Error loading dashboard: ' + err.message);
                return;
            }
            // Safely sanitize Jinja template tags so the dashboard runs in Node
            let safeData = data
                .replace(/\{\{\s*session\.get\('user_id',\s*0\)\s*\|\s*tojson\s*\}\}/g, '1')
                .replace(/\{\{\s*session\.get\('user',\s*''\)\s*\|\s*tojson\s*\}\}/g, '"admin"')
                .replace(/\{\{\s*session\.get\('email',\s*''\)\s*\|\s*tojson\s*\}\}/g, '"admin@clauseguard.io"')
                .replace(/\{%\s*if\s+[\s\S]*?%\}/g, '')
                .replace(/\{%\s*endif\s*%\}/g, '')
                .replace(/\{\{[\s\S]*?\}\}/g, '""');

            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(safeData);
        });
        return;
    }

    if (reqPath === '/3d') {
        const filePath = path.join(BASE_DIR, 'templates', 'landing_3d.html');
        fs.readFile(filePath, 'utf8', (err, data) => {
            if (err) {
                res.writeHead(500, { 'Content-Type': 'text/plain' });
                res.end('Error loading 3D showcase: ' + err.message);
                return;
            }
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(data);
        });
        return;
    }

    // ── Static Assets ────────────────────────────────────────────
    if (reqPath.startsWith('/static/')) {
        const safePath = path.normalize(reqPath).replace(/^(\.\.[\/\\])+/, '');
        const filePath = path.join(BASE_DIR, safePath);
        const ext = path.extname(filePath).toLowerCase();

        fs.readFile(filePath, (err, data) => {
            if (err) {
                res.writeHead(404, { 'Content-Type': 'text/plain' });
                res.end('404 Not Found');
                return;
            }
            res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
            res.end(data);
        });
        return;
    }

    // ── Mock API fallback for local dev ──────────────────────────
    if (reqPath.startsWith('/api/')) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, message: 'Local development mock response' }));
        return;
    }

    // ── Fallback 404 ─────────────────────────────────────────────
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('404 Not Found: ' + reqPath);
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`\n======================================================`);
    console.log(`✨ ClauseGuard Server Running on Localhost!`);
    console.log(`👉 Landing Page: http://localhost:${PORT}`);
    console.log(`👉 Dashboard App: http://localhost:${PORT}/app`);
    console.log(`👉 3D Showcase: http://localhost:${PORT}/3d`);
    console.log(`======================================================\n`);
});
