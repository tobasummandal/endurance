'use client';

import { ReactNode, useEffect, useRef } from 'react';

type Props = {
  children: ReactNode;
  delay?: 0 | 1 | 2 | 3;
  className?: string;
};

export default function Reveal({ children, delay = 0, className = '' }: Props) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            (e.target as HTMLElement).classList.add('in');
            io.unobserve(e.target);
          }
        }
      },
      { threshold: 0.12 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const delayClass = delay ? ` delay-${delay}` : '';
  return (
    <div ref={ref} className={`reveal${delayClass} ${className}`}>
      {children}
    </div>
  );
}
