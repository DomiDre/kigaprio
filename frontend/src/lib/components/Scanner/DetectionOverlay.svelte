<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { DetectionResult } from '../../types/scanner.types';

	export let videoElement: HTMLVideoElement;
	export let detectionResult: DetectionResult | null;
	export let paperDetected: boolean;
	export let detectionConfidence: number;
	export let captureCountdown: number;
	export let opencvReady: boolean;

	let overlayCanvas: HTMLCanvasElement;
	let animationFrame: number | null = null;

	onMount(() => {
		startDrawing();
	});

	onDestroy(() => {
		stopDrawing();
	});

	function startDrawing() {
		const draw = () => {
			if (!overlayCanvas || !videoElement) {
				animationFrame = null;
				return;
			}

			drawOverlay();
			animationFrame = requestAnimationFrame(draw);
		};

		draw();
	}

	function stopDrawing() {
		if (animationFrame) {
			cancelAnimationFrame(animationFrame);
			animationFrame = null;
		}
	}

	function drawOverlay() {
		const ctx = overlayCanvas.getContext('2d');
		if (!ctx) return;

		// Set canvas size to match video
		if (
			overlayCanvas.width !== videoElement.videoWidth ||
			overlayCanvas.height !== videoElement.videoHeight
		) {
			overlayCanvas.width = videoElement.videoWidth;
			overlayCanvas.height = videoElement.videoHeight;
		}

		// Clear canvas
		ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

		if (detectionResult?.detected && detectionResult.corners) {
			// Draw detected paper outline
			ctx.strokeStyle = '#00ff00';
			ctx.lineWidth = 3;
			ctx.beginPath();

			detectionResult.corners.forEach((corner, i) => {
				if (i === 0) {
					ctx.moveTo(corner.x, corner.y);
				} else {
					ctx.lineTo(corner.x, corner.y);
				}
			});

			ctx.closePath();
			ctx.stroke();

			// Draw corner markers
			ctx.fillStyle = '#00ff00';
			detectionResult.corners.forEach((corner) => {
				ctx.beginPath();
				ctx.arc(corner.x, corner.y, 5, 0, 2 * Math.PI);
				ctx.fill();
			});
		} else if (paperDetected) {
			// Draw guide rectangle when paper is detected but no corners
			const padding = 0.1;
			ctx.strokeStyle = paperDetected ? '#00ff00' : '#ffaa00';
			ctx.lineWidth = 3;
			ctx.setLineDash([10, 10]);
			ctx.strokeRect(
				overlayCanvas.width * padding,
				overlayCanvas.height * padding,
				overlayCanvas.width * (1 - 2 * padding),
				overlayCanvas.height * (1 - 2 * padding)
			);
			ctx.setLineDash([]);
		}

		// Draw guide corners when no paper detected
		if (!paperDetected) {
			drawGuideCorners(ctx);
		}
	}

	function drawGuideCorners(ctx: CanvasRenderingContext2D) {
		const cornerLength = 30;
		const margin = 20;
		const width = overlayCanvas.width;
		const height = overlayCanvas.height;

		ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
		ctx.lineWidth = 2;

		// Top-left
		ctx.beginPath();
		ctx.moveTo(margin, margin + cornerLength);
		ctx.lineTo(margin, margin);
		ctx.lineTo(margin + cornerLength, margin);
		ctx.stroke();

		// Top-right
		ctx.beginPath();
		ctx.moveTo(width - margin - cornerLength, margin);
		ctx.lineTo(width - margin, margin);
		ctx.lineTo(width - margin, margin + cornerLength);
		ctx.stroke();

		// Bottom-left
		ctx.beginPath();
		ctx.moveTo(margin, height - margin - cornerLength);
		ctx.lineTo(margin, height - margin);
		ctx.lineTo(margin + cornerLength, height - margin);
		ctx.stroke();

		// Bottom-right
		ctx.beginPath();
		ctx.moveTo(width - margin - cornerLength, height - margin);
		ctx.lineTo(width - margin, height - margin);
		ctx.lineTo(width - margin, height - margin - cornerLength);
		ctx.stroke();
	}
</script>

<!-- Overlay canvas -->
<canvas
	bind:this={overlayCanvas}
	class="pointer-events-none absolute inset-0 h-full w-full"
	style="min-height: 300px; max-height: 500px;"
></canvas>

<!-- Status overlay -->
<div class="absolute top-4 right-20 left-4">
	<div class="rounded-lg bg-black/50 p-3 backdrop-blur-sm">
		<div class="flex items-center justify-between">
			<div class="text-white">
				{#if paperDetected}
					<span class="flex items-center gap-2">
						<span class="h-3 w-3 animate-pulse rounded-full bg-green-500"></span>
						Paper detected ({detectionConfidence}%)
					</span>
				{:else}
					<span class="flex items-center gap-2">
						<span class="h-3 w-3 rounded-full bg-yellow-500"></span>
						Searching for paper...
					</span>
				{/if}
			</div>

			{#if captureCountdown > 0}
				<div class="animate-pulse text-lg font-bold text-white">
					Capturing in {captureCountdown}...
				</div>
			{/if}
		</div>

		{#if !opencvReady}
			<div class="mt-2 text-sm text-yellow-300">Using simple detection (OpenCV loading...)</div>
		{/if}
	</div>
</div>
