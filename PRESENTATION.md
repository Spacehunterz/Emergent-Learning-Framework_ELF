# ELF Technical Presentation

Professional reveal.js presentation for demonstrating the Emergent Learning Framework to technical audiences.

## Quick Start

### Option 1: Open Directly in Browser (Recommended)

```bash
# Navigate to the repo
cd Emergent-Learning-Framework_ELF

# Open in browser (Mac)
open demo-presentation.html

# Or (Linux)
xdg-open demo-presentation.html

# Or (Windows)
start demo-presentation.html
```

### Option 2: Serve with Python

```bash
# Start simple HTTP server
python3 -m http.server 8000

# Open browser to:
# http://localhost:8000/demo-presentation.html
```

### Option 3: Serve with Node

```bash
# Install serve globally
npm install -g serve

# Serve the directory
serve .

# Navigate to demo-presentation.html in browser
```

## Controls

### Navigation
- **Space** / **Arrow Keys** - Next slide
- **Shift + Space** - Previous slide
- **Esc** - Slide overview (bird's eye view)
- **Alt + Click** - Zoom in/out on any element

### Presentation Mode
- **S** - Speaker notes view (shows notes + next slide)
- **F** - Fullscreen toggle
- **B** - Blackout screen (pause)
- **?** - Help overlay (show all shortcuts)

### Advanced
- **Arrow Down** - Vertical slides (nested content)
- **Arrow Up** - Previous vertical slide
- **Home** - First slide
- **End** - Last slide

## Presentation Structure

### Total: ~40 slides, 15-20 minute talk

1. **Title & Problem** (3-5 min)
   - The amnesia problem
   - Cost of repetition

2. **Core Insight** (2-3 min)
   - Building metaphor
   - Architecture visualization

3. **Technical Deep Dive** (5-7 min)
   - Tech stack
   - Database schema
   - Learning loop code

4. **Security** (2-3 min)
   - Input validation
   - Audit results

5. **Features** (3-4 min)
   - Cross-session search
   - Swarm coordination
   - Dashboard

6. **Economics & Installation** (2-3 min)
   - Token costs
   - Getting started

7. **Closing & Q&A** (2-3 min)
   - Key takeaways
   - Resources

## Customization

### Change Theme

Edit line 13 in `demo-presentation.html`:

```html
<!-- Available themes: black, white, league, beige, sky, night, serif, simple, solarized -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.5.0/dist/theme/black.css">
```

### Modify Colors

Edit the CSS variables in the `<style>` section:

```css
:root {
    --primary-color: #00d9ff;    /* Main accent */
    --secondary-color: #ff6b6b;  /* Errors/warnings */
    --success-color: #51cf66;    /* Success states */
    --warning-color: #ffd43b;    /* Cautions */
}
```

### Add Your Own Slides

Insert new `<section>` blocks:

```html
<section>
    <h2>Your Title</h2>
    <p>Your content</p>
</section>
```

For vertical (nested) slides:

```html
<section>
    <section>
        <h2>Parent Slide</h2>
    </section>
    <section>
        <h2>Child Slide 1</h2>
    </section>
    <section>
        <h2>Child Slide 2</h2>
    </section>
</section>
```

## Tips for Presenting

### Before the Talk

1. **Test the presentation** in the actual venue browser
2. **Check internet connection** (CDN dependencies)
3. **Have offline backup** (download reveal.js locally if needed)
4. **Practice transitions** (especially vertical slides)
5. **Prepare live demo environment** (separate terminal window)

### During the Talk

1. **Use Esc for overview** - shows audience where you are
2. **Press S for speaker notes** - see next slide + notes
3. **Use B to pause** - blackout during discussions
4. **Zoom with Alt+Click** - focus on specific code
5. **Navigate with confidence** - know your vertical slides

### Live Demo Sections

The presentation includes placeholders for live demos:
- Slide 19: useEffect cleanup example
- Slide 39: Installation walkthrough

**Tip:** Have terminal window ready with:
```bash
# Pre-installed ELF instance
cd ~/.claude/emergent-learning

# Fresh install for demo
cd ~/elf-demo
```

## Offline Mode (No Internet)

To run without internet connection:

1. **Download reveal.js:**
```bash
mkdir -p assets/reveal.js
cd assets/reveal.js
wget https://github.com/hakimel/reveal.js/archive/refs/tags/4.5.0.tar.gz
tar -xzf 4.5.0.tar.gz
```

2. **Update paths in demo-presentation.html:**
```html
<!-- Change CDN links to local -->
<link rel="stylesheet" href="assets/reveal.js/dist/reveal.css">
<script src="assets/reveal.js/dist/reveal.js"></script>
```

## Exporting to PDF

### Method 1: Print to PDF

1. Open presentation in Chrome/Edge
2. Add `?print-pdf` to URL: `file://.../demo-presentation.html?print-pdf`
3. Open Print dialog (Ctrl/Cmd + P)
4. Select "Save as PDF"
5. Set margins to "None"
6. Enable "Background graphics"

### Method 2: Using decktape

```bash
npm install -g decktape

decktape reveal \
  file:///path/to/demo-presentation.html \
  elf-presentation.pdf
```

## Markdown Alternative

If you prefer editing in markdown, use the companion file:

```bash
# Edit slides
vim demo-slides-technical.md

# Convert to reveal.js with Marp
npm install -g @marp-team/marp-cli
marp demo-slides-technical.md -o slides.html --theme default
```

## Troubleshooting

### Slides Don't Load

- **Check console** for CDN errors
- **Disable browser extensions** (ad blockers can interfere)
- **Try different browser** (Chrome/Firefox recommended)

### Code Highlighting Broken

- **Verify internet connection** (highlight.js from CDN)
- **Check language class** (should be `language-python`, not just `python`)

### Transitions Laggy

- **Disable animations** in reveal config:
```javascript
Reveal.initialize({
    transition: 'none',
    backgroundTransition: 'none'
});
```

### Fonts Look Wrong

- **Clear browser cache**
- **Check font CDN** (Inter, JetBrains Mono)
- **Fallback fonts** should load automatically

## Advanced Features

### Speaker Notes

Add notes that only you see in speaker view (press `S`):

```html
<section>
    <h2>Your Slide</h2>
    <aside class="notes">
        Remember to mention the security audit here.
        Transition to live demo after this slide.
    </aside>
</section>
```

### Auto-Slide (Auto-Advance)

```javascript
Reveal.initialize({
    autoSlide: 5000,  // 5 seconds per slide
    loop: true        // Loop back to start
});
```

### Fragments (Incremental Reveals)

Already used extensively in slides. Add to your own:

```html
<p class="fragment">Appears on click</p>
<p class="fragment fade-up">Fades up</p>
<p class="fragment highlight-cyan">Highlights</p>
```

## Resources

- [Reveal.js Documentation](https://revealjs.com/)
- [Keyboard Shortcuts Reference](https://revealjs.com/keyboard/)
- [Markdown Slides with Marp](https://marp.app/)
- [PDF Export Guide](https://revealjs.com/pdf-export/)

## License

Same as ELF: MIT License

---

**Questions or Issues?**

Open an issue at: https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues
