'use client';

import { useState } from 'react';

type Service = { number: string; title: string; copy: string; icon: string };

const services: Service[] = [
  { number: '01', title: 'Storage & inventory', copy: 'A reliable home for your products, with inventory cared for across both sides of the Atlantic.', icon: '▦' },
  { number: '02', title: 'Pick, pack & prepare', copy: 'Orders move from shelf to parcel with the attention your brand puts into every product.', icon: '↗' },
  { number: '03', title: 'Last-mile delivery', copy: 'A network of carrier partners takes every shipment closer to the customer’s door.', icon: '⌁' },
  { number: '04', title: 'Returns, handled', copy: 'A considered reverse-logistics experience for the moments when a parcel comes back.', icon: '↶' },
];

const arrow = <span aria-hidden="true">↗</span>;

function ServiceCard({ number, title, copy, icon }: Service) {
  return <article className="service-card"><div className="service-card__top"><span className="service-card__number">{number} / SERVICE</span><span className="service-card__icon" aria-hidden="true">{icon}</span></div><h3>{title}</h3><p>{copy}</p><a className="text-link" href="#contact">Explore service {arrow}</a></article>;
}

export default function Website() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div id="app">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="TrackFlow home"><span className="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span><span>trackflow<span className="brand-period">.</span></span></a>
        <nav className={`main-nav${menuOpen ? ' main-nav--open' : ''}`} aria-label="Main navigation" onClick={() => setMenuOpen(false)}><a href="#services">What we do</a><a href="#network">Our network</a><a href="#about">About us</a></nav>
        <a className="button button--dark header-cta" href="#contact">Let’s talk {arrow}</a>
        <button className="menu-toggle" aria-label="Open navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}><span></span><span></span></button>
      </header>
      <main id="top">
        <section className="hero section-wrap">
          <div className="hero-copy"><p className="eyebrow"><span className="eyebrow-dot"></span> LOGISTICS, IN MOTION</p><h1>Your next order<br />is already <em>moving.</em></h1><p className="hero-lede">The people and logistics behind your e-commerce promise. We store, prepare and deliver—so your brand can keep growing.</p><div className="hero-actions"><a className="button button--lime" href="#contact">Build your flow {arrow}</a><a className="quiet-link" href="#services">See what we do <span aria-hidden="true">↓</span></a></div><div className="hero-note"><span className="note-line"></span><span>One logistics partner.<br />From first shelf to front door.</span></div></div>
          <div className="hero-art" role="img" aria-label="Abstract illustration of a parcel moving through a connected logistics network"><div className="art-grid"></div><div className="art-route art-route--one"></div><div className="art-route art-route--two"></div><div className="art-route art-route--three"></div><div className="art-node art-node--la"><span className="node-pulse"></span><span>LOS ANGELES</span></div><div className="art-node art-node--zg"><span className="node-pulse"></span><span>ZARAGOZA</span></div><div className="parcel"><span className="parcel-top"></span><span className="parcel-side"></span><span className="parcel-tape"></span><span className="parcel-label">TF<br /><small>ON ITS WAY</small></span></div><div className="art-caption"><span>YOUR BRAND</span><span className="caption-dash"></span><span>OUR NETWORK</span></div><div className="art-stamp">FULFILL<br /><b>WHAT’S<br />NEXT</b></div></div>
        </section>
        <section className="ticker" aria-label="Our logistics services"><div className="ticker-track"><span>WAREHOUSE &amp; INVENTORY</span><b>✳</b><span>ORDER FULFILLMENT</span><b>✳</b><span>LAST-MILE DELIVERY</span><b>✳</b><span>RETURNS MANAGEMENT</span><b>✳</b><span>WAREHOUSE &amp; INVENTORY</span><b>✳</b><span>ORDER FULFILLMENT</span><b>✳</b><span>LAST-MILE DELIVERY</span><b>✳</b><span>RETURNS MANAGEMENT</span><b>✳</b></div></section>
        <section className="intro section-wrap" id="about"><div className="section-kicker"><span>01</span><span>THE TRACKFLOW WAY</span></div><div className="intro-content"><h2>Good products deserve<br />a <em>great journey.</em></h2><div className="intro-text"><p>You make something people love. We take care of everything that happens after the order comes in—from a place on the shelf to a parcel at the door, and what happens if it comes back.</p><p>One connected logistics partner, built around the way e-commerce actually works.</p></div></div></section>
        <section className="services-section" id="services"><div className="section-wrap"><div className="services-heading"><div><p className="eyebrow">FROM SHELF TO SOMEONE’S DOOR</p><h2>Every step,<br /><em>in good hands.</em></h2></div><p className="services-intro">The details behind a delivery matter. We bring the essential parts of your logistics operation together, so each order can move with care.</p></div><div className="service-grid">{services.map((service) => <ServiceCard key={service.number} {...service} />)}</div></div></section>
        <section className="network-section" id="network"><div className="network-visual"><div className="network-circle network-circle--outer"></div><div className="network-circle network-circle--inner"></div><div className="network-map-label">TWO CONTINENTS<br /><span>ONE CONNECTED OPERATION</span></div><div className="network-city network-city--la"><span></span><b>Los Angeles</b><small>UNITED STATES</small></div><div className="network-city network-city--zg"><span></span><b>Zaragoza</b><small>SPAIN</small></div><svg className="network-arc" viewBox="0 0 500 300" aria-hidden="true"><path d="M55 215 C145 16 315 16 430 92" /></svg><span className="network-plane" aria-hidden="true">✳</span></div><div className="network-copy"><p className="eyebrow"><span className="eyebrow-dot"></span> LOCAL KNOW-HOW, INTERNATIONAL REACH</p><h2>Across oceans.<br /><em>Closer together.</em></h2><p>With warehouse operations in Los Angeles and Zaragoza, TrackFlow supports brands across the United States and Spain. Two locations, connected by one commitment: getting your products where they need to go.</p><a className="text-link text-link--light" href="#contact">Let’s move forward {arrow}</a><div className="network-coordinates"><span>34°03&apos; N &nbsp; 118°14&apos; W</span><span>41°39&apos; N &nbsp; 0°53&apos; W</span></div></div></section>
        <section className="promise section-wrap"><div className="promise-mark"><span className="brand-mark brand-mark--large" aria-hidden="true"><i></i><i></i><i></i></span></div><div><p className="eyebrow">THE WORK BEHIND THE PROMISE</p><h2>Your customer sees<br />the delivery. <em>You know<br />what it took.</em></h2></div><p className="promise-aside">Thoughtful fulfillment lets you focus on what comes next: building your brand, your products and the relationships that make them matter.</p></section>
        <section className="contact-section" id="contact"><div className="contact-inner section-wrap"><div><p className="eyebrow"><span className="eyebrow-dot"></span> READY WHEN YOU ARE</p><h2>Let’s get your<br />orders <em>moving.</em></h2></div><div className="contact-action"><p>Tell us where you want to go. We’ll talk through what it takes to get there.</p><a className="button button--lime" href="#services">Explore our services {arrow}</a><span className="contact-small">For e-commerce brands ready for the next step.</span></div><div className="contact-orbit" aria-hidden="true"></div></div></section>
      </main>
      <footer className="site-footer"><a className="brand brand--footer" href="#top"><span className="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span><span>trackflow<span className="brand-period">.</span></span></a><span>Logistics for the journey ahead.</span><span className="footer-locations">LOS ANGELES <i>·</i> ZARAGOZA</span><span className="footer-copy">© TrackFlow</span></footer>
    </div>
  );
}