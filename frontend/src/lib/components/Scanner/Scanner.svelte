<script lang="ts">
	import CameraView from './CameraView.svelte';
	import CapturePreview from './CapturePreview.svelte';
	import AnalysisResults from './AnalysisResults.svelte';
	import { CameraService } from '../../services/camera.service';
	import { DetectionService } from '../../services/detection.service';
	import type { ScannerState, CameraFacingMode } from '../../types/scanner.types';

	// Services
	const cameraService = new CameraService();
	const detectionService = new DetectionService();

	// State
	let scannerState: ScannerState = $state({
		cameraActive: false,
		capturedImage: null,
		isProcessing: false,
		analysisResult: null,
		error: null,
		paperDetected: false,
		detectionConfidence: 0,
		captureCountdown: 0
	});

	let facingMode: CameraFacingMode = $state('environment');
	let opencvReady = $state(false);
	let autoCapture = $state(true);
	let extractedImage: string | null = $state(null);

	$effect(() => {
		// onMount equivalent
		(async () => {
			if (!cameraService.isSupported()) {
				scannerState.error = 'Camera API is not supported in your browser';
				return;
			}

			opencvReady = await detectionService.initialize();
		})();

		// Cleanup
		return () => {
			cameraService.stopCamera();
		};
	});

	async function handleStartCamera() {
		scannerState.error = null;
		scannerState.cameraActive = true;

		try {
			await cameraService.startCamera(facingMode);
		} catch (error) {
			scannerState.error = `Camera access error: ${error}`;
			scannerState.cameraActive = false;
		}
	}

	function handleStopCamera() {
		cameraService.stopCamera();
		scannerState.cameraActive = false;
		scannerState.paperDetected = false;
		scannerState.detectionConfidence = 0;
	}

	function handleCapture(detail: { image: string; extractedImage?: string }) {
		scannerState.capturedImage = detail.image;
		extractedImage = detail.extractedImage || null;
		handleStopCamera();
	}

	function handleRetake() {
		scannerState.capturedImage = null;
		extractedImage = null;
		scannerState.analysisResult = null;
		handleStartCamera();
	}

	function handleReset() {
		handleStopCamera();
		scannerState = {
			cameraActive: false,
			capturedImage: null,
			isProcessing: false,
			analysisResult: null,
			error: null,
			paperDetected: false,
			detectionConfidence: 0,
			captureCountdown: 0
		};
		extractedImage = null;
	}

	async function handleAnalyze() {
		// Use extracted image if available, otherwise use full capture
		const imageToAnalyze = extractedImage || scannerState.capturedImage;
		if (!imageToAnalyze) return;

		scannerState.isProcessing = true;
		scannerState.error = null;

		try {
			const response = await fetch(imageToAnalyze);
			const blob = await response.blob();
			const formData = new FormData();
			formData.append('image', blob, 'capture.jpg');

			const apiResponse = await fetch('/api/analyze-schedule', {
				method: 'POST',
				body: formData
			});

			if (!apiResponse.ok) {
				throw new Error(`Server error: ${apiResponse.status}`);
			}

			scannerState.analysisResult = await apiResponse.json();
		} catch (error) {
			scannerState.error = `Analysis error: ${error}`;
		} finally {
			scannerState.isProcessing = false;
		}
	}

	function handleSwitchCamera() {
		facingMode = facingMode === 'user' ? 'environment' : 'user';
	}

	function handleError(detail: { message: string }) {
		scannerState.error = detail.message;
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="container mx-auto max-w-4xl px-4 py-8">
		<!-- Header -->
		<div class="mb-8 text-center">
			<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">📸 Priolisten Scanner</h1>
			<p class="text-gray-600 dark:text-gray-300">Einmal schnell alle Blätter fotografieren</p>
		</div>

		<!-- Main Card -->
		<div class="rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			{#if scannerState.error}
				<div
					class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
				>
					<p class="text-sm text-red-700 dark:text-red-400">{scannerState.error}</p>
				</div>
			{/if}

			{#if !scannerState.cameraActive && !scannerState.capturedImage}
				<!-- Start Screen -->
				<div class="py-12 text-center">
					<button
						onclick={handleStartCamera}
						class="transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4 font-semibold text-white shadow-lg transition hover:scale-105"
					>
						Kamera öffnen
					</button>

					<div class="mt-6 text-sm text-gray-600 dark:text-gray-400">
						<p>📋 Positioniere das Papier im Kamerabereich</p>
						<p>✨ Die App erkennt automatisch die Papierkanten</p>
						<p>📸 Das Papier wird automatisch zugeschnitten</p>
					</div>
				</div>
			{:else if scannerState.cameraActive}
				<CameraView
					{cameraService}
					{detectionService}
					{facingMode}
					{opencvReady}
					bind:autoCapture
					bind:paperDetected={scannerState.paperDetected}
					bind:detectionConfidence={scannerState.detectionConfidence}
					bind:captureCountdown={scannerState.captureCountdown}
					onCapture={handleCapture}
					onError={handleError}
					onClose={handleStopCamera}
					onSwitchCamera={handleSwitchCamera}
				/>
			{:else if scannerState.capturedImage}
				<CapturePreview
					image={extractedImage || scannerState.capturedImage}
					isProcessing={scannerState.isProcessing}
					onRetake={handleRetake}
					onAnalyze={handleAnalyze}
				>
					{#snippet children()}
						{#if extractedImage}
							<div class="mt-2 text-sm text-green-600 dark:text-green-400">
								✅ Papier wurde automatisch zugeschnitten
							</div>
						{/if}
					{/snippet}
				</CapturePreview>

				{#if scannerState.analysisResult}
					<AnalysisResults
						result={scannerState.analysisResult}
						onRetake={handleRetake}
						onReset={handleReset}
					/>
				{/if}
			{/if}
		</div>
	</div>
</div>

