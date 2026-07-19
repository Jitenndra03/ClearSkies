import { useRef, useEffect, useCallback } from 'react';
import { CONDITION_PALETTES } from '../data/conditionData';

/**
 * SkyCanvas — full-viewport canvas that paints the live AQI-driven sky behind all UI.
 *
 * 6 states: Good → Severe. Each state controls:
 *   - Background gradient
 *   - Sun visibility + glow
 *   - Wind lines (smooth sinusoids)
 *   - Particle type & density
 *   - Smog bands
 */
export default function SkyCanvas({ condition }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const stateRef = useRef({
    condition,
    windLines: [],
    particles: [],
    smokePuffs: [],
    time: 0,
    transitionProgress: 1,
    prevCondition: condition,
  });

  // Check reduced motion preference
  const prefersReducedMotion = useRef(
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  const initWindLines = useCallback((count) => {
    const lines = [];
    for (let i = 0; i < count; i++) {
      lines.push({
        y: 0.08 + Math.random() * 0.84,
        amplitude: 12 + Math.random() * 35,
        frequency: 0.002 + Math.random() * 0.004,
        speed: 0.15 + Math.random() * 0.55,
        coreWidth: 1 + Math.random() * 2,
        offset: Math.random() * 2000,
        length: 350 + Math.random() * 500,
        // Each line gets its own slight vertical drift
        drift: (Math.random() - 0.5) * 0.15,
      });
    }
    return lines;
  }, []);

  const initParticles = useCallback((count, type) => {
    const particles = [];
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random(),
        y: Math.random(),
        size: type === 'dust' ? 1 + Math.random() * 3 :
              type === 'pollen' ? 1.5 + Math.random() * 2 :
              2 + Math.random() * 2.5,
        speedX: (type === 'dust' ? 0.3 : 0.1) + Math.random() * (type === 'dust' ? 0.8 : 0.3),
        speedY: -0.05 + Math.random() * 0.1,
        opacity: 0.2 + Math.random() * 0.5,
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.02,
        type,
      });
    }
    return particles;
  }, []);

  const initSmokePuffs = useCallback((count) => {
    const puffs = [];
    for (let i = 0; i < count; i++) {
      puffs.push({
        x: Math.random(),
        y: 0.3 + Math.random() * 0.5,
        radius: 30 + Math.random() * 60,
        growthRate: 0.02 + Math.random() * 0.03,
        opacity: 0.08 + Math.random() * 0.12,
        speedX: 0.05 + Math.random() * 0.1,
        maxRadius: 80 + Math.random() * 60,
      });
    }
    return puffs;
  }, []);

  const getConditionConfig = useCallback((cond) => {
    const configs = {
      good: {
        sunVisible: true, sunOpacity: 1.0, sunGlowRings: 5,
        windLineCount: 5, windOpacity: 0.15, windThicknessMult: 1,
        particleType: 'pollen', particleCount: 15,
        smogBands: 0, smogOpacity: 0,
        smokePuffCount: 0,
        sunRays: true,
      },
      satisfactory: {
        sunVisible: true, sunOpacity: 0.65, sunGlowRings: 4,
        windLineCount: 6, windOpacity: 0.2, windThicknessMult: 1.3,
        particleType: 'leaf', particleCount: 18,
        smogBands: 0, smogOpacity: 0,
        smokePuffCount: 0,
        sunRays: true,
      },
      moderate: {
        sunVisible: true, sunOpacity: 0.3, sunGlowRings: 3,
        windLineCount: 8, windOpacity: 0.3, windThicknessMult: 1.6,
        particleType: 'dust', particleCount: 30,
        smogBands: 3, smogOpacity: 0.06,
        smokePuffCount: 0,
        sunRays: false,
      },
      poor: {
        sunVisible: false, sunOpacity: 0, sunGlowRings: 0,
        windLineCount: 6, windOpacity: 0.25, windThicknessMult: 2,
        particleType: 'dust', particleCount: 45,
        smogBands: 5, smogOpacity: 0.1,
        smokePuffCount: 0,
        sunRays: false,
      },
      'very-poor': {
        sunVisible: false, sunOpacity: 0, sunGlowRings: 0,
        windLineCount: 4, windOpacity: 0.2, windThicknessMult: 2.5,
        particleType: 'dust', particleCount: 60,
        smogBands: 6, smogOpacity: 0.15,
        smokePuffCount: 5,
        sunRays: false,
      },
      severe: {
        sunVisible: false, sunOpacity: 0, sunGlowRings: 0,
        windLineCount: 0, windOpacity: 0, windThicknessMult: 0,
        particleType: 'dust', particleCount: 85,
        smogBands: 8, smogOpacity: 0.25,
        smokePuffCount: 8,
        sunRays: false,
      },
    };
    return configs[cond] || configs.moderate;
  }, []);

  // Re-init entities when condition changes
  useEffect(() => {
    const s = stateRef.current;
    s.prevCondition = s.condition;
    s.condition = condition;
    s.transitionProgress = 0;

    const cfg = getConditionConfig(condition);
    s.windLines = initWindLines(cfg.windLineCount);
    s.particles = initParticles(cfg.particleCount, cfg.particleType);
    s.smokePuffs = initSmokePuffs(cfg.smokePuffCount);
  }, [condition, getConditionConfig, initWindLines, initParticles, initSmokePuffs]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + 'px';
      canvas.style.height = window.innerHeight + 'px';
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener('resize', resize);

    const drawGradient = (ctx, w, h, cond, progress) => {
      const palette = CONDITION_PALETTES[cond];
      const prevPalette = CONDITION_PALETTES[stateRef.current.prevCondition];
      const lerpColor = (a, b, t) => {
        const pa = parseInt(a.slice(1), 16);
        const pb = parseInt(b.slice(1), 16);
        const r = Math.round(((pa >> 16) & 0xff) * (1 - t) + ((pb >> 16) & 0xff) * t);
        const g = Math.round(((pa >> 8) & 0xff) * (1 - t) + ((pb >> 8) & 0xff) * t);
        const bl = Math.round((pa & 0xff) * (1 - t) + (pb & 0xff) * t);
        return `rgb(${r},${g},${bl})`;
      };
      const t = Math.min(1, progress);
      const c1 = lerpColor(prevPalette.gradStart, palette.gradStart, t);
      const c2 = lerpColor(prevPalette.gradEnd, palette.gradEnd, t);
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, c1);
      grad.addColorStop(1, c2);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);
    };

    const drawSun = (ctx, w, _h, cfg, time) => {
      if (!cfg.sunVisible) return;
      const cx = w * 0.82;
      const cy = 90;
      const baseRadius = 36;

      // Glow rings
      for (let i = cfg.sunGlowRings; i >= 1; i--) {
        const r = baseRadius + i * 22;
        const op = cfg.sunOpacity * (0.08 / i);
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,220,120,${op})`;
        ctx.fill();
      }

      // Sun rays
      if (cfg.sunRays) {
        const rayCount = 12;
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(time * 0.0003);
        for (let i = 0; i < rayCount; i++) {
          const angle = (i / rayCount) * Math.PI * 2;
          ctx.beginPath();
          ctx.moveTo(Math.cos(angle) * (baseRadius + 6), Math.sin(angle) * (baseRadius + 6));
          ctx.lineTo(Math.cos(angle) * (baseRadius + 35), Math.sin(angle) * (baseRadius + 35));
          ctx.strokeStyle = `rgba(255,235,150,${cfg.sunOpacity * 0.15})`;
          ctx.lineWidth = 2;
          ctx.stroke();
        }
        ctx.restore();
      }

      // Sun body
      ctx.beginPath();
      ctx.arc(cx, cy, baseRadius, 0, Math.PI * 2);
      const sunGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, baseRadius);
      sunGrad.addColorStop(0, `rgba(255,255,255,${cfg.sunOpacity})`);
      sunGrad.addColorStop(0.5, `rgba(255,240,180,${cfg.sunOpacity * 0.9})`);
      sunGrad.addColorStop(1, `rgba(255,210,100,${cfg.sunOpacity * 0.6})`);
      ctx.fillStyle = sunGrad;
      ctx.fill();

      // White core
      ctx.beginPath();
      ctx.arc(cx, cy, baseRadius * 0.35, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${cfg.sunOpacity * 0.9})`;
      ctx.fill();
    };

    const drawWindLines = (ctx, w, h, windLines, cfg, time) => {
      if (cfg.windLineCount === 0) return;

      // Render each wind line as a multi-layer translucent ribbon
      // Layers from outer (wide+faint) to inner (narrow+slightly brighter)
      const layers = [
        { widthMult: 18, opacityMult: 0.08 },
        { widthMult: 12, opacityMult: 0.12 },
        { widthMult: 7,  opacityMult: 0.18 },
        { widthMult: 3.5, opacityMult: 0.25 },
        { widthMult: 1,  opacityMult: 0.35 },
      ];

      windLines.forEach((line) => {
        const baseY = line.y * h;
        const speed = time * line.speed * 0.04;
        const scrollX = (speed + line.offset) % (w + line.length * 2);
        const startX = -line.length + scrollX;

        // Build the sine path points once
        const points = [];
        const step = 3;
        for (let x = 0; x <= line.length; x += step) {
          const px = startX + x;
          const py = baseY + Math.sin((x + speed * 8) * line.frequency) * line.amplitude
                           + Math.sin((x * 0.001 + time * 0.002) * 0.8) * line.amplitude * 0.3;
          points.push({ x: px, y: py });
        }

        // Draw each feathering layer
        layers.forEach((layer) => {
          ctx.beginPath();
          for (let i = 0; i < points.length; i++) {
            const pt = points[i];
            if (i === 0) {
              ctx.moveTo(pt.x, pt.y);
            } else {
              // Smooth bezier between points for organic curves
              const prev = points[i - 1];
              const cpx = (prev.x + pt.x) / 2;
              const cpy = (prev.y + pt.y) / 2;
              ctx.quadraticCurveTo(prev.x, prev.y, cpx, cpy);
            }
          }
          // Fade-in/out along the length via a linear gradient stroke
          const grad = ctx.createLinearGradient(startX, 0, startX + line.length, 0);
          const baseOp = cfg.windOpacity * layer.opacityMult;
          grad.addColorStop(0, `rgba(255,255,255,0)`);
          grad.addColorStop(0.1, `rgba(255,255,255,${baseOp})`);
          grad.addColorStop(0.5, `rgba(255,255,255,${baseOp * 1.2})`);
          grad.addColorStop(0.9, `rgba(255,255,255,${baseOp})`);
          grad.addColorStop(1, `rgba(255,255,255,0)`);

          ctx.strokeStyle = grad;
          ctx.lineWidth = line.coreWidth * layer.widthMult * cfg.windThicknessMult;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';
          ctx.stroke();
        });
      });
    };

    const drawParticles = (ctx, w, h, particles, time) => {
      particles.forEach((p) => {
        p.x -= p.speedX * 0.0005;
        p.y += p.speedY * 0.0005;
        p.rotation += p.rotationSpeed;

        // Wrap
        if (p.x < -0.05) p.x = 1.05;
        if (p.x > 1.05) p.x = -0.05;
        if (p.y < -0.05) p.y = 1.05;
        if (p.y > 1.05) p.y = -0.05;

        const px = p.x * w;
        const py = p.y * h;

        ctx.save();
        ctx.translate(px, py);
        ctx.rotate(p.rotation);
        ctx.globalAlpha = p.opacity;

        if (p.type === 'pollen') {
          // Small circle + tiny stem
          ctx.beginPath();
          ctx.arc(0, 0, p.size, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(255,255,220,0.6)';
          ctx.fill();
          ctx.beginPath();
          ctx.moveTo(0, p.size);
          ctx.lineTo(0, p.size + 3);
          ctx.strokeStyle = 'rgba(255,255,220,0.3)';
          ctx.lineWidth = 0.5;
          ctx.stroke();
        } else if (p.type === 'leaf') {
          // Leaf shape via bezier
          ctx.beginPath();
          ctx.moveTo(0, -p.size * 1.5);
          ctx.bezierCurveTo(p.size, -p.size * 0.5, p.size, p.size * 0.5, 0, p.size * 1.5);
          ctx.bezierCurveTo(-p.size, p.size * 0.5, -p.size, -p.size * 0.5, 0, -p.size * 1.5);
          ctx.fillStyle = 'rgba(120,180,80,0.45)';
          ctx.fill();
          // center vein
          ctx.beginPath();
          ctx.moveTo(0, -p.size * 1.2);
          ctx.lineTo(0, p.size * 1.2);
          ctx.strokeStyle = 'rgba(80,140,40,0.3)';
          ctx.lineWidth = 0.5;
          ctx.stroke();
        } else {
          // Dust — simple filled circle
          ctx.beginPath();
          ctx.arc(0, 0, p.size, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(180,160,130,0.5)';
          ctx.fill();
        }

        ctx.globalAlpha = 1;
        ctx.restore();
      });
    };

    const drawSmogBands = (ctx, w, h, count, opacity) => {
      if (count === 0) return;
      for (let i = 0; i < count; i++) {
        const y = (h / (count + 1)) * (i + 1);
        const bandHeight = 20 + Math.random() * 30;
        const grad = ctx.createLinearGradient(0, y - bandHeight / 2, 0, y + bandHeight / 2);
        grad.addColorStop(0, `rgba(0,0,0,0)`);
        grad.addColorStop(0.5, `rgba(100,90,80,${opacity})`);
        grad.addColorStop(1, `rgba(0,0,0,0)`);
        ctx.fillStyle = grad;
        ctx.fillRect(0, y - bandHeight / 2, w, bandHeight);
      }
    };

    const drawSmokePuffs = (ctx, w, h, puffs) => {
      puffs.forEach((puff) => {
        puff.x -= puff.speedX * 0.0003;
        puff.radius = Math.min(puff.maxRadius, puff.radius + puff.growthRate * 0.05);
        if (puff.x < -0.15) {
          puff.x = 1.15;
          puff.radius = 30 + Math.random() * 40;
        }
        const px = puff.x * w;
        const py = puff.y * h;
        const grad = ctx.createRadialGradient(px, py, 0, px, py, puff.radius);
        grad.addColorStop(0, `rgba(120,100,70,${puff.opacity})`);
        grad.addColorStop(1, 'rgba(120,100,70,0)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(px, py, puff.radius, 0, Math.PI * 2);
        ctx.fill();
      });
    };

    const animate = () => {
      const s = stateRef.current;
      s.time++;
      if (s.transitionProgress < 1) {
        s.transitionProgress = Math.min(1, s.transitionProgress + 0.008);
      }

      const w = window.innerWidth;
      const h = window.innerHeight;
      const cfg = getConditionConfig(s.condition);

      ctx.save();
      ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);

      // Background gradient
      drawGradient(ctx, w, h, s.condition, s.transitionProgress);

      // Sun
      drawSun(ctx, w, h, cfg, s.time);

      // Wind lines
      // drawWindLines(ctx, w, h, s.windLines, cfg, s.time);

      // Smog bands
      // drawSmogBands(ctx, w, h, cfg.smogBands, cfg.smogOpacity);

      // Smoke puffs
      drawSmokePuffs(ctx, w, h, s.smokePuffs);

      // Particles
      drawParticles(ctx, w, h, s.particles, s.time);

      ctx.restore();

      if (!prefersReducedMotion.current) {
        animRef.current = requestAnimationFrame(animate);
      }
    };

    if (prefersReducedMotion.current) {
      // Draw single frame
      const s = stateRef.current;
      s.transitionProgress = 1;
      const w = window.innerWidth;
      const h = window.innerHeight;
      const cfg = getConditionConfig(s.condition);
      ctx.save();
      ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
      drawGradient(ctx, w, h, s.condition, 1);
      drawSun(ctx, w, h, cfg, 0);
      ctx.restore();
    } else {
      animRef.current = requestAnimationFrame(animate);
    }

    return () => {
      window.removeEventListener('resize', resize);
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [condition, getConditionConfig]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        pointerEvents: 'none',
      }}
      aria-hidden="true"
    />
  );
}
