<script lang="ts">
	import type { Snippet } from 'svelte';
	import LoadingSpinner from '../shared/LoadingSpinner.svelte';

	interface Props {
		image: string;
		isProcessing: boolean;
		onRetake?: () => void;
		onAnalyze?: () => void;
		children?: Snippet;
	}

	let { image, isProcessing, onRetake, onAnalyze, children }: Props = $props();
</script>

<div class="space-y-4">
	<div class="relative overflow-hidden rounded-xl">
		<img
			src={image}
			alt="Captured schedule"
			class="h-auto max-h-[400px] w-full bg-gray-100 object-contain dark:bg-gray-900"
		/>

		{#if children}
			{@render children()}
		{/if}

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
				onclick={onRetake}
				aria-label="Retake photo"
				disabled={isProcessing}
				class="flex-1 rounded-lg bg-gray-200 px-4 py-2 font-medium text-gray-800 transition hover:bg-gray-300 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
			>
				📷 Neues Foto
			</button>

			<button
				onclick={onAnalyze}
				aria-label="Analyze photo"
				disabled={isProcessing}
				class="flex-1 rounded-lg bg-purple-600 px-4 py-2 font-medium text-white transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-50"
			>
				{#if isProcessing}
					<span class="inline-block animate-spin">⏳</span> Analysiere...
				{:else}
					🔍 Analysieren
				{/if}
			</button>
		</div>
	{/if}
</div>
