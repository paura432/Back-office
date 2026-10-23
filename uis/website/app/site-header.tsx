'use client';

import { useState } from 'react';
import { BrandMark } from './brand-mark';
import { DecorativeArrow } from './decorative-arrow';

const arrow = <DecorativeArrow />;

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <header className="site-header">
      <a className="brand" href="#top" aria-label="TrackFlow home"><BrandMark /><span>trackflow<span className="brand-period">.</span></span></a>
      <nav className={`main-nav${menuOpen ? ' main-nav--open' : ''}`} aria-label="Main navigation" onClick={() => setMenuOpen(false)}><a href="#services">What we do</a><a href="#network">Our network</a><a href="#about">About us</a></nav>
      <a className="button button--dark header-cta" href="#contact">Let’s talk {arrow}</a>
      <button className="menu-toggle" aria-label="Open navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}><span></span><span></span></button>
    </header>
  );
}
