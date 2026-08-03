// ClauseGuard Premium Application Logic

const API = {
    upload: '/api/upload',
    explain: '/api/explain',
    settings: '/api/settings',
    health: '/api/health',
    chat: '/api/chat',
    report: '/api/report'
};

class ClauseGuard {
    constructor() {
        this.results = null;
        this.selectedFiles = []; // Now supporting multiple files correctly
        this.docId = null;
        this.history = [];
        this.init();
    }

    init() {
        this.cacheDOM();
        this.bindEvents();
        this.initDragDrop();
        this.checkHealth();
        this.initTheme();
        this.loadHistory();
    }

    cacheDOM() {
        // Sidebar & Mobile
        this.sidebar = document.getElementById('sidebar');
        this.btnMobileMenu = document.getElementById('btn-mobile-menu');
        this.btnNewAnalysis = document.getElementById('btn-new-analysis');
        this.btnSidebarCollapse = document.getElementById('btn-sidebar-collapse');
        
        // Navigation / Modals
        this.btnOpenDataset = document.getElementById('btn-open-dataset');
        this.btnOpenSettings = document.getElementById('btn-open-settings');
        
        // Theme toggles (Top Bar & Mobile)
        this.btnThemeToggle = document.getElementById('btn-theme-toggle');
        this.btnThemeToggleMobile = document.getElementById('btn-theme-toggle-mobile');
        
        this.datasetModal = document.getElementById('dataset-modal');
        this.settingsModal = document.getElementById('settings-modal');
        this.datasetClose = document.getElementById('dataset-close');
        this.settingsClose = document.getElementById('settings-close');
        
        // Settings elements
        this.apiKeyInput = document.getElementById('api-key-input');
        this.btnToggleKey = document.getElementById('btn-toggle-key');
        this.btnSaveKey = document.getElementById('btn-save-key');
        this.llmStatus = document.getElementById('sb-llm-status');
        
        // Panels
        this.panelLanding = document.getElementById('panel-landing');
        this.panelProcessing = document.getElementById('panel-processing');
        this.panelResults = document.getElementById('panel-results');
        
        // Upload elements
        this.uploadBar = document.getElementById('upload-bar');
        this.fileInput = document.getElementById('file-input');
        this.ubText = document.getElementById('ub-text');
        this.ubFile = document.getElementById('ub-file');
        this.btnAnalyze = document.getElementById('btn-analyze');
        this.userPrompt = document.getElementById('user-prompt');
        
        // Processing elements
        this.procTitle = document.getElementById('proc-title');
        this.procSub = document.getElementById('proc-sub');
        this.procBar = document.getElementById('proc-bar');
        this.pDots = [document.getElementById('pd-1'), document.getElementById('pd-2'), document.getElementById('pd-3')];
        
        // Results elements
        this.resFilename = document.getElementById('res-filename');
        this.resWordcount = document.getElementById('res-wordcount');
        this.resSummaryText = document.getElementById('res-summary-text');
        this.stTotal = document.getElementById('stat-total');
        this.stHigh = document.getElementById('stat-high');
        this.stMed = document.getElementById('stat-med');
        this.stLow = document.getElementById('stat-low');
        this.rsH = document.getElementById('rs-h');
        this.rsM = document.getElementById('rs-m');
        this.rsL = document.getElementById('rs-l');
        
        // Action Buttons in Results
        this.btnDownloadReport = document.getElementById('btn-download-report');
        this.btnBackHome = document.getElementById('btn-back-home');
        
        // Filter & List
        this.filterBtns = document.querySelectorAll('.fbtn');
        this.cardList = document.getElementById('card-list');
        this.cardTpl = document.getElementById('card-tpl');
        
        // Chat UI
        this.chatFab = document.getElementById('chat-fab');
        this.chatWindow = document.getElementById('chat-window');
        this.chatClose = document.getElementById('chat-close');
        this.chatBody = document.getElementById('chat-body');
        this.chatInput = document.getElementById('chat-input');
        this.chatSend = document.getElementById('chat-send');
        
        // Toast
        this.toastArea = document.getElementById('toast-area');
    }

    bindEvents() {
        // Mobile menu
        if (this.btnMobileMenu) {
            this.btnMobileMenu.addEventListener('click', () => {
                this.sidebar.classList.toggle('open');
            });
        }
        
        // Sidebar collapse
        if (this.btnSidebarCollapse) {
            this.btnSidebarCollapse.addEventListener('click', () => {
                this.sidebar.classList.toggle('collapsed');
                localStorage.setItem('sidebarCollapsed', this.sidebar.classList.contains('collapsed'));
            });
            if (localStorage.getItem('sidebarCollapsed') === 'true') {
                this.sidebar.classList.add('collapsed');
            }
        }
        
        // Nav actions
        if (this.btnNewAnalysis) this.btnNewAnalysis.addEventListener('click', () => this.resetApp());
        if (this.btnBackHome) this.btnBackHome.addEventListener('click', () => this.resetApp());
        
        // Modals
        if (this.btnOpenDataset) this.btnOpenDataset.addEventListener('click', () => this.openModal(this.datasetModal));
        if (this.btnOpenSettings) this.btnOpenSettings.addEventListener('click', () => this.openModal(this.settingsModal));
        if (this.datasetClose) this.datasetClose.addEventListener('click', () => this.closeModal(this.datasetModal));
        if (this.settingsClose) this.settingsClose.addEventListener('click', () => this.closeModal(this.settingsModal));
        
        [this.datasetModal, this.settingsModal].forEach(m => {
            m.addEventListener('click', (e) => {
                if (e.target === m) this.closeModal(m);
            });
        });
        
        // Theme toggle
        if (this.btnThemeToggle) this.btnThemeToggle.addEventListener('click', () => this.toggleTheme());
        if (this.btnThemeToggleMobile) this.btnThemeToggleMobile.addEventListener('click', () => this.toggleTheme());
        
        // Settings logic
        this.btnToggleKey.addEventListener('click', () => {
            this.apiKeyInput.type = this.apiKeyInput.type === 'password' ? 'text' : 'password';
        });
        this.btnSaveKey.addEventListener('click', () => this.saveSettings());
        
        // File selection
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.btnAnalyze.addEventListener('click', () => this.startAnalysis());
        
        // Report generation
        if (this.btnDownloadReport) {
            this.btnDownloadReport.addEventListener('click', () => this.generateReport());
        }
        
        // Filter logic
        this.filterBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.filterResults(btn.dataset.filter);
            });
        });
        
        // Chat logic
        this.chatFab.addEventListener('click', () => {
            this.chatWindow.classList.remove('hidden');
            this.chatFab.classList.add('hidden');
            this.chatInput.focus();
        });
        
        this.chatClose.addEventListener('click', () => {
            this.chatWindow.classList.add('hidden');
            this.chatFab.classList.remove('hidden');
        });
        
        this.chatSend.addEventListener('click', () => this.sendChatMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendChatMessage();
        });
    }

    initDragDrop() {
        const bar = this.uploadBar;
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev => {
            bar.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); });
        });
        ['dragenter', 'dragover'].forEach(ev => {
            bar.addEventListener(ev, () => bar.classList.add('dragover'));
        });
        ['dragleave', 'drop'].forEach(ev => {
            bar.addEventListener(ev, () => bar.classList.remove('dragover'));
        });
        bar.addEventListener('drop', (e) => {
            if (e.dataTransfer.files.length) {
                this.processFileSelection(Array.from(e.dataTransfer.files));
            }
        });
    }

    handleFileSelect(e) {
        if (e.target.files.length) {
            this.processFileSelection(Array.from(e.target.files));
        }
    }

    processFileSelection(files) {
        // For now, take the first valid file or multiple if needed
        const validFiles = files.filter(file => {
            const ext = '.' + file.name.split('.').pop().toLowerCase();
            return ['.pdf', '.docx', '.txt'].includes(ext) && file.size <= 16 * 1024 * 1024;
        });

        if (validFiles.length === 0) {
            return this.toast('Invalid format or size. Use PDF, DOCX, TXT under 16MB.', 'error');
        }

        this.selectedFiles = validFiles;
        this.ubText.classList.add('hidden');
        
        if (this.selectedFiles.length === 1) {
            this.ubFile.innerHTML = `<span class="file-chip">${this.selectedFiles[0].name} <span class="chip-remove" title="Remove">&times;</span></span>`;
        } else {
            this.ubFile.innerHTML = `<span class="file-chip">${this.selectedFiles.length} files selected <span class="chip-remove" title="Remove">&times;</span></span>`;
        }
        
        this.ubFile.classList.remove('hidden');
        this.btnAnalyze.disabled = false;

        this.ubFile.querySelector('.chip-remove').addEventListener('click', (e) => {
            e.stopPropagation();
            this.resetUpload();
        });
    }

    resetUpload() {
        this.selectedFiles = [];
        this.fileInput.value = '';
        this.ubText.classList.remove('hidden');
        this.ubFile.classList.add('hidden');
        this.btnAnalyze.disabled = true;
    }

    async startAnalysis() {
        if (this.selectedFiles.length === 0) return;

        this.showPanel('processing');
        this.animateProcessing();

        const promptText = this.userPrompt.value.trim();
        this.allDocResults = [];

        try {
            // Send ALL files in a single request
            const fd = new FormData();
            this.selectedFiles.forEach(file => fd.append('document', file));
            if (promptText) fd.append('user_prompt', promptText);

            const res  = await fetch(API.upload, { method: 'POST', body: fd });
            if (!res.ok) {
                let errorMsg = `Server error (${res.status}).`;
                try {
                    const errData = await res.json();
                    if (errData.error) errorMsg = errData.error;
                } catch(e) {}
                this.toast(errorMsg, 'error');
                this.resetApp();
                return;
            }
            const data = await res.json();

            if (!data.success) {
                this.toast(data.error || 'Analysis failed.', 'error');
                this.resetApp();
                return;
            }

            // Multi-doc response
            if (data.multi && data.documents) {
                this.allDocResults = data.documents;
                if (data.failed && data.failed.length > 0) {
                    data.failed.forEach(f => this.toast(`✗ ${f.filename}: ${f.error}`, 'error'));
                }
            } else {
                // Single doc: legacy flat format
                this.allDocResults = [data];
            }

            if (this.allDocResults.length === 0) {
                this.toast('No documents were analyzed successfully.', 'error');
                this.resetApp();
                return;
            }

            // Save the entire batch as a single history item
            this.saveToHistory(this.allDocResults);

            // Show results
            const primary = this.allDocResults[0];
            this.results = primary;
            setTimeout(() => this.renderResults(primary), 1500);
        } catch (e) {
            console.error(e);
            this.toast('Network error during analysis.', 'error');
            this.resetApp();
        }
    }

    animateProcessing() {
        this.procBar.style.width = '0%';
        this.pDots.forEach(d => d.className = 'pd');
        
        this.pDots[0].classList.add('active');
        this.procTitle.textContent = 'Dissecting document…';
        this.procSub.textContent = 'Extracting structural layout and text securely';
        setTimeout(() => this.procBar.style.width = '35%', 100);
        
        setTimeout(() => {
            this.pDots[0].className = 'pd done';
            this.pDots[1].classList.add('active');
            this.procTitle.textContent = 'Analyzing risk patterns…';
            this.procSub.textContent = 'Running Playbook alignment and NLP models';
            this.procBar.style.width = '70%';
        }, 1500);
        
        setTimeout(() => {
            this.pDots[1].className = 'pd done';
            this.pDots[2].classList.add('active');
            this.procTitle.textContent = 'Finalizing insights…';
            this.procSub.textContent = 'Generating comprehensive risk report';
            this.procBar.style.width = '90%';
        }, 3000);
    }

    renderResults(data) {
        this.pDots[2].className = 'pd done';
        this.procBar.style.width = '100%';

        const allDocs = (this.allDocResults && this.allDocResults.length > 0) ? this.allDocResults : [data];
        const isMulti = allDocs.length > 1;

        setTimeout(() => {
            this.showPanel('results');

            if (isMulti) {
                // ── MULTI-DOC SUMMARY PAGE ──────────────────────────────
                const totalClauses = allDocs.reduce((s,d) => s + (d.total_clauses||0), 0);
                const totalHigh    = allDocs.reduce((s,d) => s + (d.summary?.high_risk||0), 0);
                const totalMed     = allDocs.reduce((s,d) => s + (d.summary?.medium_risk||0), 0);
                const totalLow     = allDocs.reduce((s,d) => s + (d.summary?.low_risk||0), 0);

                // Header: show count of docs
                this.resFilename.textContent = `${allDocs.length} Documents Analyzed`;
                this.resWordcount.textContent = `${totalClauses} total clauses across all documents`;

                // Overall summary box
                const execBox = this.resSummaryText.parentElement;
                execBox.classList.remove('hidden');
                this.resSummaryText.innerHTML = allDocs.map((d, i) => {
                    const h = d.summary?.high_risk || 0;
                    const m = d.summary?.medium_risk || 0;
                    const dotColor = h > 0 ? 'var(--high)' : (m > 0 ? 'var(--med)' : 'var(--low)');
                    const verdict  = h > 0 ? 'HIGH RISK' : (m > 0 ? 'MEDIUM RISK' : 'LOW RISK');
                    return `<div style="border:1.5px solid #e0e0e0;border-left:4px solid ${dotColor};border-radius:6px;padding:12px 16px;margin-bottom:10px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                            <strong style="font-size:13px;">${i+1}. ${d.filename}</strong>
                            <span style="font-size:10px;font-weight:700;text-transform:uppercase;background:${dotColor};color:#fff;padding:2px 10px;border-radius:20px;">${verdict}</span>
                        </div>
                        <div style="font-size:12px;color:#555;">${d.document_summary_text || ''}</div>
                    </div>`;
                }).join('');

                // Breakdown
                const breakdownDiv = document.getElementById('res-summary-breakdown');
                if (breakdownDiv) {
                    breakdownDiv.innerHTML = `
                        <div class="breakdown-item"><strong>Total Clauses</strong><span>${totalClauses}</span></div>
                        <div class="breakdown-item"><strong>High Risk</strong><span style="color:var(--high);">${totalHigh}</span></div>
                        <div class="breakdown-item"><strong>Medium Risk</strong><span style="color:var(--med);">${totalMed}</span></div>
                        <div class="breakdown-item"><strong>Low Risk</strong><span style="color:var(--low);">${totalLow}</span></div>
                    `;
                }

                // Stats animation (combined)
                this.animateCount(this.stTotal, totalClauses);
                this.animateCount(this.stHigh,  totalHigh);
                this.animateCount(this.stMed,   totalMed);
                this.animateCount(this.stLow,   totalLow);
                const tot = totalClauses || 1;
                this.rsH.style.width = `${(totalHigh / tot) * 100}%`;
                this.rsM.style.width = `${(totalMed  / tot) * 100}%`;
                this.rsL.style.width = `${(totalLow  / tot) * 100}%`;

                // Obligations: combine all docs
                const obContainer = document.getElementById('obligations-summary');
                const allObs = allDocs.flatMap(d => d.obligations || []);
                if (allObs.length > 0) {
                    const obList = document.getElementById('obligations-list');
                    obList.innerHTML = '';
                    allObs.forEach(ob => {
                        const li = document.createElement('li');
                        li.className = 'obligation-item';
                        li.innerHTML = `<strong>${ob.title}</strong>: ${ob.description}<br>
                        <span class="ob-meta">📅 <strong>${ob.timeline}</strong> | 👤 ${ob.responsible_party}</span>`;
                        obList.appendChild(li);
                    });
                    obContainer.classList.remove('hidden');
                } else {
                    if (obContainer) obContainer.classList.add('hidden');
                }

                // Clause cards: show per-document sections
                this.cardList.innerHTML = '';
                allDocs.forEach((d, docIdx) => {
                    // Doc separator heading
                    const hdr = document.createElement('div');
                    hdr.style.cssText = 'margin:24px 0 10px;padding:12px 18px;background:#1a2530;color:#fff;border-radius:6px;font-weight:800;font-size:14px;letter-spacing:.4px;border-left:4px solid #4a9eff;';
                    hdr.textContent = `Document ${docIdx+1}: ${d.filename}`;
                    this.cardList.appendChild(hdr);

                    // Sort clauses high→low
                    const riskOrder = { high:3, medium:2, low:1 };
                    const sorted = [...(d.clauses||[])].sort((a,b) => (riskOrder[b.risk_level]||0)-(riskOrder[a.risk_level]||0));
                    sorted.forEach((c, i) => {
                        const el = this.buildCard(c);
                        el.style.animationDelay = `${i * 0.04}s`;
                        this.cardList.appendChild(el);
                    });
                });

                this.docId = allDocs[0].doc_id;

            } else {
                // ── SINGLE DOC (original behaviour) ────────────────────
                this.resFilename.textContent = data.filename;
                this.resWordcount.textContent = `${data.document_info.word_count.toLocaleString()} words · ${data.document_info.char_count.toLocaleString()} characters`;

                if (data.document_summary_text) {
                    this.resSummaryText.innerHTML = data.document_summary_text;
                    this.resSummaryText.parentElement.classList.remove('hidden');
                    const breakdownDiv = document.getElementById('res-summary-breakdown');
                    if (breakdownDiv) {
                        breakdownDiv.innerHTML = `
                            <div class="breakdown-item"><strong>Total Clauses</strong><span>${data.total_clauses}</span></div>
                            <div class="breakdown-item"><strong>High Risk</strong><span style="color:var(--high);">${data.summary.high_risk}</span></div>
                            <div class="breakdown-item"><strong>Medium Risk</strong><span style="color:var(--med);">${data.summary.medium_risk}</span></div>
                            <div class="breakdown-item"><strong>Low Risk</strong><span style="color:var(--low);">${data.summary.low_risk}</span></div>
                        `;
                    }
                } else {
                    this.resSummaryText.parentElement.classList.add('hidden');
                }

                const obContainer = document.getElementById('obligations-summary');
                if (data.obligations && data.obligations.length > 0) {
                    const obList = document.getElementById('obligations-list');
                    obList.innerHTML = '';
                    data.obligations.forEach(ob => {
                        const li = document.createElement('li');
                        li.className = 'obligation-item';
                        li.innerHTML = `<strong>${ob.title}</strong>: ${ob.description}<br>
                        <span class="ob-meta">📅 <strong>${ob.timeline}</strong> | 👤 ${ob.responsible_party}</span>`;
                        obList.appendChild(li);
                    });
                    obContainer.classList.remove('hidden');
                } else {
                    if (obContainer) obContainer.classList.add('hidden');
                }

                this.docId = data.doc_id;
                this.animateCount(this.stTotal, data.total_clauses);
                this.animateCount(this.stHigh,  data.summary.high_risk);
                this.animateCount(this.stMed,   data.summary.medium_risk);
                this.animateCount(this.stLow,   data.summary.low_risk);
                const tot = data.total_clauses || 1;
                this.rsH.style.width = `${(data.summary.high_risk / tot) * 100}%`;
                this.rsM.style.width = `${(data.summary.medium_risk / tot) * 100}%`;
                this.rsL.style.width = `${(data.summary.low_risk  / tot) * 100}%`;

                this.cardList.innerHTML = '';
                data.clauses.forEach((c, i) => {
                    const el = this.buildCard(c);
                    el.style.animationDelay = `${i * 0.05}s`;
                    this.cardList.appendChild(el);
                });
                this.cardList.querySelectorAll('.cc-explain-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => this.explainClause(e.currentTarget));
                });
            }

            this.chatFab.classList.remove('hidden');
            // Attach explain listeners for all cards
            this.cardList.querySelectorAll('.cc-explain-btn').forEach(btn => {
                btn.addEventListener('click', (e) => this.explainClause(e.currentTarget));
            });

        }, 500);
    }

    buildCard(clause) {
        const clone = this.cardTpl.content.cloneNode(true);
        const card = clone.querySelector('.clause-card');
        
        card.dataset.id = clause.id;
        card.dataset.risk = clause.risk_level;
        card.classList.add(`risk-${clause.risk_level}`);
        
        card.querySelector('.cc-badge').textContent = `${clause.risk_level} risk`;
        card.querySelector('.cc-section-name').textContent = clause.section_header || `Clause ${clause.id + 1}`;
        card.querySelector('.cc-score-label').textContent = `Score: ${clause.risk_score}/100`;
        
        let txt = clause.text;
        if (clause.keywords) {
            clause.keywords.forEach(kw => {
                const rx = new RegExp(`\\b${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
                const cls = clause.risk_level === 'high' ? 'hl-high' : 'hl-med';
                txt = txt.replace(rx, `<span class="${cls}">$&</span>`);
            });
        }
        card.querySelector('.cc-body-text').innerHTML = txt;
        
        const catBox = card.querySelector('.cc-categories');
        (clause.risk_categories || []).forEach(cat => {
            const sp = document.createElement('span');
            sp.className = 'cc-cat';
            sp.textContent = cat;
            catBox.appendChild(sp);
        });
        
        if (clause.playbook_violations && clause.playbook_violations.length > 0) {
            const pbBox = document.createElement('div');
            pbBox.className = 'pb-violations';
            clause.playbook_violations.forEach(v => {
                const vDiv = document.createElement('div');
                vDiv.className = 'pb-violation-item';
                vDiv.innerHTML = `<div class="pb-v-title">⚠️ Playbook Violation: ${v.rule_id} - ${v.category}</div>
                <div class="pb-v-desc">${v.explanation}</div>
                <div class="pb-v-alt"><strong>Suggested Alternative:</strong> ${v.alternative_text}</div>`;
                pbBox.appendChild(vDiv);
            });
            card.querySelector('.cc-body-text').insertAdjacentElement('afterend', pbBox);
        }
        
        card.querySelector('.cc-bar-fill').style.width = `${clause.risk_score}%`;
        card.querySelector('.cc-explain-btn').dataset.id = clause.id;
        
        return card;
    }

    async explainClause(btn) {
        const id = btn.dataset.id;
        const clause = this.results.clauses.find(c => c.id == id);
        if (!clause) return;
        
        const card = btn.closest('.clause-card');
        const expBox = card.querySelector('.cc-explanation');
        
        if (!expBox.classList.contains('hidden') && expBox.dataset.loaded) {
            expBox.classList.toggle('hidden');
            btn.textContent = expBox.classList.contains('hidden') ? 'Explain in plain English ✨' : 'Hide Explanation';
            return;
        }
        
        btn.textContent = 'Generating...';
        btn.disabled = true;
        
        try {
            const res = await fetch(API.explain, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    clause_text: clause.text,
                    risk_level: clause.risk_level,
                    risk_categories: clause.risk_categories
                })
            });
            const data = await res.json();
            
            if (data.success !== false) {
                expBox.classList.remove('hidden');
                expBox.dataset.loaded = 'true';
                btn.textContent = 'Hide Explanation';
                btn.disabled = false;
                
                this.typeWrite(expBox.querySelector('.ex-means'), data.what_it_means);
                setTimeout(() => this.typeWrite(expBox.querySelector('.ex-risky'), data.why_risky), 700);
                setTimeout(() => this.typeWrite(expBox.querySelector('.ex-action'), data.what_to_do), 1400);
            } else {
                this.toast(data.error || 'Failed to explain.', 'error');
                btn.textContent = 'Explain in plain English ✨';
                btn.disabled = false;
            }
        } catch (e) {
            this.toast('Network error during explanation.', 'error');
            btn.textContent = 'Explain in plain English ✨';
            btn.disabled = false;
        }
    }

    async generateReport() {
        const allDocs = (this.allDocResults && this.allDocResults.length > 0)
                            ? this.allDocResults
                            : (this.results ? [this.results] : []);
        if (allDocs.length === 0) { this.toast('No analysis data to export.', 'error'); return; }

        this.btnDownloadReport.disabled = true;
        this.btnDownloadReport.innerHTML = `<span class="spinner"></span> Generating PDF...`;

        try {
            const generatedAt = new Date().toUTCString();
            // allDocs is already declared above — use it directly

            const riskCatExplain = {
                'Indemnification':       'You may be required to cover the other party\'s legal costs or damages.',
                'Unlimited Liability':   'There is no cap on how much money you could owe if something goes wrong.',
                'Auto Renewal':          'The contract will renew automatically unless you cancel in time.',
                'Non-Compete':           'You may be restricted from working in a similar business after this contract ends.',
                'IP Assignment':         'Your creative work or inventions may become the other party\'s property.',
                'Unilateral Termination':'Only the other party can end this contract — you may not be able to exit.',
                'Rights Waiver':         'You may be giving up important legal rights or protections.',
                'Penalty Clauses':       'You could face large financial penalties for minor or accidental violations.',
                'Perpetual Terms':       'Some obligations in this contract last forever, even after it ends.',
                'Data Rights':           'The other party may control or keep your data indefinitely.',
                'Force Majeure':         'Circumstances beyond anyone\'s control could affect obligations.',
                'Arbitration':           'Disputes must be resolved through arbitration, not court.',
                'Governing Law':         'A specific jurisdiction\'s law governs this contract.',
                'Payment Terms':         'There are specific rules about when and how payments are made.',
                'Confidentiality':       'You must keep certain information private, possibly indefinitely.',
            };
            const levelColor = { high: '#c0392b', medium: '#e67e22', low: '#27ae60' };
            const levelBg    = { high: '#fdf0ef', medium: '#fef5e4', low: '#eafaf1' };

            // ── Helper: build one document section HTML ───────────────────
            const buildDocSection = (data, docNum, totalDocs) => {
                const filename    = data.filename  || 'contract';
                const summary     = data.summary   || {};
                const clauses     = data.clauses   || [];
                const obligations = data.obligations || [];
                const high  = summary.high_risk  || 0;
                const med   = summary.medium_risk || 0;
                const low   = summary.low_risk   || 0;
                const total = data.total_clauses || 0;

                const riskColor = high > 0 ? '#c0392b' : (med > 0 ? '#e67e22' : '#27ae60');
                const riskLabel = high > 0 ? 'HIGH RISK' : (med > 0 ? 'MEDIUM RISK' : 'LOW RISK');

                // Bullet summary
                const highClauses = clauses.filter(c => c.risk_level === 'high');
                const medClauses  = clauses.filter(c => c.risk_level === 'medium');
                const foundHighCats = [...new Set(highClauses.flatMap(c => c.risk_categories || []))].slice(0, 5);
                const foundMedCats  = [...new Set(medClauses.flatMap(c  => c.risk_categories || []))].slice(0, 4);

                const bullets = [];
                if (high > 0) bullets.push(`<li style="margin-bottom:7px;color:#c0392b;"><strong>${high} High-Risk Clause${high>1?'s':''}</strong> &mdash; Requires immediate attention.</li>`);
                if (med  > 0) bullets.push(`<li style="margin-bottom:7px;color:#b7590a;"><strong>${med} Medium-Risk Clause${med>1?'s':''}</strong> &mdash; Review recommended.</li>`);
                if (low  > 0) bullets.push(`<li style="margin-bottom:7px;color:#1a7340;"><strong>${low} Low-Risk Clause${low>1?'s':''}</strong> &mdash; Appear standard.</li>`);
                foundHighCats.forEach(cat => {
                    const exp = riskCatExplain[cat] || `Involves ${cat} language.`;
                    bullets.push(`<li style="margin-bottom:7px;"><strong>${cat}:</strong> ${exp}</li>`);
                });
                foundMedCats.forEach(cat => {
                    if (!foundHighCats.includes(cat)) {
                        const exp = riskCatExplain[cat] || `Involves ${cat} language.`;
                        bullets.push(`<li style="margin-bottom:7px;"><strong>${cat}:</strong> ${exp}</li>`);
                    }
                });
                if (high === 0 && med === 0) bullets.push(`<li style="margin-bottom:7px;color:#1a7340;">No significant risk patterns detected. Document appears balanced.</li>`);

                const actionLine = high > 0
                    ? `<div style="background:#fff;border:1px solid #c0392b;border-left:4px solid #c0392b;border-radius:4px;padding:12px 14px;margin-top:12px;font-size:12px;color:#333;"><strong style="color:#c0392b;text-transform:uppercase;letter-spacing:0.5px;">Primary Recommendation:</strong> Do not proceed until high-risk clauses are reviewed and negotiated. Legal consultation is advised.</div>`
                    : med > 0
                    ? `<div style="background:#fff;border:1px solid #e67e22;border-left:4px solid #e67e22;border-radius:4px;padding:12px 14px;margin-top:12px;font-size:12px;color:#333;"><strong style="color:#e67e22;text-transform:uppercase;letter-spacing:0.5px;">Primary Recommendation:</strong> Review medium-risk clauses and confirm all obligations are acceptable before proceeding.</div>`
                    : `<div style="background:#fff;border:1px solid #27ae60;border-left:4px solid #27ae60;border-radius:4px;padding:12px 14px;margin-top:12px;font-size:12px;color:#333;"><strong style="color:#27ae60;text-transform:uppercase;letter-spacing:0.5px;">Primary Recommendation:</strong> Document terms appear standard. A final review is advised before formal execution.</div>`;

                // Clauses (Sorted High to Low Risk)
                const riskOrder = { high: 3, medium: 2, low: 1 };
                const sortedClauses = [...clauses].sort((a,b) => (riskOrder[b.risk_level] || 0) - (riskOrder[a.risk_level] || 0));
                
                const clausesHtml = sortedClauses.map((c, idx) => {
                    const lvl     = c.risk_level || 'low';
                    const score   = c.risk_score || 0;
                    const section = c.section_header || ('Clause ' + (idx + 1));
                    const cats    = (c.risk_categories || []).join(', ') || 'General';
                    const text    = (c.text || '').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                    const lc      = levelColor[lvl] || '#888';
                    const lb      = '#ffffff';
                    const lvlLabel= { high: 'HIGH RISK &mdash; IMMEDIATE REVIEW REQUIRED', medium: 'MEDIUM RISK &mdash; REVIEW RECOMMENDED', low: 'LOW RISK &mdash; STANDARD TERMS' };
                    const meaning = (c.risk_categories || []).map(cat => riskCatExplain[cat]).filter(Boolean)[0] || '';

                    const violHtml = (c.playbook_violations || []).map(v => `
                        <div style="margin-top:8px;padding:9px;background:#fff5f5;border-left:3px solid #c0392b;border-radius:4px;">
                            <div style="font-size:10px;font-weight:700;color:#c0392b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px;">Policy Issue: ${v.category||''}</div>
                            <div style="font-size:11px;color:#555;margin-bottom:3px;">${v.explanation||''}</div>
                            <div style="font-size:11px;color:#1a73e8;"><strong>Suggested fix:</strong> ${v.alternative_text||''}</div>
                        </div>`).join('');

                    return `
                    <div class="avoid-break" style="page-break-inside:avoid; break-inside:avoid; background:${lb};border:1px solid #ddd;border-left:5px solid ${lc};border-radius:4px;padding:14px 16px;margin-bottom:14px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                            <span style="font-size:11px;font-weight:700;color:${lc};">${lvlLabel[lvl]||lvl}</span>
                            <span style="font-size:10px;background:${lc};color:#fff;padding:2px 9px;border-radius:20px;font-weight:600;">Score: ${score}/100</span>
                        </div>
                        <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;font-weight:600;">${section} &nbsp;|&nbsp; ${cats}</div>
                        ${meaning ? `<div style="background:#fff;border:1px solid #ddd;border-radius:5px;padding:7px 10px;margin-bottom:7px;font-size:12px;color:#333;"><strong>What this means:</strong> ${meaning}</div>` : ''}
                        <p style="font-size:12px;color:#444;line-height:1.6;margin:0;font-style:italic;">"${text}"</p>
                        ${violHtml}
                    </div>`;
                }).join('');

                // Obligations
                const obliHtml = obligations.length ? `
                    <h3 style="font-size:13px;font-weight:700;margin:22px 0 8px;color:#111;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #ddd;padding-bottom:4px;">Schedule of Obligations</h3>
                    <table class="avoid-break" style="width:100%;border-collapse:collapse;font-size:11px;border:1px solid #e0e0e0;">
                        <thead><tr style="background:#1a1a2e;color:#fff;">
                            <th style="padding:7px 10px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">Task</th>
                            <th style="padding:7px 10px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">Description</th>
                            <th style="padding:7px 10px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">Deadline</th>
                            <th style="padding:7px 10px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">Who</th>
                        </tr></thead>
                        <tbody>${obligations.map((o,i) => `
                            <tr style="border-top:1px solid #eee;background:${i%2===0?'#fff':'#fafafa'};">
                                <td style="padding:7px 10px;font-weight:600;color:#333;">${o.title||''}</td>
                                <td style="padding:7px 10px;color:#555;">${o.description||''}</td>
                                <td style="padding:7px 10px;color:#1a73e8;font-weight:600;">${o.timeline||'—'}</td>
                                <td style="padding:7px 10px;color:#666;">${o.responsible_party||'—'}</td>
                            </tr>`).join('')}
                        </tbody>
                    </table>` : '';

                const pageBreak = totalDocs > 1 ? 'page-break-before: always; break-before: always;' : '';

                return `
                <!-- DOC SECTION ${docNum} -->
                <div style="${pageBreak} margin:24px 28px; border:2px solid #1a2530; border-radius:6px;">

                    <!-- Document Title Bar -->
                    <div style="background:#1a2530; padding:14px 20px; display:flex; align-items:center; justify-content:space-between;">
                        <div>
                            <div style="font-size:9px;color:rgba(255,255,255,.55);text-transform:uppercase;letter-spacing:2px;font-weight:700;margin-bottom:3px;">${totalDocs > 1 ? `Document ${docNum} of ${totalDocs}` : 'Document'}</div>
                            <div style="font-size:16px;font-weight:700;color:#fff;letter-spacing:-.2px;">${filename}</div>
                            <div style="font-size:10px;color:rgba(255,255,255,.5);margin-top:2px;">${total} clauses &nbsp;&middot;&nbsp; ${(data.document_info||{}).word_count||0} words</div>
                        </div>
                        <span style="display:inline-block;padding:5px 14px;border-radius:4px;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;background:${riskColor};color:#fff;white-space:nowrap;flex-shrink:0;">${riskLabel}</span>
                    </div>

                    <!-- Analysis Content Box -->
                    <div style="border:1px solid #dce1e7; margin:16px; border-radius:5px; padding:18px 20px; background:#fff;">

                        <!-- Stats -->
                        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px;">
                            <div style="background:#f8f9fa;border:1px solid #e0e0e0;border-radius:6px;padding:10px;text-align:center;">
                                <div style="font-size:22px;font-weight:700;color:#111;">${total}</div>
                                <div style="font-size:8px;color:#888;text-transform:uppercase;letter-spacing:.8px;font-weight:700;margin-top:2px;">Total</div>
                            </div>
                            <div style="background:#fdf0ef;border:1px solid #f5c6c2;border-radius:6px;padding:10px;text-align:center;">
                                <div style="font-size:22px;font-weight:700;color:#c0392b;">${high}</div>
                                <div style="font-size:8px;color:#c0392b;text-transform:uppercase;letter-spacing:.8px;font-weight:700;margin-top:2px;">High Risk</div>
                            </div>
                            <div style="background:#fef5e4;border:1px solid #f7d6a0;border-radius:6px;padding:10px;text-align:center;">
                                <div style="font-size:22px;font-weight:700;color:#e67e22;">${med}</div>
                                <div style="font-size:8px;color:#e67e22;text-transform:uppercase;letter-spacing:.8px;font-weight:700;margin-top:2px;">Medium Risk</div>
                            </div>
                            <div style="background:#eafaf1;border:1px solid #a9dfbf;border-radius:6px;padding:10px;text-align:center;">
                                <div style="font-size:22px;font-weight:700;color:#27ae60;">${low}</div>
                                <div style="font-size:8px;color:#27ae60;text-transform:uppercase;letter-spacing:.8px;font-weight:700;margin-top:2px;">Low Risk</div>
                            </div>
                        </div>

                        <!-- Executive Summary -->
                        <h3 style="font-size:12px;font-weight:700;margin:0 0 7px;color:#1a2530;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #ddd;padding-bottom:4px;">Executive Summary</h3>
                        <div style="background:#f8f9fa;border:1px solid #e0e0e0;border-radius:4px;padding:12px 16px;margin-bottom:4px;">
                            <ul style="margin:0;padding-left:16px;line-height:1.8;font-size:11px;color:#333;">${bullets.join('')}</ul>
                        </div>
                        ${actionLine}

                        ${obliHtml}

                        <!-- Detailed Clause Analysis -->
                        <h3 style="font-size:12px;font-weight:700;margin:18px 0 5px;color:#1a2530;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #ddd;padding-bottom:4px;">Detailed Clause Analysis</h3>
                        <p style="font-size:11px;color:#666;margin:5px 0 10px;">Clauses sorted by risk level (High → Medium → Low). Each clause is analyzed for potential risks and liabilities.</p>
                        ${clausesHtml || '<p style="color:#888;font-size:12px;">No clauses found.</p>'}
                    </div>
                </div>`;
            };

            // ── Build cover (multi-doc only) ──────────────────────────────
            const totalHigh = allDocs.reduce((s,d) => s + (d.summary?.high_risk||0), 0);
            const totalMed  = allDocs.reduce((s,d) => s + (d.summary?.medium_risk||0), 0);
            const totalLow  = allDocs.reduce((s,d) => s + (d.summary?.low_risk||0), 0);
            const totalAll  = allDocs.reduce((s,d) => s + (d.total_clauses||0), 0);

            const coverSection = allDocs.length > 1 ? `
            <div style="padding:28px 40px;background:#f8f9fa;border-bottom:1px solid #e0e0e0;">
                <h2 style="font-size:15px;font-weight:700;margin:0 0 12px;color:#111;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #ddd;padding-bottom:6px;">Overall Summary — ${allDocs.length} Documents Analyzed</h2>
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;">
                    <div style="background:#fff;border:1px solid #e0e0e0;border-radius:7px;padding:12px;text-align:center;">
                        <div style="font-size:22px;font-weight:700;color:#111;">${totalAll}</div>
                        <div style="font-size:8px;color:#888;text-transform:uppercase;letter-spacing:.8px;font-weight:700;margin-top:2px;">Total Clauses</div>
                    </div>
                    <div style="background:#fdf0ef;border:1px solid #f5c6c2;border-radius:7px;padding:12px;text-align:center;">
                        <div style="font-size:22px;font-weight:700;color:#c0392b;">${totalHigh}</div>
                        <div style="font-size:8px;color:#c0392b;text-transform:uppercase;letter-spacing:.8px;font-weight:700;margin-top:2px;">High Risk</div>
                    </div>
                    <div style="background:#fef5e4;border:1px solid #f7d6a0;border-radius:7px;padding:12px;text-align:center;">
                        <div style="font-size:22px;font-weight:700;color:#e67e22;">${totalMed}</div>
                        <div style="font-size:8px;color:#e67e22;text-transform:uppercase;letter-spacing:.8px;font-weight:700;margin-top:2px;">Medium Risk</div>
                    </div>
                    <div style="background:#eafaf1;border:1px solid #a9dfbf;border-radius:7px;padding:12px;text-align:center;">
                        <div style="font-size:22px;font-weight:700;color:#27ae60;">${totalLow}</div>
                        <div style="font-size:8px;color:#27ae60;text-transform:uppercase;letter-spacing:.8px;font-weight:700;margin-top:2px;">Low Risk</div>
                    </div>
                </div>
                <table style="width:100%;border-collapse:collapse;font-size:11px;">
                    <thead><tr style="background:#1a1a2e;color:#fff;">
                        <th style="padding:7px 12px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">#</th>
                        <th style="padding:7px 12px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">Document</th>
                        <th style="padding:7px 12px;text-align:center;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">Clauses</th>
                        <th style="padding:7px 12px;text-align:center;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">High</th>
                        <th style="padding:7px 12px;text-align:center;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">Medium</th>
                        <th style="padding:7px 12px;text-align:center;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">Low</th>
                        <th style="padding:7px 12px;text-align:center;font-size:9px;text-transform:uppercase;letter-spacing:.5px;">Verdict</th>
                    </tr></thead>
                    <tbody>${allDocs.map((d, i) => {
                        const h = d.summary?.high_risk||0, m = d.summary?.medium_risk||0;
                        const verdict = h>0?'HIGH RISK':m>0?'MEDIUM RISK':'LOW RISK';
                        const vc = h>0?'#c0392b':m>0?'#e67e22':'#27ae60';
                        return `<tr class="avoid-break" style="page-break-inside:avoid; break-inside:avoid; border-top:1px solid #eee;background:${i%2===0?'#fff':'#fafafa'};">
                            <td style="padding:7px 12px;color:#888;font-weight:700;">${i+1}</td>
                            <td style="padding:7px 12px;font-weight:600;color:#333;">${d.filename||''}</td>
                            <td style="padding:7px 12px;text-align:center;color:#333;">${d.total_clauses||0}</td>
                            <td style="padding:7px 12px;text-align:center;color:#c0392b;font-weight:700;">${h}</td>
                            <td style="padding:7px 12px;text-align:center;color:#e67e22;font-weight:700;">${m}</td>
                            <td style="padding:7px 12px;text-align:center;color:#27ae60;font-weight:700;">${d.summary?.low_risk||0}</td>
                            <td style="padding:7px 12px;text-align:center;"><span style="background:${vc};color:#fff;padding:2px 8px;border-radius:4px;font-size:9px;font-weight:700;text-transform:uppercase;">${verdict}</span></td>
                        </tr>`;
                    }).join('')}
                    </tbody>
                </table>
            </div>` : '';

            // ── Assemble full HTML ────────────────────────────────────────
            const docSections = allDocs.map((d, i) => buildDocSection(d, i+1, allDocs.length)).join('');
            
            const formatTitle = (name) => {
                if (!name) return 'Contract';
                const clean = name.replace(/\.[^/.]+$/, ''); // remove extension
                return clean.length > 28 ? clean.substring(0, 25) + '...' : clean;
            };
            const reportTitle = allDocs.length > 1 ? `${allDocs.length} Documents` : formatTitle(allDocs[0]?.filename);

            const innerHtml = `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; background:#fff; margin:0; padding:0; color:#111; font-size:12px; }
  .wrap { width:100%; margin:0; background:#fff; }
  .avoid-break { page-break-inside: avoid !important; break-inside: avoid !important; }
</style>
</head><body>
<div class="wrap">
  <!-- Cover Header -->
  <div style="background:#1a2530;color:#fff;padding:24px 30px;border-radius:6px;margin-bottom:20px;">
    <div style="font-size:10px;letter-spacing:2px;opacity:.8;text-transform:uppercase;margin-bottom:8px;">ClauseGuard AI — Full Contract Analysis Report</div>
    <h1 style="font-size:20px;font-weight:700;margin:0 0 4px;letter-spacing:-.3px;">${reportTitle}</h1>
    <p style="font-size:11px;opacity:.8;margin:0;">Prepared on ${generatedAt}</p>
  </div>

  ${coverSection}
  
  <div style="padding-bottom:8px;">
    ${docSections.replace(/border:2px solid #1a2530;/g, 'border:none; border-top:2px solid #1a2530;')}
  </div>

  <!-- Footer -->
  <div style="padding:14px 20px;border-top:1px solid #ddd;margin-top:20px;">
    <p style="font-size:9px;color:#888;text-align:center;margin:0;">
      Generated by ClauseGuard AI &middot; ${generatedAt} &middot; For informational purposes only &mdash; not legal advice. Consult a qualified lawyer before making decisions based on this report.
    </p>
  </div>
</div>
</body></html>`;

            // 1. Show a beautiful loading overlay to the user
            const overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(234, 238, 243, 0.8); z-index:999999; display:flex; align-items:center; justify-content:center; backdrop-filter:blur(3px);';
            overlay.innerHTML = `
                <div style="text-align:center; font-family:sans-serif; color:#1a2530; background:#fff; padding:30px 50px; border-radius:8px; box-shadow:0 4px 20px rgba(0,0,0,0.15);">
                    <h2 style="margin:0 0 10px;font-size:18px;">Generating PDF</h2>
                    <p style="margin:0;font-size:13px;color:#555;">Please wait while we format your report...</p>
                </div>
            `;
            document.body.appendChild(overlay);

            // Give the browser a moment to paint the overlay
            await new Promise(r => setTimeout(r, 100));

            const safeFilename = reportTitle.replace(/[^a-zA-Z0-9_\-]/g, '_').slice(0, 60);
            
            // 2. Set PDF options with a 10mm margin for perfectly centered, neat content
            const opt = {
                margin:       [10, 10, 10, 10], 
                filename:     `ClauseGuard_Report_${safeFilename}.pdf`,
                image:        { type: 'jpeg', quality: 0.98 },
                html2canvas:  { scale: 1.35, useCORS: true, logging: false },
                jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
                pagebreak:    { mode: ['css', 'legacy'], avoid: ['.avoid-break', 'tr'] }
            };

            // 3. Generate the PDF natively from the HTML string to avoid UI viewport layout bugs!
            try {
                await html2pdf().set(opt).from(innerHtml, 'string').save();
                this.toast('PDF report downloaded!', 'success');
            } finally {
                if (document.body.contains(overlay)) {
                    document.body.removeChild(overlay);
                }
            }

        } catch (e) {
            console.error(e);
            this.toast('Error generating PDF report.', 'error');
        } finally {
            this.btnDownloadReport.disabled = false;
            this.btnDownloadReport.innerHTML = `
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Export Report
            `;
        }
    }

    filterResults(level) {
        const cards = this.cardList.querySelectorAll('.clause-card');
        cards.forEach(c => {
            c.style.display = (level === 'all' || c.dataset.risk === level) ? 'block' : 'none';
        });
    }

    // Helpers
    showPanel(name) {
        this.panelLanding.classList.add('hidden');
        this.panelProcessing.classList.add('hidden');
        this.panelResults.classList.add('hidden');
        if (name === 'landing') this.panelLanding.classList.remove('hidden');
        else if (name === 'processing') this.panelProcessing.classList.remove('hidden');
        else if (name === 'results') this.panelResults.classList.remove('hidden');
    }

    resetApp() {
        this.resetUpload();
        if (this.userPrompt) this.userPrompt.value = '';
        
        if (window.innerWidth <= 768) {
            this.sidebar.classList.remove('open');
        }
        
        this.showPanel('landing');
    }

    openModal(m) {
        m.classList.remove('hidden');
        if (window.innerWidth <= 768) this.sidebar.classList.remove('open');
    }
    
    closeModal(m) {
        m.classList.add('hidden');
    }

    async saveSettings() {
        const key = this.apiKeyInput.value.trim();
        this.btnSaveKey.disabled = true;
        this.btnSaveKey.textContent = 'Saving...';
        
        try {
            const res = await fetch(API.settings, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: key })
            });
            const data = await res.json();
            
            if (data.success) {
                this.toast('Settings saved', 'success');
                this.updateLLMStatus(data.llm_available);
                setTimeout(() => this.closeModal(this.settingsModal), 300);
            } else {
                this.toast(data.error || 'Failed to save', 'error');
            }
        } catch (e) {
            this.toast('Network error', 'error');
        } finally {
            this.btnSaveKey.disabled = false;
            this.btnSaveKey.textContent = 'Save Settings';
        }
    }

    async checkHealth() {
        try {
            const res = await fetch(API.health);
            const data = await res.json();
            this.updateLLMStatus(data.llm_available);
        } catch (e) {}
    }

    updateLLMStatus(available) {
        if (available) {
            this.llmStatus.classList.add('connected');
            this.llmStatus.querySelector('span:last-child').textContent = 'Gemini LLM Active';
        } else {
            this.llmStatus.classList.remove('connected');
            this.llmStatus.querySelector('span:last-child').textContent = 'ML Fallback Active';
        }
    }

    toast(msg, type = 'info') {
        const t = document.createElement('div');
        t.className = `toast ${type}`;
        t.textContent = msg;
        this.toastArea.appendChild(t);
        setTimeout(() => {
            t.style.animation = 'slideIn 0.28s ease reverse forwards';
            setTimeout(() => t.remove(), 300);
        }, 4000);
    }

    animateCount(el, target, duration = 800) {
        let start = null;
        const step = (ts) => {
            if (!start) start = ts;
            const prog = Math.min((ts - start) / duration, 1);
            el.textContent = Math.floor(prog * target);
            if (prog < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }

    typeWrite(el, text, speed = 15) {
        el.textContent = '';
        el.classList.add('typing');
        let i = 0;
        const txt = text || '';
        const tick = () => {
            if (i < txt.length) {
                el.textContent += txt.charAt(i++);
                setTimeout(tick, speed);
            } else {
                el.classList.remove('typing');
            }
        };
        tick();
    }

    initTheme() {
        const isLight = localStorage.getItem('cg-theme') !== 'dark';
        const iconDark = document.getElementById('theme-icon-dark');
        const iconLight = document.getElementById('theme-icon-light');
        const label = document.getElementById('theme-label');

        if (isLight) {
            document.documentElement.classList.remove('light-preload');
            document.body.classList.add('light');
            if(iconDark) iconDark.classList.add('hidden');
            if(iconLight) iconLight.classList.remove('hidden');
            if(label) label.textContent = 'Light';
        } else {
            document.documentElement.classList.remove('light-preload');
            if(iconDark) iconDark.classList.remove('hidden');
            if(iconLight) iconLight.classList.add('hidden');
            if(label) label.textContent = 'Dark';
        }
    }
    
    toggleTheme() {
        document.body.classList.toggle('light');
        const isLight = document.body.classList.contains('light');
        localStorage.setItem('cg-theme', isLight ? 'light' : 'dark');
        
        const iconDark = document.getElementById('theme-icon-dark');
        const iconLight = document.getElementById('theme-icon-light');
        const label = document.getElementById('theme-label');
        
        if (isLight) {
            if(iconDark) iconDark.classList.add('hidden');
            if(iconLight) iconLight.classList.remove('hidden');
            if(label) label.textContent = 'Light';
        } else {
            if(iconDark) iconDark.classList.remove('hidden');
            if(iconLight) iconLight.classList.add('hidden');
            if(label) label.textContent = 'Dark';
        }
    }
    
    async sendChatMessage() {
        const text = this.chatInput.value.trim();
        if (!text || !this.docId) return;
        
        // Add user message
        this.chatInput.value = '';
        this.chatInput.disabled = true;
        this.chatSend.disabled = true;
        
        const userMsg = document.createElement('div');
        userMsg.className = 'msg msg-user';
        userMsg.textContent = text;
        this.chatBody.appendChild(userMsg);
        this.chatBody.scrollTop = this.chatBody.scrollHeight;
        
        // Add thinking indicator
        const aiMsg = document.createElement('div');
        aiMsg.className = 'msg msg-ai';
        aiMsg.textContent = 'Thinking...';
        this.chatBody.appendChild(aiMsg);
        this.chatBody.scrollTop = this.chatBody.scrollHeight;
        
        try {
            const res = await fetch(API.chat, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ doc_id: this.docId, question: text })
            });
            const data = await res.json();
            
            if (data.success) {
                this.typeWrite(aiMsg, data.answer, 15);
            } else {
                aiMsg.textContent = data.error || 'Failed to get answer.';
                aiMsg.style.color = 'var(--high)';
            }
        } catch (e) {
            aiMsg.textContent = 'Network error. Please try again.';
            aiMsg.style.color = 'var(--high)';
        } finally {
            this.chatInput.disabled = false;
            this.chatSend.disabled = false;
            this.chatInput.focus();
        }
    }

    loadHistory() {
        const stored = localStorage.getItem('cg-history');
        if (stored) {
            try {
                this.history = JSON.parse(stored);
                this.renderHistorySidebar();
            } catch (e) {
                this.history = [];
            }
        }
    }

    saveToHistory(batch) {
        // Support legacy single items or new batches
        const docs = Array.isArray(batch) ? batch : [batch];
        const primaryId = docs[0].doc_id;
        
        // Prevent duplicates based on primary doc_id
        this.history = this.history.filter(h => {
            const hId = Array.isArray(h) ? h[0].doc_id : h.doc_id;
            return hId !== primaryId;
        });
        
        this.history.unshift(docs);
        // Keep last 20
        if (this.history.length > 20) this.history.pop();
        localStorage.setItem('cg-history', JSON.stringify(this.history));
        this.renderHistorySidebar();
    }

    renderHistorySidebar() {
        const historyContainer = document.getElementById('sb-history');
        if (!historyContainer) return;
        
        if (this.history.length === 0) {
            historyContainer.innerHTML = '<div class="sb-history-empty">No analyses yet</div>';
            return;
        }
        
        historyContainer.innerHTML = '';
        this.history.forEach((batch, index) => {
            const isBatch = Array.isArray(batch);
            const docs = isBatch ? batch : [batch];
            const primary = docs[0];
            
            const hItem = document.createElement('div');
            hItem.className = 'sb-history-item';
            hItem.style.cssText = 'position:relative;padding-right:28px;';
            
            // Risk dot logic (aggregate)
            const h = docs.reduce((sum, d) => sum + (d.summary?.high_risk || 0), 0);
            const m = docs.reduce((sum, d) => sum + (d.summary?.medium_risk || 0), 0);
            const dotClass = h > 0 ? 'h-risk' : (m > 0 ? 'm-risk' : 'l-risk');
            
            const title = docs.length > 1 ? `${primary.filename} +${docs.length - 1}` : primary.filename;
            const totalClauses = docs.reduce((sum, d) => sum + (d.total_clauses || 0), 0);
            
            hItem.innerHTML = `
                <div class="h-dot ${dotClass}"></div>
                <div class="h-info">
                    <span class="h-name">${title}</span>
                    <span class="h-time">${totalClauses} clauses${docs.length > 1 ? ' (Batch)' : ''}</span>
                </div>
                <button class="h-delete-btn" title="Delete" style="position:absolute;right:6px;top:50%;transform:translateY(-50%);background:none;border:none;color:#999;cursor:pointer;font-size:16px;line-height:1;padding:2px 5px;border-radius:3px;" aria-label="Delete history item">&times;</button>
            `;
            
            // Delete button
            hItem.querySelector('.h-delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.history.splice(index, 1);
                localStorage.setItem('cg-history', JSON.stringify(this.history));
                this.renderHistorySidebar();
            });

            hItem.addEventListener('click', () => {
                if (window.innerWidth <= 768) this.sidebar.classList.remove('open');
                this.allDocResults = docs;
                this.results = primary;
                this.docId = primary.doc_id;
                this.resetUpload();
                this.renderResults(primary);
            });
            
            historyContainer.appendChild(hItem);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new ClauseGuard());
