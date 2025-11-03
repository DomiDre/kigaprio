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

	// Priority colors
	const priorityColors: Record<number, string> = {
		1: 'bg-red-100 text-red-800 border-red-300',
		2: 'bg-orange-100 text-orange-800 border-orange-300',
		3: 'bg-yellow-100 text-yellow-800 border-yellow-300',
		4: 'bg-green-100 text-green-800 border-green-300',
		5: 'bg-blue-100 text-blue-800 border-blue-300'
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
	class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4"
	role="dialog"
	aria-labelledby="modal-title"
>
	<div class="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-white shadow-2xl">
		<!-- Header -->
		<div class="sticky top-0 z-10 border-b border-gray-200 bg-white p-6">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div
						class="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-blue-600 text-xl font-bold text-white"
					>
						{userName.charAt(0).toUpperCase()}
					</div>
					<div>
						<h2 id="modal-title" class="text-xl font-bold text-gray-900">
							{userName}
						</h2>
						<p class="text-sm text-gray-500">Entschlüsselte Daten</p>
					</div>
				</div>
				<button
					type="button"
					class="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
					onclick={onClose}
					aria-label="Schließen"
				>
					<Close class="h-6 w-6" />
				</button>
			</div>
		</div>

		<div class="space-y-6 p-6">
			<!-- User Information Section -->
			<div class="rounded-lg border border-gray-200 bg-gray-50 p-6">
				<div class="mb-4 flex items-center gap-2">
					<Account class="h-5 w-5 text-gray-700" />
					<h3 class="text-lg font-semibold text-gray-900">Benutzerinformationen</h3>
				</div>

				<div class="space-y-3">
					{#if userData.name}
						<div class="flex items-start gap-3">
							<span class="w-32 text-sm font-medium text-gray-600">Name:</span>
							<span class="text-sm text-gray-900">{userData.name}</span>
						</div>
					{/if}

					<!-- {#if userData.email} -->
					<!-- 	<div class="flex items-start gap-3"> -->
					<!-- 		<span class="w-32 text-sm font-medium text-gray-600">E-Mail:</span> -->
					<!-- 		<span class="text-sm text-gray-900">{userData.email}</span> -->
					<!-- 	</div> -->
					<!-- {/if} -->

					{#each Object.entries(userData) as [key, value] (key)}
						{#if key !== 'name' && value}
							<div class="flex items-start gap-3">
								<span class="w-32 text-sm font-medium text-gray-600 capitalize">{key}:</span>
								<span class="text-sm text-gray-900">{value}</span>
							</div>
						{/if}
					{/each}
				</div>
			</div>

			<!-- Priorities Section -->
			{#if priorities && priorities.weeks && priorities.weeks.length > 0}
				<div class="rounded-lg border border-gray-200 bg-white p-6">
					<div class="mb-4 flex items-center gap-2">
						<Calendar class="h-5 w-5 text-gray-700" />
						<h3 class="text-lg font-semibold text-gray-900">Prioritäten</h3>
					</div>

					<div class="space-y-4">
						{#each priorities.weeks as week (week)}
							<div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
								<div class="mb-3 flex items-center justify-between">
									<h4 class="font-semibold text-gray-900">Woche {week.weekNumber}</h4>
									<!-- {#if week.startDate && week.endDate} -->
									<!-- 	<span class="text-sm text-gray-500"> -->
									<!-- 		{week.startDate} - {week.endDate} -->
									<!-- 	</span> -->
									<!-- {/if} -->
								</div>

								<div class="grid grid-cols-1 gap-2 sm:grid-cols-5">
									{#each Object.entries(dayNames) as [dayLabel] (dayLabel)}
										{@const priority = week[dayLabel as DayName]}
										<div class="rounded-lg border bg-white p-3 text-center">
											<div class="mb-2 text-xs font-medium text-gray-600">{dayLabel}</div>
											{#if priority && priority !== null}
												<div
													class="inline-flex items-center justify-center rounded-full border px-3 py-1 text-sm font-semibold {priorityColors[
														priority
													]}"
												>
													{priority}
												</div>
												<div class="mt-1 text-xs text-gray-500">
													{priorityLabels[priority]}
												</div>
											{:else}
												<div class="text-sm text-gray-400">-</div>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{:else}
				<div class="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
					<div class="flex items-start gap-2">
						<Information class="h-5 w-5 text-yellow-600" />
						<div>
							<p class="text-sm font-medium text-yellow-800">Keine Prioritäten verfügbar</p>
							<p class="text-sm text-yellow-700">
								Dieser Benutzer hat noch keine Prioritäten eingereicht.
							</p>
						</div>
					</div>
				</div>
			{/if}

			<!-- Security Notice -->
			<div class="rounded-lg border border-blue-200 bg-blue-50 p-4">
				<div class="flex items-start gap-2">
					<Information class="h-5 w-5 text-blue-600" />
					<div class="flex-1">
						<p class="text-sm font-medium text-blue-900">Datenschutzhinweis</p>
						<p class="text-sm text-blue-800">
							Diese Daten wurden lokal in Ihrem Browser entschlüsselt. Der Server hat niemals
							Zugriff auf die unverschlüsselten Daten.
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div class="sticky bottom-0 border-t border-gray-200 bg-gray-50 p-6">
			<div class="flex justify-end gap-3">
				<button
					type="button"
					class="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-100"
					onclick={onClose}
				>
					Schließen
				</button>
			</div>
		</div>
	</div>
</div>
