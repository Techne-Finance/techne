/**
 * Yield Chart System
 * Canvas-based APY visualization for vaults
 */

class YieldChart {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.canvas = null;
        this.ctx = null;

        this.options = {
            width: options.width || 400,
            height: options.height || 200,
            padding: options.padding || 40,
            lineColor: options.lineColor || '#D4AF37',
            gridColor: options.gridColor || 'rgba(255, 255, 255, 0.05)',
            textColor: options.textColor || '#666',
            fillColor: options.fillColor || 'rgba(212, 175, 55, 0.1)',
            showGrid: options.showGrid !== false,
            showPoints: options.showPoints !== false,
            smooth: options.smooth !== false
        };

        this.data = [];
    }

    init() {
        if (!this.container) return;

        this.canvas = document.createElement('canvas');
        this.canvas.width = this.options.width;
        this.canvas.height = this.options.height;
        this.canvas.style.width = '100%';
        this.canvas.style.height = 'auto';
        this.container.appendChild(this.canvas);

        this.ctx = this.canvas.getContext('2d');
    }

    setData(data) {
        // Data format: [{ date: Date, apy: number }, ...]
        this.data = data;
        this.render();
    }

    render() {
        if (!this.ctx || this.data.length === 0) return;

        const { width, height, padding } = this.options;
        const ctx = this.ctx;

        // Clear
        ctx.clearRect(0, 0, width, height);

        // Calculate bounds
        const values = this.data.map(d => d.apy);
        const minVal = Math.min(...values) * 0.9;
        const maxVal = Math.max(...values) * 1.1;

        const chartWidth = width - padding * 2;
        const chartHeight = height - padding * 2;

        // Draw grid
        if (this.options.showGrid) {
            this.drawGrid(padding, chartWidth, chartHeight, minVal, maxVal);
        }

        // Calculate points
        const points = this.data.map((d, i) => ({
            x: padding + (i / (this.data.length - 1)) * chartWidth,
            y: padding + chartHeight - ((d.apy - minVal) / (maxVal - minVal)) * chartHeight,
            value: d.apy,
            date: d.date
        }));

        // Draw filled area
        ctx.beginPath();
        ctx.moveTo(points[0].x, height - padding);
        points.forEach(p => ctx.lineTo(p.x, p.y));
        ctx.lineTo(points[points.length - 1].x, height - padding);
        ctx.closePath();

        const gradient = ctx.createLinearGradient(0, padding, 0, height - padding);
        gradient.addColorStop(0, 'rgba(212, 175, 55, 0.3)');
        gradient.addColorStop(1, 'rgba(212, 175, 55, 0)');
        ctx.fillStyle = gradient;
        ctx.fill();

        // Draw line
        ctx.beginPath();
        if (this.options.smooth && points.length > 2) {
            this.drawSmoothLine(points);
        } else {
            ctx.moveTo(points[0].x, points[0].y);
            points.forEach(p => ctx.lineTo(p.x, p.y));
        }
        ctx.strokeStyle = this.options.lineColor;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw points
        if (this.options.showPoints) {
            points.forEach(p => {
                ctx.beginPath();
                ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
                ctx.fillStyle = this.options.lineColor;
                ctx.fill();
                ctx.strokeStyle = '#0f0f23';
                ctx.lineWidth = 2;
                ctx.stroke();
            });
        }

        // Draw current value
        const latest = points[points.length - 1];
        ctx.font = 'bold 14px Inter, sans-serif';
        ctx.fillStyle = this.options.lineColor;
        ctx.textAlign = 'right';
        ctx.fillText(`${latest.value.toFixed(1)}%`, width - 10, 20);
    }

    drawGrid(padding, chartWidth, chartHeight, minVal, maxVal) {
        const ctx = this.ctx;
        const { height } = this.options;

        ctx.strokeStyle = this.options.gridColor;
        ctx.lineWidth = 1;
        ctx.font = '10px Inter, sans-serif';
        ctx.fillStyle = this.options.textColor;

        // Horizontal lines
        const ySteps = 4;
        for (let i = 0; i <= ySteps; i++) {
            const y = padding + (chartHeight / ySteps) * i;
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(padding + chartWidth, y);
            ctx.stroke();

            const value = maxVal - ((maxVal - minVal) / ySteps) * i;
            ctx.textAlign = 'right';
            ctx.fillText(`${value.toFixed(0)}%`, padding - 5, y + 3);
        }
    }

    drawSmoothLine(points) {
        const ctx = this.ctx;
        ctx.moveTo(points[0].x, points[0].y);

        for (let i = 0; i < points.length - 1; i++) {
            const p0 = points[i - 1] || points[i];
            const p1 = points[i];
            const p2 = points[i + 1];
            const p3 = points[i + 2] || p2;

            const cp1x = p1.x + (p2.x - p0.x) / 6;
            const cp1y = p1.y + (p2.y - p0.y) / 6;
            const cp2x = p2.x - (p3.x - p1.x) / 6;
            const cp2y = p2.y - (p3.y - p1.y) / 6;

            ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
        }
    }

    resize(width, height) {
        this.options.width = width;
        this.options.height = height;
        this.canvas.width = width;
        this.canvas.height = height;
        this.render();
    }

    destroy() {
        if (this.canvas) {
            this.canvas.remove();
        }
    }
}

/**
 * Multi-line comparison chart
 */
class ComparisonChart extends YieldChart {
    constructor(containerId, options = {}) {
        super(containerId, options);
        this.datasets = [];
        this.colors = options.colors || [
            '#D4AF37', '#10b981', '#3b82f6', '#ef4444', '#8b5cf6'
        ];
    }

    setDatasets(datasets) {
        // Format: [{ label: 'Vault 1', data: [...] }, ...]
        this.datasets = datasets;
        this.render();
    }

    render() {
        if (!this.ctx || this.datasets.length === 0) return;

        const { width, height, padding } = this.options;
        const ctx = this.ctx;

        ctx.clearRect(0, 0, width, height);

        // Get all values for bounds
        const allValues = this.datasets.flatMap(ds => ds.data.map(d => d.apy));
        const minVal = Math.min(...allValues) * 0.9;
        const maxVal = Math.max(...allValues) * 1.1;

        const chartWidth = width - padding * 2;
        const chartHeight = height - padding * 2;

        // Draw grid
        if (this.options.showGrid) {
            this.drawGrid(padding, chartWidth, chartHeight, minVal, maxVal);
        }

        // Draw each dataset
        this.datasets.forEach((dataset, idx) => {
            const color = this.colors[idx % this.colors.length];
            const points = dataset.data.map((d, i) => ({
                x: padding + (i / (dataset.data.length - 1)) * chartWidth,
                y: padding + chartHeight - ((d.apy - minVal) / (maxVal - minVal)) * chartHeight
            }));

            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            points.forEach(p => ctx.lineTo(p.x, p.y));
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.stroke();
        });

        // Legend
        this.drawLegend();
    }

    drawLegend() {
        const ctx = this.ctx;
        const startX = this.options.padding;
        let x = startX;

        ctx.font = '11px Inter, sans-serif';

        this.datasets.forEach((dataset, idx) => {
            const color = this.colors[idx % this.colors.length];

            // Color box
            ctx.fillStyle = color;
            ctx.fillRect(x, 10, 12, 12);

            // Label
            ctx.fillStyle = '#aaa';
            ctx.textAlign = 'left';
            ctx.fillText(dataset.label, x + 16, 20);

            x += ctx.measureText(dataset.label).width + 30;
        });
    }
}

/**
 * Mini sparkline chart for inline use
 */
class SparklineChart {
    constructor(containerId, data, options = {}) {
        this.container = document.getElementById(containerId);
        this.data = data;
        this.options = {
            width: options.width || 80,
            height: options.height || 24,
            color: options.color || '#D4AF37'
        };

        this.render();
    }

    render() {
        if (!this.container || this.data.length < 2) return;

        const { width, height, color } = this.options;

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');

        const min = Math.min(...this.data);
        const max = Math.max(...this.data);
        const range = max - min || 1;

        const points = this.data.map((v, i) => ({
            x: (i / (this.data.length - 1)) * width,
            y: height - ((v - min) / range) * (height - 4) - 2
        }));

        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);
        points.forEach(p => ctx.lineTo(p.x, p.y));
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        this.container.appendChild(canvas);
    }
}

// Export
window.YieldChart = YieldChart;
window.ComparisonChart = ComparisonChart;
window.SparklineChart = SparklineChart;
