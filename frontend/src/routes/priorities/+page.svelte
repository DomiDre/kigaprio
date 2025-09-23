<script lang="ts">
	import { onMount } from 'svelte';
	import { pb } from '$lib/services/pocketbase';
	import { currentUser } from '$lib/stores/auth';
	import type { Priority, DayPriorities, WeekData } from '$lib/types/priorities';

	// Import components
	import Header from '$lib/components/Header.svelte';
	import Legend from '$lib/components/Legend.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import WeekTabs from '$lib/components/WeekTabs.svelte';
	import Notifications from '$lib/components/Notifications.svelte';
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

	// Component state
	const monthOptions = getMonthOptions();
	let selectedMonth = $state(monthOptions[0]);
	let activeWeekIndex = $state(0);
	let isMobile = $state(false);
	let showEditModal = $state(false);
	let editingWeek = $state<WeekData | null>(null);
	let saveError = $state('');
	let saveSuccess = $state('');
	let weeks = $state<WeekData[]>([]);

	// Derived state
	let completedWeeks = $derived(weeks.filter((w) => w.status === 'completed').length);
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
			const records = await pb.collection('priorities').getFullList({
				filter: `userId = "${$currentUser.id}" && month = "${selectedMonth}"`,
				sort: 'weekNumber'
			});

			records.forEach((record: any) => {
				const weekIndex = weeks.findIndex((w) => w.weekNumber === record.weekNumber);
				if (weekIndex !== -1) {
					weeks[weekIndex] = {
						...weeks[weekIndex],
						priorities: record.priorities,
						status: 'completed',
						id: record.id
					};
				}
			});
		} catch (error) {
			console.error('Error loading priorities:', error);
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
	}

	function openEditModal(week: WeekData, index: number) {
		editingWeek = { ...week };
		activeWeekIndex = index;
		showEditModal = true;
	}

	function closeEditModal() {
		showEditModal = false;
		editingWeek = null;
	}

	async function saveWeek(weekIndex: number) {
		const week = weeks[weekIndex];
		const validation = validateWeekPriorities(week.priorities);

		if (!validation.isValid) {
			saveError = validation.message;
			setTimeout(() => (saveError = ''), 3000);
			return;
		}

		try {
			const data = {
				userId: $currentUser?.id,
				month: selectedMonth,
				weekNumber: week.weekNumber,
				priorities: week.priorities,
				startDate: week.startDate,
				endDate: week.endDate
			};

			if (week.id) {
				await pb.collection('priorities').update(week.id, data);
			} else {
				const record = await pb.collection('priorities').create(data);
				weeks[weekIndex].id = record.id;
			}

			weeks[weekIndex].status = 'completed';
			saveSuccess = 'Woche erfolgreich gespeichert!';
			setTimeout(() => (saveSuccess = ''), 3000);
			closeEditModal();
		} catch (error) {
			saveError = 'Fehler beim Speichern. Bitte versuchen Sie es erneut.';
			setTimeout(() => (saveError = ''), 3000);
			console.error('Save error:', error);
		}
	}
</script>

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
		<EditModal {editingWeek} {activeWeekIndex} {closeEditModal} {saveWeek} {weeks} {getDayDates} />
	{/if}
</div>
