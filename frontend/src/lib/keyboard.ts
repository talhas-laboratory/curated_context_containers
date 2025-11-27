/**
 * Keyboard navigation utilities
 */

/**
 * Global keyboard shortcuts handler
 */
export function useKeyboardShortcuts(
  shortcuts: Record<string, (e: KeyboardEvent) => void>
) {
  if (typeof window === 'undefined') {
    return;
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    const key = e.key.toLowerCase();
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const modifier = isMac ? e.metaKey : e.ctrlKey;

    // Build key string (e.g., "cmd+k", "shift+?", "escape")
    let keyString = '';
    if (modifier) keyString += isMac ? 'cmd+' : 'ctrl+';
    if (e.shiftKey) keyString += 'shift+';
    if (e.altKey) keyString += 'alt+';
    keyString += key;

    const handler = shortcuts[keyString] || shortcuts[key];
    if (handler) {
      e.preventDefault();
      handler(e);
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => {
    window.removeEventListener('keydown', handleKeyDown);
  };
}

/**
 * Focus trap for modals
 */
export function createFocusTrap(container: HTMLElement | null): () => void {
  if (!container) {
    return () => {};
  }

  const focusableElements = container.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
  );

  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  const handleTab = (e: KeyboardEvent) => {
    if (e.key !== 'Tab') {
      return;
    }

    if (e.shiftKey) {
      if (document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      }
    } else {
      if (document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    }
  };

  container.addEventListener('keydown', handleTab);
  
  // Focus first element
  firstElement?.focus();

  return () => {
    container.removeEventListener('keydown', handleTab);
  };
}

