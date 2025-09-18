import type { DetectionResult, PaperDetectionConfig } from '../types/scanner.types';

export class DetectionService {
	private cv: any = null;
	private config: PaperDetectionConfig = {
		minConfidence: 20,
		minAreaRatio: 0.05,
		maxAreaRatio: 0.95,
		targetAspectRatio: 1.41,
		autoCaptureDelay: 2000,
		edgeThreshold: 20,
		minContourArea: 1000,
		cannyLower: 50, // Lowered for better edge detection
		cannyUpper: 150 // Lowered for better edge detection
	};

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
				// OpenCV.js sets cv on window immediately but needs initialization
				const checkReady = () => {
					if ((window as any).cv && typeof (window as any).cv.Mat === 'function') {
						this.cv = (window as any).cv;
						console.log('OpenCV ready');
						resolve(true);
						return true;
					}
					return false;
				};

				// Try immediate check
				if (checkReady()) return;

				// If cv.onRuntimeInitialized exists, use it
				if ((window as any).cv && (window as any).cv.onRuntimeInitialized) {
					(window as any).cv.onRuntimeInitialized = () => {
						checkReady();
					};
				} else {
					// Poll for readiness
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
			return this.opencvDetection(videoElement, canvas);
		} else {
			console.log('OpenCV not ready, using fallback detection');
			return this.fallbackDetection(videoElement, canvas);
		}
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
			const dilated = new this.cv.Mat();

			// Convert to grayscale
			this.cv.cvtColor(src, gray, this.cv.COLOR_RGBA2GRAY);

			// Apply Gaussian blur to reduce noise
			const ksize = new this.cv.Size(5, 5);
			this.cv.GaussianBlur(gray, blurred, ksize, 0);

			// Apply Canny edge detection
			this.cv.Canny(blurred, edges, this.config.cannyLower, this.config.cannyUpper);

			// Dilate edges to close gaps
			const kernel = this.cv.Mat.ones(3, 3, this.cv.CV_8U);
			this.cv.dilate(edges, dilated, kernel, new this.cv.Point(-1, -1), 1);

			// Find contours
			const contours = new this.cv.MatVector();
			const hierarchy = new this.cv.Mat();

			this.cv.findContours(
				dilated,
				contours,
				hierarchy,
				this.cv.RETR_EXTERNAL,
				this.cv.CHAIN_APPROX_SIMPLE
			);

			console.log(`Found ${contours.size()} contours`);

			// Find the best quadrilateral
			let bestResult: DetectionResult = { detected: false, confidence: 0 };
			const imageArea = canvas.width * canvas.height;

			for (let i = 0; i < contours.size(); i++) {
				const contour = contours.get(i);
				const area = this.cv.contourArea(contour);

				// Log contour areas for debugging
				if (area > 500) {
					console.log(`Contour ${i}: area = ${area}, ratio = ${area / imageArea}`);
				}

				// Check area constraints
				if (area < this.config.minContourArea) {
					continue;
				}

				if (
					area < imageArea * this.config.minAreaRatio ||
					area > imageArea * this.config.maxAreaRatio
				) {
					continue;
				}

				// Approximate polygon
				const perimeter = this.cv.arcLength(contour, true);

				// Try different epsilon values
				const epsilonValues = [0.01, 0.02, 0.03, 0.04, 0.05];

				for (const epsilon of epsilonValues) {
					const approx = new this.cv.Mat();
					this.cv.approxPolyDP(contour, approx, epsilon * perimeter, true);

					// Check if it's a quadrilateral
					if (approx.rows === 4) {
						const corners = this.extractCorners(approx);

						// Validate the quadrilateral
						if (this.isValidPaperShape(corners, canvas)) {
							const confidence = this.calculateConfidence(corners, area, imageArea);
							console.log(`Valid quad found with confidence: ${confidence}`);

							if (confidence > bestResult.confidence) {
								bestResult = {
									detected: confidence > this.config.minConfidence,
									corners,
									confidence: Math.round(confidence)
								};
							}
						}
						approx.delete();
						break; // Found a quad, no need to try other epsilon values
					}
					approx.delete();
				}
			}

			// Cleanup
			src.delete();
			gray.delete();
			blurred.delete();
			edges.delete();
			dilated.delete();
			kernel.delete();
			contours.delete();
			hierarchy.delete();

			return bestResult;
		} catch (error) {
			console.error('OpenCV detection error:', error);
			return { detected: false, confidence: 0 };
		}
	}

	private isValidPaperShape(
		corners: { x: number; y: number }[],
		canvas: HTMLCanvasElement
	): boolean {
		// Check minimum size - reduced threshold
		const minSide = Math.min(canvas.width, canvas.height) * 0.1; // Reduced from 0.2

		for (let i = 0; i < 4; i++) {
			const next = (i + 1) % 4;
			const dist = this.distance(corners[i], corners[next]);
			if (dist < minSide) {
				console.log(`Side too small: ${dist} < ${minSide}`);
				return false;
			}
		}

		// Check if corners are too close to image edges
		const margin = 5;
		for (const corner of corners) {
			if (
				corner.x <= margin ||
				corner.x >= canvas.width - margin ||
				corner.y <= margin ||
				corner.y >= canvas.height - margin
			) {
				// Allow some corners to be at edge (paper might be partially out of frame)
				// Just don't allow all corners at edge
				const edgeCorners = corners.filter(
					(c) =>
						c.x <= margin ||
						c.x >= canvas.width - margin ||
						c.y <= margin ||
						c.y >= canvas.height - margin
				).length;

				if (edgeCorners >= 4) {
					console.log('All corners at edge - likely detecting frame');
					return false;
				}
			}
		}

		// Check if shape is roughly rectangular - more lenient
		const angles = this.calculateAngles(corners);
		const avgAngle = angles.reduce((a, b) => a + b, 0) / 4;
		const angleDeviation = Math.abs(avgAngle - 90);

		if (angleDeviation > 45) {
			// Increased from 30
			console.log(`Not rectangular enough: angle deviation = ${angleDeviation}`);
			return false;
		}

		// Check aspect ratio - more lenient
		const aspectRatio = this.calculateAspectRatio(corners);
		if (aspectRatio < 0.3 || aspectRatio > 3.0) {
			// More lenient
			console.log(`Bad aspect ratio: ${aspectRatio}`);
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
		// Area score (0-40 points)
		const areaRatio = area / imageArea;
		let areaScore = 0;
		if (areaRatio > 0.05 && areaRatio < 0.95) {
			// Peak at 0.3-0.5 area ratio
			if (areaRatio >= 0.3 && areaRatio <= 0.5) {
				areaScore = 40;
			} else if (areaRatio < 0.3) {
				areaScore = 40 * (areaRatio / 0.3);
			} else {
				areaScore = 40 * (1 - (areaRatio - 0.5) / 0.45);
			}
		}

		// Aspect ratio score (0-30 points)
		const aspectRatio = this.calculateAspectRatio(corners);
		const aspectDiff = Math.abs(aspectRatio - this.config.targetAspectRatio);
		let aspectScore = 30;
		if (aspectDiff > 0.5) {
			aspectScore = Math.max(0, 30 * (1 - aspectDiff / 1.5));
		}

		// Rectangularity score (0-30 points)
		const angles = this.calculateAngles(corners);
		const angleDeviation = angles.map((a) => Math.abs(a - 90)).reduce((a, b) => a + b, 0) / 4;
		let rectangleScore = 30;
		if (angleDeviation > 0) {
			rectangleScore = Math.max(0, 30 * (1 - angleDeviation / 45));
		}

		const totalScore = areaScore + aspectScore + rectangleScore;
		console.log(
			`Confidence breakdown: area=${areaScore}, aspect=${aspectScore}, rect=${rectangleScore}, total=${totalScore}`
		);

		return totalScore;
	}

	private fallbackDetection(
		videoElement: HTMLVideoElement,
		canvas: HTMLCanvasElement
	): DetectionResult {
		const ctx = canvas.getContext('2d');
		if (!ctx) return { detected: false, confidence: 0 };

		canvas.width = videoElement.videoWidth || 640;
		canvas.height = videoElement.videoHeight || 480;
		ctx.drawImage(videoElement, 0, 0);

		const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

		// Use edge-based detection as fallback
		return this.edgeBasedDetection(imageData);
	}

	private edgeBasedDetection(imageData: ImageData): DetectionResult {
		const { data, width, height } = imageData;

		// Detect edges using simple gradient
		const edges: boolean[] = new Array(width * height).fill(false);

		for (let y = 1; y < height - 1; y++) {
			for (let x = 1; x < width - 1; x++) {
				// Check horizontal and vertical gradients
				const idxLeft = (y * width + (x - 1)) * 4;
				const idxRight = (y * width + (x + 1)) * 4;
				const idxTop = ((y - 1) * width + x) * 4;
				const idxBottom = ((y + 1) * width + x) * 4;

				const grayLeft = (data[idxLeft] + data[idxLeft + 1] + data[idxLeft + 2]) / 3;
				const grayRight = (data[idxRight] + data[idxRight + 1] + data[idxRight + 2]) / 3;
				const grayTop = (data[idxTop] + data[idxTop + 1] + data[idxTop + 2]) / 3;
				const grayBottom = (data[idxBottom] + data[idxBottom + 1] + data[idxBottom + 2]) / 3;

				const gradX = Math.abs(grayRight - grayLeft);
				const gradY = Math.abs(grayBottom - grayTop);

				if (gradX > this.config.edgeThreshold || gradY > this.config.edgeThreshold) {
					edges[y * width + x] = true;
				}
			}
		}

		// Find rectangular regions
		const rectangles = this.findRectangularRegions(edges, width, height);

		if (rectangles.length > 0) {
			const best = rectangles[0];
			return {
				detected: best.confidence > this.config.minConfidence,
				corners: best.corners,
				confidence: best.confidence
			};
		}

		return { detected: false, confidence: 0 };
	}

	private findRectangularRegions(edges: boolean[], width: number, height: number): any[] {
		// Simplified rectangle detection
		// Look for regions with high edge density forming rectangular patterns

		const rectangles = [];
		const regionSize = 50;

		for (let y = 0; y < height - regionSize; y += regionSize / 2) {
			for (let x = 0; x < width - regionSize; x += regionSize / 2) {
				// Check if this region has rectangular edge pattern
				let topEdges = 0,
					bottomEdges = 0,
					leftEdges = 0,
					rightEdges = 0;

				// Count edges along boundaries
				for (let i = 0; i < regionSize; i++) {
					if (edges[y * width + (x + i)]) topEdges++;
					if (edges[(y + regionSize) * width + (x + i)]) bottomEdges++;
					if (edges[(y + i) * width + x]) leftEdges++;
					if (edges[(y + i) * width + (x + regionSize)]) rightEdges++;
				}

				const edgeRatio = (topEdges + bottomEdges + leftEdges + rightEdges) / (regionSize * 4);

				if (edgeRatio > 0.3 && edgeRatio < 0.8) {
					// Potential rectangle
					rectangles.push({
						corners: [
							{ x, y },
							{ x: x + regionSize, y },
							{ x: x + regionSize, y: y + regionSize },
							{ x, y: y + regionSize }
						],
						confidence: Math.round(edgeRatio * 100)
					});
				}
			}
		}

		return rectangles.sort((a, b) => b.confidence - a.confidence);
	}

	private detectLightRectangle(imageData: ImageData): DetectionResult {
		// Keep existing implementation as is
		const { data, width, height } = imageData;

		const brightPixels: boolean[] = new Array(width * height).fill(false);
		const threshold = 180;

		for (let i = 0; i < data.length; i += 4) {
			const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3;
			if (brightness > threshold) {
				brightPixels[Math.floor(i / 4)] = true;
			}
		}

		const largestRegion = this.findLargestConnectedRegion(brightPixels, width, height);

		if (largestRegion.size < width * height * 0.1) {
			return { detected: false, confidence: 0 };
		}

		const bounds = this.getRegionBounds(largestRegion.pixels, width, height);
		const boundsArea = (bounds.maxX - bounds.minX) * (bounds.maxY - bounds.minY);
		const fillRatio = largestRegion.size / boundsArea;

		if (fillRatio < 0.7) {
			return { detected: false, confidence: 0 };
		}

		const confidence = Math.min(100, fillRatio * 100);

		return {
			detected: confidence > 60,
			corners: [
				{ x: bounds.minX, y: bounds.minY },
				{ x: bounds.maxX, y: bounds.minY },
				{ x: bounds.maxX, y: bounds.maxY },
				{ x: bounds.minX, y: bounds.maxY }
			],
			confidence: Math.round(confidence)
		};
	}

	// Keep all existing helper methods unchanged
	private findLargestConnectedRegion(
		pixels: boolean[],
		width: number,
		height: number
	): { pixels: Set<number>; size: number } {
		const visited = new Array(pixels.length).fill(false);
		let largestRegion = { pixels: new Set<number>(), size: 0 };

		for (let i = 0; i < pixels.length; i++) {
			if (pixels[i] && !visited[i]) {
				const region = this.floodFill(pixels, visited, i, width, height);
				if (region.size > largestRegion.size) {
					largestRegion = region;
				}
			}
		}

		return largestRegion;
	}

	private floodFill(
		pixels: boolean[],
		visited: boolean[],
		start: number,
		width: number,
		height: number
	): { pixels: Set<number>; size: number } {
		const stack = [start];
		const region = new Set<number>();

		while (stack.length > 0) {
			const idx = stack.pop()!;
			if (visited[idx]) continue;

			visited[idx] = true;
			region.add(idx);

			const x = idx % width;
			const y = Math.floor(idx / width);

			const neighbors = [
				{ x: x - 1, y },
				{ x: x + 1, y },
				{ x, y: y - 1 },
				{ x, y: y + 1 }
			];

			for (const neighbor of neighbors) {
				if (neighbor.x >= 0 && neighbor.x < width && neighbor.y >= 0 && neighbor.y < height) {
					const nIdx = neighbor.y * width + neighbor.x;
					if (pixels[nIdx] && !visited[nIdx]) {
						stack.push(nIdx);
					}
				}
			}
		}

		return { pixels: region, size: region.size };
	}

	private getRegionBounds(
		pixels: Set<number>,
		width: number,
		height: number
	): { minX: number; maxX: number; minY: number; maxY: number } {
		let minX = width,
			maxX = 0,
			minY = height,
			maxY = 0;

		for (const idx of pixels) {
			const x = idx % width;
			const y = Math.floor(idx / width);
			minX = Math.min(minX, x);
			maxX = Math.max(maxX, x);
			minY = Math.min(minY, y);
			maxY = Math.max(maxY, y);
		}

		return { minX, maxX, minY, maxY };
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
