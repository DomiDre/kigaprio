<script lang="ts">
	export let selectedMonth: string;
	export let monthOptions: string[];
</script>

<div class="mb-8 text-center">
	<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">Prioritäten</h1>
	<p class="text-gray-600 dark:text-gray-300">
		Geben Sie für jeden Tag Ihre Betreuungspriorität an <br />(5 = höchste Priorität)
	</p>
	<div class="mt-4 inline-flex items-center rounded-lg bg-white px-4 py-2 shadow dark:bg-gray-800">
		<span class="text-sm text-gray-600 dark:text-gray-300">Monat:</span>
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
