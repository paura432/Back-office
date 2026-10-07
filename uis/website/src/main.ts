import './styles.css';

type Service = { number: string; title: string; copy: string; icon: string };

const services: Service[] = [
  { number: '01', title: 'Storage & inventory', copy: 'A reliable home for your products, with inventory cared for across both sides of the Atlantic.', icon: '▦' },
  { number: '02', title: 'Pick, pack & prepare', copy: 'Orders move from shelf to parcel with the attention your brand puts into every product.', icon: '↗' },
  { number: '03', title: 'Last-mile delivery', copy: 'A network of carrier partners takes every shipment closer to the customer’s door.', icon: '⌁' },
  { number: '04', title: 'Returns, handled', copy: 'A considered reverse-logistics experience for the moments when a parcel comes back.', icon: '↶' },
];

const arrow = '<span aria-hidden="true">↗</span>';

function renderService({ number, title, copy, icon }: Service): string {
  return `<article class="service-card"><div class="service-card__top"><span class="service-card__number">${number} / SERVICE</span><span class="service-card__icon" aria-hidden="true">${icon}</span></div><h3>${title}</h3><p>${copy}</p><a class="text-link" href="#contact">Explore service ${arrow}</a></article>`;
}

function renderApp(): string {
  return `
    <header class="site-header">
      <a class="brand" href="#top" aria-label="TrackFlow home"><span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span><span>trackflow<span class="brand-period">.</span></span></a>
      <nav class="main-nav" aria-label="Main navigation"><a href="#services">What we do</a><a href="#network">Our network</a><a href="#about">About us</a></nav>
      <a class="button button--dark header-cta" href="#contact">Let’s talk ${arrow}</a>
      <button class="menu-toggle" aria-label="Open navigation" aria-expanded="false"><span></span><span></span></button>
    </header>
    <main id="top">
      <section class="hero section-wrap">
        <div class="hero-copy"><p class="eyebrow"><span class="eyebrow-dot"></span> LOGISTICS, IN MOTION</p><h1>Your next order<br>is already <em>moving.</em></h1><p class="hero-lede">The people and logistics behind your e-commerce promise. We store, prepare and deliver—so your brand can keep growing.</p><div class="hero-actions"><a class="button button--lime" href="#contact">Build your flow ${arrow}</a><a class="quiet-link" href="#services">See what we do <span aria-hidden="true">↓</span></a></div><div class="hero-note"><span class="note-line"></span><span>One logistics partner.<br>From first shelf to front door.</span></div></div>
        <div class="hero-art" role="img" aria-label="Abstract illustration of a parcel moving through a connected logistics network"><div class="art-grid"></div><div class="art-route art-route--one"></div><div class="art-route art-route--two"></div><div class="art-route art-route--three"></div><div class="art-node art-node--la"><span class="node-pulse"></span><span>LOS ANGELES</span></div><div class="art-node art-node--zg"><span class="node-pulse"></span><span>ZARAGOZA</span></div><div class="parcel"><span class="parcel-top"></span><span class="parcel-side"></span><span class="parcel-tape"></span><span class="parcel-label">TF<br><small>ON ITS WAY</small></span></div><div class="art-caption"><span>YOUR BRAND</span><span class="caption-dash"></span><span>OUR NETWORK</span></div><div class="art-stamp">FULFILL<br><b>WHAT’S<br>NEXT</b></div></div>
      </section>
      <section class="ticker" aria-label="Our logistics services"><div class="ticker-track"><span>WAREHOUSE & INVENTORY</span><b>✳</b><span>ORDER FULFILLMENT</span><b>✳</b><span>LAST-MILE DELIVERY</span><b>✳</b><span>RETURNS MANAGEMENT</span><b>✳</b><span>WAREHOUSE & INVENTORY</span><b>✳</b><span>ORDER FULFILLMENT</span><b>✳</b><span>LAST-MILE DELIVERY</span><b>✳</b><span>RETURNS MANAGEMENT</span><b>✳</b></div></section>
      <section class="intro section-wrap" id="about"><div class="section-kicker"><span>01</span><span>THE TRACKFLOW WAY</span></div><div class="intro-content"><h2>Good products deserve<br>a <em>great journey.</em></h2><div class="intro-text"><p>You make something people love. We take care of everything that happens after the order comes in—from a place on the shelf to a parcel at the door, and what happens if it comes back.</p><p>One connected logistics partner, built around the way e-commerce actually works.</p></div></div></section>
      <section class="services-section" id="services"><div class="section-wrap"><div class="services-heading"><div><p class="eyebrow">FROM SHELF TO SOMEONE’S DOOR</p><h2>Every step,<br><em>in good hands.</em></h2></div><p class="services-intro">The details behind a delivery matter. We bring the essential parts of your logistics operation together, so each order can move with care.</p></div><div class="service-grid">${services.map(renderService).join('')}</div></div></section>
      <section class="network-section" id="network"><div class="network-visual"><div class="network-circle network-circle--outer"></div><div class="network-circle network-circle--inner"></div><div class="network-map-label">TWO CONTINENTS<br><span>ONE CONNECTED OPERATION</span></div><div class="network-city network-city--la"><span></span><b>Los Angeles</b><small>UNITED STATES</small></div><div class="network-city network-city--zg"><span></span><b>Zaragoza</b><small>SPAIN</small></div><svg class="network-arc" viewBox="0 0 500 300" aria-hidden="true"><path d="M55 215 C145 16 315 16 430 92" /></svg><span class="network-plane" aria-hidden="true">✳</span></div><div class="network-copy"><p class="eyebrow"><span class="eyebrow-dot"></span> LOCAL KNOW-HOW, INTERNATIONAL REACH</p><h2>Across oceans.<br><em>Closer together.</em></h2><p>With warehouse operations in Los Angeles and Zaragoza, TrackFlow supports brands across the United States and Spain. Two locations, connected by one commitment: getting your products where they need to go.</p><a class="text-link text-link--light" href="#contact">Let’s move forward ${arrow}</a><div class="network-coordinates"><span>34°03' N &nbsp; 118°14' W</span><span>41°39' N &nbsp; 0°53' W</span></div></div></section>
      <section class="promise section-wrap"><div class="promise-mark"><span class="brand-mark brand-mark--large" aria-hidden="true"><i></i><i></i><i></i></span></div><div><p class="eyebrow">THE WORK BEHIND THE PROMISE</p><h2>Your customer sees<br>the delivery. <em>You know<br>what it took.</em></h2></div><p class="promise-aside">Thoughtful fulfillment lets you focus on what comes next: building your brand, your products and the relationships that make them matter.</p></section>
      <section class="contact-section" id="contact"><div class="contact-inner section-wrap"><div><p class="eyebrow"><span class="eyebrow-dot"></span> READY WHEN YOU ARE</p><h2>Let’s get your<br>orders <em>moving.</em></h2></div><div class="contact-action"><p>Tell us where you want to go. We’ll talk through what it takes to get there.</p><a class="button button--lime" href="#services">Explore our services ${arrow}</a><span class="contact-small">For e-commerce brands ready for the next step.</span></div><div class="contact-orbit" aria-hidden="true"></div></div></section>
    </main>
    <footer class="site-footer"><a class="brand brand--footer" href="#top"><span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span><span>trackflow<span class="brand-period">.</span></span></a><span>Logistics for the journey ahead.</span><span class="footer-locations">LOS ANGELES <i>·</i> ZARAGOZA</span><span class="footer-copy">© TrackFlow</span></footer>
  `;
}

const root = document.querySelector<HTMLDivElement>('#app');
if (!root) throw new Error('App root #app was not found');
root.innerHTML = renderApp();

document.querySelector<HTMLButtonElement>('.menu-toggle')?.addEventListener('click', (event) => {
  const button = event.currentTarget as HTMLButtonElement;
  const expanded = button.getAttribute('aria-expanded') === 'true';
  button.setAttribute('aria-expanded', String(!expanded));
  document.querySelector('.main-nav')?.classList.toggle('main-nav--open', !expanded);
});

document.querySelectorAll<HTMLAnchorElement>('.main-nav a').forEach((link) => {
  link.addEventListener('click', () => {
    document.querySelector('.main-nav')?.classList.remove('main-nav--open');
    document.querySelector('.menu-toggle')?.setAttribute('aria-expanded', 'false');
  });
});
