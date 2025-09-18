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
			name?: string;
			schedule?: Record<string, string>;
		};
		error?: string;
	}

	interface DetectionResult {
		detected: boolean;
		corners?: { x: number; y: number }[];
		confidence: number;
	}

	type CameraFacingMode = 'user' | 'environment';

	// Component state
	let videoElement: HTMLVideoElement | undefined;
	let canvasElement: HTMLCanvasElement | undefined;
	let detectionCanvas: HTMLCanvasElement | undefined;
	let stream: MediaStream | null = null;
	let cameraActive: boolean = false;
	let capturedImage: string | null = null;
	let isProcessing: boolean = false;
	let analysisResult: AnalysisResult | null = null;
	let error: string | null = null;
	let facingMode: CameraFacingMode = 'environment';
	let isVideoReady: boolean = false;
	
	// Paper detection state
	let paperDetected: boolean = false;
	let detectionConfidence: number = 0;
	let autoCapture: boolean = true;
	let autoCaptureDelay: number = 2000; // 2 seconds after stable detection
	let stableDetectionStart: number | null = null;
	let captureCountdown: number = 0;
	let animationFrame: number | null = null;
	let opencvReady: boolean = false;

	// Load OpenCV.js
	onMount(async () => {
		// Check for camera support
		if (!checkCameraSupport()) {
			error = 'Camera API is not supported in your browser';
			return;
		}

		// Load OpenCV.js
		await loadOpenCV();
	});

	async function loadOpenCV(): Promise<void> {
		if (typeof window !== 'undefined' && !(window as any).cv) {
			const script = document.createElement('script');
			script.src = 'https://docs.opencv.org/4.5.0/opencv.js';
			script.async = true;
			script.onload = () => {
				(window as any).cv['onRuntimeInitialized'] = () => {
					opencvReady = true;
					console.log('OpenCV.js loaded successfully');
				};
			};
			document.head.appendChild(script);
		} else if ((window as any).cv) {
			opencvReady = true;
		}
	}

	// Paper detection using edge detection and contour finding
	function detectPaper(): DetectionResult {
		if (!videoElement || !detectionCanvas || !opencvReady) {
			return { detected: false, confidence: 0 };
		}

		const cv = (window as any).cv;
		const ctx = detectionCanvas.getContext('2d');
		if (!ctx) return { detected: false, confidence: 0 };

		// Draw current frame to detection canvas
		detectionCanvas.width = videoElement.videoWidth;
		detectionCanvas.height = videoElement.videoHeight;
		ctx.drawImage(videoElement, 0, 0);

		try {
			// Convert to OpenCV Mat
			const src = cv.imread(detectionCanvas);
			const gray = new cv.Mat();
			const blurred = new cv.Mat();
			const edges = new cv.Mat();
			
			// Convert to grayscale
			cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY, 0);
			
			// Apply Gaussian blur to reduce noise
			const ksize = new cv.Size(5, 5);
			cv.GaussianBlur(gray, blurred, ksize, 0);
			
			// Edge detection using Canny
			cv.Canny(blurred, edges, 50, 150, 3, false);
			
			// Find contours
			const contours = new cv.MatVector();
			const hierarchy = new cv.Mat();
			cv.findContours(edges, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);
			
			let largestArea = 0;
			let largestContour = null;
			let detectedCorners = null;
			
			// Find the largest rectangular contour
			for (let i = 0; i < contours.size(); i++) {
				const contour = contours.get(i);
				const perimeter = cv.arcLength(contour, true);
				const approx = new cv.Mat();
				cv.approxPolyDP(contour, approx, 0.02 * perimeter, true);
				
				// Check if contour has 4 corners (rectangle)
				if (approx.rows === 4) {
					const area = cv.contourArea(contour);
					
					// Check if this is a significant rectangle (at least 20% of image area)
					const minArea = (detectionCanvas.width * detectionCanvas.height) * 0.2;
					
					if (area > minArea && area > largestArea) {
						largestArea = area;
						largestContour = contour;
						
						// Extract corner points
						detectedCorners = [];
						for (let j = 0; j < approx.rows; j++) {
							detectedCorners.push({
								x: approx.data32S[j * 2],
								y: approx.data32S[j * 2 + 1]
							});
						}
					}
				}
				
				approx.delete();
			}
			
			// Clean up OpenCV objects
			src.delete();
			gray.delete();
			blurred.delete();
			edges.delete();
			contours.delete();
			hierarchy.delete();
			
			if (detectedCorners && largestArea > 0) {
				// Calculate confidence based on area and aspect ratio
				const imageArea = detectionCanvas.width * detectionCanvas.height;
				const areaRatio = largestArea / imageArea;
				
				// A4 aspect ratio is approximately 1.41 (210mm / 297mm)
				const corners = detectedCorners;
				const width = Math.max(
					Math.sqrt(Math.pow(corners[1].x - corners[0].x, 2) + Math.pow(corners[1].y - corners[0].y, 2)),
					Math.sqrt(Math.pow(corners[3].x - corners[2].x, 2) + Math.pow(corners[3].y - corners[2].y, 2))
				);
				const height = Math.max(
					Math.sqrt(Math.pow(corners[2].x - corners[1].x, 2) + Math.pow(corners[2].y - corners[1].y, 2)),
					Math.sqrt(Math.pow(corners[3].x - corners[0].x, 2) + Math.pow(corners[3].y - corners[0].y, 2))
				);
				
				const aspectRatio = Math.max(width, height) / Math.min(width, height);
				const aspectRatioScore = 1 - Math.abs(aspectRatio - 1.41) / 1.41;
				
				// Calculate overall confidence
				const confidence = (areaRatio * 0.5 + aspectRatioScore * 0.5) * 100;
				
				return {
					detected: confidence > 60,
					corners: detectedCorners,
					confidence: Math.min(100, Math.round(confidence))
				};
			}
			
			return { detected: false, confidence: 0 };
			
		} catch (err) {
			console.error('Paper detection error:', err);
			return { detected: false, confidence: 0 };
		}
	}

	// Alternative simpler detection without OpenCV
	function simpleEdgeDetection(): DetectionResult {
		if (!videoElement || !detectionCanvas) {
			return { detected: false, confidence: 0 };
		}

		const ctx = detectionCanvas.getContext('2d');
		if (!ctx) return { detected: false, confidence: 0 };

		// Draw current frame
		detectionCanvas.width = videoElement.videoWidth;
		detectionCanvas.height = videoElement.videoHeight;
		ctx.drawImage(videoElement, 0, 0);

		// Get image data
		const imageData = ctx.getImageData(0, 0, detectionCanvas.width, detectionCanvas.height);
		const data = imageData.data;

		// Simple edge detection using brightness changes
		let edgePixels = 0;
		const threshold = 30;

		for (let y = 1; y < detectionCanvas.height - 1; y++) {
			for (let x = 1; x < detectionCanvas.width - 1; x++) {
				const idx = (y * detectionCanvas.width + x) * 4;
				const gray = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;

				// Check neighboring pixels
				const idxLeft = (y * detectionCanvas.width + (x - 1)) * 4;
				const grayLeft = (data[idxLeft] + data[idxLeft + 1] + data[idxLeft + 2]) / 3;

				const idxTop = ((y - 1) * detectionCanvas.width + x) * 4;
				const grayTop = (data[idxTop] + data[idxTop + 1] + data[idxTop + 2]) / 3;

				// Detect edges
				if (Math.abs(gray - grayLeft) > threshold || Math.abs(gray - grayTop) > threshold) {
					edgePixels++;
				}
			}
		}

		// Calculate detection confidence based on edge density
		const totalPixels = detectionCanvas.width * detectionCanvas.height;
		const edgeDensity = edgePixels / totalPixels;
		
		// Typical paper has edge density between 0.02 and 0.1
		let confidence = 0;
		if (edgeDensity > 0.02 && edgeDensity < 0.1) {
			confidence = Math.min(100, (edgeDensity - 0.02) / 0.08 * 100);
		}

		return {
			detected: confidence > 50,
			confidence: Math.round(confidence)
		};
	}

	// Continuous detection loop
	function startDetection(): void {
		if (!cameraActive || !isVideoReady) return;

		const detect = () => {
			if (!cameraActive) return;

			// Use OpenCV detection if available, otherwise fallback to simple detection
			const result = opencvReady ? detectPaper() : simpleEdgeDetection();
			
			paperDetected = result.detected;
			detectionConfidence = result.confidence;

			// Draw detection overlay
			drawDetectionOverlay(result);

			// Handle auto-capture
			if (autoCapture && result.detected && result.confidence > 70) {
				if (!stableDetectionStart) {
					stableDetectionStart = Date.now();
				} else {
					const elapsed = Date.now() - stableDetectionStart;
					captureCountdown = Math.max(0, Math.ceil((autoCaptureDelay - elapsed) / 1000));
					
					if (elapsed >= autoCaptureDelay) {
						capturePhoto();
						stableDetectionStart = null;
						return;
					}
				}
			} else {
				stableDetectionStart = null;
				captureCountdown = 0;
			}

			animationFrame = requestAnimationFrame(detect);
		};

		detect();
	}

	// Draw detection overlay on video
	function drawDetectionOverlay(result: DetectionResult): void {
		if (!videoElement || !canvasElement) return;

		const ctx = canvasElement.getContext('2d');
		if (!ctx) return;

		// Set canvas size to match video
		canvasElement.width = videoElement.videoWidth;
		canvasElement.height = videoElement.videoHeight;

		// Clear canvas
		ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);

		if (result.detected && result.corners) {
			// Draw corner markers
			ctx.strokeStyle = '#00ff00';
			ctx.lineWidth = 3;
			ctx.beginPath();
			
			result.corners.forEach((corner, i) => {
				if (i === 0) {
					ctx.moveTo(corner.x, corner.y);
				} else {
					ctx.lineTo(corner.x, corner.y);
				}
			});
			
			ctx.closePath();
			ctx.stroke();

			// Draw corner circles
			ctx.fillStyle = '#00ff00';
			result.corners.forEach(corner => {
				ctx.beginPath();
				ctx.arc(corner.x, corner.y, 5, 0, 2 * Math.PI);
				ctx.fill();
			});
		} else if (result.detected) {
			// Draw simple border indication
			ctx.strokeStyle = paperDetected ? '#00ff00' : '#ffaa00';
			ctx.lineWidth = 3;
			ctx.strokeRect(
				canvasElement.width * 0.1,
				canvasElement.height * 0.1,
				canvasElement.width * 0.8,
				canvasElement.height * 0.8
			);
		}
	}

	// Start camera (modified to include detection)
	async function startCamera(): Promise<void> {
		try {
			error = null;
			isVideoReady = false;
			cameraActive = true;

			let constraints: MediaStreamConstraints = {
				video: {
					facingMode: facingMode,
					width: { ideal: 1920 },
					height: { ideal: 1080 }
				},
				audio: false
			};

			try {
				stream = await navigator.mediaDevices.getUserMedia(constraints);
			} catch (err) {
				console.log('First attempt failed, trying basic constraints');
				constraints = {
					video: true,
					audio: false
				};
				stream = await navigator.mediaDevices.getUserMedia(constraints);
			}

			if (videoElement && stream) {
				videoElement.srcObject = stream;
				videoElement.setAttribute('autoplay', '');
				videoElement.setAttribute('muted', '');
				videoElement.setAttribute('playsinline', '');

				await new Promise<void>((resolve) => {
					if (!videoElement) return resolve();

					let resolved = false;
					const timeout = setTimeout(() => {
						if (!resolved) {
							resolved = true;
							isVideoReady = true;
							resolve();
						}
					}, 2000);

					const handleVideoReady = () => {
						if (!resolved && videoElement) {
							resolved = true;
							clearTimeout(timeout);
							isVideoReady = true;
							
							// Start paper detection
							setTimeout(() => startDetection(), 500);
							
							resolve();
						}
					};

					videoElement.onloadedmetadata = () => {
						if (videoElement) {
							videoElement.play()
								.then(() => handleVideoReady())
								.catch(() => handleVideoReady());
						}
					};

					videoElement.oncanplay = handleVideoReady;
					videoElement.onplaying = handleVideoReady;

					if (videoElement.readyState >= 3) {
						handleVideoReady();
					}

					videoElement.play().catch(() => {});
				});
			}
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
			error = `Camera access error: ${errorMessage}`;
			cameraActive = false;
		}
	}

	// Stop camera (modified to stop detection)
	function stopCamera(): void {
		if (animationFrame) {
			cancelAnimationFrame(animationFrame);
			animationFrame = null;
		}
		
		if (stream) {
			stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
			stream = null;
			cameraActive = false;
			isVideoReady = false;
		}
		
		if (videoElement) {
			videoElement.srcObject = null;
		}
		
		paperDetected = false;
		detectionConfidence = 0;
		stableDetectionStart = null;
		captureCountdown = 0;
	}

	// Rest of the original functions remain the same...
	async function switchCamera(): Promise<void> {
		facingMode = facingMode === 'user' ? 'environment' : 'user';
		if (cameraActive) {
			stopCamera();
			await startCamera();
		}
	}

	function capturePhoto(): void {
		if (!videoElement || !canvasElement) return;

		const context: CanvasRenderingContext2D | null = canvasElement.getContext('2d');
		if (!context) return;

		const width = videoElement.videoWidth || videoElement.clientWidth;
		const height = videoElement.videoHeight || videoElement.clientHeight;

		canvasElement.width = width;
		canvasElement.height = height;

		if (facingMode === 'user') {
			context.translate(width, 0);
			context.scale(-1, 1);
		}

		context.drawImage(videoElement, 0, 0, width, height);
		capturedImage = canvasElement.toDataURL('image/jpeg', 0.95); // Higher quality for OCR
		stopCamera();
	}

	async function base64ToBlob(base64: string): Promise<Blob> {
		const response = await fetch(base64);
		return await response.blob();
	}

	async function analyzePhoto(): Promise<void> {
		if (!capturedImage) return;

		isProcessing = true;
		error = null;

		try {
			const blob: Blob = await base64ToBlob(capturedImage);
			const formData = new FormData();
			formData.append('image', blob, 'capture.jpg');

			const apiResponse: Response = await fetch('/api/analyze-schedule', {
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
		} finally {
			isProcessing = false;
		}
	}

	function retakePhoto(): void {
		capturedImage = null;
		analysisResult = null;
		startCamera();
	}

	function reset(): void {
		stopCamera();
		capturedImage = null;
		analysisResult = null;
		error = null;
	}

	function checkCameraSupport(): boolean {
		return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
	}

	onDestroy(() => {
		stopCamera();
	});
</script>

<div class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800">
	<div class="container mx-auto max-w-4xl px-4 py-8">
		<!-- Header -->
		<div class="mb-8 text-center">
			<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">📸 Priolisten Scanner</h1>
			<p class="text-gray-600 dark:text-gray-300">Position the schedule sheet within the frame</p>
		</div>

		<!-- Main Card -->
		<div class="rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			{#if error}
				<div class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
					<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
				</div>
			{/if}

			{#if !cameraActive && !capturedImage}
				<!-- Start Screen -->
				<div class="py-12 text-center">
					<div class="mb-8">
						<div class="mx-auto mb-4 flex h-32 w-32 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-blue-500">
							<svg class="h-16 w-16 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
							</svg>
						</div>
						<p class="text-gray-600 dark:text-gray-300">Klicken um Aufnahme zu starten</p>
					</div>

					<button
						on:click={startCamera}
						class="transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4 font-semibold text-white shadow-lg transition hover:scale-105"
					>
						<span class="flex items-center gap-2">
							<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"></path>
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"></path>
							</svg>
							Start Scanner
						</span>
					</button>
				</div>
			{/if}

			{#if cameraActive}
				<!-- Camera View with Detection -->
				<div class="relative overflow-hidden rounded-xl bg-black">
					<!-- Video element -->
					<video
						bind:this={videoElement}
						autoplay
						playsinline
						muted
						webkit-playsinline
						class="h-auto w-full object-cover"
						class:mirror={facingMode === 'user'}
						class:opacity-0={!isVideoReady}
						style="min-height: 300px; max-height: 500px;"
					></video>

					<!-- Detection overlay canvas -->
					<canvas
						bind:this={canvasElement}
						class="absolute inset-0 h-full w-full pointer-events-none"
						style="min-height: 300px; max-height: 500px;"
					></canvas>

					<!-- Detection status -->
					<div class="absolute top-4 left-4 right-4">
						<div class="bg-black/50 backdrop-blur-sm rounded-lg p-3">
							<div class="flex items-center justify-between">
								<div class="text-white">
									{#if paperDetected}
										<span class="flex items-center gap-2">
											<span class="h-3 w-3 bg-green-500 rounded-full animate-pulse"></span>
											Paper detected ({detectionConfidence}%)
										</span>
									{:else}
										<span class="flex items-center gap-2">
											<span class="h-3 w-3 bg-yellow-500 rounded-full"></span>
											Searching for paper...
										</span>
									{/if}
								</div>
								
								{#if captureCountdown > 0}
									<div class="text-white font-bold text-lg">
										Capturing in {captureCountdown}...
									</div>
								{/if}
							</div>
							
							{#if !opencvReady}
								<div class="text-yellow-300 text-sm mt-2">
									Using simple detection (OpenCV loading...)
								</div>
							{/if}
						</div>
					</div>

					<!-- Auto-capture toggle -->
					<div class="absolute top-20 right-4">
						<label class="flex items-center gap-2 bg-black/50 backdrop-blur-sm rounded-lg p-2 text-white">
							<input
								type="checkbox"
								bind:checked={autoCapture}
								class="rounded"
							/>
							<span class="text-sm">Auto-capture</span>
						</label>
					</div>

					<!-- Loading overlay -->
					{#if !isVideoReady}
						<div class="absolute inset-0 flex items-center justify-center bg-black">
							<div class="text-center">
								<div class="mx-auto mb-2 h-12 w-12 animate-spin rounded-full border-4 border-white border-t-transparent"></div>
								<p class="font-semibold text-white">Loading camera...</p>
							</div>
						</div>
					{/if}

					<!-- Camera Controls -->
					<div class="absolute right-0 bottom-0 left-0 bg-gradient-to-t from-black/70 to-transparent p-4">
						<div class="flex items-center justify-center gap-4">
							<button
								on:click={stopCamera}
								aria-label="Kamera schließen"
								class="rounded-full bg-white/20 p-3 text-white backdrop-blur-sm transition hover:bg-white/30"
								title="Close camera"
							>
								<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
								</svg>
							</button>

							<button
								on:click={capturePhoto}
								aria-label="Foto aufnehmen"
								class="transform rounded-full p-5 text-gray-900 shadow-xl transition hover:scale-110 disabled:cursor-not-allowed disabled:opacity-50"
								class:bg-green-500={paperDetected}
								class:bg-white={!paperDetected}
								disabled={!isVideoReady}
							>
								<svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"></path>
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"></path>
								</svg>
							</button>

							<button
								on:click={switchCamera}
								aria-label="Kamera wechseln"
								class="rounded-full bg-white/20 p-3 text-white backdrop-blur-sm transition hover:bg-white/30"
								title="Switch camera"
							>
								<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
								</svg>
							</button>
						</div>
					</div>
				</div>

				<!-- Hidden canvas for detection processing -->
				<canvas bind:this={detectionCanvas} class="hidden"></canvas>
			{/if}

			{#if capturedImage}
				<!-- Captured Image Preview -->
				<div class="space-y-4">
					<div class="relative overflow-hidden rounded-xl">
						<img
							src={capturedImage}
							alt="Captured schedule"
							class="h-auto max-h-[400px] w-full object-cover"
						/>
						{#if isProcessing}
							<div class="absolute inset-0 flex items-center justify-center bg-black/50">
								<div class="text-center">
									<div class="mx-auto mb-2 h-12 w-12 animate-spin rounded-full border-4 border-white border-t-transparent"></div>
									<p class="font-semibold text-white">Analyzing schedule...</p>
								</div>
							</div>
						{/if}
					</div>

					{#if !analysisResult && !isProcessing}
						<div class="flex gap-3">
							<button
								on:click={retakePhoto}
								aria-label="Foto erneut aufnehmen"
								class="flex-1 rounded-xl bg-gray-100 px-6 py-3 font-semibold text-gray-800 transition hover:bg-gray-200"
							>
								Retake Photo
							</button>
							<button
								on:click={analyzePhoto}
								aria-label="Foto analysieren"
								class="flex-1 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-3 font-semibold text-white shadow-lg"
							>
								Extract Schedule
							</button>
						</div>
					{/if}

					{#if analysisResult}
						<!-- Analysis Results -->
						<div class="mt-6 space-y-4">
							{#if analysisResult.analysis?.name}
								<div class="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
									<h3 class="font-semibold text-blue-800 dark:text-blue-400">Name Detected</h3>
									<p class="text-lg">{analysisResult.analysis.name}</p>
								</div>
							{/if}
							
							{#if analysisResult.analysis?.schedule}
								<div class="rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
									<h3 class="font-semibold text-green-800 dark:text-green-400 mb-3">Weekly Schedule</h3>
									<div class="grid grid-cols-7 gap-2 text-sm">
										{#each ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as day}
											<div class="text-center">
												<div class="font-semibold text-gray-600 dark:text-gray-400">{day}</div>
												<div class="mt-1 p-2 bg-white dark:bg-gray-700 rounded">
													{analysisResult.analysis.schedule[day] || '-'}
												</div>
											</div>
										{/each}
									</div>
								</div>
							{/if}
							
							{#if analysisResult.error}
								<div class="rounded-lg bg-red-50 p-4 dark:bg-red-900/20">
									<p class="text-red-700 dark:text-red-400">{analysisResult.error}</p>
								</div>
							{/if}
						</div>

						<div class="mt-4 flex gap-3">
							<button
								on:click={retakePhoto}
								aria-label="Weiteres Foto aufnehmen"
								class="flex-1 rounded-xl bg-gray-100 px-6 py-3 font-semibold text-gray-800 transition hover:bg-gray-200 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
							>
								Take Another Photo
							</button>
							<button
								on:click={reset}
								aria-label="Zurücksetzen"
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

	/* Smooth opacity transition */
	.opacity-0 {
		opacity: 0;
		transition: opacity 0.3s ease-in-out;
	}
</style>
