<template>
  <div class="home-page-scroll">
    <section class="hero-parallax">
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <h1>Ride the City,<br />Smarter.</h1>
        <p>
          Intelligent routing, live safety heatmaps, and community-driven reports. Discover the
          best way to move through Melbourne.
        </p>
        <div class="hero-actions">
          <RouterLink to="/map">
            <button class="primary hero-button">Launch Map</button>
          </RouterLink>
          <RouterLink to="/report">
            <button class="hero-button hero-ghost-button">Report Issue</button>
          </RouterLink>
        </div>
      </div>
      <div class="scroll-indicator">Scroll Down</div>
    </section>

    <section class="home-features">
      <article class="feature-card">
        <h2 class="feature-number mint">01</h2>
        <h3>Intelligent Routing</h3>
        <p>We analyze route data to find paths with continuous cycling infrastructure.</p>
      </article>

      <article class="feature-card">
        <h2 class="feature-number violet">02</h2>
        <h3>Live Heatmaps</h3>
        <p>Toggle the SA2 layer to visualize risk patterns and avoid exposed intersections.</p>
      </article>

      <article class="feature-card">
        <h2 class="feature-number slate">03</h2>
        <h3>Community Alerts</h3>
        <p>Warn fellow cyclists about road closures, blocked lanes, and sudden hazards.</p>
      </article>
    </section>
  </div>
</template>
