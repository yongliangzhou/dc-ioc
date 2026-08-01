<template>
  <div ref="el" class="base-chart" :style="{ height, width }"></div>
</template>

<script setup lang="ts">
import { ref, toRef } from "vue";
import { useECharts, type EChartsOption } from "@/hooks/useECharts";

const props = withDefaults(
  defineProps<{
    option: EChartsOption | Record<string, unknown>;
    height?: string;
    width?: string;
    theme?: string | object;
  }>(),
  { height: "260px", width: "100%" }
);

const el = ref<HTMLElement | null>(null);
const { chart, resize } = useECharts(el, toRef(props, "option"), { theme: props.theme });

defineExpose({ chart, resize });
</script>

<style scoped>
.base-chart { display: block; }
</style>
