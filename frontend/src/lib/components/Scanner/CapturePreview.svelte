<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import LoadingSpinner from '../shared/LoadingSpinner.svelte';

	export let image: string;
	export let isProcessing: boolean = false;

	const dispatch = createEventDispatcher();

	function handleRetake() {
		dispatch('retake');
	}

	function handleAnalyze() {
		dispatch('analyze');
	}
</script>

<div class="space-y-4">
	<div class="relative overflow-hidden rounded-xl">
		<img
			src={image}
			alt="Captured schedule"
			class="h-auto max-h-[400px] w-full bg-gray-100 object-contain dark:bg-gray-900"
		/>

		{#if isProcessing}
			<div class="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm">
				<div class="text-center">
					<LoadingSpinner size="lg" color="white" />
					<p class="mt-4 font-semibold text-white">Analyzing schedule...</p>
					<p class="mt-2 text-sm text-white/80">This may take a few seconds</p>
				</div>
			</div>
		{/if}
	</div>

	{#if !isProcessing}
		<div class="flex gap-3">
			<button
				on:click={handleRetake}
				aria-label="Retake photo"
				class="flex-1 rounded-xl bg-gray-100 px-6 py-3 font-semibold text-gray-800 transition hover:bg-gray-200 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
			>
				<span class="flex items-center justify-center gap-2">
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
						></path>
					</svg>
					Retake Photo
				</span>
			</button>

			<button
				on:click={handleAnalyze}
				aria-label="Analyze photo"
				class="flex-1 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-3 font-semibold text-white shadow-lg transition hover:from-purple-700 hover:to-blue-700"
			>
				<span class="flex items-center justify-center gap-2">
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
						></path>
					</svg>
					Extract Schedule
				</span>
			</button>
		</div>
	{/if}
</div>
