import React, { useState, useEffect } from 'react';

interface HeroTextProps {
  language: string;
}

const HeroText: React.FC<HeroTextProps> = ({ language }) => {
  const titleText = language === 'zh-cn' || language === 'zh-tw' ? '你好, 我是 AgentRAG' : 'Hello, I am AgentRAG';
  const descText = language === 'zh-cn' || language === 'zh-tw'
    ? '请问我一些问题吧！'
    : 'Ask me some questions please!';

  const [displayedTitle, setDisplayedTitle] = useState('');
  const [displayedDesc, setDisplayedDesc] = useState('');
  const [isTypingDone, setIsTypingDone] = useState(false);

  // Reset text when language changes
  useEffect(() => {
    setDisplayedTitle('');
    setDisplayedDesc('');
    setIsTypingDone(false);

    let tIndex = 0;
    const tInterval = setInterval(() => {
      if (tIndex <= titleText.length) {
        setDisplayedTitle(titleText.slice(0, tIndex));
        tIndex++;
      } else {
        clearInterval(tInterval);
      }
    }, 100); // Title speed

    return () => clearInterval(tInterval);
  }, [titleText]);

  // Start description after title is roughly done (or just run in parallel but slower/delayed?
  // User asked for "print effect", usually sequential or parallel is fine.
  // Let's make description start after a short delay or run independently but maybe slower.
  // Actually, let's run it with a slight delay so it feels like a sequence.
  useEffect(() => {
    let dIndex = 0;
    const timeout = setTimeout(() => {
      const dInterval = setInterval(() => {
        if (dIndex <= descText.length) {
          setDisplayedDesc(descText.slice(0, dIndex));
          dIndex++;
        } else {
          clearInterval(dInterval);
          setIsTypingDone(true);
        }
      }, 50); // Description speed (faster)
      return () => clearInterval(dInterval);
    }, titleText.length * 100 + 200); // Wait for title to finish + 200ms

    return () => clearTimeout(timeout);
  }, [descText, titleText.length]);

  // Blinking cursor effect
  const [showCursor, setShowCursor] = useState(true);
  useEffect(() => {
    const interval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="d-flex flex-column align-items-center w-100">
      <div style={{ width: '100%', maxWidth: '900px', position: 'relative' }}>
        <svg width="100%" viewBox="0 0 900 220" style={{ overflow: 'visible' }}>
          <defs>
            {/*
              Title Curve: Higher and narrower
              M 200 120 Q 450 20 700 120
            */}
            <path id="titleCurve" d="M 200 120 Q 450 20 700 120" fill="transparent" />

            {/*
              Description Curve: Lower but same curvature as Title
              Parallel-ish curve: Start lower, control point lower
              M 200 170 Q 450 70 700 170
            */}
            <path id="descCurve" d="M 200 170 Q 450 70 700 170" fill="transparent" />
          </defs>

          {/* Title Text */}
          <text style={{ fill: 'var(--lingnan-red)', fontSize: '36px', fontWeight: 'bold', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
            <textPath href="#titleCurve" startOffset="50%" textAnchor="middle">
              {displayedTitle}
            </textPath>
          </text>

          {/* Description Text */}
          <text style={{ fill: '#6c757d', fontSize: '18px', fontWeight: '500', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
            <textPath href="#descCurve" startOffset="50%" textAnchor="middle">
              {displayedDesc}{(!isTypingDone && showCursor) ? '|' : ''}
            </textPath>
          </text>
        </svg>
      </div>
    </div>
  );
};

export default HeroText;
