/**
 * ClauseGuard — Awwwards Page Transition Engine
 * Inspired by United Carriers (Bearplus)
 */
(function() {
    // 1. Create Transition Curtain DOM Element
    let curtain = document.querySelector('.cg-transition-curtain');
    if (!curtain) {
        curtain = document.createElement('div');
        curtain.className = 'cg-transition-curtain';
        curtain.innerHTML = `
            <div class="cg-curtain-layer cg-curtain-accent"></div>
            <div class="cg-curtain-layer cg-curtain-primary"></div>
            <div class="cg-curtain-content">
                <div class="cg-curtain-logo">§</div>
                <div class="cg-curtain-text">ClauseGuard</div>
                <div class="cg-curtain-sub">Contracts, Dissected</div>
                <div class="cg-curtain-bar"><div class="cg-curtain-bar-fill"></div></div>
            </div>
        `;
        document.body.appendChild(curtain);
    }

    // 2. Play Page Entrance Animation
    window.addEventListener('DOMContentLoaded', () => {
        // Trigger reveal texts
        setTimeout(() => {
            document.querySelectorAll('.reveal-text').forEach((el) => {
                el.classList.add('is-revealed');
            });
        }, 120);
    });

    // 3. Intercept Internal Link Clicks for Cinematic Page Transitions
    document.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (!link) return;

        const href = link.getAttribute('href');
        if (!href) return;

        // Skip anchors on current page (#how-it-works, etc.) or external URLs
        if (href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:') || link.target === '_blank') {
            return;
        }

        // Only intercept internal relative or same-origin paths
        const isInternal = href.startsWith('/') || href.includes(window.location.host);
        if (!isInternal) return;

        e.preventDefault();

        // Trigger Curtain Wipe Transition
        curtain.classList.remove('is-leaving');
        curtain.classList.add('is-transitioning');

        setTimeout(() => {
            window.location.href = href;
        }, 580);
    });

    // Handle back-forward navigation cache
    window.addEventListener('pageshow', (e) => {
        if (e.persisted) {
            curtain.classList.remove('is-transitioning');
            curtain.classList.remove('is-leaving');
        }
    });
})();
