<script lang="ts">
	import type { WeekData, WeekPriority } from '$lib/priorities.types';
	import { dayNames, priorityColors } from '$lib/priorities.config';

	export let weeks: WeekData[];
	export let openEditModal: (week: WeekData, index: number) => void;
</script>

<div class="mb-6 grid gap-4 md:grid-cols-2 lg:grid-cols-{weeks.length}">
	{#each weeks as week, index (index)}
		<div
			class="rounded-xl bg-white p-4 shadow-xl transition hover:translate-y-[-2px] dark:bg-gray-800
			{week.status === 'pending' ? 'border-2 border-purple-400' : ''}"
		>
			<div class="mb-4 flex items-center justify-between">
				<h3 class="font-bold text-gray-800 dark:text-white">
					Woche {week.weekNumber}
				</h3>
				<span
					class="rounded-full px-2 py-1 text-xs
					{week.status === 'completed'
						? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
						: week.status === 'pending'
							? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
							: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}"
				>
					{week.status === 'completed'
						? '✓ Fertig'
						: week.status === 'pending'
							? 'Offen'
							: 'Gesperrt'}
				</span>
			</div>

			<div class="mb-3 text-xs text-gray-500 dark:text-gray-400">
				{week.startDate} - {week.endDate}
			</div>

			<div class="space-y-2">
				{#each Object.entries(dayNames) as [dayKey, dayName] (dayKey)}
					{@const priority = week[dayKey as keyof WeekPriority]}
					<div
						class="flex items-center justify-between rounded p-2
						{week.status === 'pending'
							? 'border border-purple-200 bg-purple-50 dark:border-purple-700 dark:bg-purple-900/20'
							: 'bg-gray-50 dark:bg-gray-700'}"
					>
						<span class="text-sm font-medium dark:text-gray-300">
							{dayName.substring(0, 2)}
						</span>
						<span
							class="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white
							{priority
								? priorityColors[priority as 1 | 2 | 3 | 4 | 5]
								: 'bg-gray-200 text-gray-400 dark:bg-gray-600'}"
						>
							{priority || '?'}
						</span>
					</div>
				{/each}
			</div>

			<button
				class="mt-3 w-full rounded-lg bg-purple-600 py-2 text-sm font-semibold text-white transition hover:bg-purple-700"
				onclick={() => openEditModal(week, index)}
			>
				Bearbeiten
			</button>
		</div>
	{/each}
</div>
