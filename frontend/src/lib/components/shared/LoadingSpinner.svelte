<script lang="ts">
	export let size: 'sm' | 'md' | 'lg' = 'md';
	export let color: 'primary' | 'white' | 'gray' = 'primary';

	const sizeClasses = {
		sm: 'h-4 w-4',
		md: 'h-8 w-8',
		lg: 'h-12 w-12'
	};

	const colorClasses = {
		primary: 'border-purple-600 border-t-transparent',
		white: 'border-white border-t-transparent',
		gray: 'border-gray-400 border-t-transparent'
	};
</script>

<div
	class="animate-spin rounded-full border-4 {sizeClasses[size]} {colorClasses[color]}"
	role="status"
	aria-label="Loading"
>
	<span class="sr-only">Loading...</span>
</div>
