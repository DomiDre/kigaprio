<script lang="ts">
	import Close from 'virtual:icons/mdi/close';
	import Account from 'virtual:icons/mdi/account';
	import Calendar from 'virtual:icons/mdi/calendar';
	import Information from 'virtual:icons/mdi/information';
	import type { DecryptedPriorities, DecryptedUserData } from '$lib/dashboard.types';
	import type { DayName } from '$lib/priorities.types';

	interface Props {
		userName: string;
		userData: DecryptedUserData;
		priorities: DecryptedPriorities;
		onClose: () => void;
	}

	let { userName, userData, priorities, onClose }: Props = $props();

	// Days of the week
	const dayNames = {
		monday: 'Montag',
		tuesday: 'Dienstag',
		wednesday: 'Mittwoch',
		thursday: 'Donnerstag',
		friday: 'Freitag'
	};

	// Priority colors with dark mode support
	const priorityColors: Record<number, string> = {
		1: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700',
		2: 'bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-700',
		3: 'bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-700',
		4: 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700',
		5: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700'
	};

	const priorityLabels: Record<number, string> = {
		5: 'Höchste Priorität',
		4: 'Hohe Priorität',
		3: 'Mittlere Priorität',
		2: 'Niedrige Priorität',
		1: 'Niedrigste Priorität'
	};
</script>

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
	role="dialog"
	aria-labelledby="modal-title"
>
	<div
		class="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl dark:bg-gray-800"
	>
		<!-- Header - Sticky -->
		<div class="border-b border-gray-200 bg-white p-4 sm:p-6 dark:border-gray-700 dark:bg-gray-800">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2 sm:gap-3">
					<div
						class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-blue-600 text-lg font-bold text-white sm:h-12 sm:w-12 sm:text-xl"
					>
						{userName.charAt(0).toUpperCase()}
					</div>
					<div class="min-w-0">
						<h2
							id="modal-title"
							class="truncate text-lg font-bold text-gray-900 sm:text-xl dark:text-white"
						>
							{userName}
						</h2>
						<p class="text-xs text-gray-500 sm:text-sm dark:text-gray-400">Entschlüsselte Daten</p>
					</div>
				</div>
				<button
					type="button"
					class="flex-shrink-0 rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
					onclick={onClose}
					aria-label="Schließen"
				>
					<Close class="h-5 w-5 sm:h-6 sm:w-6" />
				</button>
			</div>
		</div>

		<!-- Body - Scrollable -->
		<div class="flex-1 space-y-4 overflow-y-auto p-4 sm:space-y-6 sm:p-6">
			<!-- User Information Section -->
			<div
				class="rounded-lg border border-gray-200 bg-gray-50 p-4 sm:p-6 dark:border-gray-700 dark:bg-gray-900/50"
			>
				<div class="mb-3 flex items-center gap-2 sm:mb-4">
					<Account class="h-4 w-4 text-gray-700 sm:h-5 sm:w-5 dark:text-gray-300" />
					<h3 class="text-base font-semibold text-gray-900 sm:text-lg dark:text-white">
						Benutzerinformationen
					</h3>
				</div>

				<div class="space-y-2 sm:space-y-3">
					{#if userData.name}
						<div class="flex flex-col gap-1 sm:flex-row sm:items-start sm:gap-3">
							<span class="text-xs font-medium text-gray-600 sm:w-32 sm:text-sm dark:text-gray-400"
								>Name:</span
							>
							<span class="text-sm text-gray-900 dark:text-gray-100">{userData.name}</span>
						</div>
					{/if}

					{#each Object.entries(userData) as [key, value] (key)}
						{#if key !== 'name' && value}
							<div class="flex flex-col gap-1 sm:flex-row sm:items-start sm:gap-3">
								<span
									class="text-xs font-medium text-gray-600 capitalize sm:w-32 sm:text-sm dark:text-gray-400"
									>{key}:</span
								>
								<span class="text-sm text-gray-900 dark:text-gray-100">{value}</span>
							</div>
						{/if}
					{/each}
				</div>
			</div>

			<!-- Priorities Section -->
			{#if priorities && priorities.weeks && priorities.weeks.length > 0}
				<div
					class="rounded-lg border border-gray-200 bg-white p-4 sm:p-6 dark:border-gray-700 dark:bg-gray-800"
				>
					<div class="mb-3 flex items-center gap-2 sm:mb-4">
						<Calendar class="h-4 w-4 text-gray-700 sm:h-5 sm:w-5 dark:text-gray-300" />
						<h3 class="text-base font-semibold text-gray-900 sm:text-lg dark:text-white">
							Prioritäten
						</h3>
					</div>

					<div class="space-y-3 sm:space-y-4">
						{#each priorities.weeks as week (week)}
							<div
								class="rounded-lg border border-gray-200 bg-gray-50 p-3 sm:p-4 dark:border-gray-700 dark:bg-gray-900/50"
							>
								<div class="mb-2 flex items-center justify-between sm:mb-3">
									<h4 class="text-sm font-semibold text-gray-900 sm:text-base dark:text-white">
										Woche {week.weekNumber}
									</h4>
								</div>

								<div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
									{#each Object.entries(dayNames) as [dayKey, dayLabel] (dayKey)}
										{@const priority = week[dayKey as DayName]}
										<div
											class="rounded-lg border border-gray-200 bg-white p-2 text-center sm:p-3 dark:border-gray-700 dark:bg-gray-800"
										>
											<div
												class="mb-1 text-xs font-medium text-gray-600 sm:mb-2 dark:text-gray-400"
											>
												{dayLabel}
											</div>
											{#if priority && priority !== null}
												<div
													class="inline-flex items-center justify-center rounded-full border px-2 py-0.5 text-xs font-semibold sm:px-3 sm:py-1 sm:text-sm {priorityColors[
														priority
													]}"
												>
													{priority}
												</div>
												<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
													{priorityLabels[priority]}
												</div>
											{:else}
												<div class="text-sm text-gray-400 dark:text-gray-500">-</div>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{:else}
				<div
					class="rounded-lg border border-yellow-200 bg-yellow-50 p-3 sm:p-4 dark:border-yellow-800 dark:bg-yellow-900/20"
				>
					<div class="flex items-start gap-2">
						<Information
							class="h-4 w-4 flex-shrink-0 text-yellow-600 sm:h-5 sm:w-5 dark:text-yellow-500"
						/>
						<div class="min-w-0 flex-1">
							<p class="text-xs font-medium text-yellow-800 sm:text-sm dark:text-yellow-300">
								Keine Prioritäten verfügbar
							</p>
							<p class="text-xs text-yellow-700 dark:text-yellow-400">
								Dieser Benutzer hat noch keine Prioritäten eingereicht.
							</p>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Footer - Sticky -->
		<div
			class="border-t border-gray-200 bg-gray-50 p-4 sm:p-6 dark:border-gray-700 dark:bg-gray-900/50"
		>
			<div class="flex justify-end gap-3">
				<button
					type="button"
					class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-700 transition-colors hover:bg-gray-100 sm:w-auto sm:py-2 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
					onclick={onClose}
				>
					Schließen
				</button>
			</div>
		</div>
	</div>
</div>
