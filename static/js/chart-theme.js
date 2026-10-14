// Shared Chart.js color palette pulled from the current CSS theme —
// used by every report page so charts stay in sync with light/dark mode.
function getChartTheme() {
    var root = getComputedStyle(document.documentElement);
    var isLight = document.documentElement.getAttribute('data-theme') === 'light';
    return {
        primary: (root.getPropertyValue('--primary').trim()) || 'hsl(202, 100%, 59%)',
        text: (root.getPropertyValue('--muted-foreground').trim()) || 'rgba(255, 255, 255, 0.7)',
        grid: (root.getPropertyValue('--border').trim()) || 'rgba(255, 255, 255, 0.08)',
        fgSolid: (root.getPropertyValue('--foreground').trim()) || '#fff',
        cardBg: isLight ? 'rgba(255,255,255,0.96)' : 'rgba(15, 23, 42, 0.92)',
        warning: (root.getPropertyValue('--warning').trim()) || 'hsl(38, 92%, 55%)',
        destructive: (root.getPropertyValue('--destructive').trim()) || 'hsl(0, 84%, 60%)',
        success: (root.getPropertyValue('--success').trim()) || 'hsl(142, 71%, 45%)',
        pointFill: (root.getPropertyValue('--card').trim()) || '#ffffff',
    };
}
