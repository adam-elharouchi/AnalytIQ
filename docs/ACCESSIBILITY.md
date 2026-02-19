# Accessibility Reference

## Standard: WCAG 2.1 Level AA

AnalytIQ targets WCAG 2.1 AA compliance. This document records what was implemented and any known gaps.

---

## Changes Applied (Task 65, Feb 2026)

### Modal Dialogs — all HTML files

Every modal overlay now has:
- `role="dialog"` and `aria-modal="true"` on the inner content div
- `aria-labelledby` pointing to the modal's `<h2>` heading id
- `aria-label="Close dialog"` on the `×` close button

**Files updated:**
- `professor-dashboard.html` — createClassModal
- `student-classes.html` — joinClassModal
- `login.html` — forgotPasswordModal
- `professor-class.html` — uploadChapterModal, editClassModal, addResourceModal, createExerciseModal, deleteChapterModal, editChapterModal

### ConfirmModal (`js/ui-states.js`)

`uiStates.showConfirmModal()` replaces all browser `confirm()` calls. Accessibility features:

- `role="dialog"`, `aria-modal="true"`, `aria-labelledby` on the card div
- Focus moved to Cancel button on open (`cancelBtn.focus()`)
- **Focus trap**: Tab cycles between Cancel and Confirm only (no escape to page behind)
- **Esc key**: closes modal and calls `onCancel`
- Backdrop click cancels the modal

Used in:
- `professor-dashboard.js` — delete class
- `professor-class.js` — delete resource, delete exercise
- `code-assistant.js` — delete conversation, clear chat
- `navigation.js` — sign out

### Navigation (`js/navigation.js`)

- Nav container: `role="navigation"`, `aria-label="Main navigation"`
- Nav brand link: `aria-label="AnalytIQ home"`
- Logo spans: `aria-hidden="true"`
- Mobile toggle: `aria-label="Open navigation menu"`, `aria-expanded`, `aria-controls="navLinks"`
- User menu toggle: `aria-label="User menu"`, `aria-expanded`, `aria-controls="userMenuDropdown"`
- `toggleMobileMenu()` and `toggleUserMenu()` sync `aria-expanded` on state change

### Forms and Inputs

**`resources.html`**
- Added `<label for="searchInput" class="sr-only">Search resources</label>`
- Added `aria-label="Search resources"` to the input

**`code-assistant.html`**
- Sidebar buttons: `aria-label` on toggle, new conversation, hide sidebar buttons
- `chatInput` textarea: `aria-label="Chat message"`
- File upload label: `aria-label="Upload file"`, `aria-label="Upload a file"` on input, `aria-hidden="true"` on icon span
- Gemini model select: `aria-label="Gemini model selector"`

**`practice-playground.html`**
- Chat widget button: `aria-label="Open Code Assistant"`, icon `aria-hidden="true"`
- Chat modal close button: `aria-label="Close Code Assistant"`
- Chat input: `aria-label="Chat message"`
- Code editor: `aria-labelledby="codeEditorTitle"`

### Heading Hierarchy (`chapter-view.html`)

The sidebar used `<h4>` for Bookmarks and Notes without parent `<h3>` — skipped two levels from `<h2>`. Fixed:
- `<h4>Bookmarks</h4>` → `<h3>Bookmarks</h3>`
- `<h4>Notes</h4>` → `<h3>Notes</h3>`

### Focus Rings (`chapter-view.html`)

The note panel textarea had `outline: none` without a replacement. Added:

```css
box-shadow: 0 0 0 3px rgba(37, 105, 244, 0.2);
```

This preserves the design while meeting WCAG 2.4.7 (Focus Visible).

### Associated Labels (`chapter-view.html`)

- `addNotePanelTextarea`: `aria-labelledby="addNotePanelLabel"`
- `addNoteTextarea`: `aria-labelledby="addNoteLabel"`

---

## Known Gaps

| Issue | Criteria | Status |
|---|---|---|
| `#64748b` text on white (~4.6:1 contrast) | 1.4.3 AA (4.5:1 min) | Borderline pass |
| `#94a3b8` placeholder text on white (~3.1:1) | 1.4.3 exempts placeholder | Exempt per spec |
| No keyboard-accessible toast notifications | 4.1.3 Status Messages | Not implemented |
| Dynamic class/chapter cards lack `aria-live` | 4.1.3 | Not implemented |
| No skip-to-main-content link | 2.4.1 | Not implemented |

---

## Screen Reader Testing

Manual testing with VoiceOver (macOS) on:
- Login flow
- Professor Dashboard modal open/close
- ConfirmModal keyboard navigation

Automated: axe-core integration planned for Playwright E2E suite (Task 47).
