<template>
  <div class="home-scroll-container">
    <section class="hero-parallax">
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <span class="eyebrow-light">RydeSmrt Melbourne</span>
        <h1>Ride the City,<br />Smarter.</h1>
        <p>
          Intelligent routing, live safety heatmaps, and community-driven reports. Discover the
          best way to move through Melbourne.
        </p>
        <div class="hero-cta-group">
          <RouterLink to="/map" class="btn-primary-glow">Launch Map</RouterLink>
          <RouterLink :to="{ path: '/profile', hash: '#simple-recovery' }" class="btn-glass">Access Profile</RouterLink>
        </div>
      </div>
      <div class="scroll-prompt">
        <span>Explore Insights</span>
        <div class="mouse-icon">
          <div class="wheel"></div>
        </div>
      </div>
    </section>

    <div class="editorial-content">
      <section class="home-about-section">
        <div class="about-grid">
          <div class="about-title">
            <span class="eyebrow">Why RydeSmrt</span>
            <h2>Practical support for riders who want clear safety signals.</h2>
          </div>
          <div class="about-description">
            <p>
              Melbourne's cycling network can feel fragmented. A protected lane may disappear
              without warning, pushing riders into traffic-heavy roads and making a simple commute
              feel uncertain.
            </p>
            <p>
              RydeSmrt brings infrastructure data, route conditions, and community reporting into
              one web experience so riders can understand a route before committing to it.
            </p>
          </div>
        </div>
      </section>

      <section class="home-features-section">
        <span class="section-kicker">Core Capabilities</span>
        <div class="feature-cards-layout">
          <article class="feature-editorial-card">
            <div class="img-zoom-wrapper">
              <img
                src="/home-images/rider.jpg"
                alt="Cyclist moving along a protected road"
              />
            </div>
            <div class="card-inner">
              <h3>Intelligent Routing</h3>
              <p>
                Detect infrastructure gaps, compare route options, and understand where a journey
                may become exposed to surrounding traffic.
              </p>
            </div>
          </article>

          <article class="feature-editorial-card">
            <div class="img-zoom-wrapper">
              <img
                src="/home-images/heatmap.jpg"
                alt="City map with streets and spatial data"
              />
            </div>
            <div class="card-inner">
              <h3>Safety Heatmaps</h3>
              <p>
                Visualize Melbourne safety patterns through colour-coded SA2 overlays and quickly
                identify areas where cycling conditions are more supportive.
              </p>
            </div>
          </article>

          <article class="feature-editorial-card">
            <div class="img-zoom-wrapper">
              <img
                src="/home-images/takephoto.jpg"
                alt="People reporting a city street issue"
              />
            </div>
            <div class="card-inner">
              <h3>Smart Reporting</h3>
              <p>
                Report missing lanes, unsafe crossings, blocked paths, and sudden hazards so local
                cycling knowledge can improve over time.
              </p>
            </div>
          </article>
        </div>
      </section>

      <section class="home-intelligence-section">
        <div class="intelligence-grid">
          <div class="intelligence-header">
            <div class="sticky-content">
              <span class="eyebrow-dark">Rider Intelligence</span>
              <h2>From route data to decisions you can act on.</h2>
              <p>
                We analyze infrastructure, traffic, and community data to give you the clearest
                picture of your ride before you even pedal.
              </p>
            </div>
          </div>

          <div class="intelligence-cards">
            <article class="intel-card">
              <div class="card-index">01</div>
              <div class="card-text">
                <h3>Route Score</h3>
                <p>A single feasibility score turns complex infrastructure signals into a quick decision.</p>
              </div>
            </article>

            <article class="intel-card">
              <div class="card-index">02</div>
              <div class="card-text">
                <h3>Risk Segments</h3>
                <p>Colour-coded route sections reveal where a journey is comfortable, uncertain, or exposed.</p>
              </div>
            </article>

            <article class="intel-card">
              <div class="card-index">03</div>
              <div class="card-text">
                <h3>Local Reports</h3>
                <p>Community reports add current context that static cycling maps often miss.</p>
              </div>
            </article>
          </div>
        </div>
      </section>

      <section class="home-conditions-section">
        <div class="conditions-intro">
          <span class="eyebrow-dark">Riding Conditions</span>
          <h2>Safety is also shaped by the day around you.</h2>
          <p>
            Gradient, ultraviolet exposure, and air quality all change how a ride feels. Explore the
            live data behind those conditions before choosing when and where to cycle.
          </p>
          <RouterLink to="/conditions" class="conditions-link">Explore conditions</RouterLink>
        </div>

        <div class="conditions-preview-grid">
          <article class="conditions-preview-card">
            <div class="conditions-preview-card-inner">
              <div class="conditions-preview-face conditions-preview-front">
                <span>01</span>
                <h3>Elevation</h3>
                <p>See where a route becomes more demanding across sampled terrain points.</p>
              </div>
              <div class="conditions-preview-face conditions-preview-back">
                <span>Why it matters</span>
                <p>Spot climbing effort early so a route does not surprise newer riders halfway through.</p>
              </div>
            </div>
          </article>
          <article class="conditions-preview-card">
            <div class="conditions-preview-card-inner">
              <div class="conditions-preview-face conditions-preview-front">
                <span>02</span>
                <h3>UV forecast</h3>
                <p>Compare daily UV curves and identify when sun protection matters most.</p>
              </div>
              <div class="conditions-preview-face conditions-preview-back">
                <span>Why it matters</span>
                <p>Choose a safer riding window when the midday UV peak becomes less forgiving.</p>
              </div>
            </div>
          </article>
          <article class="conditions-preview-card">
            <div class="conditions-preview-card-inner">
              <div class="conditions-preview-face conditions-preview-front">
                <span>03</span>
                <h3>Air quality</h3>
                <p>Check hourly particle forecasts before committing to a longer outdoor ride.</p>
              </div>
              <div class="conditions-preview-face conditions-preview-back">
                <span>Why it matters</span>
                <p>Long rides mean deeper breathing, so particle spikes deserve a quick check first.</p>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="home-impact-section">
        <div class="impact-grid">
          <div class="impact-copy">
            <span class="eyebrow-light">City-Scale Intelligence</span>
            <h2>Powered by real urban data.</h2>
            <p>
              RydeSmrt does more than show the shortest path. It combines infrastructure signals,
              traffic exposure, Census context, and rider reports to evaluate whether a cycling
              route feels practical in real city conditions.
            </p>
            <div class="goal-badges">
              <span class="goal-tag">Traffic Exposure</span>
              <span class="goal-tag">ABS Census Context</span>
              <span class="goal-tag">Community Reports</span>
            </div>
          </div>
          <div class="impact-visual">
            <div class="data-grid-bg"></div>

            <div class="data-cards-stack">
              <div class="data-card-glow">
                <span class="big-num">2.3k+</span>
                <span class="label">Regions analysed</span>
              </div>
              <div class="data-card-glow offset-1">
                <span class="big-num">Live</span>
                <span class="label">Community validated</span>
              </div>
              <div class="data-card-glow offset-2">
                <span class="big-num">15+</span>
                <span class="label">Data layers synced</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <footer class="home-footer-pro">
      <div class="footer-container">
        <div class="footer-brand">
          <strong>RydeSmrt</strong>
          <span class="footer-divider">|</span>
          <span class="brand-group">Presented by Auracron · 2026</span>
        </div>

        <div class="footer-legal">
          <p>
            © 2026 Auracron. All rights reserved. Contains data sourced from the ABS Census, VicRoads, and
            OpenStreetMap, licensed under CC BY 4.0.
          </p>
          <p>
            <strong>Disclaimer:</strong> Feasibility scores, heatmaps, and routing recommendations are
            generated via AI and are for informational purposes only. Real-world road conditions may
            vary. Always follow local traffic regulations and ride with caution.
          </p>
          <p>Data privacy: All routing preferences and temporary location inputs are processed locally on your device.</p>
        </div>
      </div>
    </footer>
  </div>
</template>
