<script setup>
import { communityReports } from '../data/mockData'
</script>

<template>
  <section class="panel">
    <span class="eyebrow">Community validation</span>
    <h2>Reported issues near key cycling routes</h2>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Issue</th>
            <th>Area</th>
            <th>Status</th>
            <th>Votes</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="report in communityReports" :key="report.id">
            <td>{{ report.type }}</td>
            <td>{{ report.area }}</td>
            <td><span class="pill">{{ report.status }}</span></td>
            <td>{{ report.votes }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
