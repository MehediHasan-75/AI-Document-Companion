# AI Document Companion — Frontend Implementation Guide

## 1. Project Setup

### Initialize the project

```bash
npx create-next-app@latest ai-doc-companion-ui --js --app --tailwind --eslint --no-src-dir --import-alias "@/*"
cd ai-doc-companion-ui
```

### Environment

Create `.env.local` with:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Tailwind Config

Modify `tailwind.config.js`:

- Enable `darkMode: "class"` for class-based dark mode toggling
- Extend the color palette: set `primary` to `#2563eb` and define gray shades for backgrounds (`gray-50`, `gray-100`, `gray-800`, `gray-900`)
- Set `fontFamily.sans` to a system font stack: `['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif']`

### Global CSS (`app/globals.css`)

- Keep the Tailwind directives (`@tailwind base/components/utilities`)
- Add a smooth transition on `body` for background/color changes when toggling themes
- Set base background: `bg-white dark:bg-gray-900`, text: `text-gray-900 dark:text-gray-100`

---

## 2. File Structure

```
app/
  layout.js
  page.js                    ← Auth page (login/register)
  chat/
    page.js                  ← Main chat dashboard (protected)
components/
  AuthForm.js
  Sidebar.js
  ChatArea.js
  MessageBubble.js
  FileUploadModal.js
  ThemeToggle.js
  SourceCard.js
lib/
  api.js                     ← Fetch wrapper
  AuthContext.js              ← Auth React context + provider
  ThemeContext.js             ← Theme React context + provider
```

---

## 3. `lib/api.js` — API Client

This is the central HTTP layer. Every API call goes through here.

### Core: `apiFetch(path, options)`

- Read `NEXT_PUBLIC_API_URL` from `process.env` and prepend it to `path`
- If `options.body` is a `FormData` instance, do NOT set `Content-Type` (browser sets multipart boundary automatically). Otherwise set `Content-Type: application/json`
- Read the JWT from `localStorage.getItem("token")` and attach `Authorization: Bearer <token>` header if present
- Call `fetch(url, mergedOptions)`
- If response status is `401`: remove token from localStorage, redirect to `/` via `window.location.href = "/"`, and throw an error
- If response is not ok: parse the JSON body, throw an error with `detail` from the response (FastAPI error format) or a generic message
- If ok: return `response.json()`

### Convenience Functions

| Function                             | Method | Path                      | Body                                | Notes                                         |
| ------------------------------------ | ------ | ------------------------- | ----------------------------------- | --------------------------------------------- |
| `register(username, email, password)` | POST   | `/auth/register`          | JSON `{ username, email, password }` |                                               |
| `login(username, password)`          | POST   | `/auth/login`             | JSON `{ username, password }`       |                                               |
| `uploadFile(file)`                   | POST   | `/file/upload`            | `FormData` with field `file`        |                                               |
| `getFileStatus(fileId)`              | GET    | `/file/status/{fileId}`   | —                                   |                                               |
| `getFiles()`                         | GET    | `/file/files`             | —                                   |                                               |
| `createConversation()`               | POST   | `/conversation/`          | —                                   |                                               |
| `getConversations()`                 | GET    | `/conversation/`          | —                                   |                                               |
| `getConversation(id)`                | GET    | `/conversation/{id}`      | —                                   |                                               |
| `deleteConversation(id)`             | DELETE | `/conversation/{id}`      | —                                   |                                               |
| `sendQuery(question, conversationId)` | POST   | `/query/`                 | JSON `{ question, conversation_id }` | `conversation_id` is optional — omit if null |
| `askStreaming(question, conversationId, callbacks, docIds?)` | POST | `/conversations/{id}/ask` | JSON `{ question, doc_ids? }` | SSE streaming — see below |

### `askStreaming` — SSE Streaming Chat

The conversation `/ask` endpoint streams tokens via SSE. This function parses the stream and calls callbacks as tokens arrive — giving a ChatGPT-like experience:

```js
async function askStreaming(question, conversationId, { onDelta, onComplete, onError }, docIds = null) {
  const token = localStorage.getItem("token");

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/conversations/${conversationId}/ask`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({ question, ...(docIds ? { doc_ids: docIds } : {}) }),
    }
  );

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop(); // keep incomplete chunk

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6));
        switch (event.type) {
          case "delta":    onDelta?.(event.content); break;
          case "complete": onComplete?.(event.content, event.sources); break;
          case "error":    onError?.(event.content); break;
        }
      } catch (e) { /* skip non-JSON lines */ }
    }
  }
}
```

**Usage in a React component:**

```js
const [text, setText] = useState("");

// Search across all user documents:
askStreaming(question, activeConversationId, {
  onDelta: (token) => setText((prev) => prev + token),
  onComplete: (full, sources) => {
    setSources(sources);
    setLoading(false);
  },
  onError: (msg) => setError(msg),
});

// Scope to specific documents (doc-scoped chat):
askStreaming(question, activeConversationId, {
  onDelta: (token) => setText((prev) => prev + token),
  onComplete: (full, sources) => { setSources(sources); setLoading(false); },
  onError: (msg) => setError(msg),
}, selectedDocIds);  // string[] | null
```

---

## 4. `lib/AuthContext.js` — Auth State

**This is a `"use client"` module.**

Create a React context that provides: `{ user, token, login, register, logout, loading }`

### State

- `token` — string or null
- `user` — object or null (decoded from token or fetched)
- `loading` — boolean, true during initial hydration check

### On mount (`useEffect`)

- Read `localStorage.getItem("token")`
- If token exists, set it in state. Optionally decode the JWT payload (it's base64 — use `JSON.parse(atob(token.split('.')[1]))`) to extract user info like `sub` (username). Set `loading = false`
- If no token, set `loading = false`

### `login(username, password)` method

- Call `api.login(username, password)`
- Store `access_token` in localStorage
- Set token and user in state
- Return success (let the caller handle redirect)

### `register(username, email, password)` method

- Call `api.register(username, email, password)`
- After success, automatically call `login(username, password)` so the user is logged in immediately

### `logout()` method

- Remove token from localStorage
- Set token and user to null
- Redirect to `/` via `window.location.href`

### Provider component

- Wrap `children` in `AuthContext.Provider`
- Export a `useAuth()` hook that calls `useContext(AuthContext)`

---

## 5. `lib/ThemeContext.js` — Dark/Light Mode

**This is a `"use client"` module.**

### State

`theme` — `"light"` or `"dark"`

### On mount

- Read `localStorage.getItem("theme")`
- If stored, use it. Otherwise default to `"light"`
- Apply `document.documentElement.classList.add("dark")` or remove it accordingly

### `toggleTheme()` method

- Flip the theme, update localStorage, toggle the `dark` class on `<html>`

### Provider

Wraps children, provides `{ theme, toggleTheme }`

---

## 6. `app/layout.js` — Root Layout

- `"use client"` is NOT needed here — but the providers are client components, so wrap the body content in a client component wrapper
- Create a small `Providers.js` client component that wraps children in `AuthProvider` → `ThemeProvider`
- In `layout.js`: standard HTML skeleton, import `globals.css`, set metadata (title: "AI Document Companion"), render `<Providers>{children}</Providers>` inside `<body>`
- Set `suppressHydrationWarning` on `<html>` (needed for dark mode class manipulation)

---

## 7. `app/page.js` — Auth Page

**This is a `"use client"` page.**

### Behavior

- On mount: if `useAuth().token` exists and `loading` is false, redirect to `/chat` using `next/navigation`'s `useRouter().push("/chat")`
- While `loading` is true, show a centered spinner or blank screen
- Otherwise render `<AuthForm />`

### Layout

Full-screen centered card with the app name as heading above the form.

---

## 8. `components/AuthForm.js`

### State

- `mode` — `"login"` or `"register"` (toggle between forms)
- `username`, `email`, `password` — form fields
- `error` — string for displaying API errors
- `submitting` — boolean for loading state

### UI

- A card (white bg, rounded, shadow, `dark:bg-gray-800`) centered on the page, max-width ~400px
- Two tabs or text links at the top: "Login" / "Register" — clicking toggles `mode` and clears `error`
- **Login mode:** username + password fields
- **Register mode:** username + email + password fields
- Submit button: blue (`bg-primary`), full width, shows "Signing in..." / "Creating account..." when `submitting`
- Error message displayed in red text below the button
- Fields: standard `<input>` with Tailwind classes — border, rounded, padding, focus ring in blue, `dark:bg-gray-700 dark:border-gray-600`

### On submit

- Prevent default, set `submitting = true`, clear error
- Call `auth.login()` or `auth.register()` from `useAuth()`
- On success: `router.push("/chat")`
- On error: set `error` to the caught message, set `submitting = false`

---

## 9. `app/chat/page.js` — Chat Dashboard (Protected)

**This is a `"use client"` page.**

### Auth guard

- If `useAuth().loading` is true, show loading screen
- If `!token` and `!loading`, redirect to `/` via `router.push("/")`

### State (managed here, passed down as props)

- `conversations` — array of conversation objects
- `activeConversationId` — string or null
- `messages` — array of messages for the active conversation
- `uploadModalOpen` — boolean
- `sidebarOpen` — boolean (for mobile responsive toggle)

### On mount

- Fetch conversations via `api.getConversations()`, set state

### Conversation selection handler (`selectConversation(id)`)

- Set `activeConversationId = id`
- Fetch messages via `api.getConversation(id)`, set `messages` from the response

### New chat handler

- Call `api.createConversation()`
- Prepend to conversations list, set as active, clear messages

### Delete conversation handler

- Call `api.deleteConversation(id)`
- Remove from list. If it was active, clear active and messages

### Send message handler (`sendMessage(question)`)

- If `activeConversationId` is null: create a conversation first via `api.createConversation()`, set it as active
- Immediately append a user message object `{ role: "user", content: question }` to `messages`
- Append a placeholder assistant message `{ role: "assistant", content: "", loading: true }`
- Call `api.askStreaming(question, activeConversationId, callbacks)`:
  - `onDelta(token)`: append token to the placeholder message's content (user sees tokens arrive in real time)
  - `onComplete(full, sources)`: mark loading=false, render source cards, refresh conversations list
  - `onError(msg)`: replace placeholder with error bubble

### Layout (desktop)

```
┌──────────────────────────────────────────────────┐
│  Header (app name + theme toggle + logout)       │
├────────────┬─────────────────────────────────────┤
│  Sidebar   │  ChatArea                           │
│  (280px)   │  (flex-1)                           │
│            │                                     │
└────────────┴─────────────────────────────────────┘
```

- Header: `h-14`, flex row, `border-b`, app name left, theme toggle + logout button right
- Below header: flex row, full remaining height (`h-[calc(100vh-3.5rem)]`)
- Sidebar: `w-72`, `border-r`, hidden on mobile (toggled by hamburger in header)
- ChatArea: `flex-1`

### Mobile responsive

- Sidebar is off-screen by default, slides in as an overlay when `sidebarOpen` is true
- Add a hamburger menu button (three lines icon) in the header, visible only on `md:hidden`
- When sidebar is open on mobile, show a semi-transparent backdrop; clicking it closes the sidebar

---

## 10. `components/Sidebar.js`

### Props

`conversations`, `activeConversationId`, `onSelect`, `onNewChat`, `onDelete`, `onOpenUpload`

### Layout

Flex column, full height.

### Top section

- "New Chat" button: full width, blue outline or ghost style, `+` icon. Calls `onNewChat`
- "Upload File" button: full width, gray ghost style, paperclip/upload icon. Calls `onOpenUpload`

### Conversations list (scrollable, `flex-1`, `overflow-y-auto`)

- Each conversation: a row/button showing the conversation title (or "New Conversation" if untitled) and a creation date
- Active conversation highlighted with `bg-blue-50 dark:bg-gray-700` and left blue border
- On hover: show a delete icon (trash) on the right side — clicking calls `onDelete(id)` with `e.stopPropagation()` to prevent selecting

### Bottom section

- Small text: "AI Document Companion" or version info (optional)

---

## 11. `components/ChatArea.js`

### Props

`messages`, `onSendMessage`, `activeConversationId`

### Layout

Flex column, full height.

### Messages container (`flex-1`, `overflow-y-auto`, padding)

- If no messages and no active conversation: show a centered welcome/empty state — app name, brief tagline, suggestion to start a conversation or upload a document
- Otherwise: map `messages` to `<MessageBubble />` components
- **Auto-scroll:** use a `useRef` on a dummy div at the bottom. After messages change, call `ref.current.scrollIntoView({ behavior: "smooth" })`

### Input bar (bottom, `border-t`, padding)

- Flex row: `<textarea>` (auto-grows, max 4 rows) + send button
- Textarea: `resize-none`, `rows={1}`, border, rounded-xl, padding. On `Enter` (without Shift): submit. On `Shift+Enter`: newline
- Send button: blue circle with arrow-up icon, disabled when input is empty or a message is loading
- Auto-focus the textarea when `activeConversationId` changes

---

## 12. `components/MessageBubble.js`

### Props

`message` — `{ role, content, sources, loading }`

### Layout

- Wrapper div: flex row, `justify-end` if user, `justify-start` if assistant
- Bubble: `max-w-[75%]`, rounded-2xl, padding
  - User: `bg-blue-600 text-white`, rounded-br-sm
  - Assistant: `bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100`, rounded-bl-sm

### Content

- If `loading` is true: show 3 animated dots (CSS animation, bouncing or pulsing)
- Otherwise: render `content` as text. Preserve whitespace/newlines with `whitespace-pre-wrap`

### Sources (assistant only)

- If `sources` array exists and is non-empty, render below the bubble
- Each source as a `<SourceCard />` — collapsible
- Label: "Sources (N)" as a clickable toggle

---

## 13. `components/SourceCard.js`

### Props

`source` — object with fields like `content`, `metadata`, `summary`

### Behavior

- Collapsed by default — shows source title/filename or "Source N"
- Click to expand: shows content text in a bordered, slightly indented card
- Subtle styling: small text, gray border, rounded

---

## 14. `components/FileUploadModal.js`

### Props

`isOpen`, `onClose`

### State

- `files` — array of uploaded file objects (fetched from API)
- `uploading` — boolean
- `uploadProgress` — object tracking files being processed `{ fileId, status }`
- `dragActive` — boolean for drag-and-drop styling

### On open (`useEffect` when `isOpen` becomes true)

- Fetch file list via `api.getFiles()`, set `files`

### UI

Modal overlay (semi-transparent black backdrop + centered white card).

### Upload area

- Drag-and-drop zone: dashed border, centered icon + text "Drop files here or click to browse"
- Hidden `<input type="file">` triggered on click, accepts `.pdf,.docx,.pptx,.xlsx,.csv,.txt,.md,.html,.json`
- On drag events: toggle `dragActive` for visual feedback (blue border)

### Upload handler

- On file selection: set `uploading = true`
- Call `api.uploadFile(file)`
- On success: receive `file_id`, start polling `api.getFileStatus(file_id)` every 3 seconds
- While polling: show the file in the list with a spinning/progress indicator and current status text
- When status is `"completed"`: stop polling, update the file's status badge to green "Completed"
- When status is `"failed"`: stop polling, show red "Failed" badge
- Use `setInterval` + `clearInterval` for polling. Clean up intervals on unmount or modal close

### File list

- Below the upload area, scrollable
- Each file: filename, file type badge, status badge (processing/completed/failed), upload date
- Status badges: yellow/spinning for processing, green for completed, red for failed

### Close

X button top-right + clicking backdrop. On close, clear any active polling intervals.

---

## 15. `components/ThemeToggle.js`

Uses `useTheme()` from ThemeContext.

- A button with sun icon (in dark mode) or moon icon (in light mode)
- On click: call `toggleTheme()`
- Icons: use simple inline SVG (sun = circle with rays, moon = crescent) — about 5 lines each
- Smooth transition on the icon swap (opacity or rotate)

---

## 16. Icons

Since no component libraries are allowed, use inline SVGs for all icons:

| Icon             | Used in               | Description                         |
| ---------------- | --------------------- | ----------------------------------- |
| Plus             | Sidebar (New Chat)    | Simple `+` sign                     |
| Upload/Paperclip | Sidebar (Upload)      | Arrow pointing up into a tray       |
| Trash            | Sidebar (Delete)      | Trash can outline                   |
| Send/ArrowUp     | ChatArea input        | Upward arrow                        |
| Sun              | ThemeToggle           | Circle with lines                   |
| Moon             | ThemeToggle           | Crescent                            |
| Menu/Hamburger   | Header (mobile)       | Three horizontal lines              |
| X/Close          | Modal, Sidebar        | X mark                              |
| Spinner          | Loading states        | Circular, animated with `animate-spin` |
| ChevronDown      | SourceCard            | Small downward arrow                |

Each icon should be a small functional component or inline SVG. Keep them in the component that uses them, or create a `components/Icons.js` file exporting simple SVG components if reused in 3+ places.

---

## 17. Loading & Empty States

**Auth page loading (checking token):** Blank screen or centered small spinner.

**Chat page loading (fetching conversations):** Sidebar shows 3–4 skeleton placeholder bars (gray animated shimmer via Tailwind `animate-pulse` on gray rectangles).

**Empty conversation list:** Centered text in sidebar: "No conversations yet"

**Empty chat (no active conversation):** Center of ChatArea shows a welcome message:

- App icon or name
- "Upload a document and start asking questions"
- Optional: quick action buttons ("Upload a file", "Start a chat")

**Message loading (waiting for AI response):** The placeholder assistant bubble with animated dots (three `<span>` with staggered `animation-delay`, bouncing via a CSS keyframe defined in `globals.css`).

---

## 18. Error Handling

- **API errors:** Display in-context. Auth errors below the form. Chat errors as a red-tinted assistant bubble. File upload errors as a toast or inline error in the modal.
- **Network errors:** Catch fetch failures, show "Network error — check your connection"
- **401 handling:** Centralized in `api.js` — auto-clears token and redirects. No component needs to handle this explicitly.

---

## 19. Toast Notifications

Create a minimal toast system for non-blocking feedback.

### `components/Toast.js` + context or simple state in layout

- Position: fixed, bottom-right, `z-50`
- Types: success (green left border), error (red left border), info (blue left border)
- Auto-dismiss after 4 seconds with fade-out transition
- Use for: "File uploaded successfully", "File processing complete", "Conversation deleted", upload errors

Alternatively, manage toasts via a simple array state in the chat page and pass `addToast` down. No need for a heavy toast library.

---

## 20. Dark Mode Specifics

Ensure every component respects dark mode with Tailwind's `dark:` variant:

| Element         | Light                       | Dark                              |
| --------------- | --------------------------- | --------------------------------- |
| Page background | `bg-white`                  | `dark:bg-gray-900`               |
| Sidebar         | `bg-gray-50`               | `dark:bg-gray-900`               |
| Cards/Modals    | `bg-white`                  | `dark:bg-gray-800`               |
| Input fields    | `bg-white border-gray-300` | `dark:bg-gray-700 dark:border-gray-600` |
| Text primary    | `text-gray-900`            | `dark:text-gray-100`             |
| Text secondary  | `text-gray-500`            | `dark:text-gray-400`             |
| Borders         | `border-gray-200`          | `dark:border-gray-700`           |
| Hover (sidebar) | `hover:bg-gray-100`        | `dark:hover:bg-gray-700`         |

---

## 21. Responsive Breakpoints

| Breakpoint    | Behavior                                                                                             |
| ------------- | ---------------------------------------------------------------------------------------------------- |
| `< md` (mobile) | Sidebar hidden, toggled via hamburger. Modal is full-screen. Chat input bar sticks to bottom.       |
| `>= md` (tablet+) | Sidebar visible, 280px wide. Modal is centered card (max-w-lg).                                  |
| `>= lg` (desktop) | Same as tablet but more generous spacing. Message max-width stays at 75%.                        |

---

## 22. Implementation Order

Build in this sequence — each step produces something testable:

1. **Project scaffolding** — Next.js init, Tailwind config, env vars, `globals.css`
2. **`lib/api.js`** — The API client. Test with `console.log` calls from a temp page.
3. **`lib/AuthContext.js`** + **`lib/ThemeContext.js`** + **`app/layout.js`** with `Providers`
4. **`components/AuthForm.js`** + **`app/page.js`** — Get login/register working end-to-end
5. **`app/chat/page.js`** skeleton — Auth guard, header, empty layout with sidebar + chat area placeholders
6. **`components/Sidebar.js`** — Conversation list, new chat, delete. Wire up API calls.
7. **`components/ChatArea.js`** + **`components/MessageBubble.js`** — Message display + send. Wire up query API.
8. **`components/SourceCard.js`** — Collapsible sources below assistant messages
9. **`components/FileUploadModal.js`** — Upload, polling, file list
10. **`components/ThemeToggle.js`** — Dark/light toggle
11. **Toast notifications** — Wire up to file upload completion and other events
12. **Mobile responsive pass** — Sidebar toggle, responsive adjustments
13. **Polish** — Transitions, hover states, edge cases, empty states

---

## 23. Key Implementation Notes

- **All components are client components** (`"use client"`) since they use hooks, localStorage, and browser APIs. The only server component is `app/layout.js` (which delegates to a client `Providers` wrapper).
- **No `useEffect` fetch in server components** — all data fetching is client-side via the api module.
- **Textarea auto-resize:** Set `textarea.style.height = "auto"` then `textarea.style.height = textarea.scrollHeight + "px"` on every `onChange`. Cap at ~4 lines (`max-h-32`).
- **Polling cleanup:** Always store interval IDs and clear them in `useEffect` cleanup functions or on modal close. Avoid memory leaks.
- **Conversation title:** The API may return a title field or you may use the first user message content (truncated to ~30 chars) as a display title.
- **No SSR issues:** Since localStorage is used, wrap any localStorage reads in `typeof window !== "undefined"` checks or read them only in `useEffect`.
