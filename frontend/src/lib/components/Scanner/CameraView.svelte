<script lang="ts">
	import { onMount, onDestroy, createEventDispatcher } from 'svelte';
	import DetectionOverlay from './DetectionOverlay.svelte';
	import type { CameraService } from '../../services/camera.service';
	import type { DetectionService } from '../../services/detection.service';
	import type { CameraFacingMode, DetectionResult } from '../../types/scanner.types';

	export let cameraService: CameraService;
	export let detectionService: DetectionService;
	export let facingMode: CameraFacingMode;
	export let opencvReady: boolean;
	export let autoCapture: boolean;
	export let paperDetected: boolean = false;
	export let detectionConfidence: number = 0;
	export let captureCountdown: number = 0;

	const dispatch = createEventDispatcher();

	let videoElement: HTMLVideoElement;
	let captureCanvas: HTMLCanvasElement;
	let detectionCanvas: HTMLCanvasElement;
	let stream: MediaStream | null = null;
	let isVideoReady = false;
	let animationFrame: number | null = null;
	let stableDetectionStart: number | null = null;
	let lastDetectionResult: DetectionResult | null = null;

	const AUTO_CAPTURE_DELAY = 2000;
	const MIN_CONFIDENCE_FOR_CAPTURE = 70;

	onMount(async () => {
		await startCamera();
	});

	onDestroy(() => {
		stopDetection();
		if (stream) {
			cameraService.stopCamera();
		}
	});

	async function startCamera() {
		try {
			stream = await cameraService.startCamera(facingMode);
			if (videoElement && stream) {
				await cameraService.setupVideo(videoElement, stream);
				isVideoReady = true;
				// Start detection after a short delay to ensure video is stable
				setTimeout(() => startDetection(), 500);
			}
		} catch (error) {
			const e = error as Error; // Type assertion
			console.error('Failed to start camera:', e);
			dispatch('error', { message: e.message });
		}
	}

	function startDetection() {
		if (!isVideoReady || animationFrame) return;

		const detectFrame = () => {
			if (!isVideoReady) {
				animationFrame = null;
				return;
			}

			// Perform detection
			console.debug('Performing detection');
			const result = detectionService.detectPaper(videoElement, detectionCanvas);
			console.debug(result);
			lastDetectionResult = result;
			paperDetected = result.detected;
			detectionConfidence = result.confidence;

			// Handle auto-capture
			handleAutoCapture(result);

			// Continue detection loop
			animationFrame = requestAnimationFrame(detectFrame);
		};

		detectFrame();
	}

	function stopDetection() {
		if (animationFrame) {
			cancelAnimationFrame(animationFrame);
			animationFrame = null;
		}
		stableDetectionStart = null;
		captureCountdown = 0;
	}

	function handleAutoCapture(result: DetectionResult) {
		if (!autoCapture) {
			stableDetectionStart = null;
			captureCountdown = 0;
			return;
		}

		if (result.detected && result.confidence > MIN_CONFIDENCE_FOR_CAPTURE) {
			if (!stableDetectionStart) {
				stableDetectionStart = Date.now();
			} else {
				const elapsed = Date.now() - stableDetectionStart;
				const remaining = AUTO_CAPTURE_DELAY - elapsed;

				if (remaining <= 0) {
					// Auto capture now
					capturePhoto();
					stableDetectionStart = null;
					captureCountdown = 0;
				} else {
					captureCountdown = Math.ceil(remaining / 1000);
				}
			}
		} else {
			stableDetectionStart = null;
			captureCountdown = 0;
		}
	}

	function capturePhoto() {
		if (!videoElement || !captureCanvas) return;

		try {
			const imageData = cameraService.capturePhoto(videoElement, captureCanvas, facingMode);
			dispatch('capture', { image: imageData });
		} catch (error) {
			console.error('Failed to capture photo:', error);
			dispatch('error', { message: 'Failed to capture photo' });
		}
	}

	function handleClose() {
		stopDetection();
		dispatch('close');
	}

	function handleSwitchCamera() {
		stopDetection();
		dispatch('switchCamera');
		// Restart with new facing mode
		setTimeout(() => startCamera(), 100);
	}
</script>

<div class="relative overflow-hidden rounded-xl bg-black">
	<!-- Video element -->
	<video
		bind:this={videoElement}
		autoplay
		playsinline
		muted
		class="h-auto w-full object-cover"
		class:mirror={facingMode === 'user'}
		class:opacity-0={!isVideoReady}
		style="min-height: 300px; max-height: 500px;"
	></video>

	<!-- Detection overlay -->
	{#if isVideoReady}
		<DetectionOverlay
			{videoElement}
			detectionResult={lastDetectionResult}
			{paperDetected}
			{detectionConfidence}
			{captureCountdown}
			{opencvReady}
		/>
	{/if}

	<!-- Controls overlay -->
	<div class="absolute top-4 right-4">
		<label
			class="flex cursor-pointer items-center gap-2 rounded-lg bg-black/50 p-2 text-white backdrop-blur-sm"
		>
			<input type="checkbox" bind:checked={autoCapture} class="rounded" />
			<span class="text-sm">Auto-capture</span>
		</label>
	</div>

	<!-- Loading overlay -->
	{#if !isVideoReady}
		<div class="absolute inset-0 flex items-center justify-center bg-black">
			<div class="text-center">
				<div
					class="mx-auto mb-2 h-12 w-12 animate-spin rounded-full border-4 border-white border-t-transparent"
				></div>
				<p class="font-semibold text-white">Loading camera...</p>
			</div>
		</div>
	{/if}

	<!-- Camera Controls -->
	<div class="absolute right-0 bottom-0 left-0 bg-gradient-to-t from-black/70 to-transparent p-4">
		<div class="flex items-center justify-center gap-4">
			<button
				on:click={handleClose}
				aria-label="Close camera"
				class="rounded-full bg-white/20 p-3 text-white backdrop-blur-sm transition hover:bg-white/30"
			>
				<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					></path>
				</svg>
			</button>

			<button
				on:click={capturePhoto}
				aria-label="Take photo"
				class="transform rounded-full p-5 text-gray-900 shadow-xl transition hover:scale-110 disabled:cursor-not-allowed disabled:opacity-50"
				class:bg-green-500={paperDetected}
				class:bg-white={!paperDetected}
				disabled={!isVideoReady}
			>
				<svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
					></path>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
					></path>
				</svg>
			</button>

			<button
				on:click={handleSwitchCamera}
				aria-label="Switch camera"
				class="rounded-full bg-white/20 p-3 text-white backdrop-blur-sm transition hover:bg-white/30"
			>
				<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
					></path>
				</svg>
			</button>
		</div>
	</div>

	<!-- Hidden canvases -->
	<canvas bind:this={captureCanvas} class="hidden"></canvas>
	<canvas bind:this={detectionCanvas} class="hidden"></canvas>
</div>

<style>
	.mirror {
		transform: scaleX(-1);
	}

	.opacity-0 {
		opacity: 0;
		transition: opacity 0.3s ease-in-out;
	}
</style>
