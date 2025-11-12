<script lang="ts">
	import Close from 'virtual:icons/mdi/close';
	import ChevronLeft from 'virtual:icons/mdi/chevron-left';
	import ChevronRight from 'virtual:icons/mdi/chevron-right';
	import Delete from 'virtual:icons/mdi/delete';
	import Edit from 'virtual:icons/mdi/pencil';
	import { fade, scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import type { VacationDayAdmin, VacationDayType } from '$lib/vacation-days.types';
	import { SvelteMap } from 'svelte/reactivity';

	interface Props {
		onClose: () => void;
		onSave: (date: string, type: VacationDayType, description: string) => Promise<void>;
		onUpdate: (date: string, type: VacationDayType, description: string) => Promise<void>;
		onDelete: (date: string) => Promise<void>;
		vacationDays: VacationDayAdmin[];
	}

	let { onClose, onSave, onUpdate, onDelete, vacationDays }: Props = $props();

	// State
	let currentYear = $state(new Date().getFullYear());
	let currentMonth = $state(new Date().getMonth()); // 0-11
	let selectedDate: string | null = $state(null);
	let showAddForm = $state(false);
	let editingDate: string | null = $state(null);
	let error = $state('');
	let isLoading = $state(false);

	// Form state
	let formType: VacationDayType = $state('public_holiday');
	let formDescription = $state('');

	const monthNames = [
		'Januar',
		'Februar',
		'März',
		'April',
		'Mai',
		'Juni',
		'Juli',
		'August',
		'September',
		'Oktober',
		'November',
		'Dezember'
	];

	const typeLabels: Record<VacationDayType, string> = {
		vacation: 'Urlaub',
		admin_leave: 'Admin Abwesenheit',
		public_holiday: 'Feiertag'
	};

	const typeColors: Record<VacationDayType, string> = {
		vacation:
			'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900/30 dark:text-blue-200 dark:border-blue-700',
		admin_leave:
			'bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-900/30 dark:text-purple-200 dark:border-purple-700',
		public_holiday:
			'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-200 dark:border-green-700'
	};

	// Convert vacation days to a map for quick lookup
	let vacationDayMap = $derived.by(() => {
		const map = new SvelteMap<string, VacationDayAdmin>();
		vacationDays.forEach((day) => {
			// Extract YYYY-MM-DD from the date string (might include time)
			const dateStr = day.date.split(' ')[0];
			map.set(dateStr, day);
		});
		return map;
	});

	// Get days in current month
	let daysInMonth = $derived.by(() => {
		const firstDay = new Date(currentYear, currentMonth, 1);
		const lastDay = new Date(currentYear, currentMonth + 1, 0);
		const daysInMonth = lastDay.getDate();
		const startDayOfWeek = firstDay.getDay(); // 0 = Sunday
		const adjustedStartDay = startDayOfWeek === 0 ? 6 : startDayOfWeek - 1; // Convert to Monday = 0

		const days: Array<{
			date: number | null;
			dateStr: string | null;
			vacation: VacationDayAdmin | null;
		}> = [];

		// Add empty cells for days before month starts
		for (let i = 0; i < adjustedStartDay; i++) {
			days.push({ date: null, dateStr: null, vacation: null });
		}

		// Add actual days of the month
		for (let date = 1; date <= daysInMonth; date++) {
			const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(date).padStart(2, '0')}`;
			const vacation = vacationDayMap.get(dateStr) || null;
			days.push({ date, dateStr, vacation });
		}

		return days;
	});

	function previousMonth() {
		if (currentMonth === 0) {
			currentMonth = 11;
			currentYear--;
		} else {
			currentMonth--;
		}
	}

	function nextMonth() {
		if (currentMonth === 11) {
			currentMonth = 0;
			currentYear++;
		} else {
			currentMonth++;
		}
	}

	function previousYear() {
		currentYear--;
	}

	function nextYear() {
		currentYear++;
	}

	function handleDayClick(dateStr: string | null) {
		if (!dateStr) return;
		selectedDate = dateStr;
		const existing = vacationDayMap.get(dateStr);

		if (existing) {
			// Edit existing vacation day
			editingDate = dateStr;
			formType = existing.type;
			formDescription = existing.description || '';
			showAddForm = true;
		} else {
			// Add new vacation day
			editingDate = null;
			formType = 'public_holiday';
			formDescription = '';
			showAddForm = true;
		}
	}

	function closeForm() {
		showAddForm = false;
		selectedDate = null;
		editingDate = null;
		formType = 'public_holiday';
		formDescription = '';
		error = '';
	}

	async function handleSave() {
		if (!selectedDate) return;

		error = '';
		isLoading = true;

		try {
			if (editingDate) {
				await onUpdate(selectedDate, formType, formDescription);
			} else {
				await onSave(selectedDate, formType, formDescription);
			}
			closeForm();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten';
		} finally {
			isLoading = false;
		}
	}

	async function handleDelete(dateStr: string) {
		if (!confirm('Möchten Sie diesen Eintrag wirklich löschen?')) return;

		error = '';
		isLoading = true;

		try {
			await onDelete(dateStr);
			closeForm();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten';
		} finally {
			isLoading = false;
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			if (showAddForm) {
				closeForm();
			} else {
				onClose();
			}
		}
	}

	function handleStopPropagation(event: Event) {
		event.stopPropagation();
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div
	class="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4"
	transition:fade={{ duration: 200 }}
	onclick={onClose}
	role="button"
	tabindex="-1"
>
	<div
		class="flex h-[95vh] w-full max-w-5xl flex-col rounded-t-2xl bg-white shadow-2xl sm:h-auto sm:max-h-[90vh] sm:rounded-2xl dark:bg-gray-800"
		transition:scale={{ duration: 300, easing: cubicOut, start: 0.9 }}
		onclick={handleStopPropagation}
		role="dialog"
		aria-modal="true"
		tabindex="0"
	>
		<!-- Header -->
		<div
			class="flex items-center justify-between border-b border-gray-200 p-4 sm:p-6 dark:border-gray-700"
		>
			<h2 class="text-lg font-bold text-gray-800 sm:text-2xl dark:text-white">
				Abwesenheitstage verwalten
			</h2>
			<button
				onclick={onClose}
				class="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-200"
				aria-label="Schließen"
			>
				<Close class="h-5 w-5 sm:h-6 sm:w-6" />
			</button>
		</div>

		<!-- Body -->
		<div class="flex-1 overflow-y-auto p-4 sm:p-6">
			{#if error}
				<div
					class="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200"
					transition:scale={{ duration: 200 }}
				>
					{error}
				</div>
			{/if}

			<!-- Calendar Navigation -->
			<div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
				<!-- Month Navigation -->
				<div class="flex items-center justify-center gap-2">
					<button
						onclick={previousMonth}
						class="rounded-lg p-2 text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
						aria-label="Vorheriger Monat"
					>
						<ChevronLeft class="h-5 w-5" />
					</button>
					<span
						class="min-w-[140px] text-center text-lg font-semibold text-gray-800 dark:text-white"
					>
						{monthNames[currentMonth]}
					</span>
					<button
						onclick={nextMonth}
						class="rounded-lg p-2 text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
						aria-label="Nächster Monat"
					>
						<ChevronRight class="h-5 w-5" />
					</button>
				</div>

				<!-- Year Navigation -->
				<div class="flex items-center justify-center gap-2">
					<button
						onclick={previousYear}
						class="rounded-lg p-2 text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
						aria-label="Vorheriges Jahr"
					>
						<ChevronLeft class="h-5 w-5" />
					</button>
					<span
						class="min-w-[80px] text-center text-lg font-semibold text-gray-800 dark:text-white"
					>
						{currentYear}
					</span>
					<button
						onclick={nextYear}
						class="rounded-lg p-2 text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
						aria-label="Nächstes Jahr"
					>
						<ChevronRight class="h-5 w-5" />
					</button>
				</div>
			</div>

			<!-- Legend -->
			<div class="mb-4 flex flex-wrap gap-3 text-sm">
				{#each Object.entries(typeLabels) as [type, label] (type)}
					<div class="flex items-center gap-2">
						<div class="h-4 w-4 rounded border {typeColors[type as VacationDayType]}"></div>
						<span class="text-gray-700 dark:text-gray-300">{label}</span>
					</div>
				{/each}
			</div>

			<!-- Calendar Grid -->
			<div class="mb-6 overflow-x-auto">
				<div class="inline-block min-w-full">
					<!-- Weekday headers -->
					<div
						class="mb-2 grid grid-cols-7 gap-1 text-center text-sm font-semibold text-gray-600 dark:text-gray-400"
					>
						<div>Mo</div>
						<div>Di</div>
						<div>Mi</div>
						<div>Do</div>
						<div>Fr</div>
						<div>Sa</div>
						<div>So</div>
					</div>

					<!-- Days grid -->
					<div class="grid grid-cols-7 gap-1">
						{#each daysInMonth as day (day.dateStr || Math.random())}
							{#if day.date === null}
								<div class="aspect-square"></div>
							{:else}
								<button
									onclick={() => handleDayClick(day.dateStr)}
									class="group relative aspect-square rounded-lg border transition-all hover:shadow-md
									{day.vacation
										? `${typeColors[day.vacation.type]} border-2`
										: 'border-gray-200 bg-white hover:border-purple-300 hover:bg-purple-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-purple-600 dark:hover:bg-gray-700'}"
								>
									<span
										class="text-sm font-medium
									{day.vacation ? '' : 'text-gray-700 dark:text-gray-300'}"
									>
										{day.date}
									</span>
									{#if day.vacation}
										<div
											class="absolute inset-0 flex items-center justify-center opacity-0 transition-opacity group-hover:opacity-100"
										>
											<Edit class="h-4 w-4" />
										</div>
									{/if}
								</button>
							{/if}
						{/each}
					</div>
				</div>
			</div>

			<!-- Add/Edit Form -->
			{#if showAddForm && selectedDate}
				<div
					class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/50"
					transition:scale={{ duration: 200 }}
				>
					<h3 class="mb-4 text-lg font-semibold text-gray-800 dark:text-white">
						{editingDate ? 'Abwesenheit bearbeiten' : 'Abwesenheit hinzufügen'} - {selectedDate}
					</h3>

					<div class="space-y-4">
						<!-- Type Selection -->
						<div>
							<label class="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-300">
								Typ:
							</label>
							<select
								bind:value={formType}
								class="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-purple-500 focus:ring-4 focus:ring-purple-500/10 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-white"
							>
								{#each Object.entries(typeLabels) as [type, label] (type)}
									<option value={type}>{label}</option>
								{/each}
							</select>
						</div>

						<!-- Description -->
						<div>
							<label class="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-300">
								Beschreibung (optional):
							</label>
							<input
								type="text"
								bind:value={formDescription}
								placeholder="z.B. Weihnachten, Neujahr, etc."
								class="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-purple-500 focus:ring-4 focus:ring-purple-500/10 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-white"
							/>
						</div>

						<!-- Action Buttons -->
						<div class="flex flex-col gap-2 sm:flex-row sm:justify-between">
							<div class="flex gap-2">
								<button
									onclick={handleSave}
									disabled={isLoading}
									class="flex-1 rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none dark:bg-purple-500 dark:hover:bg-purple-600"
								>
									{isLoading ? 'Speichere...' : editingDate ? 'Aktualisieren' : 'Hinzufügen'}
								</button>
								<button
									onclick={closeForm}
									disabled={isLoading}
									class="flex-1 rounded-lg bg-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-300 disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
								>
									Abbrechen
								</button>
							</div>
							{#if editingDate}
								<button
									onclick={() => handleDelete(editingDate!)}
									disabled={isLoading}
									class="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-red-500 dark:hover:bg-red-600"
								>
									<Delete class="inline h-4 w-4" /> Löschen
								</button>
							{/if}
						</div>
					</div>
				</div>
			{/if}

			<!-- Help Text -->
			<div
				class="mt-6 rounded-lg bg-blue-50 p-3 text-xs text-blue-800 sm:text-sm dark:bg-blue-900/20 dark:text-blue-200"
			>
				<strong>Hinweis:</strong> Klicken Sie auf einen Tag im Kalender, um eine Abwesenheit hinzuzufügen
				oder zu bearbeiten. Markierte Tage werden für alle Benutzer angezeigt.
			</div>
		</div>
	</div>
</div>
