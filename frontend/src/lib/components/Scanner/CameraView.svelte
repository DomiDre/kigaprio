<script lang="ts">
	import DetectionOverlay from './DetectionOverlay.svelte';
	import type { CameraService } from '../../services/camera.service';
	import type { DetectionService } from '../../services/detection.service';
	import type { CameraFacingMode, DetectionResult } from '../../types/scanner.types';

	interface Props {
		cameraService: CameraService;
		detectionService: DetectionService;
		facingMode: CameraFacingMode;
		opencvReady: boolean;
		autoCapture: boolean;
		paperDetected?: boolean;
		detectionConfidence?: number;
		captureCountdown?: number;
		onCapture?: (detail: { image: string; extractedImage?: string }) => void;
		onError?: (detail: { message: string }) => void;
		onClose?: () => void;
		onSwitchCamera?: () => void;
	}

	let {
		cameraService,
		detectionService,
		facingMode,
		opencvReady,
		autoCapture = $bindable(),
		paperDetected = $bindable(false),
		detectionConfidence = $bindable(0),
		captureCountdown = $bindable(0),
		onCapture,
		onError,
		onClose,
		onSwitchCamera
	}: Props = $props();

	let videoElement = $state<HTMLVideoElement>();
	let captureCanvas = $state<HTMLCanvasElement>();
	let detectionCanvas = $state<HTMLCanvasElement>();
	let extractedCanvas = $state<HTMLCanvasElement>();
	let stream = $state<MediaStream | null>(null);
	let isVideoReady = $state(false);
	let animationFrame = $state<number | null>(null);
	let stableDetectionStart = $state<number | null>(null);
	let lastDetectionResult = $state<DetectionResult | null>(null);
	let showExtracted = $state(false);
	let extractedImageData = $state<string | null>(null);

	const AUTO_CAPTURE_DELAY = 2000;
	const MIN_CONFIDENCE_FOR_CAPTURE = 70;
	const MIN_CONFIDENCE_FOR_STABLE = 60;

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
			const e = error as Error;
			console.error('Failed to start camera:', e);
			onError?.({ message: e.message });
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
			const result = detectionService.detectPaper(videoElement!, detectionCanvas!);
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

		// Use lower threshold for stable detection
		if (
			result.detected &&
			result.confidence > MIN_CONFIDENCE_FOR_STABLE &&
			result.stabilized !== false
		) {
			if (!stableDetectionStart) {
				stableDetectionStart = Date.now();
			} else {
				const elapsed = Date.now() - stableDetectionStart;
				const remaining = AUTO_CAPTURE_DELAY - elapsed;

				if (remaining <= 0 && result.confidence > MIN_CONFIDENCE_FOR_CAPTURE) {
					// Auto capture now
					capturePhoto();
					stableDetectionStart = null;
					captureCountdown = 0;
				} else if (remaining > 0) {
					captureCountdown = Math.ceil(remaining / 1000);
				}
			}
		} else {
			stableDetectionStart = null;
			captureCountdown = 0;
		}
	}

	function capturePhoto() {
		if (!videoElement || !captureCanvas || !extractedCanvas) return;

		try {
			// Capture the full image
			const imageData = cameraService.capturePhoto(videoElement, captureCanvas, facingMode);

			// Try to extract paper if detected
			if (lastDetectionResult?.detected && lastDetectionResult.corners && opencvReady) {
				const success = detectionService.extractPaper(
					videoElement,
					lastDetectionResult.corners,
					extractedCanvas,
					800 // Target width for extracted paper
				);

				if (success) {
					// Get the extracted image as data URL
					const extractedDataURL = extractedCanvas.toDataURL('image/png');
					extractedImageData = extractedDataURL;
					showExtracted = true;
					stopDetection();
					return; // Don't send the capture event yet, wait for user confirmation
				}
			}

			// If no extraction or extraction failed, just send the full image
			onCapture?.({
				image: imageData
			});
		} catch (error) {
			console.error('Failed to capture photo:', error);
			onError?.({ message: 'Failed to capture photo' });
		}
	}

	function retakePhoto() {
		showExtracted = false;
		extractedImageData = null;
		startDetection();
	}

	function confirmExtracted() {
		if (extractedImageData) {
			// Send both the original and extracted image
			const fullImageData = cameraService.capturePhoto(videoElement!, captureCanvas!, facingMode);
			onCapture?.({
				image: fullImageData,
				extractedImage: extractedImageData
			});
			handleClose();
		}
	}

	function handleClose() {
		stopDetection();
		onClose?.();
	}

	function handleSwitchCamera() {
		stopDetection();
		onSwitchCamera?.();
		// Restart with new facing mode
		setTimeout(() => startCamera(), 100);
	}

	// Lifecycle
	$effect(() => {
		// onMount equivalent
		startCamera();

		// onDestroy equivalent (cleanup function)
		return () => {
			stopDetection();
			if (stream) {
				cameraService.stopCamera();
			}
		};
	});
</script>

<div class="relative overflow-hidden rounded-xl bg-black">
	{#if !showExtracted}
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
		<div class="absolute top-4 right-4 flex gap-2">
			<label
				class="flex cursor-pointer items-center gap-2 rounded-lg bg-black/50 p-2 text-white backdrop-blur-sm"
			>
				<input type="checkbox" bind:checked={autoCapture} class="rounded" />
				<span class="text-sm">Auto-capture</span>
			</label>

			{#if paperDetected && lastDetectionResult?.stabilized}
				<span class="rounded-lg bg-green-500/80 px-3 py-2 text-sm text-white backdrop-blur-sm">
					Paper stable
				</span>
			{/if}
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
					onclick={handleClose}
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
					onclick={capturePhoto}
					aria-label="Take photo"
					class="transform rounded-full p-5 text-gray-900 shadow-xl transition hover:scale-110 disabled:cursor-not-allowed disabled:opacity-50"
					class:bg-green-500={paperDetected && lastDetectionResult?.stabilized}
					class:bg-yellow-500={paperDetected && !lastDetectionResult?.stabilized}
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
					onclick={handleSwitchCamera}
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
	{:else}
		<!-- Extracted paper preview -->
		<div class="relative bg-gray-100">
			<canvas bind:this={extractedCanvas} class="mx-auto h-auto w-full max-w-2xl"></canvas>

			<div class="absolute top-4 left-4">
				<span class="rounded-lg bg-green-500 px-3 py-2 text-sm text-white">
					Paper extracted successfully
				</span>
			</div>

			<!-- Confirm/Retake controls -->
			<div
				class="absolute right-0 bottom-0 left-0 bg-gradient-to-t from-black/70 to-transparent p-4"
			>
				<div class="flex items-center justify-center gap-4">
					<button
						onclick={retakePhoto}
						class="rounded-lg bg-white/90 px-6 py-3 font-medium text-gray-900 backdrop-blur-sm transition hover:bg-white"
					>
						Retake
					</button>

					<button
						onclick={confirmExtracted}
						class="rounded-lg bg-green-500 px-6 py-3 font-medium text-white transition hover:bg-green-600"
					>
						Use this image
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Hidden canvases -->
	<canvas bind:this={captureCanvas} class="hidden"></canvas>
	<canvas bind:this={detectionCanvas} class="hidden"></canvas>
	{#if !showExtracted}
		<canvas bind:this={extractedCanvas} class="hidden"></canvas>
	{/if}
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
