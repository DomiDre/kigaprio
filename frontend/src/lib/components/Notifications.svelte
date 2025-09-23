<script lang="ts">
	export let saveError: string;
	export let saveSuccess: string;
</script>

<!-- Notifications -->
{#if saveError}
	<div class="fixed right-4 bottom-4 z-[60] rounded-lg bg-red-500 px-4 py-3 text-white shadow-lg">
		{saveError}
	</div>
{/if}
{#if saveSuccess}
	<div class="fixed right-4 bottom-4 z-[60] rounded-lg bg-green-500 px-4 py-3 text-white shadow-lg">
		{saveSuccess}
	</div>
{/if}
