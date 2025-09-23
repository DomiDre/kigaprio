<script lang="ts">
	import type { WeekData, Priority, DayPriorities } from '$lib/types/priorities';
	import { dayNames } from '$lib/config/priorities';

	export let week: WeekData;
	export let weekIndex: number;
	export let selectPriority: (
		weekIndex: number,
		day: keyof DayPriorities,
		priority: Priority
	) => void;
	export let saveWeek: (weekIndex: number) => void;
	export let getDayDates: (weekData: WeekData) => string[];
</script>

<div class="rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
	<div class="mb-6 flex items-center justify-between">
		<div>
			<h3 class="text-lg font-bold text-gray-800 dark:text-white">
				Woche {week.weekNumber}
			</h3>
			<p class="text-xs text-gray-500 dark:text-gray-400">
				{week.startDate} - {week.endDate}
			</p>
		</div>
		<span
			class="rounded-full px-3 py-1 text-sm
			{week.status === 'completed'
				? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
				: week.status === 'pending'
					? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
					: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}"
		>
			{week.status === 'completed' ? '✓ Fertig' : week.status === 'pending' ? 'Offen' : 'Gesperrt'}
		</span>
	</div>

	<div class="space-y-4">
		{#each Object.entries(dayNames) as [dayKey, dayName], dayIndex (dayKey)}
			{@const dayDates = getDayDates(week)}
			{@const monthName = week.startDate.split('.')[1]}
			<div
				class="rounded-lg bg-gradient-to-r from-purple-50 to-blue-50 p-4 dark:from-gray-700 dark:to-gray-600"
			>
				<div class="mb-3 flex items-center justify-between">
					<span class="text-lg font-semibold text-gray-700 dark:text-gray-200">{dayName}</span>
					<span class="text-sm text-gray-500 dark:text-gray-400">
						{dayDates[dayIndex]}{monthName}
					</span>
				</div>
				<div class="flex justify-center gap-2">
					{#each [1, 2, 3, 4, 5] as priority (priority)}
						<button
							class="h-12 w-12 transform rounded-full font-bold shadow transition
							{week.priorities[dayKey as keyof DayPriorities] === priority
								? 'scale-110 bg-gradient-to-r from-purple-600 to-blue-600 text-white'
								: 'border-2 border-gray-300 bg-white text-gray-700 hover:scale-105 hover:border-purple-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300'}"
							onclick={() =>
								selectPriority(weekIndex, dayKey as keyof DayPriorities, priority as Priority)}
						>
							{priority}
						</button>
					{/each}
				</div>
			</div>
		{/each}
	</div>

	{#if week.status === 'pending'}
		<div class="mt-6 flex gap-3">
			<button
				class="flex-1 transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 py-3 font-semibold text-white shadow-lg transition hover:scale-105"
				onclick={() => saveWeek(weekIndex)}
			>
				Woche speichern
			</button>
		</div>
	{/if}
</div>
