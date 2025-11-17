<script lang="ts">
	import { priorityColors } from '$lib/priorities.config';
	import { LL } from '$i18n/i18n-svelte';

	const priorities = [
		{ num: 1, key: 'veryImportant' as const },
		{ num: 2, key: 'important' as const },
		{ num: 3, key: 'normal' as const },
		{ num: 4, key: 'lessImportant' as const },
		{ num: 5, key: 'unimportant' as const }
	];
</script>

<div class="mb-6 rounded-xl bg-white p-4 shadow-lg dark:bg-gray-800">
	<div class="flex flex-col gap-3">
		<!-- Priority Legend -->
		<div class="flex flex-wrap items-center justify-center gap-4 text-sm">
			<span class="font-semibold text-gray-700 dark:text-gray-300">{$LL.priorities.title()}:</span>
			{#each priorities as { num, key } (num)}
				<div class="flex items-center gap-2">
					<span
						class="flex h-8 w-8 items-center justify-center rounded-full {priorityColors[
							num as 1 | 2 | 3 | 4 | 5
						]} font-bold text-white"
					>
						{num}
					</span>
					<span class="text-gray-600 dark:text-gray-400">{$LL.priorities.labels[key]()}</span>
				</div>
			{/each}
		</div>

		<!-- Vacation Days Legend -->
		<div
			class="flex flex-wrap items-center justify-center gap-4 border-t border-gray-200 pt-3 text-sm dark:border-gray-700"
		>
			<span class="font-semibold text-gray-700 dark:text-gray-300">{$LL.vacation.title()}:</span>
			<div class="flex items-center gap-2">
				<span class="text-base">🏖️</span>
				<span class="text-gray-600 dark:text-gray-400">{$LL.priorities.vacation()}</span>
			</div>
			<div class="flex items-center gap-2">
				<span class="text-base">🎉</span>
				<span class="text-gray-600 dark:text-gray-400">{$LL.priorities.holiday()}</span>
			</div>
			<div class="flex items-center gap-2">
				<span class="text-base">📋</span>
				<span class="text-gray-600 dark:text-gray-400">{$LL.vacation.title()}</span>
			</div>
		</div>
	</div>
</div>
