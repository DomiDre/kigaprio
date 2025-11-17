<script lang="ts">
	import { LL } from '$i18n/i18n-svelte';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';

	export let selectedMonth: string;
	export let monthOptions: string[];
</script>

<div class="mb-8">
	<!-- Header Content -->
	<div class="text-center">
		<div class="mb-4 flex items-center justify-between sm:justify-center sm:gap-4">
			<div class="flex-1 sm:flex-initial"></div>
			<h1 class="text-2xl font-bold text-gray-800 sm:text-4xl dark:text-white">
				{$LL.priorities.title()}
			</h1>
			<div class="flex flex-1 justify-end sm:flex-initial">
				<LanguageSwitcher />
			</div>
		</div>
		<p class="mb-4 text-gray-600 dark:text-gray-300">
			{$LL.app.subtitle()}
		</p>
		<div class="inline-flex items-center rounded-lg bg-white px-4 py-2 shadow dark:bg-gray-800">
			<span class="text-sm text-gray-600 dark:text-gray-300">{$LL.priorities.selectMonth()}:</span>
			<select
				bind:value={selectedMonth}
				class="ml-2 border-0 bg-transparent font-semibold text-purple-600 focus:outline-none dark:text-purple-400"
			>
				{#each monthOptions as month (month)}
					<option value={month}>{month}</option>
				{/each}
			</select>
		</div>
	</div>
</div>
