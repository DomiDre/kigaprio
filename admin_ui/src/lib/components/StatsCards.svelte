<script lang="ts">
	import AccountGroup from 'virtual:icons/mdi/account-group';
	import CheckCircle from 'virtual:icons/mdi/check-circle';
	import ClockOutline from 'virtual:icons/mdi/clock-outline';
	import TrendingUp from 'virtual:icons/mdi/trending-up';
	import type { Stats } from '$lib/dashboard.types';

	interface Props {
		stats: Stats;
	}

	let { stats }: Props = $props();
</script>

<!-- Mobile: 1 column, Tablet: 2 columns, Desktop: 4 columns -->
<div class="mb-6 grid grid-cols-1 gap-4 sm:mb-8 sm:grid-cols-2 sm:gap-6 lg:grid-cols-4">
	<!-- Total Users -->
	<div
		class="rounded-xl border border-gray-200 bg-white p-4 shadow-xl sm:p-6 dark:border-gray-700 dark:bg-gray-800"
	>
		<div class="flex items-center justify-between">
			<div>
				<p class="text-xs font-medium text-gray-600 sm:text-sm dark:text-gray-300">Anzahl Nutzer</p>
				<p class="mt-1 text-2xl font-bold text-gray-900 sm:mt-2 sm:text-3xl dark:text-white">
					{stats.totalUsers}
				</p>
			</div>
			<div
				class="rounded-lg bg-gradient-to-br from-purple-100 to-blue-100 p-2 sm:p-3 dark:from-purple-900/30 dark:to-blue-900/30"
			>
				<AccountGroup class="h-5 w-5 text-purple-600 sm:h-6 sm:w-6 dark:text-purple-400" />
			</div>
		</div>
	</div>

	<!-- Submitted -->
	<div
		class="rounded-xl border border-gray-200 bg-white p-4 shadow-xl sm:p-6 dark:border-gray-700 dark:bg-gray-800"
	>
		<div class="flex items-center justify-between">
			<div>
				<p class="text-xs font-medium text-gray-600 sm:text-sm dark:text-gray-300">Eingereicht</p>
				<p class="mt-1 text-2xl font-bold text-green-600 sm:mt-2 sm:text-3xl dark:text-green-400">
					{stats.submitted}
				</p>
			</div>
			<div class="rounded-lg bg-green-50 p-2 sm:p-3 dark:bg-green-900/30">
				<CheckCircle class="h-5 w-5 text-green-600 sm:h-6 sm:w-6 dark:text-green-400" />
			</div>
		</div>
	</div>

	<!-- Pending -->
	<div
		class="rounded-xl border border-gray-200 bg-white p-4 shadow-xl sm:p-6 dark:border-gray-700 dark:bg-gray-800"
	>
		<div class="flex items-center justify-between">
			<div>
				<p class="text-xs font-medium text-gray-600 sm:text-sm dark:text-gray-300">Ausstehend</p>
				<p class="mt-1 text-2xl font-bold text-orange-600 sm:mt-2 sm:text-3xl dark:text-orange-400">
					{stats.pending}
				</p>
			</div>
			<div class="rounded-lg bg-orange-50 p-2 sm:p-3 dark:bg-orange-900/30">
				<ClockOutline class="h-5 w-5 text-orange-600 sm:h-6 sm:w-6 dark:text-orange-400" />
			</div>
		</div>
	</div>

	<!-- Submission Rate -->
	<div
		class="rounded-xl border border-gray-200 bg-white p-4 shadow-xl sm:p-6 dark:border-gray-700 dark:bg-gray-800"
	>
		<div class="flex items-center justify-between">
			<div>
				<p class="text-xs font-medium text-gray-600 sm:text-sm dark:text-gray-300">Einreich Rate</p>
				<p class="mt-1 text-2xl font-bold text-purple-600 sm:mt-2 sm:text-3xl dark:text-purple-400">
					{stats.submissionRate}%
				</p>
			</div>
			<div
				class="rounded-lg bg-gradient-to-br from-purple-100 to-blue-100 p-2 sm:p-3 dark:from-purple-900/30 dark:to-blue-900/30"
			>
				<TrendingUp class="h-5 w-5 text-purple-600 sm:h-6 sm:w-6 dark:text-purple-400" />
			</div>
		</div>
	</div>
</div>
