# --- UPGRADED MAPPING LOGIC ---
REPLACEMENTS = {
    # 1. TEXT COLORS (Broader Scope)
    r'text-white': 'text-aurelia-text',
    r'text-gray-100': 'text-aurelia-text',        # Very light gray -> Main Text
    r'text-gray-[2-3]00': 'text-aurelia-muted',   # Light gray -> Muted
    r'text-gray-[4-6]00': 'text-aurelia-muted',   # Medium gray -> Muted
    r'text-gray-[7-9]00': 'text-aurelia-inverted', # Dark gray -> Inverted
    r'text-black': 'text-aurelia-inverted',
    
    # 2. BACKGROUNDS (Handling Hex & Opacity)
    r'bg-\[#0a0a0b\]': 'bg-aurelia-bg',           # Catch specific hex
    r'bg-\[#0f0f11\]': 'bg-aurelia-surface',      # Catch slightly lighter hex
    r'bg-black(?!\/)': 'bg-aurelia-bg',           # Catch solid black (negative lookahead for /)
    r'bg-black\/': 'bg-aurelia-bg/',              # Catch black with opacity (preserve opacity)
    r'bg-gray-900': 'bg-aurelia-bg',
    r'bg-gray-800': 'bg-aurelia-surface',
    
    # 3. BORDERS
    r'border-gray-[7-9]00': 'border-aurelia-border',
    r'border-gray-400': 'border-aurelia-border',
    r'border-white\/10': 'border-aurelia-border',
    
    # 4. HOVER STATES
    r'hover:text-white': 'hover:text-aurelia-text',
    r'hover:bg-white\/5': 'hover:bg-aurelia-text/5',
    r'hover:border-white': 'hover:border-aurelia-text',
    
    # 5. SPECIFIC FIXES (Found in your audit)
    r'prose-invert': '',                          # REMOVE prose-invert (it forces white text). 
                                                  # We will handle prose colors via CSS variables.
}