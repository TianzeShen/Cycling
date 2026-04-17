<script setup>
import { badges } from '../data/mockData'
</script>

<template>
  <section class="profile-grid">
    <article class="panel profile-summary">
      <span class="eyebrow">Contribution impact</span>
      <h2>426 safety points</h2>
      <p>18 reports submitted - 64 validations received - 9 routes improved</p>
    </article>

    <article v-for="badge in badges" :key="badge.name" class="panel badge-card">
      <span class="badge-icon">{{ badge.name.charAt(0) }}</span>
      <h3>{{ badge.name }}</h3>
      <p>{{ badge.detail }}</p>
    </article>
  </section>
</template>
