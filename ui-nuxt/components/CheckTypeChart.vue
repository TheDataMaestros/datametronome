<template>
  <div class="w-full" :style="height ? `height: ${height}px` : 'height: 100%'">
    <div
      v-if="!data || !hasData"
      class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400"
    >
      <div class="text-center">
        <Icon name="i-heroicons-chart-bar" class="w-12 h-12 mx-auto mb-2 text-gray-400" />
        <p>No data available for {{ checkType }} checks</p>
      </div>
    </div>
    <TrendChart
      v-else
      :data="chartData"
      :type="chartType"
      :height="height"
      :show-legend="showLegend"
      :options="chartOptions"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  checkType: string
  data: any[]
  height?: number
  showLegend?: boolean
  clefConfig?: Record<string, any> // Clef configuration to get thresholds
  clefWarn?: string | null // Warn condition (e.g., "< 1200")
  clefFail?: string | null // Fail condition (e.g., "< 1000")
}

const props = withDefaults(defineProps<Props>(), {
  height: 300,
  showLegend: true,
  clefConfig: () => ({}),
  clefWarn: null,
  clefFail: null,
})

const hasData = computed(() => {
  if (!props.data || props.data.length === 0) return false

  // Check if we have data for this specific check type
  const checkTypeData = props.data.filter((item: any) => {
    const itemType = String(item?.check_type || '').toLowerCase()
    return (
      itemType === props.checkType.toLowerCase() ||
      (props.checkType === 'drift' && (itemType === 'data_profile_drift' || itemType === 'drift'))
    )
  })

  return checkTypeData.length > 0
})

const chartType = computed(() => {
  // Different chart types for different check types
  const typeMap: Record<string, 'line' | 'bar'> = {
    row_count: 'line',
    freshness: 'line',
    column_values: 'bar',
    forecast: 'line',
    data_profile_drift: 'line',
    drift: 'line',
    lookup_validation: 'bar',
    python: 'line',
  }
  return typeMap[props.checkType] || 'line'
})

const chartData = computed(() => {
  if (!hasData.value) return null

  const checkTypeData = props.data.filter((item: any) => {
    const itemType = String(item?.check_type || '').toLowerCase()
    return (
      itemType === props.checkType.toLowerCase() ||
      (props.checkType === 'drift' && (itemType === 'data_profile_drift' || itemType === 'drift'))
    )
  })

  if (checkTypeData.length === 0) return null

  // Process data based on check type
  switch (props.checkType.toLowerCase()) {
    case 'row_count':
      return buildRowCountChart(checkTypeData)
    case 'freshness':
      return buildFreshnessChart(checkTypeData)
    case 'column_values':
      return buildColumnValuesChart(checkTypeData)
    case 'forecast':
      return buildForecastChart(checkTypeData)
    case 'drift':
    case 'data_profile_drift':
      return buildDriftChart(checkTypeData)
    default:
      return buildGenericChart(checkTypeData)
  }
})

function buildRowCountChart(data: any[]) {
  const points = data
    .map((r: any) => {
      const ts = parseTimestamp(r?.timestamp || r?.executed_at || r?.executed_at)
      const label = ts.toLocaleTimeString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
      })
      const meta = r?.metadata || r?.details || {}

      // Try multiple ways to get the count value - check metadata first, then top level
      let count = Number(
        meta?.row_count ??
          meta?.count ??
          meta?.actual_count ??
          meta?.total_orders ?? // From sample data
          meta?.total_rows ??
          r?.observed_value ?? // Sometimes the value is directly in observed_value
          (typeof meta === 'object' && meta !== null ? meta.value : null),
      )

      // If still no value and metadata is a string, try parsing it
      if (!Number.isFinite(count) && typeof meta === 'string') {
        try {
          const parsed = JSON.parse(meta)
          count = Number(
            parsed?.row_count ?? parsed?.count ?? parsed?.total_orders ?? parsed?.observed_value,
          )
        } catch {
          // Not JSON, ignore
        }
      }

      // Get thresholds from multiple sources:
      // 1. Check result metadata (expected_range, expected_min/max)
      // 2. Clef config (expected_min/max)
      // 3. Parse warn/fail conditions (e.g., "< 1200" -> min: 1200)

      // Helper function to extract number from condition string like "< 1200" or "> 5000"
      const extractThresholdFromCondition = (
        condition: string | null | undefined,
      ): number | null => {
        if (!condition || typeof condition !== 'string') return null
        const match = condition.match(/[<>]=?\s*(\d+(?:\.\d+)?)/)
        return match ? Number(match[1]) : null
      }

      const expectedRange = meta?.expected_range || {}

      // Try to get min threshold from multiple sources
      let expectedMin = Number(
        expectedRange?.min ??
          meta?.expected_min ??
          meta?.min_threshold ??
          meta?.min_expected ??
          props.clefConfig?.expected_min,
      )

      // If no min found, try parsing from fail condition (prefer fail over warn for min)
      if (!Number.isFinite(expectedMin)) {
        const failCondition = meta?.fail_condition || r?.fail_condition || props.clefFail
        if (failCondition) {
          const failThreshold = extractThresholdFromCondition(failCondition)
          if (failThreshold !== null && failCondition.includes('<')) {
            expectedMin = failThreshold
          }
        }
      }

      // If still no min, try parsing from warn condition
      if (!Number.isFinite(expectedMin)) {
        const warnCondition = meta?.warn_condition || r?.warn_condition || props.clefWarn
        if (warnCondition) {
          const warnThreshold = extractThresholdFromCondition(warnCondition)
          if (warnThreshold !== null && warnCondition.includes('<')) {
            expectedMin = warnThreshold
          }
        }
      }

      // Try to get max threshold from multiple sources
      let expectedMax = Number(
        expectedRange?.max ??
          meta?.expected_max ??
          meta?.max_threshold ??
          meta?.max_expected ??
          props.clefConfig?.expected_max,
      )

      // If no max found, try parsing from warn/fail conditions (e.g., "> 5000" means max is 5000)
      if (!Number.isFinite(expectedMax)) {
        const warnCondition = meta?.warn_condition || r?.warn_condition || props.clefWarn
        const warnThreshold = extractThresholdFromCondition(warnCondition)
        if (warnThreshold !== null && warnCondition?.includes('>')) {
          expectedMax = warnThreshold
        }
      }

      if (!Number.isFinite(expectedMax)) {
        const failCondition = meta?.fail_condition || r?.fail_condition || props.clefFail
        const failThreshold = extractThresholdFromCondition(failCondition)
        if (failThreshold !== null && failCondition?.includes('>')) {
          expectedMax = failThreshold
        }
      }
      // Determine if this point is an outlier
      let isOutlier = false
      if (Number.isFinite(count)) {
        if (Number.isFinite(expectedMin) && Number.isFinite(expectedMax)) {
          isOutlier = count < expectedMin || count > expectedMax
        } else if (Number.isFinite(expectedMin)) {
          isOutlier = count < expectedMin
        } else if (Number.isFinite(expectedMax)) {
          isOutlier = count > expectedMax
        }
      }

      return { label, value: count, min: expectedMin, max: expectedMax, isOutlier }
    })
    .filter((p) => p.label && Number.isFinite(p.value) && p.value > 0)
    .reverse()

  if (points.length === 0) return null

  // Check if we have any valid thresholds
  const hasMin = points.some((p) => Number.isFinite(p.min))
  const hasMax = points.some((p) => Number.isFinite(p.max))

  const datasets: any[] = []

  // Add maximum threshold line if we have max values
  if (hasMax) {
    datasets.push({
      label: 'Expected Maximum',
      data: points.map((p) => (Number.isFinite(p.max) ? p.max : null)) as any,
      borderColor: 'rgba(239, 68, 68, 0.8)', // Red for max threshold
      backgroundColor: 'rgba(239, 68, 68, 0.1)',
      borderWidth: 2,
      borderDash: [8, 4],
      fill: false,
      pointRadius: 0,
      order: 1, // Render after main data
    })
  }

  // Add minimum threshold line if we have min values
  if (hasMin) {
    datasets.push({
      label: 'Expected Minimum',
      data: points.map((p) => (Number.isFinite(p.min) ? p.min : null)) as any,
      borderColor: 'rgba(34, 197, 94, 0.8)', // Green for min threshold
      backgroundColor: 'rgba(34, 197, 94, 0.1)',
      borderWidth: 2,
      borderDash: [8, 4],
      fill: hasMax ? '-1' : false,
      pointRadius: 0,
      order: 1, // Render after main data
    })
  }

  return {
    labels: points.map((p) => p.label),
    datasets: [
      ...datasets,
      {
        label: 'Row Count',
        data: points.map((p) => p.value) as any,
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59,130,246,0.1)',
        borderWidth: 2,
        tension: 0.2,
        fill: false,
        pointRadius: points.map((p) => (p.isOutlier ? 8 : 4)),
        pointBackgroundColor: points.map((p) => (p.isOutlier ? '#EF4444' : '#3B82F6')),
        pointBorderColor: points.map((p) => (p.isOutlier ? '#DC2626' : '#3B82F6')),
        pointBorderWidth: points.map((p) => (p.isOutlier ? 2 : 1)),
        isOutlier: points.map((p) => p.isOutlier),
        order: 0, // Render first (on top of thresholds)
      },
    ],
  }
}

function buildFreshnessChart(data: any[]) {
  const points = data
    .map((r: any) => {
      const ts = parseTimestamp(r?.timestamp)
      const label = ts.toLocaleTimeString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
      })
      const meta = r?.metadata || r?.details || {}
      const freshness = Number(meta?.freshness_hours ?? meta?.hours_since_update ?? meta?.age_hours)
      const threshold = Number(meta?.max_age_hours ?? meta?.threshold)
      const isOutlier =
        Number.isFinite(freshness) && Number.isFinite(threshold) ? freshness > threshold : false
      return { label, value: freshness, threshold, isOutlier }
    })
    .filter((p) => p.label && Number.isFinite(p.value))
    .reverse()

  if (points.length === 0) return null

  return {
    labels: points.map((p) => p.label),
    datasets: [
      {
        label: 'Threshold',
        data: points.map((p) => (Number.isFinite(p.threshold) ? p.threshold : null)) as any,
        borderColor: 'rgba(239,68,68,0.5)',
        backgroundColor: 'transparent',
        borderWidth: 2,
        borderDash: [5, 5],
        pointRadius: 0,
      },
      {
        label: 'Freshness (hours)',
        data: points.map((p) => p.value) as any,
        borderColor: '#F59E0B',
        backgroundColor: 'rgba(245,158,11,0.1)',
        borderWidth: 2,
        tension: 0.2,
        fill: false,
        isOutlier: points.map((p) => p.isOutlier),
      },
    ],
  }
}

function buildColumnValuesChart(data: any[]) {
  const points = data
    .map((r: any) => {
      const ts = parseTimestamp(r?.timestamp)
      const label = ts.toLocaleTimeString(undefined, { month: 'short', day: 'numeric' })
      const meta = r?.metadata || r?.details || {}
      const violations = Number(meta?.violation_count ?? meta?.failures ?? meta?.count ?? 0)
      const threshold = Number(meta?.threshold ?? meta?.max_violations ?? 0)
      return { label, value: violations, threshold }
    })
    .filter((p) => p.label)
    .reverse()

  if (points.length === 0) return null

  return {
    labels: points.map((p) => p.label),
    datasets: [
      {
        label: 'Violations',
        data: points.map((p) => p.value) as any,
        backgroundColor: points.map((p) =>
          p.value > p.threshold ? 'rgba(239,68,68,0.8)' : 'rgba(34,197,94,0.8)',
        ),
        borderColor: points.map((p) =>
          p.value > p.threshold ? 'rgb(239,68,68)' : 'rgb(34,197,94)',
        ),
        borderWidth: 2,
        borderRadius: 4,
      },
    ],
  }
}

function buildForecastChart(data: any[]) {
  const points = data
    .map((r: any) => {
      const meta = r?.metadata || r?.details || {}
      const ts = parseTimestamp(r?.timestamp)
      const label = ts.toLocaleTimeString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
      })

      // Try multiple ways to extract observed value
      const observed = Number(
        meta?.observed_value ??
          meta?.observed ??
          r?.observed_value ??
          (typeof meta === 'object' && meta !== null ? meta.value : null),
      )

      // Try multiple ways to extract bounds
      const lower = Number(meta?.lower_bound ?? meta?.lower ?? meta?.forecast_lower)
      const upper = Number(meta?.upper_bound ?? meta?.upper ?? meta?.forecast_upper)

      // If we have observed but no bounds, calculate reasonable bounds
      const hasObserved = Number.isFinite(observed)
      const hasBounds = Number.isFinite(lower) && Number.isFinite(upper)

      let finalLower = lower
      let finalUpper = upper

      if (hasObserved && !hasBounds) {
        // Create bounds around observed value (±20%)
        finalLower = observed * 0.8
        finalUpper = observed * 1.2
      }

      const isOutlier =
        hasObserved && Number.isFinite(finalLower) && Number.isFinite(finalUpper)
          ? observed < finalLower || observed > finalUpper
          : false

      return { label, observed, lower: finalLower, upper: finalUpper, isOutlier, hasObserved }
    })
    .filter((p) => p.label && p.hasObserved)
    .reverse()

  if (points.length === 0) return null

  return {
    labels: points.map((p) => p.label),
    datasets: [
      {
        label: 'Upper Bound',
        data: points.map((p) => (Number.isFinite(p.upper) ? p.upper : null)) as any,
        borderColor: 'rgba(107,114,128,0.5)',
        backgroundColor: 'rgba(107,114,128,0.05)',
        borderWidth: 1,
        borderDash: [5, 5],
        fill: '+1',
        pointRadius: 0,
      },
      {
        label: 'Lower Bound',
        data: points.map((p) => (Number.isFinite(p.lower) ? p.lower : null)) as any,
        borderColor: 'rgba(107,114,128,0.5)',
        backgroundColor: 'transparent',
        borderWidth: 1,
        borderDash: [5, 5],
        fill: false,
        pointRadius: 0,
      },
      {
        label: 'Observed',
        data: points.map((p) => p.observed) as any,
        borderColor: '#EF4444',
        backgroundColor: 'rgba(239,68,68,0.1)',
        borderWidth: 2,
        tension: 0.2,
        fill: false,
        isOutlier: points.map((p) => p.isOutlier),
      },
    ],
  }
}

function buildDriftChart(data: any[]) {
  const points = data
    .map((r: any) => {
      const meta = r?.metadata || r?.details || {}
      const ts = parseTimestamp(r?.timestamp || r?.executed_at)
      const label = ts.toLocaleTimeString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
      })

      // Try multiple ways to extract p-value
      const p = Number(
        meta?.p_value ??
          meta?.pvalue ??
          meta?.p ??
          meta?.statistical_test?.p_value ??
          r?.observed_value, // Sometimes p-value is in observed_value
      )

      // Calculate drift signal from p-value
      let signal: number | null = null
      if (Number.isFinite(p) && p > 0 && p <= 1) {
        signal = -Math.log10(p)
      } else if (Number.isFinite(p) && p > 1) {
        // If p-value is already transformed or is a signal value
        signal = p
      } else if (Number.isFinite(r?.observed_value) && r?.observed_value > 0) {
        // Fallback: use observed_value if it looks like a signal
        signal = r.observed_value
      }

      // Also try to get baseline and current means for comparison
      // The KS test stores these in stats_metadata, but also check top-level
      const statsMeta = meta?.stats_metadata || {}
      const baselineMean = Number(
        meta?.baseline_mean ??
          statsMeta?.baseline_mean ??
          meta?.baseline_stats?.mean ??
          meta?.reference_mean,
      )
      const baselineStd = Number(
        meta?.baseline_std ?? statsMeta?.baseline_std ?? meta?.baseline_stats?.std,
      )
      const currentMean = Number(
        meta?.current_mean ??
          statsMeta?.current_mean ??
          meta?.current_stats?.mean ??
          meta?.sample_mean,
      )
      const currentStd = Number(
        meta?.current_std ?? statsMeta?.current_std ?? meta?.current_stats?.std,
      )

      // Try to get drift score or distance metric as fallback
      const driftScore = Number(
        meta?.drift_score ?? meta?.distance ?? meta?.statistical_distance ?? meta?.ks_statistic,
      )

      // Use drift score if available and no signal
      if (signal === null && Number.isFinite(driftScore) && driftScore > 0) {
        signal = driftScore
      }

      const isOutlier = signal !== null && signal > 2 // p < 0.01

      return {
        label,
        signal,
        p,
        baselineMean,
        baselineStd,
        currentMean,
        currentStd,
        driftScore,
        isOutlier,
        hasSignal: signal !== null,
        hasMeans: Number.isFinite(baselineMean) && Number.isFinite(currentMean),
        hasAnyData:
          signal !== null || (Number.isFinite(baselineMean) && Number.isFinite(currentMean)),
      }
    })
    .filter((p) => p.label && p.hasAnyData) // Show if we have any data (signal or means)
    .reverse()

  if (points.length === 0) return null

  // Check if we have baseline/current means to show comparison
  const hasMeans = points.some(
    (p) => Number.isFinite(p.baselineMean) && Number.isFinite(p.currentMean),
  )

  if (hasMeans) {
    // Show comparison chart with baseline vs current means
    // Also show baseline ± 1 std as a band to show expected range
    const datasets: any[] = []

    // DEBUG: Log the data being processed
    console.log('[CheckTypeChart] Drift chart data:', {
      pointsCount: points.length,
      points: points.map((p) => ({
        label: p.label,
        baselineMean: p.baselineMean,
        baselineStd: p.baselineStd,
        currentMean: p.currentMean,
        currentStd: p.currentStd,
        baselineUpper:
          Number.isFinite(p.baselineMean) && Number.isFinite(p.baselineStd)
            ? p.baselineMean + p.baselineStd
            : null,
        currentUpper:
          Number.isFinite(p.currentMean) && Number.isFinite(p.currentStd)
            ? p.currentMean + p.currentStd
            : null,
      })),
      maxBaselineUpper: Math.max(
        ...points
          .filter((p) => Number.isFinite(p.baselineMean) && Number.isFinite(p.baselineStd))
          .map((p) => p.baselineMean + p.baselineStd),
      ),
      maxCurrentUpper: Math.max(
        ...points
          .filter((p) => Number.isFinite(p.currentMean) && Number.isFinite(p.currentStd))
          .map((p) => p.currentMean + p.currentStd),
      ),
      maxCurrentMean: Math.max(
        ...points.filter((p) => Number.isFinite(p.currentMean)).map((p) => p.currentMean),
      ),
    })

    // Add baseline mean ± std band if we have std
    const hasStd = points.some((p) => Number.isFinite(p.baselineStd))
    if (hasStd) {
      datasets.push(
        {
          label: 'Baseline Mean + 1σ',
          data: points.map((p) =>
            Number.isFinite(p.baselineMean) && Number.isFinite(p.baselineStd)
              ? p.baselineMean + p.baselineStd
              : null,
          ) as any,
          borderColor: 'rgba(59,130,246,0.3)',
          backgroundColor: 'rgba(59,130,246,0.05)',
          borderWidth: 1,
          borderDash: [3, 3],
          fill: '+1',
          pointRadius: 0,
        },
        {
          label: 'Baseline Mean',
          data: points.map((p) => (Number.isFinite(p.baselineMean) ? p.baselineMean : null)) as any,
          borderColor: 'rgba(59,130,246,0.8)',
          backgroundColor: 'rgba(59,130,246,0.1)',
          borderWidth: 2,
          borderDash: [5, 5],
          tension: 0.2,
          fill: hasStd ? '-1' : false,
          pointRadius: 0,
        },
        {
          label: 'Baseline Mean - 1σ',
          data: points.map((p) =>
            Number.isFinite(p.baselineMean) && Number.isFinite(p.baselineStd)
              ? p.baselineMean - p.baselineStd
              : null,
          ) as any,
          borderColor: 'rgba(59,130,246,0.3)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderDash: [3, 3],
          fill: false,
          pointRadius: 0,
        },
      )
    } else {
      // No std, just show baseline mean
      datasets.push({
        label: 'Baseline Mean',
        data: points.map((p) => (Number.isFinite(p.baselineMean) ? p.baselineMean : null)) as any,
        borderColor: 'rgba(59,130,246,0.8)',
        backgroundColor: 'rgba(59,130,246,0.1)',
        borderWidth: 2,
        borderDash: [5, 5],
        tension: 0.2,
        fill: false,
        pointRadius: 0,
      })
    }

    // Add current mean
    datasets.push({
      label: 'Current Mean',
      data: points.map((p) => (Number.isFinite(p.currentMean) ? p.currentMean : null)) as any,
      borderColor: '#8B5CF6',
      backgroundColor: 'rgba(139,92,246,0.1)',
      borderWidth: 3,
      tension: 0.2,
      fill: false,
      pointRadius: points.map((p) => (p.isOutlier ? 8 : 5)),
      pointBackgroundColor: points.map((p) => (p.isOutlier ? '#EF4444' : '#8B5CF6')),
      pointBorderColor: points.map((p) => (p.isOutlier ? '#DC2626' : '#8B5CF6')),
      pointBorderWidth: points.map((p) => (p.isOutlier ? 2 : 1)),
      isOutlier: points.map((p) => p.isOutlier),
    })

    return {
      labels: points.map((p) => p.label),
      datasets,
    }
  }

  // Default: show drift signal
  return {
    labels: points.map((p) => p.label),
    datasets: [
      {
        label: 'Drift Signal (-log10 p-value)',
        data: points.map((p) => p.signal) as any,
        borderColor: '#8B5CF6',
        backgroundColor: 'rgba(139,92,246,0.1)',
        borderWidth: 2,
        tension: 0.2,
        fill: false,
        isOutlier: points.map((p) => p.isOutlier),
      },
      {
        label: 'Significance Threshold',
        data: new Array(points.length).fill(2) as any,
        borderColor: 'rgba(239,68,68,0.5)',
        backgroundColor: 'transparent',
        borderWidth: 1,
        borderDash: [5, 5],
        pointRadius: 0,
        fill: false,
      },
    ],
  }
}

function buildGenericChart(data: any[]) {
  const points = data
    .map((r: any) => {
      const ts = parseTimestamp(r?.timestamp)
      const label = ts.toLocaleTimeString(undefined, { month: 'short', day: 'numeric' })
      const status = String(r?.status || '').toLowerCase()
      const value = status === 'fail' || status === 'failed' ? 1 : status === 'warn' ? 0.5 : 0
      return { label, value }
    })
    .filter((p) => p.label)
    .reverse()

  if (points.length === 0) return null

  return {
    labels: points.map((p) => p.label),
    datasets: [
      {
        label: 'Status',
        data: points.map((p) => p.value) as any,
        borderColor: '#6B7280',
        backgroundColor: 'rgba(107,114,128,0.1)',
        borderWidth: 2,
        tension: 0.2,
        fill: false,
      },
    ],
  }
}

function parseTimestamp(ts?: string): Date {
  if (!ts) return new Date()
  const d = new Date(ts)
  return Number.isNaN(d.getTime()) ? new Date() : d
}

const chartOptions = computed(() => {
  const baseOptions = {
    plugins: {
      legend: { position: 'top' as const },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
          label: function (context: any) {
            const label = context.dataset.label || ''
            const value = context.parsed.y
            if (value === null || value === undefined) return null
            const isOutlier = context.dataset.isOutlier?.[context.dataIndex]
            return `${label}: ${value.toFixed(2)}${isOutlier ? ' ⚠️ OUTLIER' : ''}`
          },
        },
      },
    },
    scales: {
      x: { grid: { display: false } },
      y: {
        grid: { color: 'rgba(0, 0, 0, 0.1)' },
      },
    },
    elements: {
      point: {
        radius: function (context: any) {
          const isOutlier = context.dataset.isOutlier?.[context.dataIndex]
          return isOutlier ? 8 : 4
        },
        hoverRadius: function (context: any) {
          const isOutlier = context.dataset.isOutlier?.[context.dataIndex]
          return isOutlier ? 10 : 6
        },
        backgroundColor: function (context: any) {
          const isOutlier = context.dataset.isOutlier?.[context.dataIndex]
          return isOutlier ? 'rgba(239, 68, 68, 1)' : context.dataset.borderColor
        },
        borderColor: function (context: any) {
          const isOutlier = context.dataset.isOutlier?.[context.dataIndex]
          return isOutlier ? 'rgba(239, 68, 68, 1)' : context.dataset.borderColor
        },
      },
    },
  }

  return baseOptions
})
</script>
