import { useState, useEffect } from 'react';
import styles from './RobotAvatar.module.css';

/**
 * RobotAvatar - Interactive, animated 3D-styled AI Robot character
 * @param {{
 *   state?: 'idle' | 'thinking' | 'talking' | 'success',
 *   size?: 'sm' | 'md' | 'lg',
 *   interactive?: boolean,
 *   onClick?: Function
 * }} props
 */
export default function RobotAvatar({
  state = 'idle',
  size = 'md',
  interactive = true,
  onClick,
}) {
  const [isWaving, setIsWaving] = useState(false);
  const [bubbleText, setBubbleText] = useState(null);

  const greetings = [
    "👋 Hi! I'm CustomerHelperAI. How can I help with your complaint today?",
    "🔬 Ready to analyze batch numbers, defect descriptions, and risk levels!",
    "💡 Tip: You can type naturally or ask me to check missing fields!",
    "⚡ I can write root cause hypotheses and draft CAPA actions for you!",
  ];

  const handleClick = (e) => {
    if (!interactive) return;
    setIsWaving(true);
    const randomGreet = greetings[Math.floor(Math.random() * greetings.length)];
    setBubbleText(randomGreet);

    setTimeout(() => setIsWaving(false), 1200);
    setTimeout(() => setBubbleText(null), 4000);

    onClick?.(e);
  };

  return (
    <div
      className={`${styles.robotWrapper} ${styles[size]} ${styles[state]} ${isWaving ? styles.waving : ''}`}
      onClick={handleClick}
      title={interactive ? "Click me to interact with CustomerHelperAI!" : "CustomerHelperAI"}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
    >
      {/* Speech Bubble popup on click/hover */}
      {bubbleText && (
        <div className={styles.speechBubble}>
          {bubbleText}
          <div className={styles.bubbleTail} />
        </div>
      )}

      {/* Hologram Aura Ring */}
      <div className={styles.auraRing} />

      {/* SVG Robot Character */}
      <svg
        viewBox="0 0 100 100"
        className={styles.robotSvg}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="botHeadGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#818cf8" />
            <stop offset="50%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#4338ca" />
          </linearGradient>

          <linearGradient id="botVisorGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0f172a" />
            <stop offset="100%" stopColor="#1e293b" />
          </linearGradient>

          <linearGradient id="botEyeCyan" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#67e8f9" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>

          <linearGradient id="botEyeThinking" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#f472b6" />
            <stop offset="100%" stopColor="#c084fc" />
          </linearGradient>

          <filter id="eyeGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Antenna */}
        <g className={styles.antennaGroup}>
          <line x1="50" y1="20" x2="50" y2="8" stroke="#818cf8" strokeWidth="3.5" strokeLinecap="round" />
          <circle cx="50" cy="8" r="5" className={styles.antennaLight} fill="#38bdf8" filter="url(#eyeGlow)" />
        </g>

        {/* Ears / Side Audio Sensors */}
        <rect x="14" y="38" width="6" height="18" rx="3" fill="#4f46e5" />
        <rect x="80" y="38" width="6" height="18" rx="3" fill="#4f46e5" />
        <circle cx="17" cy="47" r="1.5" fill="#38bdf8" />
        <circle cx="83" cy="47" r="1.5" fill="#38bdf8" />

        {/* Head Shell */}
        <rect
          x="20"
          y="20"
          width="60"
          height="54"
          rx="18"
          fill="url(#botHeadGrad)"
          stroke="#a5b4fc"
          strokeWidth="1.5"
          className={styles.headShell}
        />

        {/* Head Highlight */}
        <path
          d="M 30 24 Q 50 20 70 24"
          stroke="rgba(255,255,255,0.45)"
          strokeWidth="2"
          strokeLinecap="round"
        />

        {/* Dark Glass Visor Screen */}
        <rect
          x="26"
          y="32"
          width="48"
          height="30"
          rx="10"
          fill="url(#botVisorGrad)"
          stroke="#334155"
          strokeWidth="1"
          className={styles.visorScreen}
        />

        {/* Eyes / Face Display based on State */}
        {state === 'thinking' ? (
          /* Thinking Mode: Pulsing/Scanning Eyes */
          <g className={styles.thinkingEyes}>
            <circle cx="39" cy="45" r="4.5" fill="url(#botEyeThinking)" filter="url(#eyeGlow)" className={styles.thinkDot1} />
            <circle cx="50" cy="45" r="4.5" fill="url(#botEyeThinking)" filter="url(#eyeGlow)" className={styles.thinkDot2} />
            <circle cx="61" cy="45" r="4.5" fill="url(#botEyeThinking)" filter="url(#eyeGlow)" className={styles.thinkDot3} />
            {/* Laser Scan Beam */}
            <line x1="28" y1="45" x2="72" y2="45" stroke="#f472b6" strokeWidth="1.5" opacity="0.6" className={styles.scanBeam} />
          </g>
        ) : state === 'talking' ? (
          /* Talking Mode: Lively eyes + bouncing mouth audio wave */
          <g className={styles.talkingFace}>
            <ellipse cx="38" cy="43" rx="5" ry="4" fill="url(#botEyeCyan)" filter="url(#eyeGlow)" className={styles.talkingEye} />
            <ellipse cx="62" cy="43" rx="5" ry="4" fill="url(#botEyeCyan)" filter="url(#eyeGlow)" className={styles.talkingEye} />
            {/* Audio Wave Mouth */}
            <g className={styles.mouthWave}>
              <line x1="43" y1="53" x2="43" y2="57" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" className={styles.waveBar1} />
              <line x1="47" y1="51" x2="47" y2="59" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" className={styles.waveBar2} />
              <line x1="50" y1="49" x2="50" y2="61" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" className={styles.waveBar3} />
              <line x1="53" y1="51" x2="53" y2="59" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" className={styles.waveBar2} />
              <line x1="57" y1="53" x2="57" y2="57" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" className={styles.waveBar1} />
            </g>
          </g>
        ) : state === 'success' ? (
          /* Success Mode: Happy Arched Eyes */
          <g className={styles.happyFace}>
            <path d="M 33 46 Q 38 39 43 46" stroke="#4ade80" strokeWidth="3" strokeLinecap="round" fill="none" filter="url(#eyeGlow)" />
            <path d="M 57 46 Q 62 39 67 46" stroke="#4ade80" strokeWidth="3" strokeLinecap="round" fill="none" filter="url(#eyeGlow)" />
            <path d="M 46 54 Q 50 58 54 54" stroke="#4ade80" strokeWidth="2.5" strokeLinecap="round" fill="none" />
          </g>
        ) : (
          /* Idle Mode: Expressive LED Visor Eyes + Soft Smile */
          <g className={styles.idleFace}>
            <ellipse cx="38" cy="45" rx="5" ry="5.5" fill="url(#botEyeCyan)" filter="url(#eyeGlow)" className={styles.idleEye} />
            <ellipse cx="62" cy="45" rx="5" ry="5.5" fill="url(#botEyeCyan)" filter="url(#eyeGlow)" className={styles.idleEye} />
            <circle cx="40" cy="43" r="1.5" fill="#ffffff" />
            <circle cx="64" cy="43" r="1.5" fill="#ffffff" />
            {/* Friendly mouth line */}
            <path d="M 44 54 Q 50 58 56 54" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.8" />
          </g>
        )}

        {/* Neck / Collar */}
        <rect x="42" y="74" width="16" height="6" rx="2" fill="#312e81" />

        {/* Floating Torso */}
        <path
          d="M 30 80 Q 50 78 70 80 L 66 93 Q 50 96 34 93 Z"
          fill="url(#botHeadGrad)"
          stroke="#818cf8"
          strokeWidth="1.5"
        />
        {/* Core Chest Power Orb */}
        <circle
          cx="50"
          cy="87"
          r="3.5"
          className={styles.chestOrb}
          fill={state === 'thinking' ? '#c084fc' : state === 'success' ? '#4ade80' : '#38bdf8'}
          filter="url(#eyeGlow)"
        />
      </svg>
    </div>
  );
}
