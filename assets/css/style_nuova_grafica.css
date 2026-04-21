/* ==========================================================================
   _SETTINGS.CSS - Variabili e Token di Design
   ========================================================================== */

:root {
  /* Colors - Dark Mode (Default) */
  --bg-primary: #0A0A0A;
  --bg-secondary: #131313;
  --bg-tertiary: #1A1A1A;
  
  --accent-primary: #10B981;
  --accent-hover: #059669;
  --accent-glow: rgba(16, 185, 129, 0.15);
  
  --text-main: #E5E7EB;
  --text-muted: #9CA3AF;
  --text-dim: #4B5563;
  
  --border-color: rgba(255, 255, 255, 0.05);
  --border-glow: rgba(16, 185, 129, 0.3);

  /* Typography */
  --font-mono: 'JetBrains Mono', 'Space Mono', monospace;
  --font-sans: 'Space Grotesk', 'Inter', sans-serif;

  /* Spacing & Borders */
  --radius: 4px;
  --container-max: 1200px;
  --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Light Mode Override */
[data-theme="light"] {
  --bg-primary: #FFFFFF;
  --bg-secondary: #F9FAFB;
  --bg-tertiary: #F3F4F6;
  
  --accent-primary: #059669;
  --accent-hover: #047857;
  
  --text-main: #111827;
  --text-muted: #4B5563;
  --text-dim: #9CA3AF;
  
  --border-color: rgba(0, 0, 0, 0.1);
}

/* ==========================================================================
   _BASE.CSS - Reset e Stili Globali
   ========================================================================== */

body {
  background-color: var(--bg-primary);
  color: var(--text-main);
  font-family: var(--font-sans);
  line-height: 1.6;
  margin: 0;
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, .terminal-text {
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: -0.02em;
}

a {
  color: inherit;
  text-decoration: none;
  transition: var(--transition);
}

code {
  font-family: var(--font-mono);
  background: var(--bg-tertiary);
  padding: 0.2em 0.4em;
  border-radius: var(--radius);
  font-size: 0.9em;
}

/* ==========================================================================
   _COMPONENTS.CSS - Elementi UI
   ========================================================================== */

/* Card */
.item-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  padding: 1.5rem;
  border-radius: var(--radius);
  position: relative;
  overflow: hidden;
}

.item-card:hover {
  border-color: var(--border-glow);
  box-shadow: 0 0 20px var(--accent-glow);
  transform: translateY(-2px);
}

.item-card::before {
  content: '>_';
  position: absolute;
  top: 1rem;
  right: 1rem;
  font-family: var(--font-mono);
  color: var(--accent-primary);
  opacity: 0.3;
}

/* Tag Chips */
.tag-chip {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  padding: 0.25rem 0.6rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  border-radius: 2px;
  text-transform: lowercase;
}

.tag-chip::before { content: '--'; }

.tag-chip:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

/* Sidebar */
.sidebar-section {
  margin-bottom: 2.5rem;
}

.sidebar-title {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--accent-primary);
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Input Search */
.search-input {
  width: 100%;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 0.75rem;
  font-family: var(--font-mono);
  border-radius: var(--radius);
}

.search-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

/* ==========================================================================
   _LAYOUTS.CSS - Struttura Pagine
   ========================================================================== */

.main-container {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 2rem;
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 4rem;
}

@media (max-width: 900px) {
  .main-container {
    grid-template-columns: 1fr;
  }
}

.content-area {
  min-width: 0; /* Prevents overflow in grid */
}

/* Post Styling */
.prose h1 { color: var(--accent-primary); margin-top: 0; }
.prose blockquote {
  border-left: 2px solid var(--accent-primary);
  background: var(--bg-secondary);
  padding: 1rem 1.5rem;
  margin: 2rem 0;
  font-style: italic;
}
