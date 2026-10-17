"""Scrollable container — sidebar با اسکرول چرخ‌ماوس پایدار."""
from __future__ import annotations

import sys
import tkinter as tk
from typing import Optional

import customtkinter as ctk

from app.ui.tokens import COLORS


def _resolve_tk_color(color) -> str:
    if isinstance(color, (tuple, list)) and len(color) >= 2:
        mode = ctk.get_appearance_mode().lower()
        return str(color[1] if mode == "dark" else color[0])
    if isinstance(color, (tuple, list)) and color:
        return str(color[0])
    return str(color)


def _theme_frame_bg() -> str:
    try:
        val = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        return _resolve_tk_color(val)
    except Exception:
        return _resolve_tk_color(COLORS.get("app_bg", "#f0f2f8"))


class FastScrollableFrame(tk.Frame):
    """Canvas scroll — چرخ ماوس با تشخیص محدوده هندسی (بدون unbind_all مخرب)."""

    _WHEEL_STEP = 3
    _instances: list["FastScrollableFrame"] = []
    _global_bound = False

    def __init__(
        self,
        master,
        *,
        fg_color: str = "transparent",
        scrollbar_width: int = 12,
    ) -> None:
        self._outer = ctk.CTkFrame(master, fg_color=fg_color)
        self._configure_after: Optional[str] = None
        self._last_scrollregion: str = ""
        self._bind_children_after: Optional[str] = None

        bg = _theme_frame_bg() if fg_color in ("transparent", "", None) else _resolve_tk_color(fg_color)

        self._canvas = tk.Canvas(
            self._outer,
            highlightthickness=0,
            bd=0,
            bg=bg,
            yscrollincrement=10,
        )
        self._scrollbar = ctk.CTkScrollbar(
            self._outer,
            orientation="vertical",
            command=self._canvas.yview,
            width=scrollbar_width,
            fg_color=COLORS["card_bg_soft"],
            button_color=COLORS["primary_start"],
            button_hover_color=COLORS["primary_hover"],
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        tk.Frame.__init__(self, self._canvas, bg=bg, highlightthickness=0)
        self._window_id = self._canvas.create_window((0, 0), window=self, anchor="nw")

        self._outer.grid_columnconfigure(0, weight=1)
        self._outer.grid_rowconfigure(0, weight=1)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._scrollbar.grid(row=0, column=1, sticky="ns")

        self.bind("<Configure>", self._schedule_scrollregion_update, add="+")
        self._canvas.bind("<Configure>", self._on_canvas_configure, add="+")

        # چرخ ماوس روی خود canvas و فریم محتوا
        self._bind_wheel(self._canvas)
        self._bind_wheel(self)

        FastScrollableFrame._instances.append(self)
        FastScrollableFrame._ensure_global_wheel(self._outer)

    @classmethod
    def _ensure_global_wheel(cls, root_widget) -> None:
        """یک bind_all سراسری — هر instance فقط وقتی موس روی خودش است اسکرول می‌کند."""
        if cls._global_bound:
            return
        cls._global_bound = True

        def _dispatch(event):
            for inst in list(cls._instances):
                try:
                    if not inst.winfo_exists():
                        continue
                    if inst._pointer_over_me():
                        inst._scroll_from_event(event)
                        return "break"
                except Exception:
                    continue

        root = root_widget.winfo_toplevel()
        root.bind_all("<MouseWheel>", _dispatch, add="+")
        if sys.platform != "win32":
            root.bind_all("<Button-4>", _dispatch, add="+")
            root.bind_all("<Button-5>", _dispatch, add="+")

    def _bind_wheel(self, widget) -> None:
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        if sys.platform != "win32":
            widget.bind("<Button-4>", self._on_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_mousewheel, add="+")

    def _schedule_bind_children(self) -> None:
        if self._bind_children_after:
            try:
                self.after_cancel(self._bind_children_after)
            except Exception:
                pass
        self._bind_children_after = self.after(50, self._bind_wheel_to_descendants)

    def _bind_wheel_to_descendants(self) -> None:
        self._bind_children_after = None
        try:
            self._walk_bind(self)
        except Exception:
            pass

    def _walk_bind(self, widget) -> None:
        self._bind_wheel(widget)
        for child in widget.winfo_children():
            self._walk_bind(child)

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfigure(self._window_id, width=event.width)

    def _schedule_scrollregion_update(self, event=None) -> None:
        if event is not None and event.widget is not self:
            return
        if self._configure_after:
            try:
                self.after_cancel(self._configure_after)
            except Exception:
                pass
        self._configure_after = self.after(80, self._update_scrollregion)
        self._schedule_bind_children()

    def _update_scrollregion(self) -> None:
        self._configure_after = None
        try:
            first, _ = self._canvas.yview()
            bbox = self._canvas.bbox("all")
            if not bbox:
                return
            region = " ".join(str(v) for v in bbox)
            if region == self._last_scrollregion:
                return
            self._last_scrollregion = region
            self._canvas.configure(scrollregion=bbox)
            self._canvas.yview_moveto(first)
        except Exception:
            pass

    def _pointer_over_me(self) -> bool:
        """تشخیص با مختصات هندسی — پایدارتر از پیمایش master برای CTk."""
        try:
            if not self._outer.winfo_ismapped():
                return False
            x, y = self._outer.winfo_pointerxy()
            ox = self._outer.winfo_rootx()
            oy = self._outer.winfo_rooty()
            ow = self._outer.winfo_width()
            oh = self._outer.winfo_height()
            return ox <= x < ox + ow and oy <= y < oy + oh
        except Exception:
            return False

    def _on_mousewheel(self, event) -> Optional[str]:
        if not self._pointer_over_me():
            return None
        return self._scroll_from_event(event)

    def _scroll_from_event(self, event) -> Optional[str]:
        try:
            first, last = self._canvas.yview()
            if first <= 0.0 and last >= 1.0:
                return None
        except Exception:
            return None

        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            direction = -1
        else:
            direction = 1
        self._canvas.yview_scroll(direction * self._WHEEL_STEP, "units")
        return "break"

    def pack(self, **kwargs):
        return self._outer.pack(**kwargs)

    def grid(self, **kwargs):
        return self._outer.grid(**kwargs)

    def pack_forget(self):
        return self._outer.pack_forget()

    def grid_forget(self):
        return self._outer.grid_forget()

    def grid_remove(self):
        return self._outer.grid_remove()

    def winfo_exists(self):
        return self._outer.winfo_exists()

    def destroy(self):
        try:
            FastScrollableFrame._instances = [
                i for i in FastScrollableFrame._instances if i is not self
            ]
        except Exception:
            pass
        try:
            self._outer.destroy()
        except Exception:
            pass
        try:
            tk.Frame.destroy(self)
        except Exception:
            pass
