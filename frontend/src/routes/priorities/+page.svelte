<script lang="ts">
	import { onMount } from 'svelte';
	import { currentUser, isAuthenticated } from '$lib/stores/auth';
	import type { Priority, DayPriorities, WeekData } from '$lib/types/priorities';

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
		getDayDates
	} from '$lib/utils/dateHelpers';
	import { validateWeekPriorities } from '$lib/utils/priorityHelpers';
	import { apiService } from '$lib/services/api';
	import Loading from '$lib/components/Loading.svelte';

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

	// Helper function to check if a week is complete
	function isWeekComplete(week: WeekData): boolean {
		const totalDaysInWeek = Object.keys(week.priorities).length;
		const validPriorities = Object.values(week.priorities).filter(
			(p) => p !== null && p !== undefined
		);

		return (
			totalDaysInWeek > 0 &&
			validPriorities.length === totalDaysInWeek &&
			new Set(validPriorities).size === totalDaysInWeek
		);
	}

	// Helper function to calculate week status
	function calculateWeekStatus(week: WeekData): 'completed' | 'pending' | 'empty' {
		const validCount = Object.values(week.priorities).filter(
			(p) => p !== null && p !== undefined
		).length;

		if (isWeekComplete(week)) {
			return 'completed';
		} else if (validCount > 0) {
			return 'pending';
		} else {
			return 'empty';
		}
	}

	// Derived state - now using the helper function
	let completedWeeks = $derived(weeks.filter((w) => calculateWeekStatus(w) === 'completed').length);
	let progressPercentage = $derived(weeks.length > 0 ? (completedWeeks / weeks.length) * 100 : 0);

	// Update weeks when month changes
	$effect(() => {
		const { year, month } = parseMonthString(selectedMonth);
		weeks = getWeeksForMonth(year, month);
		loadUserData();
	});

	// Check for mobile on mount
	onMount(() => {
		checkMobile();
		window.addEventListener('resize', checkMobile);
		return () => window.removeEventListener('resize', checkMobile);
	});

	function checkMobile() {
		isMobile = window.innerWidth < 768;
	}

	async function loadUserData() {
		if (!$currentUser) return;

		try {
			const records = await apiService.getPriorities(selectedMonth);

			records.forEach((record: any) => {
				const weekIndex = weeks.findIndex((w) => w.weekNumber === record.weekNumber);
				if (weekIndex !== -1) {
					weeks[weekIndex] = {
						...weeks[weekIndex],
						priorities: record.priorities,
						id: record.id
					};
					// Calculate status based on actual priorities
					weeks[weekIndex].status = calculateWeekStatus(weeks[weekIndex]);
				}
			});
		} catch (error) {
			console.error('Error loading priorities:', error);
			saveError = 'Fehler beim Laden der Prioritäten';
			setTimeout(() => (saveError = ''), 3000);
		}
	}

	function selectPriority(weekIndex: number, day: keyof DayPriorities, priority: Priority) {
		const currentWeek = weeks[weekIndex];
		const dayEntries = Object.entries(currentWeek.priorities) as [keyof DayPriorities, Priority][];

		dayEntries.forEach(([d, p]) => {
			if (p === priority && d !== day) {
				weeks[weekIndex].priorities[d] = null;
			}
		});

		weeks[weekIndex].priorities[day] = priority;

		// Update status after changing priorities
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

	async function saveWeekData(weekIndex: number, shouldCloseModal = false) {
		const week = weeks[weekIndex];
		const validation = validateWeekPriorities(week.priorities);

		if (!validation.isValid) {
			saveError = validation.message;
			setTimeout(() => (saveError = ''), 3000);
			throw new Error(validation.message);
		}
		if (!$currentUser) {
			saveError = 'No user id is set currently';
			setTimeout(() => (saveError = ''), 3000);
			throw new Error('No user id is set currently');
		}

		try {
			const data = {
				userId: $currentUser.id,
				month: selectedMonth,
				weekNumber: week.weekNumber,
				priorities: week.priorities,
				startDate: week.startDate,
				endDate: week.endDate
			};

			let record;

			// If we have an ID, try to update first
			if (week.id) {
				try {
					record = await apiService.updatePriority(week.id, data);
				} catch (updateError: any) {
					// If update fails because record doesn't exist, try to create
					if (
						updateError.message?.includes('nicht gefunden') ||
						updateError.message?.includes('not found')
					) {
						console.log('Record not found, creating new one');
						record = await apiService.createPriority(data);
						weeks[weekIndex].id = record.id;
					} else {
						throw updateError;
					}
				}
			} else {
				// No ID, try to create
				try {
					record = await apiService.createPriority(data);
					weeks[weekIndex].id = record.id;
				} catch (createError: any) {
					// If create fails because record exists, fetch it and then update
					if (
						createError.message?.includes('existiert bereits') ||
						createError.message?.includes('already exists')
					) {
						console.log('Record already exists, fetching and updating');
						// Reload user data to get the correct ID
						await loadUserData();
						// Try updating with the newly fetched ID
						const updatedWeek = weeks[weekIndex];
						if (updatedWeek.id) {
							record = await apiService.updatePriority(updatedWeek.id, data);
						} else {
							throw new Error('Konnte die bestehende Priorität nicht finden');
						}
					} else {
						throw createError;
					}
				}
			}

			// Calculate the correct status based on priorities
			weeks[weekIndex].status = calculateWeekStatus(weeks[weekIndex]);

			// Force reactivity update
			weeks = [...weeks];

			if (shouldCloseModal) {
				closeEditModal();
			}
		} catch (error: any) {
			saveError = error.message || 'Fehler beim Speichern. Bitte versuchen Sie es erneut.';
			setTimeout(() => (saveError = ''), 3000);
			console.error('Save error:', error);
			throw error;
		}
	}

	// Save function for mobile view (should close modal)
	async function saveWeek(weekIndex: number) {
		await saveWeekData(weekIndex, true);
	}

	// Save function for edit modal (shouldn't close modal)
	async function saveEditingWeek() {
		if (!editingWeek) return;

		// Update the week in the weeks array with the edited data
		weeks[editingWeekIndex] = { ...editingWeek };

		// Save the week without closing the modal
		await saveWeekData(editingWeekIndex, false);
	}
</script>

{#if $currentUser && $isAuthenticated}
	<div
		class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="container mx-auto max-w-6xl px-4 py-8">
			<Header {monthOptions} bind:selectedMonth />
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
				{weeks}
				{getDayDates}
			/>
		{/if}
	</div>
{:else}
	<Loading message="Lade..." />
{/if}

