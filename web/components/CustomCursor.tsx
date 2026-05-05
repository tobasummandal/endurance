'use client';

import { useEffect, useRef } from 'react';

export default function CustomCursor() {
  const ringRef = useRef<HTMLDivElement | null>(null);
  const dotRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const ring = ringRef.current;
    const dot = dotRef.current;
    if (!ring || !dot) return;

    let x = -100;
    let y = -100;
    let rx = -100;
    let ry = -100;
    let raf = 0;

    function move(e: MouseEvent) {
      x = e.clientX;
      y = e.clientY;
      dot!.style.left = x + 'px';
      dot!.style.top = y + 'px';
    }

    function tick() {
      rx += (x - rx) * 0.18;
      ry += (y - ry) * 0.18;
      ring!.style.left = rx + 'px';
      ring!.style.top = ry + 'px';
      raf = requestAnimationFrame(tick);
    }

    function isHot(target: EventTarget | null) {
      let el = target as HTMLElement | null;
      while (el) {
        if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.classList?.contains('helios-tab') || el.classList?.contains('helios-btn')) return true;
        el = el.parentElement;
      }
      return false;
    }

    function over(e: MouseEvent) {
      ring!.classList.toggle('hot', isHot(e.target));
    }

    window.addEventListener('mousemove', move);
    window.addEventListener('mouseover', over);
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseover', over);
    };
  }, []);

  return (
    <>
      <div className="cursor-ring" ref={ringRef} />
      <div className="cursor-dot" ref={dotRef} />
    </>
  );
}
