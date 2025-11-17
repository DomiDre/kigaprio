<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated, authStore } from '$lib/auth.store';
	import type { DayName, Priority, WeekData } from '$lib/priorities.types';
	import type { VacationDay } from '$lib/vacation-days.types';

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
		formatMonthForAPI,
		getWeekStatus as getWeekStatusUtil
	} from '$lib/dateHelpers.utils';
	import { apiService } from '$lib/api.service';
	import Loading from '$lib/components/Loading.svelte';
	import { dayKeys } from '$lib/priorities.config';
	import ProtectedRoute from '$lib/components/ProtectedRoute.svelte';
	import { SvelteMap } from 'svelte/reactivity';
	import { LL } from '$i18n/i18n-svelte';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';

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
	let vacationDays = $state<VacationDay[]>([]);

	// Derived state
	let completedWeeks = $derived(
		weeks.filter((w) => getWeekStatusUtil(w, vacationDaysMap) === 'completed').length
	);
	let progressPercentage = $derived(weeks.length > 0 ? (completedWeeks / weeks.length) * 100 : 0);

	// Create a map of vacation days by date (YYYY-MM-DD format)
	let vacationDaysMap = $derived.by(() => {
		const map = new SvelteMap<string, VacationDay>();
		vacationDays.forEach((vd) => {
			// Extract YYYY-MM-DD from the timestamp format (YYYY-MM-DD HH:mm:ss.SSSZ)
			const dateMatch = vd.date.match(/^(\d{4}-\d{2}-\d{2})/);
			if (dateMatch) {
				map.set(dateMatch[1], vd);
			}
		});
		return map;
	});

	// Check authentication and DEK availability on mount
	onMount(() => {
		if (!$isAuthenticated) {
			goto('/login');
			return;
		}

		checkMobile();
		window.addEventListener('resize', checkMobile);

		isLoading = false;

		// Load initial data
		loadVacationDays();

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
			loadVacationDays();
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
					weeks[weekIndex].status = getWeekStatusUtil(weeks[weekIndex], vacationDaysMap);
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

	async function loadVacationDays() {
		if (!$isAuthenticated) return;

		try {
			const { year, month } = parseMonthString(selectedMonth);
			vacationDays = await apiService.getVacationDays({
				year,
				month: month + 1 // month is 0-indexed
			});
		} catch (error: any) {
			console.error('Error loading vacation days:', error);
			// Don't show error to user, vacation days are optional information
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
		weeks[weekIndex].status = getWeekStatusUtil(weeks[weekIndex], vacationDaysMap);
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
				status: getWeekStatusUtil(week, vacationDaysMap)
			}));

			saveSuccess = $LL.priorities.savedSuccess();
			setTimeout(() => (saveSuccess = ''), 3000);
		} catch (error: any) {
			saveError = error.message || $LL.priorities.errorSavingRetry();
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
				saveError = $LL.priorities.errorUniquePriorities();
				setTimeout(() => (saveError = ''), 3000);
				throw new Error($LL.priorities.errorUniquePriorities());
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
	<Loading message={$LL.common.loading()} />
{:else}
	<ProtectedRoute>
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
							{vacationDaysMap}
						/>
					{:else}
						<DesktopGridView {weeks} {openEditModal} {vacationDaysMap} />
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
					{vacationDaysMap}
				/>
			{/if}
		</div>
	</ProtectedRoute>
{/if}
