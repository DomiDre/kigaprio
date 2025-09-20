import type { DetectionResult, PaperDetectionConfig } from '../types/scanner';

interface StabilizedCorners {
	corners: { x: number; y: number }[];
	timestamp: number;
	confidence: number;
}

export class DetectionService {
	private cv: any = null;
	private config: PaperDetectionConfig = {
		minConfidence: 20,
		minAreaRatio: 0.05,
		maxAreaRatio: 0.95,
		targetAspectRatio: 1.41,
		autoCaptureDelay: 1000,
		edgeThreshold: 10,
		minContourArea: 1000,
		cannyLower: 50,
		cannyUpper: 150
	};

	// Stabilization properties - more conservative
	private detectionHistory: StabilizedCorners[] = [];
	private readonly HISTORY_SIZE = 3; // Reduced for quicker response
	private readonly CORNER_STABILITY_THRESHOLD = 30; // Increased tolerance
	private readonly MIN_STABLE_FRAMES = 2; // Reduced for faster detection
	private lastStableCorners: { x: number; y: number }[] | null = null;

	async initialize(): Promise<boolean> {
		return this.loadOpenCV();
	}

	private async loadOpenCV(): Promise<boolean> {
		return new Promise((resolve) => {
			if (typeof window === 'undefined') {
				resolve(false);
				return;
			}

			// Check if already loaded
			if ((window as any).cv && typeof (window as any).cv.Mat === 'function') {
				this.cv = (window as any).cv;
				console.log('OpenCV already loaded');
				resolve(true);
				return;
			}

			const script = document.createElement('script');
			script.src = 'https://docs.opencv.org/4.5.0/opencv.js';
			script.async = true;

			script.onload = () => {
				const checkReady = () => {
					if ((window as any).cv && typeof (window as any).cv.Mat === 'function') {
						this.cv = (window as any).cv;
						console.log('OpenCV ready');
						resolve(true);
						return true;
					}
					return false;
				};

				if (checkReady()) return;

				if ((window as any).cv && (window as any).cv.onRuntimeInitialized) {
					(window as any).cv.onRuntimeInitialized = () => {
						checkReady();
					};
				} else {
					const checkInterval = setInterval(() => {
						if (checkReady()) {
							clearInterval(checkInterval);
						}
					}, 100);

					setTimeout(() => {
						clearInterval(checkInterval);
						if (!this.cv) {
							console.warn('OpenCV loading timeout');
							resolve(false);
						}
					}, 10000);
				}
			};

			script.onerror = () => {
				console.error('Failed to load OpenCV');
				resolve(false);
			};

			document.head.appendChild(script);
		});
	}

	detectPaper(videoElement: HTMLVideoElement, canvas: HTMLCanvasElement): DetectionResult {
		if (!videoElement || !canvas || videoElement.videoWidth === 0) {
			return { detected: false, confidence: 0 };
		}

		// Use OpenCV if available, otherwise fallback
		if (this.cv && typeof this.cv.Mat === 'function') {
			const rawResult = this.opencvDetection(videoElement, canvas);
			// Apply lighter stabilization
			return this.stabilizeDetection(rawResult);
		} else {
			console.log('OpenCV not ready, using fallback detection');
			return this.fallbackDetection();
		}
	}

	/**
	 * Lighter stabilization that doesn't cause rotation issues
	 */
	private stabilizeDetection(currentResult: DetectionResult): DetectionResult {
		// If no detection, use last stable corners briefly
		if (!currentResult.detected || !currentResult.corners) {
			if (this.lastStableCorners && this.detectionHistory.length > 0) {
				const lastDetection = this.detectionHistory[this.detectionHistory.length - 1];
				const timeSinceLastDetection = Date.now() - lastDetection.timestamp;

				// Keep last detection for only 200ms to reduce jumpiness
				if (timeSinceLastDetection < 200) {
					return {
						detected: true,
						corners: this.lastStableCorners,
						confidence: Math.max(20, lastDetection.confidence - 20)
					};
				}
			}

			// Clear history if no detection
			this.detectionHistory = [];
			this.lastStableCorners = null;
			return currentResult;
		}

		// Add current detection to history
		this.detectionHistory.push({
			corners: currentResult.corners,
			timestamp: Date.now(),
			confidence: currentResult.confidence
		});

		// Keep only recent detections
		while (this.detectionHistory.length > this.HISTORY_SIZE) {
			this.detectionHistory.shift();
		}

		// Need minimum frames for stability
		if (this.detectionHistory.length < this.MIN_STABLE_FRAMES) {
			return currentResult;
		}

		// Check if corners are consistent (not jumping around)
		const isConsistent = this.checkCornersConsistency();

		if (isConsistent) {
			// Use weighted average with more weight on recent frames
			const stabilizedCorners = this.calculateWeightedAverageCorners();
			this.lastStableCorners = stabilizedCorners;

			return {
				...currentResult,
				corners: stabilizedCorners,
				stabilized: true
			};
		}

		// If not consistent, use current result but mark as unstable
		return {
			...currentResult,
			stabilized: false
		};
	}

	private checkCornersConsistency(): boolean {
		if (this.detectionHistory.length < 2) return false;

		// Check if corners are in roughly the same position
		for (let i = 1; i < this.detectionHistory.length; i++) {
			const prev = this.detectionHistory[i - 1].corners;
			const curr = this.detectionHistory[i].corners;

			// Ensure corners are in same order (no rotation)
			for (let j = 0; j < 4; j++) {
				const dist = this.distance(prev[j], curr[j]);
				if (dist > this.CORNER_STABILITY_THRESHOLD * 2) {
					return false; // Corners jumped too much
				}
			}
		}

		return true;
	}

	private calculateWeightedAverageCorners(): { x: number; y: number }[] {
		const avgCorners = [
			{ x: 0, y: 0 },
			{ x: 0, y: 0 },
			{ x: 0, y: 0 },
			{ x: 0, y: 0 }
		];

		let totalWeight = 0;

		// Give more weight to recent detections
		for (let i = 0; i < this.detectionHistory.length; i++) {
			const weight = i + 1; // 1, 2, 3, ... (recent has more weight)
			const detection = this.detectionHistory[i];

			for (let j = 0; j < 4; j++) {
				avgCorners[j].x += detection.corners[j].x * weight;
				avgCorners[j].y += detection.corners[j].y * weight;
			}
			totalWeight += weight;
		}

		// Normalize
		for (let i = 0; i < 4; i++) {
			avgCorners[i].x /= totalWeight;
			avgCorners[i].y /= totalWeight;
		}

		return avgCorners;
	}

	/**
	 * Extracts and transforms the detected paper region to a rectangular image
	 */
	extractPaper(
		sourceElement: HTMLVideoElement | HTMLCanvasElement,
		corners: { x: number; y: number }[],
		outputCanvas: HTMLCanvasElement,
		targetWidth: number = 800
	): boolean {
		if (!this.cv || !corners || corners.length !== 4) {
			console.error('Cannot extract paper: OpenCV not ready or invalid corners');
			return false;
		}

		try {
			// Create a temporary canvas for the source
			const tempCanvas = document.createElement('canvas');
			const tempCtx = tempCanvas.getContext('2d');
			if (!tempCtx) return false;

			if (sourceElement instanceof HTMLVideoElement) {
				tempCanvas.width = sourceElement.videoWidth;
				tempCanvas.height = sourceElement.videoHeight;
				tempCtx.drawImage(sourceElement, 0, 0);
			} else {
				tempCanvas.width = sourceElement.width;
				tempCanvas.height = sourceElement.height;
				tempCtx.drawImage(sourceElement, 0, 0);
			}

			const src = this.cv.imread(tempCanvas);

			// Sort corners to ensure consistent order
			const sortedCorners = this.sortCorners(corners);

			// Calculate output dimensions maintaining aspect ratio
			const { width: outputWidth, height: outputHeight } = this.calculateOutputDimensions(
				sortedCorners,
				targetWidth
			);

			// Set output canvas size
			outputCanvas.width = outputWidth;
			outputCanvas.height = outputHeight;

			// Define source points
			const srcPoints = this.cv.matFromArray(4, 1, this.cv.CV_32FC2, [
				sortedCorners[0].x,
				sortedCorners[0].y,
				sortedCorners[1].x,
				sortedCorners[1].y,
				sortedCorners[2].x,
				sortedCorners[2].y,
				sortedCorners[3].x,
				sortedCorners[3].y
			]);

			// Define destination points (rectangle)
			const dstPoints = this.cv.matFromArray(4, 1, this.cv.CV_32FC2, [
				0,
				0,
				outputWidth,
				0,
				outputWidth,
				outputHeight,
				0,
				outputHeight
			]);

			// Calculate perspective transform matrix
			const transformMatrix = this.cv.getPerspectiveTransform(srcPoints, dstPoints);

			// Apply perspective transformation
			const dst = new this.cv.Mat();
			const dsize = new this.cv.Size(outputWidth, outputHeight);
			this.cv.warpPerspective(
				src,
				dst,
				transformMatrix,
				dsize,
				this.cv.INTER_LINEAR,
				this.cv.BORDER_CONSTANT,
				new this.cv.Scalar(255, 255, 255, 255)
			);

			// Show result on output canvas
			this.cv.imshow(outputCanvas, dst);

			// Cleanup
			src.delete();
			srcPoints.delete();
			dstPoints.delete();
			transformMatrix.delete();
			dst.delete();

			return true;
		} catch (error) {
			console.error('Error extracting paper:', error);
			return false;
		}
	}

	/**
	 * Sorts corners in consistent order
	 */
	private sortCorners(corners: { x: number; y: number }[]): { x: number; y: number }[] {
		const sorted = [...corners];

		// Find top-left corner (minimum sum of x and y)
		sorted.sort((a, b) => a.x + a.y - (b.x + b.y));
		const topLeft = sorted[0];

		// Find bottom-right corner (maximum sum of x and y)
		sorted.sort((a, b) => b.x + b.y - (a.x + a.y));
		const bottomRight = sorted[0];

		// Find top-right and bottom-left
		const remaining = corners.filter((c) => c !== topLeft && c !== bottomRight);
		const topRight = remaining[0].y < remaining[1].y ? remaining[0] : remaining[1];
		const bottomLeft = remaining[0].y < remaining[1].y ? remaining[1] : remaining[0];

		return [topLeft, topRight, bottomRight, bottomLeft];
	}

	/**
	 * Calculates output dimensions maintaining aspect ratio
	 */
	private calculateOutputDimensions(
		corners: { x: number; y: number }[],
		targetWidth: number
	): { width: number; height: number } {
		const width1 = this.distance(corners[0], corners[1]);
		const width2 = this.distance(corners[3], corners[2]);
		const height1 = this.distance(corners[1], corners[2]);
		const height2 = this.distance(corners[0], corners[3]);

		const avgWidth = (width1 + width2) / 2;
		const avgHeight = (height1 + height2) / 2;

		const aspectRatio = avgHeight / avgWidth;

		return {
			width: targetWidth,
			height: Math.round(targetWidth * aspectRatio)
		};
	}

	private opencvDetection(
		videoElement: HTMLVideoElement,
		canvas: HTMLCanvasElement
	): DetectionResult {
		try {
			const ctx = canvas.getContext('2d');
			if (!ctx) return { detected: false, confidence: 0 };

			// Set canvas size to match video
			canvas.width = videoElement.videoWidth;
			canvas.height = videoElement.videoHeight;
			ctx.drawImage(videoElement, 0, 0);

			// Create OpenCV matrices
			const src = this.cv.imread(canvas);
			const gray = new this.cv.Mat();
			const blurred = new this.cv.Mat();
			const edges = new this.cv.Mat();

			// Convert to grayscale
			this.cv.cvtColor(src, gray, this.cv.COLOR_RGBA2GRAY);

			// Apply Gaussian blur to reduce noise
			const ksize = new this.cv.Size(5, 5);
			this.cv.GaussianBlur(gray, blurred, ksize, 0);

			// Apply Canny edge detection
			this.cv.Canny(blurred, edges, this.config.cannyLower, this.config.cannyUpper);

			// Dilate edges to close gaps
			const kernel = this.cv.Mat.ones(3, 3, this.cv.CV_8U);
			this.cv.dilate(edges, edges, kernel, new this.cv.Point(-1, -1), 1);

			// Find contours
			const contours = new this.cv.MatVector();
			const hierarchy = new this.cv.Mat();

			this.cv.findContours(
				edges,
				contours,
				hierarchy,
				this.cv.RETR_EXTERNAL,
				this.cv.CHAIN_APPROX_SIMPLE
			);

			// Find the best quadrilateral
			let bestResult: DetectionResult = { detected: false, confidence: 0 };
			const imageArea = canvas.width * canvas.height;

			for (let i = 0; i < contours.size(); i++) {
				const contour = contours.get(i);
				const area = this.cv.contourArea(contour);

				// Skip small contours
				if (area < this.config.minContourArea) continue;

				// Check area ratio
				const areaRatio = area / imageArea;
				if (areaRatio < this.config.minAreaRatio || areaRatio > this.config.maxAreaRatio) {
					continue;
				}

				// Approximate polygon
				const perimeter = this.cv.arcLength(contour, true);
				const approx = new this.cv.Mat();
				this.cv.approxPolyDP(contour, approx, 0.02 * perimeter, true);

				// Check if it's a quadrilateral
				if (approx.rows === 4) {
					const corners = this.extractCorners(approx);

					if (this.isValidPaperShape(corners, canvas)) {
						const confidence = this.calculateConfidence(corners, area, imageArea);

						if (confidence > bestResult.confidence) {
							bestResult = {
								detected: confidence > this.config.minConfidence,
								corners,
								confidence: Math.round(confidence)
							};
						}
					}
				}
				approx.delete();
			}

			// Cleanup
			src.delete();
			gray.delete();
			blurred.delete();
			edges.delete();
			kernel.delete();
			contours.delete();
			hierarchy.delete();

			return bestResult;
		} catch (error) {
			console.error('OpenCV detection error:', error);
			return { detected: false, confidence: 0 };
		}
	}

	// Keep all other methods as before...
	private isValidPaperShape(
		corners: { x: number; y: number }[],
		canvas: HTMLCanvasElement
	): boolean {
		const minSide = Math.min(canvas.width, canvas.height) * 0.1;

		for (let i = 0; i < 4; i++) {
			const next = (i + 1) % 4;
			const dist = this.distance(corners[i], corners[next]);
			if (dist < minSide) {
				return false;
			}
		}

		// Check angles
		const angles = this.calculateAngles(corners);
		const avgAngle = angles.reduce((a, b) => a + b, 0) / 4;
		const angleDeviation = Math.abs(avgAngle - 90);

		if (angleDeviation > 45) {
			return false;
		}

		// Check aspect ratio
		const aspectRatio = this.calculateAspectRatio(corners);
		if (aspectRatio < 0.3 || aspectRatio > 3.0) {
			return false;
		}

		return true;
	}

	private calculateAngles(corners: { x: number; y: number }[]): number[] {
		const angles = [];

		for (let i = 0; i < 4; i++) {
			const p1 = corners[i];
			const p2 = corners[(i + 1) % 4];
			const p3 = corners[(i + 2) % 4];

			const v1 = { x: p1.x - p2.x, y: p1.y - p2.y };
			const v2 = { x: p3.x - p2.x, y: p3.y - p2.y };

			const dot = v1.x * v2.x + v1.y * v2.y;
			const cross = v1.x * v2.y - v1.y * v2.x;
			const angle = (Math.atan2(Math.abs(cross), dot) * 180) / Math.PI;

			angles.push(angle);
		}

		return angles;
	}

	private calculateConfidence(
		corners: { x: number; y: number }[],
		area: number,
		imageArea: number
	): number {
		const areaRatio = area / imageArea;
		let areaScore = 0;

		if (areaRatio >= 0.2 && areaRatio <= 0.6) {
			areaScore = 40;
		} else if (areaRatio < 0.2) {
			areaScore = 40 * (areaRatio / 0.2);
		} else {
			areaScore = 40 * Math.max(0, 1 - (areaRatio - 0.6) / 0.4);
		}

		const aspectRatio = this.calculateAspectRatio(corners);
		const aspectDiff = Math.abs(aspectRatio - this.config.targetAspectRatio);
		const aspectScore = 30 * Math.max(0, 1 - aspectDiff / 1.5);

		const angles = this.calculateAngles(corners);
		const angleDeviation = angles.map((a) => Math.abs(a - 90)).reduce((a, b) => a + b, 0) / 4;
		const rectangleScore = 30 * Math.max(0, 1 - angleDeviation / 45);

		return areaScore + aspectScore + rectangleScore;
	}

	private fallbackDetection(): DetectionResult {
		// Simple fallback detection
		return { detected: false, confidence: 0 };
	}

	private extractCorners(approx: any): { x: number; y: number }[] {
		const corners = [];
		for (let j = 0; j < approx.rows; j++) {
			corners.push({
				x: approx.data32S[j * 2],
				y: approx.data32S[j * 2 + 1]
			});
		}
		return corners;
	}

	private calculateAspectRatio(corners: { x: number; y: number }[]): number {
		const width1 = this.distance(corners[0], corners[1]);
		const width2 = this.distance(corners[3], corners[2]);
		const height1 = this.distance(corners[1], corners[2]);
		const height2 = this.distance(corners[0], corners[3]);

		const avgWidth = (width1 + width2) / 2;
		const avgHeight = (height1 + height2) / 2;

		return Math.max(avgWidth, avgHeight) / Math.min(avgWidth, avgHeight);
	}

	private distance(p1: { x: number; y: number }, p2: { x: number; y: number }): number {
		return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
	}
}
