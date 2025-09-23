<script lang="ts">
	import { priorityColors, priorityLabels } from '$lib/config/priorities';
</script>

<div class="mb-6 rounded-xl bg-white p-4 shadow-lg dark:bg-gray-800">
	<div class="flex flex-wrap items-center justify-center gap-4 text-sm">
		<span class="font-semibold text-gray-700 dark:text-gray-300">Priorität:</span>
		{#each Object.entries(priorityLabels) as [priority, label] (label)}
			<div class="flex items-center gap-2">
				<span
					class="flex h-8 w-8 items-center justify-center rounded-full {priorityColors[
						Number(priority) as 1 | 2 | 3 | 4 | 5
					]} font-bold text-white"
				>
					{priority}
				</span>
				<span class="text-gray-600 dark:text-gray-400">{label}</span>
			</div>
		{/each}
	</div>
</div>
