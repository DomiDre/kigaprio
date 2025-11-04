<script lang="ts">
	import ChevronDown from 'virtual:icons/mdi/chevron-down';
	import ChevronUp from 'virtual:icons/mdi/chevron-up';
	import { dayKeys, dayLabels, priorityColors } from '$lib/priorities.config';
	import type { SvelteMap } from 'svelte/reactivity';
	import type { DecryptedData } from '$lib/dashboard.types';

	interface Props {
		showOverview: boolean;
		decryptedUsers: SvelteMap<string, DecryptedData>;
		overviewData: any[];
		allWeeks: number[];
		onToggle: () => void;
	}

	let { showOverview, decryptedUsers, overviewData, allWeeks, onToggle }: Props = $props();

	let decryptedUsersCount = $derived.by(() => {
		return decryptedUsers.size;
	});

	// Calculate demand statistics
	let demandStats = $derived.by(() => {
		const stats: Record<number, Record<string, Record<number, number>>> = {};

		decryptedUsers.forEach((userData) => {
			const weeks = userData.priorities?.weeks || [];
			weeks.forEach((week: any) => {
				if (!stats[week.weekNumber]) {
					stats[week.weekNumber] = {};
					dayKeys.forEach((day) => {
						stats[week.weekNumber][day] = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
					});
				}

				dayKeys.forEach((day) => {
					const priority = week[day];
					if (priority) {
						stats[week.weekNumber][day][priority]++;
					}
				});
			});
		});

		return stats;
	});
</script>

<div
	class="mb-6 rounded-xl border border-gray-200 bg-white shadow-xl sm:mb-8 dark:border-gray-700 dark:bg-gray-800"
>
	<div class="border-b border-gray-200 p-4 sm:p-6 dark:border-gray-700">
		<button type="button" class="flex w-full items-center justify-between" onclick={onToggle}>
			<div class="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:gap-3">
				<h2 class="text-base font-semibold text-gray-900 sm:text-lg dark:text-white">
					Priorities Overview
				</h2>
				<span
					class="rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800 sm:px-3 sm:py-1 dark:bg-purple-900/30 dark:text-purple-400"
				>
					{decryptedUsersCount} users
				</span>
			</div>
			{#if showOverview}
				<ChevronUp class="h-5 w-5 flex-shrink-0 text-gray-600 dark:text-gray-400" />
			{:else}
				<ChevronDown class="h-5 w-5 flex-shrink-0 text-gray-600 dark:text-gray-400" />
			{/if}
		</button>
	</div>

	{#if showOverview}
		<div class="p-4 sm:p-6">
			<!-- Legend -->
			<div class="mb-4 flex flex-wrap gap-2 sm:mb-6 sm:gap-4">
				<div class="flex items-center gap-2">
					<span class="text-xs font-medium text-gray-700 sm:text-sm dark:text-gray-300"
						>Priority:</span
					>
				</div>
				{#each [1, 2, 3, 4, 5] as priority (priority)}
					<div class="flex items-center gap-1.5 sm:gap-2">
						<div
							class="h-3 w-3 rounded sm:h-4 sm:w-4 {priorityColors[
								priority as 1 | 2 | 3 | 4 | 5
							]} text-white"
						></div>
						<span class="text-xs text-gray-600 dark:text-gray-400">{priority}</span>
					</div>
				{/each}
			</div>

			<!-- Mobile: Show scroll hint -->
			<div class="mb-3 text-xs text-gray-500 sm:hidden dark:text-gray-400">
				← Swipe to see all weeks →
			</div>

			<!-- Table Container with improved mobile scrolling -->
			<div class="-mx-4 sm:-mx-6">
				<div class="overflow-x-auto px-4 pb-2 sm:px-6">
					<div class="inline-block min-w-full align-middle">
						<div class="overflow-hidden">
							<!-- Overview Table -->
							<table class="min-w-full border-collapse">
								<thead>
									<tr class="border-b-2 border-gray-300 dark:border-gray-600">
										<th
											class="sticky left-0 z-20 min-w-[100px] bg-white px-2 py-2 text-left text-xs font-semibold text-gray-900 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] sm:min-w-[120px] sm:px-4 sm:py-3 sm:text-sm dark:bg-gray-800 dark:text-white dark:shadow-[2px_0_5px_-2px_rgba(0,0,0,0.3)]"
										>
											User
										</th>
										{#each allWeeks as weekNum, i (i)}
											<th
												class="border-l border-gray-200 px-1 py-2 text-center sm:px-2 sm:py-3 dark:border-gray-700"
												colspan="5"
											>
												<div
													class="text-[10px] font-semibold whitespace-nowrap text-gray-700 sm:text-xs dark:text-gray-300"
												>
													W{weekNum}
												</div>
												<div class="mt-0.5 flex justify-around gap-0.5 sm:mt-1 sm:gap-1">
													{#each dayLabels as day (day)}
														<span
															class="min-w-[1.5rem] text-[10px] text-gray-500 sm:min-w-[2rem] sm:text-xs dark:text-gray-400"
															>{day}</span
														>
													{/each}
												</div>
											</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each overviewData as userData (userData.userName)}
										<tr
											class="border-b border-gray-200 active:bg-gray-50 sm:hover:bg-gray-50 dark:border-gray-700 dark:active:bg-gray-700/50 dark:sm:hover:bg-gray-700/50"
										>
											<td
												class="sticky left-0 z-10 min-w-[100px] bg-white px-2 py-2 text-xs font-medium text-gray-900 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] sm:min-w-[120px] sm:px-4 sm:py-3 sm:text-sm dark:bg-gray-800 dark:text-white dark:shadow-[2px_0_5px_-2px_rgba(0,0,0,0.3)]"
											>
												<div class="flex items-center gap-1.5 sm:gap-2">
													<div
														class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-400 to-blue-600 text-[10px] font-semibold text-white sm:h-8 sm:w-8 sm:text-xs"
													>
														{userData.userName.charAt(0).toUpperCase()}
													</div>
													<span class="truncate">{userData.userName}</span>
												</div>
											</td>
											{#each allWeeks as weekNum (weekNum)}
												{@const week = userData.weeks.find((w: any) => w.weekNumber === weekNum)}
												{#if week}
													{#each week.priorities as priority, i (i)}
														<td
															class="border-l border-gray-200 px-1 py-2 text-center sm:px-2 sm:py-3 dark:border-gray-700"
														>
															{#if priority}
																<div
																	class="mx-auto flex h-6 w-6 items-center justify-center rounded text-[10px] font-semibold sm:h-8 sm:w-8 sm:rounded-md sm:text-sm {priorityColors[
																		priority as 1 | 2 | 3 | 4 | 5
																	]}"
																>
																	{priority}
																</div>
															{:else}
																<div
																	class="mx-auto h-6 w-6 rounded bg-gray-100 sm:h-8 sm:w-8 sm:rounded-md dark:bg-gray-700"
																></div>
															{/if}
														</td>
													{/each}
												{:else}
													{#each [1, 2, 3, 4, 5]}
														<td
															class="border-l border-gray-200 px-1 py-2 text-center sm:px-2 sm:py-3 dark:border-gray-700"
														>
															<div
																class="mx-auto h-6 w-6 rounded bg-gray-100 sm:h-8 sm:w-8 sm:rounded-md dark:bg-gray-700"
															></div>
														</td>
													{/each}
												{/if}
											{/each}
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				</div>
			</div>

			<!-- Demand Statistics -->
			<div class="mt-6 border-t border-gray-200 pt-4 sm:mt-8 sm:pt-6 dark:border-gray-700">
				<h3 class="mb-3 text-xs font-semibold text-gray-900 sm:mb-4 sm:text-sm dark:text-white">
					Demand per Day
				</h3>
				<div class="space-y-3 sm:space-y-4">
					{#each allWeeks as weekNum, i (i)}
						<div
							class="rounded-lg border border-gray-200 bg-gray-50 p-3 sm:p-4 dark:border-gray-700 dark:bg-gray-900/50"
						>
							<div
								class="mb-2 text-[10px] font-semibold text-gray-700 sm:text-xs dark:text-gray-300"
							>
								Week {weekNum}
							</div>
							<div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
								{#each dayKeys as day, dayIndex (day)}
									{@const dayStat = demandStats[weekNum]?.[day]}
									<div
										class="rounded-md border border-gray-200 bg-white p-2 dark:border-gray-600 dark:bg-gray-800"
									>
										<div
											class="mb-1 text-center text-[10px] font-medium text-gray-600 sm:text-xs dark:text-gray-400"
										>
											{dayLabels[dayIndex]}
										</div>
										{#if dayStat}
											<div class="space-y-0.5 sm:space-y-1">
												{#each [1, 2, 3, 4, 5] as priority (priority)}
													{#if dayStat[priority] > 0}
														<div class="flex items-center gap-1 text-[10px] sm:text-xs">
															<div
																class="h-2.5 w-2.5 rounded sm:h-3 sm:w-3 {priorityColors[
																	priority as 1 | 2 | 3 | 4 | 5
																]}"
															></div>
															<span class="text-gray-700 dark:text-gray-300"
																>{dayStat[priority]}</span
															>
														</div>
													{/if}
												{/each}
											</div>
										{:else}
											<div class="text-center text-xs text-gray-400">-</div>
										{/if}
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>
