<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated, authStore } from '$lib/stores/auth';
	import type { DayName, Priority, WeekData, WeekStatus } from '$lib/types/priorities';

	// Import components
	import Legend from '$lib/components/Legend.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import WeekTabs from '$lib/components/WeekTabs.svelte';
	import Notifications from '$lib/components/Notifications.svelte';
	import Header from './Header.svelte';
	import MobileWeekView from './MobileWeekView.svelte';
	import DesktopGridView from './DesktopGridView.svelte';
	import EditModal from './EditModal.svelte';

	// Import utilities
	import {
		getWeeksForMonth,
		getMonthOptions,
		parseMonthString,
		getDayDates,
		formatMonthForAPI
	} from '$lib/utils/dateHelpers';
	import { apiService } from '$lib/services/api';
	import Loading from '$lib/components/Loading.svelte';
	import { dayKeys } from '$lib/config/priorities';

	// Component state
	const monthOptions = getMonthOptions();
	let selectedMonth = $state(monthOptions[0]);
	let activeWeekIndex = $state(0);
	let isMobile = $state(false);
	let showEditModal = $state(false);
	let editingWeek = $state<WeekData | null>(null);
	let editingWeekIndex = $state<number>(0);
	let saveError = $state('');
	let saveSuccess = $state('');
	let weeks = $state<WeekData[]>([]);
	let isLoading = $state(true);
	let dekMissing = $state(false);

	// Helper function to check if a week is complete
	function isWeekComplete(week: WeekData): boolean {
		const priorities = [week.monday, week.tuesday, week.wednesday, week.thursday, week.friday];
		const validPriorities = priorities.filter((p) => p !== null && p !== undefined);

		return validPriorities.length === 5 && new Set(validPriorities).size === 5;
	}

	// Helper function to calculate week status
	function calculateWeekStatus(week: WeekData): WeekStatus {
		const priorities = [week.monday, week.tuesday, week.wednesday, week.thursday, week.friday];
		const validCount = priorities.filter((p) => p !== null && p !== undefined).length;

		if (isWeekComplete(week)) {
			return 'completed';
		} else if (validCount > 0) {
			return 'pending';
		} else {
			return 'empty';
		}
	}

	// Derived state
	let completedWeeks = $derived(weeks.filter((w) => calculateWeekStatus(w) === 'completed').length);
	let progressPercentage = $derived(weeks.length > 0 ? (completedWeeks / weeks.length) * 100 : 0);

	// Check authentication and DEK availability on mount
	onMount(() => {
		if (!$isAuthenticated) {
			goto('/login');
			return;
		}

		checkMobile();
		window.addEventListener('resize', checkMobile);

		isLoading = false;

		return () => window.removeEventListener('resize', checkMobile);
	});

	// Update weeks when month changes
	$effect(() => {
		console.log('Updating...');
		const { year, month } = parseMonthString(selectedMonth);
		weeks = getWeeksForMonth(year, month);
		if (!dekMissing && $isAuthenticated) {
			console.log('Getting that week data');
			loadUserData();
		}
	});

	function checkMobile() {
		isMobile = window.innerWidth < 768;
	}

	async function loadUserData() {
		if (!$isAuthenticated) return;

		try {
			const apiMonth = formatMonthForAPI(selectedMonth);
			const records = await apiService.getPriorities(apiMonth);

			// Update local weeks with data from backend
			records.weeks.forEach((record) => {
				const weekIndex = weeks.findIndex((w) => w.weekNumber === record.weekNumber);
				if (weekIndex !== -1) {
					weeks[weekIndex].monday = record.monday;
					weeks[weekIndex].tuesday = record.tuesday;
					weeks[weekIndex].wednesday = record.wednesday;
					weeks[weekIndex].thursday = record.thursday;
					weeks[weekIndex].friday = record.friday;
					weeks[weekIndex].status = calculateWeekStatus(weeks[weekIndex]);
				}
			});
			weeks = [...weeks];
		} catch (error: any) {
			console.error('Error loading priorities:', error);

			// Check if it's a DEK-related error
			if (error.message?.includes('Verschlüsselungsschlüssel')) {
				dekMissing = true;
				saveError = 'Sitzung abgelaufen. Sie werden zur Anmeldung weitergeleitet...';
				setTimeout(() => {
					authStore.clearAuth();
					goto('/login');
				}, 2000);
			} else {
				saveError = 'Fehler beim Laden der Prioritäten';
				setTimeout(() => (saveError = ''), 3000);
			}
		}
	}

	function selectPriority(weekIndex: number, day: DayName, priority: Priority) {
		const currentWeek = weeks[weekIndex];

		dayKeys.forEach((d) => {
			if (currentWeek[d] === priority && d !== day) {
				weeks[weekIndex][d] = null;
			}
		});

		weeks[weekIndex][day] = priority;
		weeks[weekIndex].status = calculateWeekStatus(weeks[weekIndex]);
	}

	function openEditModal(week: WeekData, index: number) {
		editingWeek = { ...week };
		editingWeekIndex = index;
		showEditModal = true;
	}

	function closeEditModal() {
		showEditModal = false;
		editingWeek = null;
	}

	async function saveMonthData() {
		if (!$isAuthenticated) {
			saveError = 'No user id is set currently';
			setTimeout(() => (saveError = ''), 3000);
			throw new Error('No user id is set currently');
		}

		try {
			// Convert display format to API format
			const apiMonth = formatMonthForAPI(selectedMonth);

			// Prepare all weeks data for the month
			// Filter out weeks that have at least some data
			const weeksData = weeks.map((week) => ({
				weekNumber: week.weekNumber,
				monday: week.monday,
				tuesday: week.tuesday,
				wednesday: week.wednesday,
				thursday: week.thursday,
				friday: week.friday
			}));

			// Send all weeks for the month
			await apiService.updatePriority(apiMonth, weeksData);

			// Update local state with response if needed
			weeks = weeks.map((week) => ({
				...week,
				status: calculateWeekStatus(week)
			}));

			saveSuccess = 'Prioritäten erfolgreich gespeichert';
			setTimeout(() => (saveSuccess = ''), 3000);
		} catch (error: any) {
			saveError = error.message || 'Fehler beim Speichern. Bitte versuchen Sie es erneut.';
			setTimeout(() => (saveError = ''), 3000);
			console.error('Save error:', error);
			throw error;
		}
	}

	async function saveWeekData(weekIndex: number, shouldCloseModal = false) {
		const week = weeks[weekIndex];

		// Validate that all 5 days have unique priorities (1-5)
		const priorities = [week.monday, week.tuesday, week.wednesday, week.thursday, week.friday];
		const validPriorities = priorities.filter((p) => p !== null && p !== undefined);

		if (validPriorities.length === 5) {
			const uniquePriorities = new Set(validPriorities);
			if (uniquePriorities.size !== 5) {
				saveError = 'Jeder Wochentag muss eine eindeutige Priorität haben';
				setTimeout(() => (saveError = ''), 3000);
				throw new Error('Jeder Wochentag muss eine eindeutige Priorität haben');
			}
		}

		// Save all weeks for the month (backend expects month-based updates)
		await saveMonthData();

		if (shouldCloseModal) {
			closeEditModal();
		}
	}

	async function saveWeek(weekIndex: number) {
		await saveWeekData(weekIndex, true);
	}

	async function saveEditingWeek() {
		if (!editingWeek) return;
		weeks[editingWeekIndex] = { ...editingWeek };
		await saveWeekData(editingWeekIndex, false);
	}

	function handleWeekChange(dayKey: DayName, priority: Priority) {
		if (!editingWeek) return;

		// Get the old priority for this day
		const oldPriority = editingWeek[dayKey];

		// Check if this priority is already used elsewhere
		const dayUsingPriority = dayKeys.find(
			(day) => day !== dayKey && editingWeek![day] === priority
		);

		// Set the priority for the selected day
		editingWeek[dayKey] = priority;

		// If this priority was used elsewhere, swap the priorities
		if (dayUsingPriority) {
			editingWeek[dayUsingPriority] = oldPriority;
		}

		// Update the main weeks array
		weeks[editingWeekIndex] = { ...editingWeek };
	}
</script>

{#if isLoading}
	<Loading message="Lade..." />
{:else if dekMissing}
	<div
		class="flex min-h-screen items-center justify-center bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="max-w-md rounded-2xl bg-white p-8 text-center shadow-xl dark:bg-gray-800">
			<div class="mb-4 text-6xl">⚠️</div>
			<h2 class="mb-4 text-2xl font-bold text-gray-800 dark:text-white">Sitzung abgelaufen</h2>
			<p class="mb-4 text-gray-600 dark:text-gray-300">
				Ihre Sitzung ist abgelaufen. Sie werden zur Anmeldung weitergeleitet...
			</p>
			<div class="animate-spin text-4xl">⟳</div>
		</div>
	</div>
{:else if $isAuthenticated}
	<div
		class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="container mx-auto max-w-6xl px-4 py-8">
			<Header {monthOptions} bind:selectedMonth />

			<!-- Navigation Bar -->
			<div class="mb-6 flex items-center justify-end gap-3">
				<a
					href="/dashboard"
					class="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors duration-200 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-5 w-5"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
						/>
					</svg>
					Dashboard
				</a>
			</div>

			<Legend />
			{#if weeks.length > 0}
				<ProgressBar {completedWeeks} totalWeeks={weeks.length} {progressPercentage} />

				{#if isMobile}
					<WeekTabs {weeks} bind:activeWeekIndex />
					<MobileWeekView
						week={weeks[activeWeekIndex]}
						weekIndex={activeWeekIndex}
						{selectPriority}
						{saveWeek}
						{getDayDates}
					/>
				{:else}
					<DesktopGridView {weeks} {openEditModal} />
				{/if}
			{/if}
			<Notifications {saveError} {saveSuccess} />
		</div>

		{#if showEditModal && editingWeek}
			<EditModal
				{editingWeek}
				activeWeekIndex={editingWeekIndex}
				{closeEditModal}
				saveWeek={saveEditingWeek}
				{getDayDates}
				onWeekChange={handleWeekChange}
			/>
		{/if}
	</div>
{:else}
	<Loading message="Lade..." />
{/if}
