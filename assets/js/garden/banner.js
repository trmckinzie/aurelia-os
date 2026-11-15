/**
 * The particle network drawn behind the Garden's banner. Decoration only:
 * nothing else on the page depends on it.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */

// --- 2. NEURAL ANIMATION (PRESERVED) ---
export function initBanner() {
    const canvas = document.getElementById('neural-canvas');
    if (!canvas) return;
    // Reduced motion: draw one static frame instead of running the
    // particle sim on a permanent requestAnimationFrame loop.
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const ctx = canvas.getContext('2d');
    let width, height;
    let particles = [];
    /* Particle count follows the banner's area rather than being a flat
       60. connectionDistance is fixed at 150px, so on a phone -- where
       the banner is ~327x256 instead of ~1550x256 -- those same 60 dots
       sat inside each other's connection radius and the "sparse network"
       rendered as a solid scribble. /5600 puts it back at 60 across
       desktop widths and about 15 on a phone. */
    const PARTICLE_AREA_PER = 5600;
    const particleTarget = () =>
        Math.max(10, Math.min(60, Math.round((width * height) / PARTICLE_AREA_PER)));
    const connectionDistance = 150;
    const mouseDistance = 200; 

    /* The backing store is sized in device pixels, the drawing surface
       stays in CSS pixels. This used to set canvas.width straight from
       offsetWidth, so on any display with devicePixelRatio above 1 --
       a Retina screen is 2, Windows at 125% scaling is 1.25 -- the
       browser stretched a half-resolution bitmap over the element and
       every line came out soft.

       setTransform (not scale) because resize() runs again on every
       window resize, and scale() would compound each time. width and
       height stay CSS pixels, which is what the particle simulation and
       the mouse mapping below both work in, so nothing else changes. */
    function resize() {
        const dpr = window.devicePixelRatio || 1;
        width = canvas.parentElement.offsetWidth;
        height = canvas.parentElement.offsetHeight;
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        syncParticles();
    }
    // Add or drop particles to match the new size instead of rebuilding
    // the array: a full rebuild on every resize event teleports every
    // surviving dot, which reads as a glitch during a window drag.
    function syncParticles() {
        const target = particleTarget();
        while (particles.length > target) particles.pop();
        while (particles.length < target) particles.push(new Particle());
    }
    window.addEventListener('resize', resize);

    const mouse = { x: null, y: null };
    canvas.parentElement.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
    });
    canvas.parentElement.addEventListener('mouseleave', () => { mouse.x = null; mouse.y = null; });

    class Particle {
        constructor() {
            this.x = Math.random() * width; this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.20; this.vy = (Math.random() - 0.5) * 0.20;
            this.size = Math.random() * 1.5 + 0.5;
        }
        update() {
            this.x += this.vx; this.y += this.vy;
            if (this.x < 0 || this.x > width) this.vx *= -1;
            if (this.y < 0 || this.y > height) this.vy *= -1;
            if (mouse.x != null) {
                let dx = mouse.x - this.x; let dy = mouse.y - this.y;
                let distance = Math.sqrt(dx*dx + dy*dy);
                if (distance < mouseDistance) {
                    const force = (mouseDistance - distance) / mouseDistance;
                    this.vx -= (dx / distance) * force * 0.5;
                    this.vy -= (dy / distance) * force * 0.5;
                }
            }
        }
        draw(rgb) { ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2); ctx.fillStyle = `rgba(${rgb}, 0.5)`; ctx.fill(); }
    }
    // First sizing happens here rather than above, because resize() now
    // populates the array and `new Particle()` needs the class declared.
    resize();

    // Canvas fillStyle/strokeStyle can't read a CSS var() directly, so
    // this used to be hardcoded cyan regardless of theme -- neon
    // particles behind a parchment-and-navy Americana page looked
    // exactly as out of place as it sounds. Read the live
    // --aurelia-primary-rgb value once per frame instead (cheap: one
    // custom-property read, not a layout-triggering call) so the
    // particle color follows whatever theme is actually active.
    function animate() {
        ctx.clearRect(0, 0, width, height);
        const rgb = (getComputedStyle(document.documentElement).getPropertyValue('--aurelia-primary-rgb').trim() || '0 242 255').replace(/\s+/g, ', ');
        particles.forEach(p => { p.update(); p.draw(rgb); });
        for (let a = 0; a < particles.length; a++) {
            for (let b = a; b < particles.length; b++) {
                let dx = particles[a].x - particles[b].x; let dy = particles[a].y - particles[b].y;
                let distance = Math.sqrt(dx * dx + dy * dy);
                if (distance < connectionDistance) {
                    ctx.strokeStyle = `rgba(${rgb}, ${1 - (distance / connectionDistance)})`;
                    ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(particles[a].x, particles[a].y); ctx.lineTo(particles[b].x, particles[b].y); ctx.stroke();
                }
            }
        }
        if (!reduceMotion) requestAnimationFrame(animate);
    }
    animate();
}
