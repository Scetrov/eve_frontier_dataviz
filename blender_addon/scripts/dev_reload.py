import addon_utils

ADDON_NAME = "addon"  # directory name if installed manually; adjust if zipped


def reload_addon():
    for mod in list(addon_utils.modules()):
        if mod.__name__.endswith(ADDON_NAME):
            try:
                addon_utils.disable(mod.__name__, default_set=False)
            except (ImportError, RuntimeError, AttributeError):
                # Best-effort reload helper - ignore disable failures
                pass
            try:
                addon_utils.enable(mod.__name__, default_set=False)
            except (ImportError, RuntimeError, AttributeError) as e:
                print("Failed to reload:", e)
            break


if __name__ == "__main__":
    reload_addon()
