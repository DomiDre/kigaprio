<script lang="ts">
	export let message: string = 'Lädt...';
	export let size: 'sm' | 'md' | 'lg' = 'md';

	const sizeClasses = {
		sm: 'h-8 w-8',
		md: 'h-12 w-12',
		lg: 'h-16 w-16'
	};
</script>

<div
	class="flex min-h-screen items-center justify-center bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="flex flex-col items-center gap-4">
		<!-- Spinner -->
		<div class="relative {sizeClasses[size]}">
			<div
				class="absolute inset-0 rounded-full border-4 border-purple-200 dark:border-purple-900"
			></div>
			<div
				class="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-purple-600 dark:border-t-purple-400"
			></div>
		</div>

		<!-- Loading message -->
		<p class="text-lg font-medium text-gray-700 dark:text-gray-200">
			{message}
		</p>
	</div>
</div>
