<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { AnalysisResult } from '../../types/scanner.types';

	export let result: AnalysisResult;

	const dispatch = createEventDispatcher();
	const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

	function handleRetake() {
		dispatch('retake');
	}

	function handleReset() {
		dispatch('reset');
	}

	function formatTime(time: string): string {
		// Format time string if needed
		return time || '-';
	}
</script>

<div class="mt-6 space-y-4">
	{#if result.success}
		{#if result.analysis?.name}
			<div class="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
				<h3 class="mb-2 font-semibold text-blue-800 dark:text-blue-400">
					<span class="flex items-center gap-2">
						<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
							></path>
						</svg>
						Name Detected
					</span>
				</h3>
				<p class="text-lg text-blue-700 dark:text-blue-300">{result.analysis.name}</p>
			</div>
		{/if}

		{#if result.analysis?.schedule}
			<div class="rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
				<h3 class="mb-3 font-semibold text-green-800 dark:text-green-400">
					<span class="flex items-center gap-2">
						<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
							></path>
						</svg>
						Weekly Schedule
					</span>
				</h3>

				<!-- Desktop view -->
				<div class="hidden gap-2 text-sm md:grid md:grid-cols-7">
					{#each days as day}
						<div class="text-center">
							<div class="mb-1 font-semibold text-gray-600 dark:text-gray-400">{day}</div>
							<div class="rounded bg-white p-2 shadow-sm dark:bg-gray-700">
								{formatTime(result.analysis.schedule[day])}
							</div>
						</div>
					{/each}
				</div>

				<!-- Mobile view -->
				<div class="space-y-2 md:hidden">
					{#each days as day}
						<div class="flex items-center justify-between rounded bg-white p-2 dark:bg-gray-700">
							<span class="font-semibold text-gray-600 dark:text-gray-400">{day}</span>
							<span>{formatTime(result.analysis.schedule[day])}</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if result.analysis?.description}
			<div class="rounded-lg bg-yellow-50 p-4 dark:bg-yellow-900/20">
				<h3 class="mb-2 font-semibold text-yellow-800 dark:text-yellow-400">Additional Notes</h3>
				<p class="text-yellow-700 dark:text-yellow-300">{result.analysis.description}</p>
			</div>
		{/if}

		{#if result.analysis?.confidence}
			<div class="text-center text-sm text-gray-600 dark:text-gray-400">
				Confidence: {Math.round(result.analysis.confidence * 100)}%
			</div>
		{/if}
	{:else if result.error}
		<div class="rounded-lg bg-red-50 p-4 dark:bg-red-900/20">
			<h3 class="mb-2 font-semibold text-red-800 dark:text-red-400">Analysis Error</h3>
			<p class="text-red-700 dark:text-red-300">{result.error}</p>
			<p class="mt-2 text-sm text-red-600 dark:text-red-400">
				Please ensure the image is clear and the schedule is fully visible.
			</p>
		</div>
	{/if}

	<div class="mt-6 flex gap-3">
		<button
			on:click={handleRetake}
			aria-label="Take another photo"
			class="flex-1 rounded-xl bg-gray-100 px-6 py-3 font-semibold text-gray-800 transition hover:bg-gray-200 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
		>
			<span class="flex items-center justify-center gap-2">
				<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
					></path>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
					></path>
				</svg>
				Take Another Photo
			</span>
		</button>

		<button
			on:click={handleReset}
			aria-label="Start over"
			class="flex-1 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-3 font-semibold text-white shadow-lg transition hover:from-purple-700 hover:to-blue-700"
		>
			<span class="flex items-center justify-center gap-2">
				<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
					></path>
				</svg>
				Start Over
			</span>
		</button>
	</div>
</div>
