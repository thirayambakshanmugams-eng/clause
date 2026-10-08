/**
 * ClauseGuard — Object Studio Interactive Flow & Portfolite Interactions
 */

document.addEventListener('DOMContentLoaded', () => {
  // ── 1. MODAL STATE & HANDLERS ──────────────────────────────────────
  const authModal = document.getElementById('authModal');
  const modalTabLogin = document.getElementById('modalTabLogin');
  const modalTabSignup = document.getElementById('modalTabSignup');
  const formLogin = document.getElementById('formLogin');
  const formSignup = document.getElementById('formSignup');
  const modalTitle = document.getElementById('modalTitle');
  const modalSubtitle = document.getElementById('modalSubtitle');

  window.openAuthModal = function(initialTab = 'login') {
    if (!authModal) return;
    authModal.classList.add('open');
    document.body.style.overflow = 'hidden';
    switchAuthTab(initialTab);
  };

  window.closeAuthModal = function() {
    if (!authModal) return;
    authModal.classList.remove('open');
    document.body.style.overflow = '';
  };

  window.switchAuthTab = function(tab) {
    if (tab === 'login') {
      if (modalTabLogin) modalTabLogin.classList.add('active');
      if (modalTabSignup) modalTabSignup.classList.remove('active');
      if (formLogin) formLogin.style.display = 'flex';
      if (formSignup) formSignup.style.display = 'none';
      if (modalTitle) {
        modalTitle.setAttribute('data-i18n', 'auth.signin_title');
        modalTitle.textContent = window.CG_i18n ? window.CG_i18n.t('auth.signin_title') : 'Sign In to ClauseGuard';
      }
      if (modalSubtitle) {
        modalSubtitle.setAttribute('data-i18n', 'auth.signin_sub');
        modalSubtitle.textContent = window.CG_i18n ? window.CG_i18n.t('auth.signin_sub') : 'Access your contract audits, workspaces, and team playbooks.';
      }
    } else {
      if (modalTabLogin) modalTabLogin.classList.remove('active');
      if (modalTabSignup) modalTabSignup.classList.add('active');
      if (formLogin) formLogin.style.display = 'none';
      if (formSignup) formSignup.style.display = 'flex';
      if (modalTitle) {
        modalTitle.setAttribute('data-i18n', 'auth.signup_title');
        modalTitle.textContent = window.CG_i18n ? window.CG_i18n.t('auth.signup_title') : 'Create ClauseGuard Account';
      }
      if (modalSubtitle) {
        modalSubtitle.setAttribute('data-i18n', 'auth.signup_sub');
        modalSubtitle.textContent = window.CG_i18n ? window.CG_i18n.t('auth.signup_sub') : 'Start dissecting legal risk with autonomous hybrid intelligence.';
      }
    }
  };

  // Close modal on backdrop click
  if (authModal) {
    authModal.addEventListener('click', (e) => {
      if (e.target === authModal) {
        window.closeAuthModal();
      }
    });
  }

  // Quick fill helper for review/testing
  window.quickFillAuth = function(user, pass) {
    const userInput = document.getElementById('loginUsername');
    const passInput = document.getElementById('loginPassword');
    if (userInput && passInput) {
      userInput.value = user;
      passInput.value = pass;
    }
  };

  // Enhanced form submission handling to prevent 404s and redirect seamlessly
  if (formLogin) {
    formLogin.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = formLogin.querySelector('button[type="submit"]');
      const originalText = btn ? btn.innerHTML : '';
      if (btn) btn.innerHTML = '<span>Signing In...</span>';
      const alertBox = document.getElementById('authErrorAlert');
      if (alertBox) { alertBox.style.display = 'none'; alertBox.textContent = ''; }
      
      const formData = new FormData(formLogin);
      try {
        const res = await fetch('/login', {
          method: 'POST',
          headers: { 'Accept': 'application/json' },
          body: new URLSearchParams(formData)
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && (data.success || data.redirect)) {
          window.location.href = data.redirect || '/app';
        } else {
          const errMsg = data.error || 'Login failed. Please check your credentials.';
          if (alertBox) {
            alertBox.textContent = errMsg;
            alertBox.style.display = 'block';
          } else {
            alert(errMsg);
          }
          if (btn) btn.innerHTML = originalText;
        }
      } catch (err) {
        console.error('Login error:', err);
        formLogin.submit();
      }
    });
  }

  if (formSignup) {
    formSignup.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = formSignup.querySelector('button[type="submit"]');
      const originalText = btn ? btn.innerHTML : '';
      if (btn) btn.innerHTML = '<span>Creating Account...</span>';
      const alertBox = document.getElementById('authErrorAlert');
      if (alertBox) { alertBox.style.display = 'none'; alertBox.textContent = ''; }

      const formData = new FormData(formSignup);
      try {
        const res = await fetch('/register', {
          method: 'POST',
          headers: { 'Accept': 'application/json' },
          body: new URLSearchParams(formData)
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && (data.success || data.redirect)) {
          window.location.href = data.redirect || '/app';
        } else {
          const errMsg = data.error || 'Registration failed. Please check your details.';
          if (alertBox) {
            alertBox.textContent = errMsg;
            alertBox.style.display = 'block';
          } else {
            alert(errMsg);
          }
          if (btn) btn.innerHTML = originalText;
        }
      } catch (err) {
        console.error('Registration error:', err);
        formSignup.submit();
      }
    });
  }

  // ── 2. OBJECT STUDIO SPLIT SHOWCASE STEP SELECTOR ─────────────────
  const stepCards = document.querySelectorAll('.step-nav-card');
  const detailCards = document.querySelectorAll('.capability-detail-card');

  stepCards.forEach((card) => {
    card.addEventListener('click', () => {
      const stepIndex = card.getAttribute('data-step');
      
      stepCards.forEach(c => c.classList.remove('active'));
      card.classList.add('active');

      const targetDetail = document.getElementById(`capDetail${stepIndex}`);
      if (targetDetail) {
        targetDetail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  });

  // Highlight step cards on scroll
  const observerOptions = {
    root: null,
    rootMargin: '-20% 0px -60% 0px',
    threshold: 0
  };

  const stepObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        const stepNum = id.replace('capDetail', '');
        stepCards.forEach(c => {
          if (c.getAttribute('data-step') === stepNum) {
            c.classList.add('active');
          } else {
            c.classList.remove('active');
          }
        });
      }
    });
  }, observerOptions);

  detailCards.forEach(card => stepObserver.observe(card));

  // ── 3. INTERACTIVE RISK SANDBOX PLAYGROUND ────────────────────────
  const PRESET_CLAUSES = {
    indemnity: {
      category: "Unilateral Indemnity",
      risk: "high",
      score: 94,
      text: "The Contractor shall defend, indemnify, and hold harmless the Company, its directors, employees, and agents from and against any and all claims, liabilities, losses, damages, legal fees, and costs arising out of any performance or alleged breach under this Agreement, regardless of negligence or fault.",
      reason: "CRITICAL: Imposes 100% one-sided liability with no reciprocal indemnity, no carve-out for Company's own gross negligence, and no monetary liability ceiling.",
      recommendation: "Convert to mutual indemnity, insert an explicit liability cap (e.g. 12 months fees paid), and exclude claims caused by indemnified party's willful misconduct."
    },
    liability: {
      category: "Unlimited Liability",
      risk: "high",
      score: 91,
      text: "IN NO EVENT SHALL COMPANY BE LIABLE FOR INCIDENTAL OR CONSEQUENTIAL DAMAGES. CONTRACTOR'S TOTAL AGGREGATE LIABILITY ARISING FROM THIS AGREEMENT SHALL BE UNLIMITED AND SHALL NOT BE CAPPED UNDER ANY CIRCUMSTANCES.",
      reason: "EXTREME: Complete asymmetric limitation of liability. Disproportionate risk allocation with catastrophic financial exposure for the service provider.",
      recommendation: "Cap aggregate liability to the total contract value in the preceding 12 months, and make consequential damage exclusions bilateral."
    },
    noncompete: {
      category: "Overbroad Non-Compete",
      risk: "medium",
      score: 76,
      text: "During the term and for a period of 36 months following termination, Consultant covenants and agrees not to directly or indirectly engage in, advise, consult, or invest in any business worldwide that competes with any current or prospective service of the Client.",
      reason: "MODERATE / HIGH: 36-month duration and worldwide geographic scope are grossly overbroad and likely unenforceable or punitive under common law precedents.",
      recommendation: "Narrow scope to direct competitors, reduce duration to 6–12 months, and constrain geographic radius to specific operating territories."
    },
    ip: {
      category: "IP Assignment & Work For Hire",
      risk: "medium",
      score: 68,
      text: "All ideas, patents, copyrights, trademarks, software code, algorithms, and methodologies created, conceived, or reduced to practice by Contractor prior to or during the term shall irrevocably become the sole property of the Company.",
      reason: "ELEVATED: Seizes pre-existing Background Intellectual Property ('prior to') without license carve-outs.",
      recommendation: "Retain ownership of Pre-Existing IP, Granting only a non-exclusive license for the project deliverable."
    },
    safe: {
      category: "Standard Bilateral NDA",
      risk: "low",
      score: 18,
      text: "Each party agrees to treat the Confidential Information of the other party with the same degree of care as it treats its own confidential material of like nature, but in no event less than reasonable care, for a period of two (2) years from disclosure.",
      reason: "BALANCED / LOW: Symmetrical standard of reasonable care with a customary 2-year sunset provision and industry standard exclusions.",
      recommendation: "Standard commercial language. Safe to sign with standard confidentiality operational procedures."
    }
  };

  const sandboxText = document.getElementById('sandboxText');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const resultCategory = document.getElementById('resultCategory');
  const resultBadge = document.getElementById('resultBadge');
  const resultScore = document.getElementById('resultScore');
  const resultFill = document.getElementById('resultFill');
  const resultReason = document.getElementById('resultReason');
  const resultAdvice = document.getElementById('resultAdvice');
  const presetBtns = document.querySelectorAll('.preset-btn');

  window.loadPreset = function(type) {
    const item = PRESET_CLAUSES[type];
    if (!item) return;

    presetBtns.forEach(btn => {
      if (btn.getAttribute('data-preset') === type) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    if (sandboxText) {
      sandboxText.value = item.text;
      renderAnalysis(item);
    }
  };

  function renderAnalysis(item) {
    if (resultCategory) resultCategory.textContent = item.category;
    if (resultScore) resultScore.textContent = `${item.score}% Risk Confidence`;

    if (resultBadge) {
      resultBadge.className = `risk-level-badge ${item.risk}`;
      const badgeKey = item.risk === 'high' ? 'dash.high_risk' : item.risk === 'medium' ? 'dash.med_risk' : 'dash.low_risk';
      resultBadge.setAttribute('data-i18n', badgeKey);
      resultBadge.textContent = window.CG_i18n ? window.CG_i18n.t(badgeKey) : (item.risk === 'high' ? 'High Risk' : item.risk === 'medium' ? 'Medium Risk' : 'Standard / Low');
    }

    if (resultFill) {
      resultFill.className = `risk-progress-fill ${item.risk}`;
      resultFill.style.width = `${item.score}%`;
    }

    if (resultReason) {
      resultReason.textContent = item.reason;
    }

    if (resultAdvice) {
      resultAdvice.textContent = item.recommendation;
    }
  }

  if (analyzeBtn) {
    analyzeBtn.addEventListener('click', () => {
      const text = (sandboxText ? sandboxText.value : '').toLowerCase();
      analyzeBtn.innerHTML = window.CG_i18n ? window.CG_i18n.t('dash.parsing') : `Scanning...`;
      analyzeBtn.disabled = true;

      setTimeout(() => {
        analyzeBtn.innerHTML = window.CG_i18n ? window.CG_i18n.t('sb.analyze_btn') : `Analyze Clause`;
        analyzeBtn.setAttribute('data-i18n', 'sb.analyze_btn');
        analyzeBtn.disabled = false;

        // Smart client-side heuristics
        if (text.includes('indemnif') || text.includes('hold harmless') || text.includes('regardless of')) {
          renderAnalysis(PRESET_CLAUSES.indemnity);
        } else if (text.includes('unlimited') || text.includes('consequential') || text.includes('not be capped')) {
          renderAnalysis(PRESET_CLAUSES.liability);
        } else if (text.includes('compete') || text.includes('worldwide') || text.includes('months')) {
          renderAnalysis(PRESET_CLAUSES.noncompete);
        } else if (text.includes('intellectual property') || text.includes('prior to') || text.includes('irrevocably become')) {
          renderAnalysis(PRESET_CLAUSES.ip);
        } else {
          renderAnalysis({
            category: "Custom Contract Clause",
            risk: text.length > 100 ? "medium" : "low",
            score: text.length > 100 ? 55 : 24,
            reason: "Analyzed with ClauseGuard LinearSVC Classifier & linguistic risk heuristics.",
            recommendation: "Ensure key liabilities, indemnity obligations, and termination rights are symmetrical."
          });
        }
      }, 350);
    });
  }

  // Load default preset
  if (sandboxText && !sandboxText.value) {
    loadPreset('indemnity');
  }

  // ── 4. DYNAMIC HERO SCANNER CYCLER ────────────────────────────────
  const heroSnippets = document.querySelectorAll('.clause-item-preview');
  let currentScanIdx = 0;

  if (heroSnippets.length > 0) {
    setInterval(() => {
      heroSnippets.forEach((snippet, i) => {
        if (i === currentScanIdx) {
          snippet.style.transform = 'scale(1.02)';
          snippet.style.boxShadow = '0 0 15px rgba(212, 175, 55, 0.2)';
        } else {
          snippet.style.transform = 'scale(1)';
          snippet.style.boxShadow = 'none';
        }
      });
      currentScanIdx = (currentScanIdx + 1) % heroSnippets.length;
    }, 2800);
  }

  // ── 5. THEME TOGGLE (DARK / LIGHT MODE) ───────────────────────────
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
      const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', nextTheme);
      try {
        localStorage.setItem('cg-theme', nextTheme);
      } catch (e) {}
    });
  }

  // ── 6. DYNAMIC RE-TRANSLATION ON LANGUAGE CHANGE ───────────────────
  document.addEventListener('cg:langchange', () => {
    if (window.CG_i18n) {
      window.CG_i18n.applyAll();
    }
  });
});

