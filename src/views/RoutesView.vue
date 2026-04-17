<script setup>
import MapPreview from '../components/MapPreview.vue'
import RouteCard from '../components/RouteCard.vue'
import { routeOptions } from '../data/mockData'
</script>

<template>
  <div class="page-grid">
    <section>
      <span class="eyebrow">Personalised options</span>
      <h2>Choose by safety, time, and comfort</h2>
      <div class="route-list">
        <RouteCard v-for="route in routeOptions" :key="route.id" :route="route" />
      </div>
    </section>
    <MapPreview />
  </div>
</template>
