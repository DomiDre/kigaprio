<!-- +page.svelte -->
<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	// Type definitions
	interface AnalysisResult {
		success: boolean;
		analysis?: {
			labels?: string[];
			confidence?: number;
			description?: string;
		};
		error?: string;
	}

	type CameraFacingMode = 'user' | 'environment';

	// Component state
	let videoElement: HTMLVideoElement | undefined;
	let canvasElement: HTMLCanvasElement | undefined;
	let stream: MediaStream | null = null;
	let cameraActive: boolean = false;
	let capturedImage: string | null = null;
	let isProcessing: boolean = false;
	let analysisResult: AnalysisResult | null = null;
	let error: string | null = null;
	let facingMode: CameraFacingMode = 'environment'; // 'user' for front camera, 'environment' for back
	let isVideoReady: boolean = false;

	// Start camera
	async function startCamera(): Promise<void> {
		try {
			error = null;
			isVideoReady = false;

			// Try exact constraint first, then fall back to ideal
			let constraints: MediaStreamConstraints = {
				video: {
					facingMode: { exact: facingMode },
					width: { ideal: 1920 },
					height: { ideal: 1080 }
				},
				audio: false
			};

			try {
				stream = await navigator.mediaDevices.getUserMedia(constraints);
			} catch {
				// Fallback to ideal if exact doesn't work
				constraints = {
					video: {
						facingMode: { ideal: facingMode },
						width: { ideal: 1920 },
						height: { ideal: 1080 }
					},
					audio: false
				};
				stream = await navigator.mediaDevices.getUserMedia(constraints);
			}

			if (videoElement && stream) {
				videoElement.srcObject = stream;

				// Wait for video to be ready
				await new Promise<void>((resolve) => {
					if (!videoElement) return resolve();

					videoElement.onloadedmetadata = () => {
						videoElement
							?.play()
							.then(() => {
								isVideoReady = true;
								cameraActive = true;
								resolve();
							})
							.catch((err) => {
								console.error('Error playing video:', err);
								resolve();
							});
					};
				});
			}
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
			error = `Camera access error: ${errorMessage}`;
			console.error('Error accessing camera:', err);
		}
	}

	// Stop camera
	function stopCamera(): void {
		if (stream) {
			stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
			stream = null;
			cameraActive = false;
			isVideoReady = false;
		}
		if (videoElement) {
			videoElement.srcObject = null;
		}
	}

	// Switch camera (mobile)
	async function switchCamera(): Promise<void> {
		facingMode = facingMode === 'user' ? 'environment' : 'user';
		if (cameraActive) {
			stopCamera();
			await startCamera();
		}
	}

	// Capture photo
	function capturePhoto(): void {
		if (!videoElement || !canvasElement || !isVideoReady) return;

		const context: CanvasRenderingContext2D | null = canvasElement.getContext('2d');
		if (!context) return;

		canvasElement.width = videoElement.videoWidth;
		canvasElement.height = videoElement.videoHeight;

		// Handle mirroring for front camera
		if (facingMode === 'user') {
			context.translate(canvasElement.width, 0);
			context.scale(-1, 1);
		}

		context.drawImage(videoElement, 0, 0);

		capturedImage = canvasElement.toDataURL('image/jpeg', 0.8);
		stopCamera();
	}

	// Convert base64 to Blob
	async function base64ToBlob(base64: string): Promise<Blob> {
		const response = await fetch(base64);
		return await response.blob();
	}

	// Send to backend for analysis
	async function analyzePhoto(): Promise<void> {
		if (!capturedImage) return;

		isProcessing = true;
		error = null;

		try {
			// Convert base64 to blob
			const blob: Blob = await base64ToBlob(capturedImage);

			const formData = new FormData();
			formData.append('image', blob, 'capture.jpg');

			// Replace with your actual backend endpoint
			const apiResponse: Response = await fetch('/api/analyze-image', {
				method: 'POST',
				body: formData
			});

			if (!apiResponse.ok) {
				throw new Error(`Server error: ${apiResponse.status}`);
			}

			const result: AnalysisResult = await apiResponse.json();
			analysisResult = result;
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
			error = `Analysis error: ${errorMessage}`;
			console.error('Error analyzing photo:', err);
		} finally {
			isProcessing = false;
		}
	}

	// Retake photo
	function retakePhoto(): void {
		capturedImage = null;
		analysisResult = null;
		startCamera();
	}

	// Reset everything
	function reset(): void {
		stopCamera();
		capturedImage = null;
		analysisResult = null;
		error = null;
	}

	// Check for camera support
	function checkCameraSupport(): boolean {
		return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
	}

	onMount(() => {
		// Check for camera support
		if (!checkCameraSupport()) {
			error = 'Camera API is not supported in your browser';
		}
	});

	onDestroy(() => {
		stopCamera();
	});
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="container mx-auto max-w-4xl px-4 py-8">
		<!-- Header -->
		<div class="mb-8 text-center">
			<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">📸 Priolisten</h1>
			<p class="text-gray-600 dark:text-gray-300">Aufnehmen, analyzieren & exportieren</p>
		</div>

		<!-- Main Card -->
		<div class="rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			{#if error}
				<div
					class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
				>
					<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
				</div>
			{/if}

			{#if !cameraActive && !capturedImage}
				<!-- Start Screen -->
				<div class="py-12 text-center">
					<div class="mb-8">
						<div
							class="mx-auto mb-4 flex h-32 w-32 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-blue-500"
						>
							<svg
								class="h-16 w-16 text-white"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
								/>
							</svg>
						</div>
						<p class="text-gray-600 dark:text-gray-300">Klicken um Aufnahme zu starten</p>
					</div>

					<button
						on:click={startCamera}
						class="transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4 font-semibold text-white shadow-lg transition hover:scale-105 hover:from-purple-700 hover:to-blue-700 focus:ring-4 focus:ring-purple-500/50 focus:outline-none"
					>
						<span class="flex items-center gap-2">
							<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
								/>
							</svg>
							Kamera öffnen
						</span>
					</button>
				</div>
			{/if}

			{#if cameraActive}
				<!-- Camera View -->
				<div class="relative overflow-hidden rounded-xl bg-black">
					<video
						bind:this={videoElement}
						autoplay
						playsinline
						muted
						class="h-auto max-h-[500px] w-full object-cover"
						class:mirror={facingMode === 'user'}
						style="display: {isVideoReady ? 'block' : 'none'}"
					/>

					{#if !isVideoReady}
						<div class="flex h-[400px] items-center justify-center">
							<div class="text-center">
								<div
									class="mx-auto mb-2 h-12 w-12 animate-spin rounded-full border-4 border-white border-t-transparent"
								></div>
								<p class="font-semibold text-white">Loading camera...</p>
							</div>
						</div>
					{/if}

					<!-- Camera Controls Overlay -->
					{#if isVideoReady}
						<div
							class="absolute right-0 bottom-0 left-0 bg-gradient-to-t from-black/70 to-transparent p-4"
						>
							<div class="flex items-center justify-center gap-4">
								<button
									on:click={stopCamera}
									class="rounded-full bg-white/20 p-3 text-white backdrop-blur-sm transition hover:bg-white/30"
									title="Close camera"
								>
									<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M6 18L18 6M6 6l12 12"
										/>
									</svg>
								</button>

								<button
									on:click={capturePhoto}
									class="transform rounded-full bg-white p-5 text-gray-900 shadow-xl transition hover:scale-110 hover:bg-gray-100"
								>
									<svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
										/>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
										/>
									</svg>
								</button>

								<button
									on:click={switchCamera}
									class="rounded-full bg-white/20 p-3 text-white backdrop-blur-sm transition hover:bg-white/30"
									title="Switch camera"
								>
									<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
										/>
									</svg>
								</button>
							</div>
						</div>
					{/if}
				</div>
			{/if}

			{#if capturedImage}
				<!-- Captured Image Preview -->
				<div class="space-y-4">
					<div class="relative overflow-hidden rounded-xl">
						<img
							src={capturedImage}
							alt="Captured"
							class="h-auto max-h-[400px] w-full object-cover"
						/>
						{#if isProcessing}
							<div class="absolute inset-0 flex items-center justify-center bg-black/50">
								<div class="text-center">
									<div
										class="mx-auto mb-2 h-12 w-12 animate-spin rounded-full border-4 border-white border-t-transparent"
									></div>
									<p class="font-semibold text-white">Analyzing...</p>
								</div>
							</div>
						{/if}
					</div>

					{#if !analysisResult && !isProcessing}
						<div class="flex gap-3">
							<button
								on:click={retakePhoto}
								class="flex-1 rounded-xl bg-gray-100 px-6 py-3 font-semibold text-gray-800 transition hover:bg-gray-200 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
							>
								Retake Photo
							</button>
							<button
								on:click={analyzePhoto}
								class="flex-1 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-3 font-semibold text-white shadow-lg transition hover:from-purple-700 hover:to-blue-700"
							>
								Analyze Photo
							</button>
						</div>
					{/if}

					{#if analysisResult}
						<!-- Analysis Results -->
						<div
							class="mt-6 rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20"
						>
							<h3 class="mb-2 text-lg font-semibold text-green-800 dark:text-green-400">
								Analysis Complete
							</h3>
							<div class="text-gray-700 dark:text-gray-300">
								<pre class="font-mono text-sm whitespace-pre-wrap">{JSON.stringify(
										analysisResult,
										null,
										2
									)}</pre>
							</div>
						</div>

						<div class="mt-4 flex gap-3">
							<button
								on:click={retakePhoto}
								class="flex-1 rounded-xl bg-gray-100 px-6 py-3 font-semibold text-gray-800 transition hover:bg-gray-200 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
							>
								Take Another Photo
							</button>
							<button
								on:click={reset}
								class="flex-1 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-3 font-semibold text-white shadow-lg transition hover:from-purple-700 hover:to-blue-700"
							>
								Start Over
							</button>
						</div>
					{/if}
				</div>
			{/if}

			<!-- Hidden canvas for photo capture -->
			<canvas bind:this={canvasElement} class="hidden"></canvas>
		</div>

		<!-- Instructions -->
		<div class="mt-8 text-center text-sm text-gray-600 dark:text-gray-400">
			<p class="mb-2">📱 Sollte mit PC/Webcam, sowie mit Handy klappen</p>
			<p>🔒 Webseite so designed, dass keine Daten gespeichert werden.</p>
		</div>
	</div>
</div>

<style>
	/* Mirror effect only for front camera */
	.mirror {
		transform: scaleX(-1);
	}
</style>

