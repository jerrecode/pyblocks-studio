from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scatter import Scatter, ScatterPlane
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from .catalog import CATEGORY_COLORS, Catalog
from .codegen import CodeGenerationError, PythonGenerator
from .model import BlockNode, BlockSpec, Workspace
from .runtime import ExecutionResult, PythonRuntime
from .storage import WorkspaceStore


BACKGROUND = (0.035, 0.047, 0.075, 1)
PANEL = (0.075, 0.094, 0.14, 1)
PANEL_LIGHT = (0.105, 0.13, 0.19, 1)
TEXT = (0.92, 0.94, 0.98, 1)
MUTED = (0.62, 0.68, 0.78, 1)
ACCENT = (0.37, 0.52, 0.96, 1)
DANGER = (0.9, 0.24, 0.31, 1)


def rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        return (*ACCENT[:3], alpha)
    return (
        int(value[0:2], 16) / 255,
        int(value[2:4], 16) / 255,
        int(value[4:6], 16) / 255,
        alpha,
    )


def button(text: str, callback: Callable[..., Any], *, width: float | None = None) -> Button:
    widget = Button(
        text=text,
        size_hint=(None, 1) if width else (1, 1),
        width=dp(width or 100),
        background_normal="",
        background_down="",
        background_color=PANEL_LIGHT,
        color=TEXT,
        font_size=sp(14),
    )
    widget.bind(on_release=callback)
    return widget


class ColorPanel(BoxLayout):
    panel_color = ListProperty(PANEL)
    radius = NumericProperty(dp(12))

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color_instruction = Color(*self.panel_color)
            self._background = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        self.bind(pos=self._sync_canvas, size=self._sync_canvas, panel_color=self._sync_color, radius=self._sync_canvas)

    def _sync_canvas(self, *_: Any) -> None:
        self._background.pos = self.pos
        self._background.size = self.size
        self._background.radius = [self.radius]

    def _sync_color(self, *_: Any) -> None:
        self._color_instruction.rgba = self.panel_color


class BlockCard(Scatter):
    node_id = StringProperty("")
    selected = BooleanProperty(False)
    controller = ObjectProperty(None, allownone=True)

    def __init__(self, node: BlockNode, spec: BlockSpec, controller: "EditorScreen", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.node_id = node.id
        self.controller = controller
        self.spec = spec
        self.do_rotation = False
        self.do_scale = False
        self.do_translation = True
        self.auto_bring_to_front = True
        self.size_hint = (None, None)
        self.width = dp(300)
        self.pos = (node.x, node.y)

        field_height = dp(42) * len(spec.fields)
        self.height = dp(58) + field_height + (dp(18) if spec.has_body else 0)

        root = ColorPanel(
            orientation="vertical",
            padding=(dp(10), dp(8)),
            spacing=dp(6),
            size_hint=(None, None),
            size=self.size,
            panel_color=rgba(spec.color, 0.96),
            radius=dp(14),
        )
        root.bind(size=lambda _instance, value: setattr(self, "size", value))
        self.add_widget(root)

        title = Label(
            text=spec.label,
            color=(1, 1, 1, 1),
            bold=True,
            font_size=sp(15),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(36),
        )
        title.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        root.add_widget(title)

        self.inputs: dict[str, TextInput] = {}
        for field_spec in spec.fields:
            row = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint_y=None, height=dp(38))
            field_label = Label(
                text=field_spec.name,
                color=(1, 1, 1, 0.82),
                font_size=sp(12),
                size_hint_x=0.32,
                halign="right",
                valign="middle",
            )
            field_label.bind(size=lambda instance, value: setattr(instance, "text_size", value))
            editor = TextInput(
                text=node.fields.get(field_spec.name, field_spec.default),
                multiline=False,
                write_tab=False,
                font_size=sp(13),
                foreground_color=TEXT,
                background_normal="",
                background_active="",
                background_color=(0.04, 0.05, 0.08, 0.64),
                padding=(dp(8), dp(8)),
                hint_text=field_spec.placeholder,
                hint_text_color=(1, 1, 1, 0.45),
            )
            editor.bind(text=self._field_callback(field_spec.name))
            self.inputs[field_spec.name] = editor
            row.add_widget(field_label)
            row.add_widget(editor)
            root.add_widget(row)

        if spec.has_body:
            body_hint = Label(
                text="↳ drop statements here",
                color=(1, 1, 1, 0.7),
                font_size=sp(11),
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=dp(18),
            )
            body_hint.bind(size=lambda instance, value: setattr(instance, "text_size", value))
            root.add_widget(body_hint)

        with self.canvas.after:
            self._selection_color = Color(1, 1, 1, 0)
            self._selection_line = Line(rounded_rectangle=(*self.pos, *self.size, dp(14)), width=dp(2))
        self.bind(pos=self._sync_outline, size=self._sync_outline, selected=self._sync_selection)

    def _field_callback(self, name: str):
        def update(_instance: TextInput, text: str) -> None:
            if self.controller:
                self.controller.update_field(self.node_id, name, text)
        return update

    def _sync_outline(self, *_: Any) -> None:
        self._selection_line.rounded_rectangle = (*self.pos, *self.size, dp(14))

    def _sync_selection(self, *_: Any) -> None:
        self._selection_color.rgba = (1, 1, 1, 0.96 if self.selected else 0)

    def on_touch_down(self, touch: Any) -> bool:
        if self.collide_point(*touch.pos) and self.controller:
            self.controller.select(self.node_id)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch: Any) -> bool:
        handled = super().on_touch_up(touch)
        if self.controller and touch.grab_current is None:
            self.controller.card_released(self)
        return handled


class PalettePanel(ColorPanel):
    def __init__(self, editor: "EditorScreen", **kwargs: Any) -> None:
        super().__init__(orientation="vertical", spacing=dp(8), padding=dp(10), **kwargs)
        self.editor = editor
        self.size_hint_x = None
        self.width = dp(320)
        self.panel_color = PANEL
        self.radius = 0

        heading = Label(
            text="BLOCKS",
            color=MUTED,
            bold=True,
            font_size=sp(12),
            size_hint_y=None,
            height=dp(28),
            halign="left",
            valign="middle",
        )
        heading.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        self.add_widget(heading)

        self.search_input = TextInput(
            hint_text="Search Python blocks",
            multiline=False,
            size_hint_y=None,
            height=dp(44),
            foreground_color=TEXT,
            hint_text_color=MUTED,
            background_normal="",
            background_active="",
            background_color=PANEL_LIGHT,
            padding=(dp(10), dp(11)),
        )
        self.search_input.bind(text=lambda *_: self.refresh())
        self.add_widget(self.search_input)

        self.category = Spinner(
            text="All",
            values=("All", *editor.app.catalog.categories()),
            size_hint_y=None,
            height=dp(42),
            background_normal="",
            background_color=PANEL_LIGHT,
            color=TEXT,
        )
        self.category.bind(text=lambda *_: self.refresh())
        self.add_widget(self.category)

        scroll = ScrollView(do_scroll_x=False)
        self.list_layout = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            padding=(0, 0, dp(4), dp(8)),
            size_hint_y=None,
        )
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        scroll.add_widget(self.list_layout)
        self.add_widget(scroll)
        self.refresh()

    def refresh(self) -> None:
        if not hasattr(self, "list_layout"):
            return
        self.list_layout.clear_widgets()
        specs = self.editor.app.catalog.search(self.search_input.text, self.category.text)
        for spec in specs:
            widget = Button(
                text=f"[b]{spec.label}[/b]\n[size=11]{spec.category}[/size]",
                markup=True,
                size_hint_y=None,
                height=dp(58),
                halign="left",
                valign="middle",
                text_size=(dp(268), None),
                background_normal="",
                background_down="",
                background_color=rgba(spec.color, 0.9),
                color=(1, 1, 1, 1),
                padding=(dp(12), dp(7)),
            )
            widget.bind(on_release=lambda _button, block_spec=spec: self.editor.add_spec(block_spec))
            self.list_layout.add_widget(widget)


class EditorScreen(Screen):
    def __init__(self, app: "PyBlocksApp", **kwargs: Any) -> None:
        super().__init__(name="editor", **kwargs)
        self.app = app
        self.cards: dict[str, BlockCard] = {}
        self.selected_id: str | None = None
        self._field_event = None

        root = BoxLayout(orientation="horizontal")
        self.palette = PalettePanel(self)
        root.add_widget(self.palette)

        self.plane = ScatterPlane(
            do_rotation=False,
            do_scale=True,
            do_translation=True,
            scale_min=0.35,
            scale_max=2.4,
        )
        self.plane.size_hint = (1, 1)
        with self.plane.canvas.before:
            Color(*BACKGROUND)
            self._plane_background = RoundedRectangle(pos=self.plane.pos, size=self.plane.size)
            Color(0.12, 0.15, 0.22, 0.35)
            self._grid = Line(points=[], width=1)
        self.plane.bind(pos=self._update_plane_canvas, size=self._update_plane_canvas)
        root.add_widget(self.plane)
        self.add_widget(root)
        Clock.schedule_once(lambda *_: self.rebuild(), 0)

    def _update_plane_canvas(self, *_: Any) -> None:
        self._plane_background.pos = self.plane.pos
        self._plane_background.size = self.plane.size
        points: list[float] = []
        step = dp(48)
        width, height = max(self.plane.width, dp(1200)), max(self.plane.height, dp(800))
        x = 0.0
        while x <= width:
            points.extend((x, 0, x, height))
            x += step
        y = 0.0
        while y <= height:
            points.extend((0, y, width, y))
            y += step
        self._grid.points = points

    def rebuild(self) -> None:
        self.plane.clear_widgets()
        self.cards.clear()
        for node in self.app.workspace.nodes.values():
            try:
                spec = self.app.catalog.get(node.spec_id)
            except KeyError:
                continue
            card = BlockCard(node, spec, self)
            self.cards[node.id] = card
            self.plane.add_widget(card)
        self._layout_connected_nodes()
        self.select(self.selected_id)

    def add_spec(self, spec: BlockSpec) -> None:
        index = len(self.app.workspace.nodes)
        node = self.app.workspace.add(spec, x=dp(360 + (index % 4) * 28), y=dp(620 - (index % 8) * 58))
        self.app.record_history()
        card = BlockCard(node, spec, self)
        self.cards[node.id] = card
        self.plane.add_widget(card)
        self.select(node.id)
        self.app.update_generated_views()

    def select(self, node_id: str | None) -> None:
        self.selected_id = node_id if node_id in self.cards else None
        for card_id, card in self.cards.items():
            card.selected = card_id == self.selected_id
        self.app.selected_node_id = self.selected_id

    def update_field(self, node_id: str, name: str, value: str) -> None:
        node = self.app.workspace.nodes.get(node_id)
        if not node:
            return
        node.fields[name] = value
        if self._field_event:
            self._field_event.cancel()
        self._field_event = Clock.schedule_once(lambda *_: self._commit_field_change(), 0.35)

    def _commit_field_change(self) -> None:
        self.app.record_history(coalesce=True)
        self.app.update_generated_views()

    def card_released(self, card: BlockCard) -> None:
        node = self.app.workspace.nodes.get(card.node_id)
        if not node:
            return
        node.x, node.y = card.pos
        candidate = self._nearest_snap(card)
        if candidate:
            mode, parent_id = candidate
            try:
                if mode == "body":
                    self.app.workspace.connect_body(parent_id, card.node_id)
                else:
                    self.app.workspace.connect_next(parent_id, card.node_id)
                self._layout_connected_nodes()
            except (ValueError, KeyError) as exc:
                self.app.notify(str(exc))
        self.app.record_history()
        self.app.update_generated_views()

    def _nearest_snap(self, card: BlockCard) -> tuple[str, str] | None:
        threshold = dp(84)
        best: tuple[float, str, str] | None = None
        for other_id, other in self.cards.items():
            if other_id == card.node_id:
                continue
            target_node = self.app.workspace.nodes[other_id]
            target_spec = self.app.catalog.get(target_node.spec_id)
            next_point = (other.x, other.y - card.height - dp(12))
            next_distance = ((card.x - next_point[0]) ** 2 + (card.y - next_point[1]) ** 2) ** 0.5
            if next_distance < threshold and (best is None or next_distance < best[0]):
                best = (next_distance, "next", other_id)
            if target_spec.has_body:
                body_point = (other.x + dp(34), other.y - card.height - dp(18))
                body_distance = ((card.x - body_point[0]) ** 2 + (card.y - body_point[1]) ** 2) ** 0.5
                if body_distance < threshold and (best is None or body_distance < best[0]):
                    best = (body_distance, "body", other_id)
        return None if best is None else (best[1], best[2])

    def _layout_connected_nodes(self) -> None:
        visited: set[str] = set()

        def place_chain(node_id: str, x: float, y: float, depth: int = 0) -> float:
            current_id: str | None = node_id
            cursor_y = y
            while current_id and current_id not in visited:
                visited.add(current_id)
                card = self.cards.get(current_id)
                node = self.app.workspace.nodes[current_id]
                if not card:
                    break
                card.pos = (x + depth * dp(34), cursor_y)
                node.x, node.y = card.pos
                body_y = cursor_y - card.height - dp(18)
                for child_id in node.body_ids:
                    body_y = place_chain(child_id, x, body_y, depth + 1) - dp(12)
                cursor_y = min(cursor_y - card.height - dp(14), body_y)
                current_id = node.next_id
            return cursor_y

        for root_id in self.app.workspace.ordered_roots():
            node = self.app.workspace.nodes[root_id]
            place_chain(root_id, node.x, node.y)

    def delete_selected(self) -> None:
        if not self.selected_id:
            return
        self.app.workspace.remove(self.selected_id)
        self.select(None)
        self.rebuild()
        self.app.record_history()
        self.app.update_generated_views()

    def detach_selected(self) -> None:
        if not self.selected_id:
            return
        self.app.workspace.detach(self.selected_id)
        self.app.record_history()
        self.app.update_generated_views()
        self._layout_connected_nodes()


class SourceScreen(Screen):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(name="source", **kwargs)
        self.editor = TextInput(
            readonly=True,
            multiline=True,
            font_name="RobotoMono",
            font_size=sp(15),
            foreground_color=(0.86, 0.91, 1, 1),
            background_normal="",
            background_active="",
            background_color=BACKGROUND,
            padding=(dp(18), dp(18)),
        )
        self.add_widget(self.editor)


class RuntimeScreen(Screen):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(name="runtime", **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        self.status = Label(text="Program has not run yet.", color=MUTED, size_hint_y=None, height=dp(36), halign="left")
        self.status.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        root.add_widget(self.status)
        self.output = TextInput(
            readonly=True,
            multiline=True,
            font_name="RobotoMono",
            font_size=sp(14),
            foreground_color=TEXT,
            background_normal="",
            background_active="",
            background_color=BACKGROUND,
            padding=(dp(16), dp(16)),
        )
        root.add_widget(self.output)
        self.add_widget(root)


class ModulesScreen(Screen):
    def __init__(self, app: "PyBlocksApp", **kwargs: Any) -> None:
        super().__init__(name="modules", **kwargs)
        self.app = app
        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        controls = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.module_input = TextInput(
            text="math",
            hint_text="Importable module name",
            multiline=False,
            foreground_color=TEXT,
            background_normal="",
            background_active="",
            background_color=PANEL_LIGHT,
            padding=(dp(10), dp(11)),
        )
        controls.add_widget(self.module_input)
        controls.add_widget(button("Discover", self.discover, width=118))
        controls.add_widget(button("Export specs", self.export_specs, width=130))
        root.add_widget(controls)
        self.status = Label(
            text="Discover functions, classes, and attributes from modules packaged with the app.",
            color=MUTED,
            size_hint_y=None,
            height=dp(40),
            halign="left",
            valign="middle",
        )
        self.status.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        root.add_widget(self.status)
        self.output = TextInput(
            readonly=True,
            multiline=True,
            font_name="RobotoMono",
            font_size=sp(13),
            foreground_color=TEXT,
            background_normal="",
            background_active="",
            background_color=BACKGROUND,
            padding=(dp(14), dp(14)),
        )
        root.add_widget(self.output)
        self.add_widget(root)

    def discover(self, *_: Any) -> None:
        name = self.module_input.text.strip()
        if not name:
            self.app.notify("Enter a module name")
            return
        self.status.text = f"Inspecting {name}…"

        def worker() -> None:
            try:
                specs = self.app.catalog.discover_module(name)
                message = "\n".join(f"{item.label}\n  {item.description}" for item in specs)
                Clock.schedule_once(lambda *_: self._discovery_done(name, specs, message), 0)
            except BaseException as exc:
                Clock.schedule_once(lambda *_: self._discovery_failed(name, str(exc)), 0)

        threading.Thread(target=worker, name="pyblocks-module-discovery", daemon=True).start()

    def _discovery_done(self, name: str, specs: list[BlockSpec], message: str) -> None:
        self.status.text = f"Discovered {len(specs)} public members from {name}."
        self.output.text = message or "No public members found."
        editor = self.app.editor_screen
        editor.palette.category.values = ("All", *self.app.catalog.categories())
        editor.palette.category.text = "Modules"
        editor.palette.refresh()

    def _discovery_failed(self, name: str, message: str) -> None:
        self.status.text = f"Could not inspect {name}."
        self.output.text = message

    def export_specs(self, *_: Any) -> None:
        path = self.app.store.export_descriptor(self.module_input.text or "catalog", self.app.catalog.to_dict())
        self.app.notify(f"Block descriptors exported to {path}")


class PyBlocksRoot(BoxLayout):
    def __init__(self, app: "PyBlocksApp", **kwargs: Any) -> None:
        super().__init__(orientation="vertical", **kwargs)
        self.app = app
        toolbar = ColorPanel(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(58),
            padding=(dp(10), dp(7)),
            spacing=dp(7),
            panel_color=PANEL,
            radius=0,
        )
        title = Label(
            text="[b]PyBlocks Studio[/b]  [color=94a3b8]Android[/color]",
            markup=True,
            color=TEXT,
            size_hint_x=None,
            width=dp(220),
            halign="left",
            valign="middle",
        )
        title.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        toolbar.add_widget(title)
        for label, screen_name in (("Blocks", "editor"), ("Code", "source"), ("Output", "runtime"), ("Modules", "modules")):
            toolbar.add_widget(button(label, lambda _button, target=screen_name: app.show_screen(target), width=82))
        toolbar.add_widget(Label())
        toolbar.add_widget(button("Undo", lambda *_: app.undo(), width=68))
        toolbar.add_widget(button("Redo", lambda *_: app.redo(), width=68))
        toolbar.add_widget(button("Detach", lambda *_: app.editor_screen.detach_selected(), width=78))
        delete = button("Delete", lambda *_: app.editor_screen.delete_selected(), width=72)
        delete.background_color = DANGER
        toolbar.add_widget(delete)
        toolbar.add_widget(button("Save", lambda *_: app.save_workspace(), width=68))
        toolbar.add_widget(button("Load", lambda *_: app.open_load_popup(), width=68))
        toolbar.add_widget(button("Export", lambda *_: app.export_python(), width=74))
        run = button("Run ▶", lambda *_: app.run_program(), width=84)
        run.background_color = ACCENT
        toolbar.add_widget(run)
        self.add_widget(toolbar)

        app.screen_manager = ScreenManager(transition=NoTransition())
        app.editor_screen = EditorScreen(app)
        app.source_screen = SourceScreen()
        app.runtime_screen = RuntimeScreen()
        app.modules_screen = ModulesScreen(app)
        app.screen_manager.add_widget(app.editor_screen)
        app.screen_manager.add_widget(app.source_screen)
        app.screen_manager.add_widget(app.runtime_screen)
        app.screen_manager.add_widget(app.modules_screen)
        self.add_widget(app.screen_manager)

        app.status_bar = Label(
            text="Ready",
            color=MUTED,
            size_hint_y=None,
            height=dp(28),
            padding=(dp(10), 0),
            halign="left",
            valign="middle",
        )
        app.status_bar.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        self.add_widget(app.status_bar)


class PyBlocksApp(App):
    title = "PyBlocks Studio"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.catalog = Catalog()
        self.workspace = Workspace(name="starter")
        self.generator = PythonGenerator(self.catalog)
        self.runtime = PythonRuntime()
        self.store: WorkspaceStore
        self.screen_manager: ScreenManager
        self.editor_screen: EditorScreen
        self.source_screen: SourceScreen
        self.runtime_screen: RuntimeScreen
        self.modules_screen: ModulesScreen
        self.status_bar: Label
        self.selected_node_id: str | None = None
        self._history: list[dict[str, Any]] = []
        self._history_index = -1
        self._coalesce_pending = False

    def build(self) -> PyBlocksRoot:
        Window.clearcolor = BACKGROUND
        self.store = WorkspaceStore(self.user_data_dir)
        self._load_or_seed()
        root = PyBlocksRoot(self)
        Clock.schedule_once(lambda *_: self._after_build(), 0)
        return root

    def _after_build(self) -> None:
        self._history = [deepcopy(self.workspace.to_dict())]
        self._history_index = 0
        self.update_generated_views()
        self.notify(f"Workspace data: {self.user_data_dir}")

    def _load_or_seed(self) -> None:
        try:
            if "autosave" in self.store.list_names():
                self.workspace = self.store.load("autosave")
                return
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        self.workspace = self._starter_workspace()

    def _starter_workspace(self) -> Workspace:
        workspace = Workspace(name="autosave")
        import_node = workspace.add(self.catalog.get("import"), x=dp(380), y=dp(650))
        import_node.fields["module"] = "math"
        function = workspace.add(self.catalog.get("function"), x=dp(380), y=dp(560))
        function.fields.update({"name": "circle_area", "parameters": "radius: float"})
        assignment = workspace.add(self.catalog.get("assign"), x=dp(414), y=dp(470))
        assignment.fields.update({"target": "area", "value": "math.pi * radius ** 2"})
        returned = workspace.add(self.catalog.get("return"), x=dp(414), y=dp(390))
        returned.fields["value"] = "area"
        call = workspace.add(self.catalog.get("print"), x=dp(380), y=dp(290))
        call.fields["value"] = "circle_area(3)"
        workspace.connect_body(function.id, assignment.id)
        workspace.connect_next(assignment.id, returned.id)
        workspace.connect_next(import_node.id, function.id)
        workspace.connect_next(function.id, call.id)
        return workspace

    def show_screen(self, name: str) -> None:
        self.screen_manager.current = name
        if name == "source":
            self.update_generated_views()

    def update_generated_views(self) -> None:
        try:
            program = self.generator.generate(self.workspace)
            self.source_screen.editor.text = program.source
        except CodeGenerationError as exc:
            self.source_screen.editor.text = f"# Code generation error\n# {exc}\n"
        self._autosave_debounced()

    def _autosave_debounced(self) -> None:
        Clock.unschedule(self._autosave)
        Clock.schedule_once(self._autosave, 0.6)

    def _autosave(self, *_: Any) -> None:
        try:
            self.workspace.name = "autosave"
            self.store.save(self.workspace)
        except (OSError, ValueError) as exc:
            self.notify(f"Autosave failed: {exc}")

    def record_history(self, *, coalesce: bool = False) -> None:
        state = deepcopy(self.workspace.to_dict())
        if self._history_index >= 0 and self._history[self._history_index] == state:
            return
        if coalesce and self._coalesce_pending and self._history_index >= 0:
            self._history[self._history_index] = state
        else:
            self._history = self._history[: self._history_index + 1]
            self._history.append(state)
            self._history_index = len(self._history) - 1
        self._coalesce_pending = coalesce
        if len(self._history) > 80:
            overflow = len(self._history) - 80
            self._history = self._history[overflow:]
            self._history_index -= overflow

    def undo(self) -> None:
        if self._history_index <= 0:
            self.notify("Nothing to undo")
            return
        self._history_index -= 1
        self._restore_history()

    def redo(self) -> None:
        if self._history_index >= len(self._history) - 1:
            self.notify("Nothing to redo")
            return
        self._history_index += 1
        self._restore_history()

    def _restore_history(self) -> None:
        self.workspace = Workspace.from_dict(deepcopy(self._history[self._history_index]))
        self._coalesce_pending = False
        self.editor_screen.rebuild()
        self.update_generated_views()

    def save_workspace(self) -> None:
        path = self.store.save(self.workspace)
        self.notify(f"Saved {path}")

    def export_python(self) -> None:
        try:
            program = self.generator.generate(self.workspace)
        except CodeGenerationError as exc:
            self.notify(str(exc))
            return
        path = self.store.export_python(self.workspace, program.source)
        self.notify(f"Exported Python to {path}")

    def open_load_popup(self) -> None:
        names = self.store.list_names()
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        popup = Popup(title="Load workspace", content=content, size_hint=(0.7, 0.75))
        scroll = ScrollView()
        choices = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        choices.bind(minimum_height=choices.setter("height"))
        for name in names:
            choice = Button(text=name, size_hint_y=None, height=dp(48), background_normal="", background_color=PANEL_LIGHT, color=TEXT)
            choice.bind(on_release=lambda _button, selected=name: self._load_workspace(selected, popup))
            choices.add_widget(choice)
        scroll.add_widget(choices)
        content.add_widget(scroll)
        content.add_widget(button("Close", lambda *_: popup.dismiss()))
        popup.open()

    def _load_workspace(self, name: str, popup: Popup) -> None:
        try:
            self.workspace = self.store.load(name)
            self.workspace.name = "autosave"
            self._history = [deepcopy(self.workspace.to_dict())]
            self._history_index = 0
            self.editor_screen.rebuild()
            self.update_generated_views()
            popup.dismiss()
            self.notify(f"Loaded {name}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.notify(f"Could not load {name}: {exc}")

    def run_program(self) -> None:
        try:
            program = self.generator.generate(self.workspace)
        except CodeGenerationError as exc:
            self.notify(str(exc))
            return
        self.runtime_screen.status.text = "Running generated Python…"
        self.runtime_screen.output.text = ""
        self.show_screen("runtime")

        def finished(result: ExecutionResult) -> None:
            Clock.schedule_once(lambda *_: self._show_execution_result(result), 0)

        self.runtime.execute_async(program.source, finished, timeout=8.0)

    def _show_execution_result(self, result: ExecutionResult) -> None:
        status = "success" if result.successful else "failed"
        self.runtime_screen.status.text = f"Execution {status} in {result.duration_seconds:.3f} seconds."
        sections = []
        if result.stdout:
            sections.append("STDOUT\n" + result.stdout)
        if result.stderr:
            sections.append("STDERR\n" + result.stderr)
        if result.traceback:
            sections.append("TRACEBACK\n" + result.traceback)
        self.runtime_screen.output.text = "\n\n".join(sections) or "Program completed without output."

    def notify(self, message: str) -> None:
        if hasattr(self, "status_bar"):
            self.status_bar.text = message
            Clock.unschedule(self._clear_notification)
            Clock.schedule_once(self._clear_notification, 6.0)

    def _clear_notification(self, *_: Any) -> None:
        self.status_bar.text = "Ready"

    def on_pause(self) -> bool:
        self._autosave()
        return True

    def on_stop(self) -> None:
        self._autosave()
