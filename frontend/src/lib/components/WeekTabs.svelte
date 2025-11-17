<script lang="ts">
	import type { WeekData } from '$lib/priorities.types';
	import { getWeekStatus } from '$lib/dateHelpers.utils';
	import { LL } from '$i18n/i18n-svelte';

	export let weeks: WeekData[];
	export let activeWeekIndex: number;
</script>

<div class="mb-6 flex gap-2 overflow-x-auto pb-2">
	{#each weeks as week, index (index)}
		{@const status = getWeekStatus(week)}
		<button
			class="flex min-w-[80px] flex-none flex-col items-center rounded-lg px-4 py-2 shadow transition
			{activeWeekIndex === index
				? 'bg-purple-600 text-white'
				: status === 'completed'
					? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
					: 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'}"
			onclick={() => (activeWeekIndex = index)}
		>
			<span>{$LL.priorities.week()} {week.weekNumber}</span>
			<span class="mt-1 text-xs">
				{#if status === 'completed'}
					<span class="inline-block rounded-full bg-green-500 px-2 py-0.5 font-bold text-white"
						>✓</span
					>
				{:else if status === 'pending'}
					<span class="inline-block rounded-full bg-yellow-400 px-2 py-0.5 font-bold text-white"
						>!</span
					>
				{:else}
					<span class="inline-block rounded-full bg-gray-400 px-2 py-0.5 font-bold text-white"
						>●</span
					>
				{/if}
			</span>
		</button>
	{/each}
</div>
