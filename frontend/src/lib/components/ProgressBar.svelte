<script lang="ts">
	import { LL } from '$i18n/i18n-svelte';

	export let completedWeeks: number;
	export let totalWeeks: number;
	export let progressPercentage: number;
</script>

<div class="mb-6 rounded-xl bg-white p-4 shadow-lg dark:bg-gray-800">
	<div class="flex items-center justify-between">
		<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{$LL.common.progress()}</span>
		<span class="text-sm font-semibold text-purple-600 dark:text-purple-400">
			{$LL.common.weeksComplete({ completed: completedWeeks, total: totalWeeks })}
		</span>
	</div>
	<div class="mt-2 h-3 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
		<div
			class="h-full rounded-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-500"
			style="width: {progressPercentage}%"
		></div>
	</div>
</div>
