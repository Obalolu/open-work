"use client";

import * as React from "react";
import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Link from "@tiptap/extension-link";
import Highlight from "@tiptap/extension-highlight";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
import Typography from "@tiptap/extension-typography";
import CharacterCount from "@tiptap/extension-character-count";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableHeader } from "@tiptap/extension-table-header";
import { TableCell } from "@tiptap/extension-table-cell";
import { Subscript } from "@tiptap/extension-subscript";
import { Superscript } from "@tiptap/extension-superscript";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bold,
  Italic,
  Strikethrough,
  Code,
  Code2,
  List,
  ListOrdered,
  ListChecks,
  Quote,
  Heading1,
  Heading2,
  Heading3,
  Link as LinkIcon,
  Highlighter,
  Undo,
  Redo,
  Table as TableIcon,
  Pencil,
  Save,
  Loader2,
  Check,
  X,
  Subscript as SubIcon,
  Superscript as SupIcon,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/Tooltip";

export interface TipTapEditorProps {
  initialContent: string;
  editable?: boolean;
  placeholder?: string;
  className?: string;
  onSave?: (markdown: string) => Promise<void> | void;
  onCancel?: () => void;
  onStartEdit?: () => void;
  autosaveMs?: number;
}

const DEFAULT_PLACEHOLDER = "Start writing your chapter…";

function buildExtensions(placeholder: string) {
  return [
    StarterKit.configure({
      codeBlock: {
        HTMLAttributes: { class: "tiptap-codeblock" },
      },
    }),
    Placeholder.configure({ placeholder }),
    Link.configure({ openOnClick: false, autolink: true }),
    Highlight,
    TaskList,
    TaskItem.configure({ nested: true }),
    Typography,
    CharacterCount,
    Table.configure({ resizable: true }),
    TableRow,
    TableHeader,
    TableCell,
    Subscript,
    Superscript,
  ];
}

export function TipTapEditor({
  initialContent,
  editable = false,
  placeholder = DEFAULT_PLACEHOLDER,
  className,
  onSave,
  onCancel,
  onStartEdit,
  autosaveMs = 1500,
}: TipTapEditorProps) {
  const [saving, setSaving] = React.useState(false);
  const [savedAt, setSavedAt] = React.useState<Date | null>(null);
  const [dirty, setDirty] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const saveTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const extensions = React.useMemo(() => buildExtensions(placeholder), [placeholder]);

  const editor = useEditor({
    extensions,
    content: initialContent,
    editable: editable,
    immediatelyRender: false,
    onUpdate: () => {
      setDirty(true);
      setError(null);
      if (autosaveMs > 0 && onSave) {
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        saveTimerRef.current = setTimeout(handleSave, autosaveMs);
      }
    },
    editorProps: {
      attributes: {
        class: cn(
          "tiptap-editor prose prose-sm md:prose-base max-w-none focus:outline-none",
          "min-h-[400px]"
        ),
        "data-placeholder": placeholder,
      },
    },
  });

  const handleSave = React.useCallback(async () => {
    if (!editor || !onSave) return;
    setSaving(true);
    setError(null);
    try {
      const md = htmlToMarkdown(editor.getHTML());
      await onSave(md);
      setDirty(false);
      setSavedAt(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }, [editor, onSave]);

  // Keep the editor's editability in sync with the `editable` prop so an
  // external Edit / Cancel toggle actually flips the ProseMirror into
  // editable mode (or back to read-only).
  React.useEffect(() => {
    if (!editor) return;
    editor.setEditable(editable);
    if (editable) {
      requestAnimationFrame(() => editor.commands.focus("end"));
    }
  }, [editor, editable]);

  React.useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, []);

  const startEdit = () => {
    if (onStartEdit) {
      onStartEdit();
      return;
    }
    // No-op when the editor controls its own editability; the parent is
    // expected to flip the `editable` prop. Fall back to just focusing.
    requestAnimationFrame(() => editor?.commands.focus("end"));
  };

  const cancelEdit = () => {
    editor?.commands.setContent(initialContent);
    setDirty(false);
    setError(null);
    onCancel?.();
  };

  if (!editor) {
    return (
      <div className="flex items-center justify-center p-12 text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Loading editor…
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {editable ? (
        <div className="space-y-2">
          <Toolbar editor={editor} />
          <EditorContent editor={editor} className="tiptap-content" />
          <EditFooter
            editor={editor}
            saving={saving}
            dirty={dirty}
            savedAt={savedAt}
            error={error}
            onSave={handleSave}
            onCancel={cancelEdit}
          />
        </div>
      ) : (
        <div className="group relative">
          <EditorContent
            editor={editor}
            className="tiptap-content"
            aria-readonly
          />
          {onSave && (
            <Button
              size="sm"
              variant="outline"
              onClick={startEdit}
              className="absolute right-3 top-3 opacity-0 transition-opacity group-hover:opacity-100"
            >
              <Pencil />
              Edit
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

function Toolbar({ editor }: { editor: Editor }) {
  const groups: {
    label: string;
    items: {
      icon: React.ReactNode;
      label: string;
      isActive?: boolean;
      onClick: () => void;
      disabled?: boolean;
    }[];
  }[] = [
    {
      label: "Text",
      items: [
        {
          icon: <Bold className="h-3.5 w-3.5" />,
          label: "Bold",
          isActive: editor.isActive("bold"),
          onClick: () => editor.chain().focus().toggleBold().run(),
        },
        {
          icon: <Italic className="h-3.5 w-3.5" />,
          label: "Italic",
          isActive: editor.isActive("italic"),
          onClick: () => editor.chain().focus().toggleItalic().run(),
        },
        {
          icon: <Strikethrough className="h-3.5 w-3.5" />,
          label: "Strike",
          isActive: editor.isActive("strike"),
          onClick: () => editor.chain().focus().toggleStrike().run(),
        },
        {
          icon: <Code className="h-3.5 w-3.5" />,
          label: "Code",
          isActive: editor.isActive("code"),
          onClick: () => editor.chain().focus().toggleCode().run(),
        },
        {
          icon: <Highlighter className="h-3.5 w-3.5" />,
          label: "Highlight",
          isActive: editor.isActive("highlight"),
          onClick: () => editor.chain().focus().toggleHighlight().run(),
        },
      ],
    },
    {
      label: "Headings",
      items: [
        {
          icon: <Heading1 className="h-3.5 w-3.5" />,
          label: "Heading 1",
          isActive: editor.isActive("heading", { level: 1 }),
          onClick: () => editor.chain().focus().toggleHeading({ level: 1 }).run(),
        },
        {
          icon: <Heading2 className="h-3.5 w-3.5" />,
          label: "Heading 2",
          isActive: editor.isActive("heading", { level: 2 }),
          onClick: () => editor.chain().focus().toggleHeading({ level: 2 }).run(),
        },
        {
          icon: <Heading3 className="h-3.5 w-3.5" />,
          label: "Heading 3",
          isActive: editor.isActive("heading", { level: 3 }),
          onClick: () => editor.chain().focus().toggleHeading({ level: 3 }).run(),
        },
      ],
    },
    {
      label: "Lists",
      items: [
        {
          icon: <List className="h-3.5 w-3.5" />,
          label: "Bullet list",
          isActive: editor.isActive("bulletList"),
          onClick: () => editor.chain().focus().toggleBulletList().run(),
        },
        {
          icon: <ListOrdered className="h-3.5 w-3.5" />,
          label: "Ordered list",
          isActive: editor.isActive("orderedList"),
          onClick: () => editor.chain().focus().toggleOrderedList().run(),
        },
        {
          icon: <ListChecks className="h-3.5 w-3.5" />,
          label: "Task list",
          isActive: editor.isActive("taskList"),
          onClick: () => editor.chain().focus().toggleTaskList().run(),
        },
        {
          icon: <Quote className="h-3.5 w-3.5" />,
          label: "Quote",
          isActive: editor.isActive("blockquote"),
          onClick: () => editor.chain().focus().toggleBlockquote().run(),
        },
      ],
    },
    {
      label: "Insert",
      items: [
        {
          icon: <LinkIcon className="h-3.5 w-3.5" />,
          label: "Link",
          isActive: editor.isActive("link"),
          onClick: () => {
            const previous = editor.getAttributes("link").href as string | undefined;
            const url = window.prompt("URL", previous ?? "https://");
            if (url === null) return;
            if (url === "") {
              editor.chain().focus().extendMarkRange("link").unsetLink().run();
              return;
            }
            editor
              .chain()
              .focus()
              .extendMarkRange("link")
              .setLink({ href: url })
              .run();
          },
        },
        {
          icon: <SubIcon className="h-3.5 w-3.5" />,
          label: "Subscript",
          isActive: editor.isActive("subscript"),
          onClick: () => editor.chain().focus().toggleSubscript().run(),
        },
        {
          icon: <SupIcon className="h-3.5 w-3.5" />,
          label: "Superscript",
          isActive: editor.isActive("superscript"),
          onClick: () => editor.chain().focus().toggleSuperscript().run(),
        },
        {
          icon: <Code2 className="h-3.5 w-3.5" />,
          label: "Code block",
          isActive: editor.isActive("codeBlock"),
          onClick: () => editor.chain().focus().toggleCodeBlock().run(),
        },
        {
          icon: <TableIcon className="h-3.5 w-3.5" />,
          label: "Table",
          onClick: () =>
            editor
              .chain()
              .focus()
              .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
              .run(),
        },
      ],
    },
  ];

  return (
    <div className="sticky top-14 z-20 -mx-1 flex flex-wrap items-center gap-1 rounded-md border border-border bg-surface-elevated/95 px-2 py-1.5 backdrop-blur">
      {groups.map((g, gi) => (
        <div key={g.label} className="flex items-center gap-0.5">
          {gi > 0 && <div className="mx-1 h-5 w-px bg-border" />}
          {g.items.map((item) => (
            <Tooltip key={item.label}>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={item.onClick}
                  className={cn(
                    "inline-flex h-7 w-7 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                    item.isActive && "bg-muted text-foreground"
                  )}
                  aria-label={item.label}
                >
                  {item.icon}
                </button>
              </TooltipTrigger>
              <TooltipContent>{item.label}</TooltipContent>
            </Tooltip>
          ))}
        </div>
      ))}
      <div className="mx-1 h-5 w-px bg-border" />
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            className="inline-flex h-7 w-7 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
            aria-label="Undo"
          >
            <Undo className="h-3.5 w-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent>Undo</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            className="inline-flex h-7 w-7 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
            aria-label="Redo"
          >
            <Redo className="h-3.5 w-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent>Redo</TooltipContent>
      </Tooltip>
    </div>
  );
}

function EditFooter({
  editor,
  saving,
  dirty,
  savedAt,
  error,
  onSave,
  onCancel,
}: {
  editor: Editor;
  saving: boolean;
  dirty: boolean;
  savedAt: Date | null;
  error: string | null;
  onSave: () => void;
  onCancel: () => void;
}) {
  const chars = editor.storage.characterCount?.characters?.() ?? 0;
  const words = editor.storage.characterCount?.words?.() ?? 0;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-2 text-2xs text-muted-foreground">
      <div className="flex items-center gap-3">
        <span>{words.toLocaleString()} words</span>
        <span>{chars.toLocaleString()} chars</span>
        <AnimatePresence>
          {saving && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="inline-flex items-center gap-1 text-info"
            >
              <Loader2 className="h-3 w-3 animate-spin" />
              Saving…
            </motion.span>
          )}
          {!saving && dirty && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-warning"
            >
              Unsaved changes
            </motion.span>
          )}
          {!saving && !dirty && savedAt && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="inline-flex items-center gap-1 text-success"
            >
              <Check className="h-3 w-3" />
              Saved {timeAgo(savedAt)}
            </motion.span>
          )}
          {error && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-danger"
            >
              {error}
            </motion.span>
          )}
        </AnimatePresence>
      </div>
      <div className="flex items-center gap-1">
        <Button size="sm" variant="ghost" onClick={onCancel} disabled={saving}>
          <X />
          Cancel
        </Button>
        <Button size="sm" onClick={onSave} loading={saving} disabled={!dirty && !saving}>
          <Save />
          Save
        </Button>
      </div>
    </div>
  );
}

function timeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return date.toLocaleString();
}

export function htmlToMarkdown(html: string): string {
  if (typeof window === "undefined") return html;
  const container = document.createElement("div");
  container.innerHTML = html;

  function walk(node: Node, depth = 0): string {
    if (node.nodeType === Node.TEXT_NODE) {
      return (node.textContent || "").replace(/\s+/g, " ");
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return "";
    const el = node as HTMLElement;
    const tag = el.tagName.toLowerCase();
    const children = Array.from(el.childNodes).map((c) => walk(c, depth + 1)).join("");

    switch (tag) {
      case "h1":
        return `\n# ${children.trim()}\n\n`;
      case "h2":
        return `\n## ${children.trim()}\n\n`;
      case "h3":
        return `\n### ${children.trim()}\n\n`;
      case "h4":
        return `\n#### ${children.trim()}\n\n`;
      case "p":
        return `${children}\n\n`;
      case "br":
        return "\n";
      case "strong":
      case "b":
        return `**${children}**`;
      case "em":
      case "i":
        return `*${children}*`;
      case "u":
        return `<u>${children}</u>`;
      case "s":
      case "del":
      case "strike":
        return `~~${children}~~`;
      case "code":
        if (el.parentElement?.tagName.toLowerCase() === "pre") return children;
        return `\`${children}\``;
      case "pre":
        return `\n\`\`\`\n${el.textContent || ""}\n\`\`\`\n\n`;
      case "blockquote":
        return children
          .split("\n")
          .map((l) => (l ? `> ${l}` : ""))
          .join("\n");
      case "ul":
        return el.outerHTML.includes('data-type="taskList"')
          ? children
          : Array.from(el.children)
              .map((li) => `- ${(li.textContent || "").trim()}`)
              .join("\n") + "\n\n";
      case "ol":
        return (
          Array.from(el.children)
            .map((li, i) => `${i + 1}. ${(li.textContent || "").trim()}`)
            .join("\n") + "\n\n"
        );
      case "li":
        if (el.closest('ul[data-type="taskList"]')) {
          const checked =
            el.querySelector('input[type="checkbox"]')?.hasAttribute("checked") ?? false;
          return `- [${checked ? "x" : " "}] ${children.trim()}\n`;
        }
        return children;
      case "a": {
        const href = el.getAttribute("href") || "";
        return href ? `[${children}](${href})` : children;
      }
      case "mark":
        return `==${children}==`;
      case "table":
        return children + "\n\n";
      case "tr":
        return `| ${Array.from(el.children)
          .map((td) => (td.textContent || "").trim())
          .join(" | ")} |\n`;
      case "td":
      case "th":
        return children;
      case "sub":
        return `~${children}~`;
      case "sup":
        return `^${children}^`;
      case "hr":
        return "\n---\n\n";
      default:
        return children;
    }
  }

  let out = walk(container);
  out = out.replace(/\n{3,}/g, "\n\n");
  return out.trim();
}
