<script lang="ts">
	import type { SecurityTier } from '$lib/stores/auth';

	export let selectedTier: SecurityTier = 'balanced';
	export let onChange: (tier: SecurityTier) => void = () => {};

	const tiers = [
		{
			id: 'high' as SecurityTier,
			name: 'Hoch',
			icon: '🔒',
			tagline: 'Maximale Sicherheit',
			description: 'Automatische Abmeldung beim Schließen',
			useCase: 'Geteilte Geräte'
		},
		{
			id: 'balanced' as SecurityTier,
			name: 'Standard',
			icon: '✓',
			tagline: 'Empfohlen',
			description: 'Bleibt 30 Min. angemeldet',
			useCase: 'Eigenes Gerät'
		},
		{
			id: 'convenience' as SecurityTier,
			name: 'Bequem',
			icon: '⏱️',
			tagline: 'Angemeldet bleiben',
			description: 'Bis zur Abmeldung aktiv',
			useCase: 'Vertrauenswürdiges Gerät'
		}
	];

	function handleSelect(tier: SecurityTier) {
		selectedTier = tier;
		onChange(tier);
	}
</script>

<div class="space-y-3">
	{#each tiers as tier (tier)}
		<button
			type="button"
			on:click={() => handleSelect(tier.id)}
			class="w-full rounded-lg border-2 bg-white p-4 text-left transition-all dark:bg-gray-800
				   {selectedTier === tier.id
				? 'border-blue-500 bg-blue-50 shadow-md dark:bg-blue-900/20'
				: 'border-gray-200 hover:border-blue-300 dark:border-gray-700'}"
		>
			<div class="flex items-center gap-3">
				<!-- Icon -->
				<div
					class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-xl
						   {selectedTier === tier.id ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-700'}"
				>
					{tier.icon}
				</div>

				<!-- Content -->
				<div class="flex-1">
					<div class="flex items-center gap-2">
						<span class="font-semibold text-gray-800 dark:text-white">
							{tier.name}
						</span>
						{#if tier.id === 'balanced'}
							<span class="rounded bg-blue-600 px-2 py-0.5 text-xs font-medium text-white">
								{tier.tagline}
							</span>
						{/if}
					</div>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						{tier.description}
					</p>
				</div>

				<!-- Selection indicator -->
				{#if selectedTier === tier.id}
					<div class="flex-shrink-0 text-blue-600">
						<svg class="h-6 w-6" fill="currentColor" viewBox="0 0 20 20">
							<path
								fill-rule="evenodd"
								d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				{/if}
			</div>
		</button>
	{/each}
</div>
