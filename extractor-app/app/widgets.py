"""ویجت‌های مشترک — منوی راست‌کلیک و میانبرهای استاندارد."""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from app.theme import font


def _tk_entry(widget: ctk.CTkEntry) -> tk.Entry:
    return widget._entry


def _tk_textbox(widget: ctk.CTkTextbox) -> tk.Text:
    return widget._textbox


def enable_entry_shortcuts(entry: ctk.CTkEntry, *, readonly: bool = False) -> None:
    """Ctrl+C/V/X/A، Shift+Insert و منوی راست‌کلیک فارسی."""
    w = _tk_entry(entry)
    if readonly:
        w.configure(state="readonly")

    menu = tk.Menu(w, tearoff=0, font=font(11))

    def _cut() -> None:
        if not readonly:
            w.event_generate("<<Cut>>")

    def _copy() -> None:
        try:
            w.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    def _paste() -> None:
        if not readonly:
            w.event_generate("<<Paste>>")

    def _select_all() -> None:
        w.select_range(0, "end")
        w.icursor("end")

    menu.add_command(label="برش  Ctrl+X", command=_cut, state="disabled" if readonly else "normal")
    menu.add_command(label="کپی  Ctrl+C", command=_copy)
    menu.add_command(label="چسباندن  Ctrl+V", command=_paste, state="disabled" if readonly else "normal")
    menu.add_separator()
    menu.add_command(label="انتخاب همه  Ctrl+A", command=_select_all)

    def _popup(event) -> str:
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    w.bind("<Button-3>", _popup)
    w.bind("<Control-c>", lambda _e: (_copy(), "break")[1])
    w.bind("<Control-C>", lambda _e: (_copy(), "break")[1])
    if not readonly:
        w.bind("<Control-v>", lambda _e: (_paste(), "break")[1])
        w.bind("<Control-V>", lambda _e: (_paste(), "break")[1])
        w.bind("<Control-x>", lambda _e: (_cut(), "break")[1])
        w.bind("<Control-X>", lambda _e: (_cut(), "break")[1])
        w.bind("<Shift-Insert>", lambda _e: (_paste(), "break")[1])
    w.bind("<Control-a>", lambda _e: (_select_all(), "break")[1])
    w.bind("<Control-A>", lambda _e: (_select_all(), "break")[1])


def enable_textbox_shortcuts(textbox: ctk.CTkTextbox, *, allow_edit: bool = True) -> None:
    w = _tk_textbox(textbox)
    menu = tk.Menu(w, tearoff=0, font=font(11))

    def _cut() -> None:
        if allow_edit and str(textbox.cget("state")) != "disabled":
            w.event_generate("<<Cut>>")

    def _copy() -> None:
        try:
            w.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    def _paste() -> None:
        if allow_edit and str(textbox.cget("state")) != "disabled":
            w.event_generate("<<Paste>>")

    def _select_all() -> None:
        w.tag_add("sel", "1.0", "end")

    menu.add_command(label="برش  Ctrl+X", command=_cut)
    menu.add_command(label="کپی  Ctrl+C", command=_copy)
    menu.add_command(label="چسباندن  Ctrl+V", command=_paste)
    menu.add_separator()
    menu.add_command(label="انتخاب همه  Ctrl+A", command=_select_all)

    def _popup(event) -> str:
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    w.bind("<Button-3>", _popup)
    w.bind("<Control-c>", lambda _e: (_copy(), "break")[1])
    w.bind("<Control-C>", lambda _e: (_copy(), "break")[1])
    w.bind("<Control-v>", lambda _e: (_paste(), "break")[1])
    w.bind("<Control-V>", lambda _e: (_paste(), "break")[1])
    w.bind("<Control-a>", lambda _e: (_select_all(), "break")[1])
    w.bind("<Control-A>", lambda _e: (_select_all(), "break")[1])


def set_readonly_entry_value(entry: ctk.CTkEntry, value: str) -> None:
    w = _tk_entry(entry)
    prev = w.cget("state")
    w.configure(state="normal")
    entry.delete(0, "end")
    entry.insert(0, value)
    w.configure(state="readonly")
