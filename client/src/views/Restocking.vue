<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error && !successMessage" class="error">{{ error }}</div>
    <div v-else>

      <!-- Success Banner -->
      <div v-if="successMessage" class="success-banner">
        <span>{{ successMessage }}</span>
        <router-link to="/orders" class="view-orders-link">{{ t('restocking.viewInOrders') }}</router-link>
      </div>

      <!-- Budget Slider -->
      <div class="card budget-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budgetTitle') }}</h3>
          <span class="budget-display">{{ currencySymbol }}{{ budget.toLocaleString() }}</span>
        </div>
        <div class="slider-wrapper">
          <input
            type="range"
            v-model.number="budget"
            min="0"
            :max="maxBudget"
            :step="sliderStep"
            class="budget-slider"
          />
          <div class="slider-labels">
            <span>{{ currencySymbol }}0</span>
            <span>{{ currencySymbol }}{{ maxBudget.toLocaleString() }}</span>
          </div>
        </div>
        <p class="budget-help">{{ t('restocking.budgetHelp') }}</p>
      </div>

      <!-- Summary Cards -->
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.summary.recommendedItems') }}</div>
          <div class="stat-value">{{ recommendedCount }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.summary.totalCost') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ totalCost.toLocaleString() }}</div>
        </div>
        <div class="stat-card" :class="budgetRemaining >= 0 ? 'info' : 'danger'">
          <div class="stat-label">{{ t('restocking.summary.budgetRemaining') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ budgetRemaining.toLocaleString() }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.summary.budgetUsed') }}</div>
          <div class="stat-value">{{ budgetUsedPct.toFixed(1) }}%</div>
        </div>
      </div>

      <!-- Recommendations Table -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendationsTitle') }} ({{ candidates.length }})</h3>
        </div>
        <div class="table-container">
          <table class="restock-table">
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.category') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
                <th>{{ t('restocking.table.recommended') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="c in candidatesWithInclusion"
                :key="c.item_sku"
                :class="{ 'row-excluded': !c.included }"
              >
                <td><code class="sku">{{ c.item_sku }}</code></td>
                <td>{{ c.item_name }}</td>
                <td>{{ c.category }}</td>
                <td>
                  <span :class="['badge', getTrendClass(c.trend)]">{{ c.trend }}</span>
                </td>
                <td>{{ c.recommended_quantity }}</td>
                <td>{{ currencySymbol }}{{ c.unit_cost.toLocaleString() }}</td>
                <td><strong>{{ currencySymbol }}{{ c.line_cost.toLocaleString() }}</strong></td>
                <td>{{ c.lead_time_days }} {{ t('restocking.days') }}</td>
                <td>
                  <span v-if="c.included" class="badge success">{{ t('restocking.included') }}</span>
                  <span v-else class="over-budget-text">{{ t('restocking.overBudget') }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Place Order / No Recommendations -->
      <div v-if="recommendedItems.length === 0" class="no-recommendations">
        {{ t('restocking.noRecommendations') }}
      </div>
      <div v-else class="order-action">
        <button
          class="btn-primary"
          :disabled="placing"
          @click="placeOrder"
        >
          {{ placing ? t('restocking.placing') : t('restocking.placeOrder') }}
        </button>
      </div>

    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const loading = ref(true)
    const error = ref(null)
    const candidates = ref([])
    const budget = ref(0)
    const placing = ref(false)
    const successMessage = ref(null)
    const submittedOrderNumber = ref(null)

    const maxBudget = computed(() => {
      if (candidates.value.length === 0) return 0
      const total = candidates.value.reduce((sum, c) => sum + c.line_cost, 0)
      return Math.ceil(total)
    })

    const sliderStep = computed(() => {
      return Math.max(1, Math.round(maxBudget.value / 100))
    })

    // Greedy recommendation: iterate candidates in order (already sorted by backend)
    // For each candidate, if line_cost <= remaining budget, include it
    const candidatesWithInclusion = computed(() => {
      let remaining = budget.value
      return candidates.value.map(c => {
        const included = c.line_cost <= remaining
        if (included) {
          remaining -= c.line_cost
        }
        return { ...c, included }
      })
    })

    const recommendedItems = computed(() => {
      return candidatesWithInclusion.value.filter(c => c.included)
    })

    const recommendedCount = computed(() => recommendedItems.value.length)

    const totalCost = computed(() => {
      return recommendedItems.value.reduce((sum, c) => sum + c.line_cost, 0)
    })

    const budgetRemaining = computed(() => {
      return budget.value - totalCost.value
    })

    const budgetUsedPct = computed(() => {
      if (budget.value <= 0) return 0
      return (totalCost.value / budget.value) * 100
    })

    const getTrendClass = (trend) => {
      const map = {
        increasing: 'success',
        stable: 'info',
        decreasing: 'danger'
      }
      return map[trend] || 'info'
    }

    const formatDate = (dateString) => {
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return new Date(dateString).toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const loadCandidates = async () => {
      try {
        loading.value = true
        error.value = null
        candidates.value = await api.getRestockCandidates()
        // Initialize budget at 50% of total max budget
        const total = candidates.value.reduce((sum, c) => sum + c.line_cost, 0)
        const max = Math.ceil(total)
        budget.value = Math.round(max * 0.5)
      } catch (err) {
        error.value = 'Failed to load restocking candidates: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (recommendedItems.value.length === 0 || placing.value) return
      placing.value = true
      error.value = null
      try {
        const payload = {
          budget: budget.value,
          items: recommendedItems.value.map(c => ({
            item_sku: c.item_sku,
            item_name: c.item_name,
            quantity: c.recommended_quantity,
            unit_cost: c.unit_cost,
            lead_time_days: c.lead_time_days
          }))
        }
        const res = await api.createRestockOrder(payload)
        submittedOrderNumber.value = res.order_number
        successMessage.value = t('restocking.orderSuccess', { orderNumber: res.order_number })
      } catch (err) {
        error.value = t('restocking.orderError')
        console.error('Failed to place restocking order:', err)
      } finally {
        placing.value = false
      }
    }

    onMounted(loadCandidates)

    return {
      t,
      currencySymbol,
      loading,
      error,
      candidates,
      budget,
      placing,
      successMessage,
      submittedOrderNumber,
      maxBudget,
      sliderStep,
      candidatesWithInclusion,
      recommendedItems,
      recommendedCount,
      totalCost,
      budgetRemaining,
      budgetUsedPct,
      getTrendClass,
      formatDate,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.budget-display {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.slider-wrapper {
  padding: 0.5rem 0 0.25rem;
}

.budget-slider {
  width: 100%;
  height: 6px;
  appearance: none;
  -webkit-appearance: none;
  background: #e2e8f0;
  border-radius: 9999px;
  outline: none;
  cursor: pointer;
  accent-color: #3b82f6;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: background 0.2s;
}

.budget-slider::-webkit-slider-thumb:hover {
  background: #2563eb;
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.375rem;
  font-size: 0.75rem;
  color: #94a3b8;
}

.budget-help {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #64748b;
}

.restock-table {
  table-layout: fixed;
  width: 100%;
}

.restock-table th:nth-child(1) { width: 90px; }
.restock-table th:nth-child(2) { width: 200px; }
.restock-table th:nth-child(3) { width: 120px; }
.restock-table th:nth-child(4) { width: 90px; }
.restock-table th:nth-child(5) { width: 110px; }
.restock-table th:nth-child(6) { width: 90px; }
.restock-table th:nth-child(7) { width: 90px; }
.restock-table th:nth-child(8) { width: 90px; }
.restock-table th:nth-child(9) { width: 100px; }

.row-excluded {
  opacity: 0.45;
}

.sku {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.813rem;
  background: #f1f5f9;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  color: #475569;
}

.over-budget-text {
  font-size: 0.75rem;
  color: #94a3b8;
  font-style: italic;
}

.no-recommendations {
  background: #fef9c3;
  border: 1px solid #fde68a;
  color: #92400e;
  padding: 1rem 1.25rem;
  border-radius: 8px;
  font-size: 0.938rem;
  margin-bottom: 1.25rem;
}

.order-action {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1.25rem;
}

.btn-primary {
  background: #2563eb;
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  font-size: 0.938rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.success-banner {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  color: #065f46;
  padding: 1rem 1.25rem;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 500;
  margin-bottom: 1.25rem;
}

.view-orders-link {
  color: #059669;
  font-weight: 600;
  text-decoration: underline;
  white-space: nowrap;
}

.view-orders-link:hover {
  color: #047857;
}
</style>
