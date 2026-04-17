<script setup>
import { alerts } from '../data/mockData'
</script>

<template>
  <section class="map-surface" aria-label="Melbourne cycling map preview">
    <img
      src="https://tile.openstreetmap.org/13/7394/5026.png"
      alt="OpenStreetMap preview of central Melbourne"
    />
    <div class="route-line">
      <span class="point start"></span>
      <span class="point end"></span>
    </div>
    <div class="map-card">
      <strong>Risk-aware route</strong>
      <span>Green lanes, yellow caution, red gap segments</span>
    </div>
    <ul class="alert-stack" aria-label="Route alerts">
      <li v-for="alert in alerts" :key="alert.title">
        <strong>{{ alert.title }}</strong>
        <span>{{ alert.location }} · {{ alert.distance }}</span>
      </li>
    </ul>
  </section>
</template>
