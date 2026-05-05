'use client';

import { useEffect, useRef } from 'react';

// Ported from web/index.html — solar grid + drifting particles.
export default function BackgroundCanvas() {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const bg = ref.current;
    if (!bg) return;
    const ctx = bg.getContext('2d');
    if (!ctx) return;
    const DPR = Math.min(window.devicePixelRatio || 1, 2);
    let W = 0;
    let H = 0;
    let mx = -9999;
    let my = -9999;
    let scrollY = 0;
    let raf = 0;

    type P = { x: number; y: number; vx: number; vy: number; r: number; a: number };
    const particles: P[] = [];

    function resize() {
      W = window.innerWidth;
      H = window.innerHeight;
      bg!.width = W * DPR;
      bg!.height = H * DPR;
      bg!.style.width = W + 'px';
      bg!.style.height = H + 'px';
      ctx!.setTransform(DPR, 0, 0, DPR, 0, 0);
    }

    function spawn() {
      const count = Math.min(Math.floor((W * H) / 18000), 80);
      particles.length = 0;
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * W,
          y: Math.random() * H,
          vx: (Math.random() - 0.5) * 0.15,
          vy: (Math.random() - 0.5) * 0.15,
          r: Math.random() * 1.4 + 0.3,
          a: Math.random() * 0.5 + 0.2,
        });
      }
    }

    function draw() {
      ctx!.clearRect(0, 0, W, H);
      // grid
      const gridSize = 80;
      const offset = (scrollY * 0.05) % gridSize;
      ctx!.strokeStyle = 'rgba(26, 34, 48, 0.5)';
      ctx!.lineWidth = 1;
      ctx!.beginPath();
      for (let x = -offset; x < W; x += gridSize) {
        ctx!.moveTo(x, 0);
        ctx!.lineTo(x, H);
      }
      for (let y = -offset; y < H; y += gridSize) {
        ctx!.moveTo(0, y);
        ctx!.lineTo(W, y);
      }
      ctx!.stroke();

      // sun glow following cursor
      if (mx > -1000) {
        const grd = ctx!.createRadialGradient(mx, my, 0, mx, my, 280);
        grd.addColorStop(0, 'rgba(232, 163, 61, 0.10)');
        grd.addColorStop(1, 'rgba(232, 163, 61, 0)');
        ctx!.fillStyle = grd;
        ctx!.fillRect(0, 0, W, H);
      }

      // particles
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x += W;
        if (p.x > W) p.x -= W;
        if (p.y < 0) p.y += H;
        if (p.y > H) p.y -= H;
        ctx!.fillStyle = `rgba(243, 236, 224, ${p.a})`;
        ctx!.beginPath();
        ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx!.fill();
      }

      raf = requestAnimationFrame(draw);
    }

    function onMouse(e: MouseEvent) {
      mx = e.clientX;
      my = e.clientY;
    }
    function onScroll() {
      scrollY = window.scrollY;
    }

    resize();
    spawn();
    draw();
    window.addEventListener('resize', () => {
      resize();
      spawn();
    });
    window.addEventListener('mousemove', onMouse);
    window.addEventListener('scroll', onScroll, { passive: true });

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('mousemove', onMouse);
      window.removeEventListener('scroll', onScroll);
    };
  }, []);

  return <canvas id="bg" ref={ref} />;
}
