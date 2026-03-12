<script setup lang="ts">
defineProps<{
  label: string;
  value: string | number;
  hint?: string;
}>();
</script>

<template>
  <article class="summary-card glass-card">
    <p class="summary-label">{{ label }}</p>
    <h3 class="summary-value">{{ value }}</h3>
    <p v-if="hint" class="summary-hint">{{ hint }}</p>
  </article>
</template>
