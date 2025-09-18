<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
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
	let state: ScannerState = {
		cameraActive: false,
		capturedImage: null,
		isProcessing: false,
		analysisResult: null,
		error: null,
		paperDetected: false,
		detectionConfidence: 0,
		captureCountdown: 0
	};

	let facingMode: CameraFacingMode = 'environment';
	let opencvReady = false;
	let autoCapture = true;

	onMount(async () => {
		if (!cameraService.isSupported()) {
			state.error = 'Camera API is not supported in your browser';
			return;
		}

		opencvReady = await detectionService.initialize();
	});

	onDestroy(() => {
		cameraService.stopCamera();
	});

	async function handleStartCamera() {
		state.error = null;
		state.cameraActive = true;

		try {
			await cameraService.startCamera(facingMode);
		} catch (error) {
			state.error = `Camera access error: ${error}`;
			state.cameraActive = false;
		}
	}

	function handleStopCamera() {
		cameraService.stopCamera();
		state.cameraActive = false;
		state.paperDetected = false;
		state.detectionConfidence = 0;
	}

	function handleCapture(event: CustomEvent<{ image: string }>) {
		state.capturedImage = event.detail.image;
		handleStopCamera();
	}

	function handleRetake() {
		state.capturedImage = null;
		state.analysisResult = null;
		handleStartCamera();
	}

	function handleReset() {
		handleStopCamera();
		state = {
			cameraActive: false,
			capturedImage: null,
			isProcessing: false,
			analysisResult: null,
			error: null,
			paperDetected: false,
			detectionConfidence: 0,
			captureCountdown: 0
		};
	}

	async function handleAnalyze() {
		if (!state.capturedImage) return;

		state.isProcessing = true;
		state.error = null;

		try {
			const response = await fetch(state.capturedImage);
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

			state.analysisResult = await apiResponse.json();
		} catch (error) {
			state.error = `Analysis error: ${error}`;
		} finally {
			state.isProcessing = false;
		}
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="container mx-auto max-w-4xl px-4 py-8">
		<!-- Header -->
		<div class="mb-8 text-center">
			<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">📸 Priolisten Scanner</h1>
			<p class="text-gray-600 dark:text-gray-300">Einmal schnell alle Blaetter fotografieren</p>
		</div>

		<!-- Main Card -->
		<div class="rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			{#if state.error}
				<div
					class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
				>
					<p class="text-sm text-red-700 dark:text-red-400">{state.error}</p>
				</div>
			{/if}

			{#if !state.cameraActive && !state.capturedImage}
				<!-- Start Screen -->
				<div class="py-12 text-center">
					<button
						on:click={handleStartCamera}
						class="transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4 font-semibold text-white shadow-lg transition hover:scale-105"
					>
						Kamera oeffnen
					</button>
				</div>
			{:else if state.cameraActive}
				<CameraView
					{cameraService}
					{detectionService}
					{facingMode}
					{opencvReady}
					{autoCapture}
					on:capture={handleCapture}
					on:close={handleStopCamera}
					on:switchCamera={() => (facingMode = facingMode === 'user' ? 'environment' : 'user')}
					bind:paperDetected={state.paperDetected}
					bind:detectionConfidence={state.detectionConfidence}
					bind:captureCountdown={state.captureCountdown}
				/>
			{:else if state.capturedImage}
				<CapturePreview
					image={state.capturedImage}
					isProcessing={state.isProcessing}
					on:retake={handleRetake}
					on:analyze={handleAnalyze}
				/>

				{#if state.analysisResult}
					<AnalysisResults
						result={state.analysisResult}
						on:retake={handleRetake}
						on:reset={handleReset}
					/>
				{/if}
			{/if}
		</div>
	</div>
</div>
