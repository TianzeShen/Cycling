<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const slopeCanvas = ref(null)
const uvCanvas = ref(null)
const aqiCanvas = ref(null)

let charts = []
let observer = null

function loadChartJs() {
  if (window.Chart) {
    return Promise.resolve(window.Chart)
  }

  return new Promise((resolve, reject) => {
    const existingScript = document.querySelector('script[data-chartjs-loader="true"]')

    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(window.Chart), { once: true })
      existingScript.addEventListener('error', reject, { once: true })
      return
    }

    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'
    script.async = true
    script.dataset.chartjsLoader = 'true'
    script.onload = () => resolve(window.Chart)
    script.onerror = reject
    document.head.appendChild(script)
  })
}

function createTooltipOptions() {
  return {
    backgroundColor: '#fff',
    titleColor: '#1f2937',
    bodyColor: '#374151',
    borderColor: '#e5e7eb',
    borderWidth: 1,
    padding: 10,
    cornerRadius: 8,
  }
}

function buildCharts(Chart) {
  Chart.defaults.color = '#9ca3af'
  Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
  Chart.defaults.font.size = 12

  const tip = createTooltipOptions()

  charts = [
    new Chart(slopeCanvas.value, {
      type: 'bar',
      data: {
        labels: ['0-1%', '1-3%', '3-5%', '5-8%', '8-12%', '12%+'],
        datasets: [
          {
            data: [42.3, 31.5, 14.8, 7.2, 3.1, 1.1],
            backgroundColor: ['#10b981cc', '#10b981cc', '#f59e0bcc', '#f97316cc', '#ef4444cc', '#ef4444cc'],
            borderColor: ['#10b981', '#10b981', '#f59e0b', '#f97316', '#ef4444', '#ef4444'],
            borderWidth: 1,
            borderRadius: 5,
            barPercentage: 0.6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 800, easing: 'easeOutQuart' },
        plugins: {
          legend: { display: false },
          tooltip: { ...tip, callbacks: { label: (context) => `${context.parsed.y}% of roads` } },
        },
        scales: {
          y: { beginAtZero: true, grid: { display: false }, ticks: { callback: (value) => `${value}%` } },
          x: { grid: { display: false } },
        },
      },
    }),
    new Chart(uvCanvas.value, {
      type: 'line',
      data: {
        labels: ['6AM', '7AM', '8AM', '9AM', '10AM', '11AM', '12PM', '1PM', '2PM', '3PM', '4PM', '5PM', '6PM', '7PM'],
        datasets: [
          createUvLine('Summer', [0.2, 0.8, 2.5, 5.1, 7.8, 10.2, 11.5, 11.8, 10.4, 7.6, 4.8, 2.1, 0.5, 0.1], '#ef4444', 2.5),
          createUvLine('Spring', [0.1, 0.5, 1.6, 3.5, 5.6, 7.4, 8.2, 8, 6.5, 4.3, 2.2, 0.8, 0.1, 0], '#f97316'),
          createUvLine('Autumn', [0, 0.3, 1.2, 2.8, 4.5, 5.8, 6.4, 6.2, 5.1, 3.4, 1.8, 0.6, 0.1, 0], '#eab308'),
          createUvLine('Winter', [0, 0.1, 0.4, 1, 1.8, 2.3, 2.6, 2.4, 1.9, 1.2, 0.5, 0.1, 0, 0], '#60a5fa'),
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1000, easing: 'easeOutQuart' },
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: { usePointStyle: true, pointStyle: 'line', padding: 14, font: { size: 11 } },
          },
          tooltip: { ...tip, callbacks: { label: (context) => `${context.dataset.label}: UV ${context.parsed.y}` } },
        },
        scales: {
          y: { beginAtZero: true, max: 14, grid: { display: false } },
          x: { grid: { display: false } },
        },
      },
      plugins: [uvThresholdPlugin],
    }),
    new Chart(aqiCanvas.value, {
      type: 'bar',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        datasets: [
          {
            label: 'Monthly average',
            data: [8.2, 7.8, 7.5, 8.1, 9.8, 11.2, 12.5, 11.8, 9.2, 8.4, 7.9, 8],
            backgroundColor: [8.2, 7.8, 7.5, 8.1, 9.8, 11.2, 12.5, 11.8, 9.2, 8.4, 7.9, 8].map(
              (value) => `${airColor(value)}bb`,
            ),
            borderColor: [8.2, 7.8, 7.5, 8.1, 9.8, 11.2, 12.5, 11.8, 9.2, 8.4, 7.9, 8].map(airColor),
            borderWidth: 1,
            borderRadius: 5,
            barPercentage: 0.45,
            order: 2,
          },
          {
            label: 'Worst day on record',
            data: [85, 62, 38, 28, 42, 55, 58, 48, 35, 30, 45, 95],
            type: 'line',
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.04)',
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 3,
            pointBackgroundColor: [85, 62, 38, 28, 42, 55, 58, 48, 35, 30, 45, 95].map(airColor),
            pointBorderColor: '#fff',
            pointBorderWidth: 1.5,
            order: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 900, easing: 'easeOutQuart' },
        plugins: {
          legend: { position: 'top', labels: { usePointStyle: true, padding: 14, font: { size: 11 } } },
          tooltip: { ...tip, callbacks: { label: (context) => `${context.dataset.label}: ${context.parsed.y} ug/m3` } },
        },
        scales: {
          y: { beginAtZero: true, max: 110, grid: { display: false } },
          x: { grid: { display: false } },
        },
      },
      plugins: [airThresholdPlugin],
    }),
  ]
}

function createUvLine(label, data, color, width = 2) {
  return {
    label,
    data,
    borderColor: color,
    borderWidth: width,
    tension: 0.4,
    fill: false,
    pointRadius: 0,
    pointHoverRadius: 5,
  }
}

function airColor(value) {
  if (value <= 12) {
    return '#10b981'
  }

  if (value <= 35) {
    return '#f59e0b'
  }

  if (value <= 55) {
    return '#f97316'
  }

  return '#ef4444'
}

const uvThresholdPlugin = {
  id: 'uvLine',
  afterDraw(chart) {
    const y = chart.scales.y.getPixelForValue(3)
    const context = chart.ctx
    context.save()
    context.setLineDash([5, 4])
    context.strokeStyle = '#9ca3af66'
    context.lineWidth = 1
    context.beginPath()
    context.moveTo(chart.chartArea.left, y)
    context.lineTo(chart.chartArea.right, y)
    context.stroke()
    context.fillStyle = '#6b7280'
    context.font = '10px -apple-system, sans-serif'
    context.textAlign = 'right'
    context.fillText('UV 3 - protection needed (WHO)', chart.chartArea.right - 4, y - 5)
    context.restore()
  },
}

const airThresholdPlugin = {
  id: 'lines',
  afterDraw(chart) {
    const context = chart.ctx
    const yScale = chart.scales.y
    context.save()
    context.font = '10px -apple-system, sans-serif'
    context.textAlign = 'right'

    const guidelineY = yScale.getPixelForValue(15)
    context.setLineDash([5, 4])
    context.strokeStyle = '#d4a01766'
    context.lineWidth = 1
    context.beginPath()
    context.moveTo(chart.chartArea.left, guidelineY)
    context.lineTo(chart.chartArea.right, guidelineY)
    context.stroke()
    context.fillStyle = '#92700c'
    context.fillText('WHO guideline - 15 ug/m3', chart.chartArea.right - 4, guidelineY - 5)

    const avoidY = yScale.getPixelForValue(55)
    context.setLineDash([5, 4])
    context.strokeStyle = '#9ca3af55'
    context.lineWidth = 1
    context.beginPath()
    context.moveTo(chart.chartArea.left, avoidY)
    context.lineTo(chart.chartArea.right, avoidY)
    context.stroke()
    context.fillStyle = '#6b7280'
    context.fillText('Avoid outdoor cycling - 55 ug/m3', chart.chartArea.right - 4, avoidY - 5)
    context.restore()
  },
}

onMounted(async () => {
  await nextTick()

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible')
        }
      })
    },
    { threshold: 0.12 },
  )

  document.querySelectorAll('.copied-card').forEach((card) => observer.observe(card))

  try {
    const Chart = await loadChartJs()
    buildCharts(Chart)
  } catch (error) {
    // The page shell still remains readable if the CDN script cannot load.
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  charts.forEach((chart) => chart.destroy())
  charts = []
})
</script>

<template>
  <section class="copied-insights-page">
    <div class="copied-insights-container">
      <h1 class="copied-page-title">Safety <span>Insights</span></h1>
      <p class="copied-page-desc">Things every Melbourne cyclist should know before heading out.</p>

      <article class="copied-card">
        <h2 class="copied-card-title">How steep are Melbourne's roads?</h2>
        <p class="copied-card-text">
          Most roads in Melbourne are fairly flat - about <strong>74% have a gradient under 3%</strong>,
          which is comfortable for all riders. But around <strong>4% of roads are steeper than 8%</strong>.
          On these sections, going downhill means longer braking distances, and going uphill can push
          your heart rate into unsafe territory.
        </p>
        <div class="copied-chart-wrap"><canvas ref="slopeCanvas"></canvas></div>
        <div class="copied-advice">
          <span class="copied-advice-icon">Advice</span>
          <p>
            If you're new to cycling, <strong>try to avoid roads above 5% gradient</strong>. Plan your
            route on flat terrain first and work your way up as you build confidence.
          </p>
        </div>
        <p class="copied-source">Data: Open-Meteo Elevation API (Copernicus DEM GLO-90) - CC BY 4.0</p>
      </article>

      <article class="copied-card">
        <h2 class="copied-card-title">When is the sun too strong to ride?</h2>
        <p class="copied-card-text">
          Australia's UV is among the highest in the world. The WHO says you should
          <strong>protect your skin when UV reaches 3 or above</strong>. In Melbourne's summer, UV
          shoots past 10 between 11 AM and 2 PM. Even in autumn and spring, midday UV regularly hits 5-7.
        </p>
        <div class="copied-chart-wrap"><canvas ref="uvCanvas"></canvas></div>
        <div class="copied-advice">
          <span class="copied-advice-icon">Advice</span>
          <p>
            <strong>Ride before 9 AM or after 4 PM in summer</strong> to avoid peak UV. Always wear
            sunscreen (SPF 50+), sunglasses, and consider UV-protective arm sleeves.
          </p>
        </div>
        <p class="copied-source">Data: Open-Meteo Forecast API (GFS UV Index) - CC BY 4.0</p>
      </article>

      <article class="copied-card">
        <h2 class="copied-card-title">Is the air safe to breathe while cycling?</h2>
        <p class="copied-card-text">
          When you ride, you breathe <strong>2 to 5 times more air</strong> than when you walk, so you
          take in more pollution too. The WHO says PM2.5 should stay <strong>below 15 ug/m3 over 24 hours</strong>.
          Melbourne's daily average is usually fine. But during bushfire season (Dec-Jan) or cold still
          winter nights, PM2.5 can spike above 80.
        </p>
        <div class="copied-chart-wrap"><canvas ref="aqiCanvas"></canvas></div>
        <div class="copied-advice">
          <span class="copied-advice-icon">Advice</span>
          <p>
            <strong>Check air quality before you ride</strong>, especially in Jan-Feb and Jun-Jul. If
            PM2.5 is over 55, consider an indoor workout instead.
          </p>
        </div>
        <p class="copied-source">Data: Open-Meteo Air Quality API (CAMS) - CC BY 4.0</p>
      </article>
    </div>
  </section>
</template>
