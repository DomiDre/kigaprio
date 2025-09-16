// src/lib/utils.test.ts - Simple placeholder test
import { describe, it, expect } from 'vitest';

// Simple utility function to test
function add(a: number, b: number): number {
	return a + b;
}

function formatCurrency(amount: number): string {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD'
	}).format(amount);
}

describe('Utility Functions', () => {
	it('should add two numbers correctly', () => {
		expect(add(2, 3)).toBe(5);
		expect(add(-1, 1)).toBe(0);
		expect(add(0, 0)).toBe(0);
	});

	it('should format currency correctly', () => {
		expect(formatCurrency(100)).toBe('$100.00');
		expect(formatCurrency(1234.56)).toBe('$1,234.56');
		expect(formatCurrency(0)).toBe('$0.00');
	});
});
