import json
import os
import importlib

class ActionMapper:
    def __init__(self, engine, controller, config_path='config.json'):
        self.engine = engine
        self.controller = controller
        self.config_path = config_path
        self.plugins = {}
        self.load_config()
        self.load_plugins()
        self._bind_events()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            # Default production config
            self.config = {
                "onPointHold": {"plugin": "core", "action": "move_mouse"},
                "onPinchStart": {"plugin": "core", "action": "click"},
                "onFistStart": {"plugin": "core", "action": "start_drag"},
                "onFistEnd": {"plugin": "core", "action": "end_drag"},
                "onPeaceHold": {"plugin": "core", "action": "scroll"},
                "onThumbsUpStart": {"plugin": "core", "action": "right_click"},
                "onSwipeLeft": {"plugin": "presentation", "action": "prev_slide"},
                "onSwipeRight": {"plugin": "presentation", "action": "next_slide"}
            }
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)

    def load_plugins(self):
        # In a real system, we'd loop through the plugins/ folder
        # For now, we mock the plugin loader
        self.plugins['core'] = self.controller
        
        # Example presentation plugin mock
        class PresentationPlugin:
            def __init__(self, ctrl): self.ctrl = ctrl
            def next_slide(self, data=None): self.ctrl.press_key('right')
            def prev_slide(self, data=None): self.ctrl.press_key('left')
            
        self.plugins['presentation'] = PresentationPlugin(self.controller)

    def _bind_events(self):
        for event, target in self.config.items():
            plugin_name = target.get('plugin')
            action_name = target.get('action')
            
            if plugin_name in self.plugins:
                plugin = self.plugins[plugin_name]
                if hasattr(plugin, action_name):
                    callback = getattr(plugin, action_name)
                    self.engine.subscribe(event, callback)
                    print(f"🔗 Bound {event} -> {plugin_name}.{action_name}")
