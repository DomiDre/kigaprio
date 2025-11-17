<script lang="ts">
	import type { WeekData, WeekPriority } from '$lib/priorities.types';
	import type { VacationDay } from '$lib/vacation-days.types';
	import { dayKeys, priorityColors } from '$lib/priorities.config';
	import { getVacationDayForDate, isWeekStarted } from '$lib/dateHelpers.utils';
	import { SvelteDate } from 'svelte/reactivity';
	import { LL } from '$i18n/i18n-svelte';

	type Props = {
		weeks: WeekData[];
		openEditModal: (week: WeekData, index: number) => void;
		vacationDaysMap: Map<string, VacationDay>;
	};

	let { weeks, openEditModal, vacationDaysMap }: Props = $props();

	// Make vacation day lookups reactive by creating a derived helper
	let getVacation = $derived.by(() => {
		return (dateStr: string) => getVacationDayForDate(dateStr, vacationDaysMap);
	});

	// Helper to get the full date for a day in a week
	function getFullDateForDay(week: WeekData, dayIndex: number): string {
		if (!week.startDate) return '';

		const [day, month, year] = week.startDate.split('.');
		const startDate = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
		const currentDate = new SvelteDate(startDate);
		currentDate.setDate(currentDate.getDate() + dayIndex);

		const dayStr = currentDate.getDate().toString().padStart(2, '0');
		const monthStr = (currentDate.getMonth() + 1).toString().padStart(2, '0');
		const yearStr = currentDate.getFullYear();
		return `${dayStr}.${monthStr}.${yearStr}`;
	}
</script>

<div class="mb-6 grid gap-4 md:grid-cols-2 lg:grid-cols-{weeks.length}">
	{#each weeks as week, index (index)}
		{@const weekStarted = isWeekStarted(week)}
		<div
			class="rounded-xl bg-white p-4 shadow-xl transition hover:translate-y-[-2px] dark:bg-gray-800
			{week.status === 'pending' ? 'border-2 border-purple-400' : ''}
			{weekStarted ? 'opacity-75' : ''}"
		>
			<div class="mb-4 flex items-center justify-between">
				<div class="flex items-center gap-2">
					<h3 class="font-bold text-gray-800 dark:text-white">
						{$LL.priorities.week()} {week.weekNumber}
					</h3>
					{#if weekStarted}
						<span class="text-orange-600 dark:text-orange-400" title="{$LL.priorities.weekAlreadyStartedTooltip()}">
							🔒
						</span>
					{/if}
				</div>
				<span
					class="rounded-full px-2 py-1 text-xs
					{week.status === 'completed'
						? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
						: week.status === 'pending'
							? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
							: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}"
				>
					{week.status === 'completed'
						? $LL.priorities.complete()
						: week.status === 'pending'
							? $LL.priorities.open()
							: $LL.priorities.locked()}
				</span>
			</div>

			<div class="mb-3 text-xs text-gray-500 dark:text-gray-400">
				{week.startDate} - {week.endDate}
			</div>

			<div class="space-y-2">
				{#each dayKeys as dayKey, dayIndex (dayKey)}
					{@const dayName = $LL.priorities.days[dayKey]()}
					{@const priority = week[dayKey as keyof WeekPriority]}
					{@const fullDate = getFullDateForDay(week, dayIndex)}
					{@const vacationDay = getVacation(fullDate)}
					<div
						class="flex items-center justify-between gap-1 rounded p-2
						{week.status === 'pending'
							? 'border border-purple-200 bg-purple-50 dark:border-purple-700 dark:bg-purple-900/20'
							: 'bg-gray-50 dark:bg-gray-700'}"
					>
						<div class="flex items-center gap-1">
							<span class="text-sm font-medium dark:text-gray-300">
								{dayName.substring(0, 2)}
							</span>
							{#if vacationDay}
								<span
									class="text-xs"
									title={`${vacationDay.type === 'vacation' ? $LL.priorities.vacation() : vacationDay.type === 'public_holiday' ? $LL.priorities.holiday() : $LL.priorities.absent()}: ${vacationDay.description}`}
								>
									{vacationDay.type === 'vacation'
										? '🏖️'
										: vacationDay.type === 'public_holiday'
											? '🎉'
											: '📋'}
								</span>
							{/if}
						</div>
						<span
							class="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white
							{priority
								? priorityColors[priority as 1 | 2 | 3 | 4 | 5]
								: 'bg-gray-200 text-gray-400 dark:bg-gray-600'}"
						>
							{priority || vacationDay ? '' : '?'}
						</span>
					</div>
				{/each}
			</div>

			<button
				class="mt-3 w-full rounded-lg py-2 text-sm font-semibold transition
				{weekStarted
					? 'cursor-default bg-gray-300 text-gray-600 dark:bg-gray-600 dark:text-gray-400'
					: 'bg-purple-600 text-white hover:bg-purple-700'}"
				onclick={() => openEditModal(week, index)}
			>
				{weekStarted ? $LL.priorities.view() : $LL.priorities.edit()}
			</button>
		</div>
	{/each}
</div>
